# Databricks notebook source
# Ingestão de Cards - Magic: The Gathering (Bulk Data)
# Objetivo: Ingerir dados de cards via Scryfall Bulk Data API para staging em Parquet no S3
# Características: Dados brutos, formato Parquet, filtro temporal, particionamento, incremental, por coleção (set)

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import json
import gzip
import requests
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, BooleanType

# COMMAND ----------

# MAGIC %run ./ingestion_utils

# COMMAND ----------

# =============================================================================
# VARIÁVEIS DE CONFIGURAÇÃO
# =============================================================================
# api_base_url/MAX_RETRIES seguem usados só pra get_filtered_set_codes (1
# request rápido contra /sets, não por carta/coleção - não é o gargalo).
API_BASE_URL = get_secret("api_base_url")
MAX_RETRIES = int(get_secret("max_retries", "3"))

# issue #123: troca a paginação coleção-por-coleção contra magicthegathering.io
# (1 request por página + sleep(0.5), ~8,6min pra 153 coleções - #121 já fez
# essa troca pro card_prices) por 1 download do catálogo inteiro da Scryfall,
# filtrado em memória pelos set_codes da janela temporal.
SCRYFALL_API_URL = get_secret("scryfall_api_url")
SCRYFALL_HEADERS = {"User-Agent": "MTGPipeline/1.0"}
# default_cards = 1 objeto por impressão (não por Oracle ID) - cards.ipynb
# grava 1 linha por impressão (set/artist/number/imageUrl variam por edição),
# granularidade que oracle_cards (usado no card_prices) não tem.
SCRYFALL_BULK_TYPE = "default_cards"

# Configurações do S3
S3_BUCKET = get_secret("s3_bucket")
S3_STAGE_PREFIX = get_secret("s3_stage_prefix", "stage")
S3_BASE_PATH = f"s3://{S3_BUCKET}/{S3_STAGE_PREFIX}"

# Configurações de janela temporal (por coleção: só ingere sets lançados nos últimos YEARS_BACK anos)
YEARS_BACK = int(get_secret("years_back", "5"))
current_year = datetime.now().year
cutoff_year = current_year - YEARS_BACK
CUTOFF_DATE = datetime(cutoff_year, 1, 1)
CUTOFF_DATE_STR = CUTOFF_DATE.strftime("%Y-%m-%d")

print(f"YEARS_BACK: {YEARS_BACK} | CUTOFF_DATE_STR: {CUTOFF_DATE_STR}")

# COMMAND ----------

# =============================================================================
# FUNÇÕES ESPECÍFICAS DE CARDS
# =============================================================================
CARDS_SCHEMA = StructType([
    StructField("name", StringType(), True),
    StructField("manaCost", StringType(), True),
    StructField("cmc", FloatType(), True),
    StructField("colors", StringType(), True),
    StructField("colorIdentity", StringType(), True),
    StructField("type", StringType(), True),
    StructField("types", StringType(), True),
    StructField("subtypes", StringType(), True),
    StructField("rarity", StringType(), True),
    StructField("set", StringType(), True),
    StructField("setName", StringType(), True),
    StructField("text", StringType(), True),
    StructField("artist", StringType(), True),
    StructField("number", StringType(), True),
    StructField("power", StringType(), True),
    StructField("toughness", StringType(), True),
    StructField("layout", StringType(), True),
    StructField("multiverseid", IntegerType(), True),
    StructField("imageUrl", StringType(), True),
    StructField("variations", StringType(), True),
    StructField("foreignNames", StringType(), True),
    StructField("printings", StringType(), True),
    StructField("originalText", StringType(), True),
    StructField("originalType", StringType(), True),
    StructField("legalities", StringType(), True),
    StructField("id", StringType(), True)
])


def clean_cards_data(data):
    # Limpa e estrutura dados de cards
    cleaned_data = []

    for item in data:
        cleaned_item = {}

        simple_fields = ['name', 'manaCost', 'type', 'rarity', 'set', 'setName', 'text',
                        'artist', 'number', 'power', 'toughness', 'layout', 'imageUrl',
                        'originalText', 'originalType', 'id']

        for field in simple_fields:
            if field in item and item[field] is not None:
                try:
                    cleaned_item[field] = str(item[field])
                except (ValueError, TypeError):
                    cleaned_item[field] = str(item[field]) if item[field] is not None else None
            else:
                cleaned_item[field] = None

        numeric_fields = {'cmc': float, 'multiverseid': int}
        for field, field_type in numeric_fields.items():
            if field in item and item[field] is not None:
                try:
                    cleaned_item[field] = field_type(item[field])
                except (ValueError, TypeError):
                    cleaned_item[field] = None
            else:
                cleaned_item[field] = None

        list_fields = ['colors', 'colorIdentity', 'types', 'subtypes', 'variations', 'foreignNames', 'printings', 'legalities']
        for field in list_fields:
            if field in item and item[field] is not None:
                if isinstance(item[field], list):
                    cleaned_item[field] = json.dumps(item[field])
                else:
                    cleaned_item[field] = str(item[field])
            else:
                cleaned_item[field] = None

        cleaned_data.append(cleaned_item)

    return cleaned_data


def _face_fallback(card, key):
    # Cards de dupla face (DFC) não têm mana_cost/oracle_text/artist/power/
    # toughness/image_uris no nível raiz - só dentro de card_faces[0] (frente).
    # `is not None` em vez de `or`: colors:[] no nível raiz é válido (incolor),
    # não "ausente".
    value = card.get(key)
    if value is not None:
        return value
    faces = card.get("card_faces")
    return faces[0].get(key) if faces else None


def _to_card_record(card):
    image_uris = _face_fallback(card, "image_uris")
    return {
        "name": card.get("name"),
        "manaCost": _face_fallback(card, "mana_cost"),
        "cmc": card.get("cmc"),
        "colors": _face_fallback(card, "colors"),
        "colorIdentity": card.get("color_identity"),
        "type": card.get("type_line"),
        "rarity": card.get("rarity"),
        "set": card.get("set"),
        "setName": card.get("set_name"),
        "text": _face_fallback(card, "oracle_text"),
        "artist": _face_fallback(card, "artist"),
        "number": card.get("collector_number"),
        "power": _face_fallback(card, "power"),
        "toughness": _face_fallback(card, "toughness"),
        "layout": card.get("layout"),
        "imageUrl": image_uris.get("normal") if image_uris else None,
        "legalities": card.get("legalities"),
        "id": card.get("id"),
    }


def fetch_cards_by_sets(valid_set_codes):
    # Mesmo padrão do card_prices.ipynb (issue #121): 1 request pro índice do
    # Bulk Data + 1 pro catálogo inteiro, filtrado em memória - em vez de 1
    # request por página/coleção contra magicthegathering.io (issue #123).
    resp = requests.get(f"{SCRYFALL_API_URL}/bulk-data", headers=SCRYFALL_HEADERS, timeout=30)
    resp.raise_for_status()
    entry = next(e for e in resp.json()["data"] if e["type"] == SCRYFALL_BULK_TYPE)

    raw = requests.get(entry["jsonl_download_uri"], headers=SCRYFALL_HEADERS, timeout=120).content
    # bug #125: magicthegathering.io devolve códigos de set em maiúsculas
    # ("10E", "2ED"...) mas a Scryfall usa minúsculas ("blb", "tsp"...) - sem
    # normalizar o filtro nunca dava match e a ingestão saía vazia.
    valid_codes = {c.lower() for c in valid_set_codes}
    records = []
    for line in gzip.decompress(raw).decode("utf-8").splitlines():
        if not line.strip():
            continue
        card = json.loads(line)
        set_code = card.get("set")
        if set_code and set_code.lower() in valid_codes:
            records.append(_to_card_record(card))
    return records


def ingest_cards_by_collection(set_codes, table_name="cards"):
    print(f"Baixando catálogo Scryfall ({SCRYFALL_BULK_TYPE}) e filtrando por {len(set_codes)} coleções...")

    all_data = fetch_cards_by_sets(set_codes)
    print(f"Cards encontrados nas coleções da janela temporal: {len(all_data)}")

    if not all_data:
        print(f"Nenhum dado válido para {table_name}")
        return None

    print("Limpando dados de cards...")
    cleaned_data = clean_cards_data(all_data)
    print(f"Dados limpos: {len(cleaned_data)} registros")

    df = save_to_parquet(spark, cleaned_data, table_name, S3_BASE_PATH, schema=CARDS_SCHEMA)

    if df:
        count = df.count()
        print(f"{table_name}: {count} registros processados")
        return df
    return None

# COMMAND ----------

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

# Verificar Spark
try:
    spark
    print("Spark disponível")
except NameError:
    print("Spark não está disponível - tentando obter do contexto")
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        print("Spark criado com sucesso")
    except Exception as e:
        print(f"Erro ao criar Spark: {e}")
        raise Exception("Spark não está disponível")

# Configurar S3 Storage
setup_success = setup_s3_storage(S3_BASE_PATH)
if not setup_success:
    raise Exception("Falha ao configurar S3 storage")

print("Setup concluído com sucesso")

# Coleções (sets) lançadas dentro da janela de YEARS_BACK anos
set_codes = get_filtered_set_codes(API_BASE_URL, CUTOFF_DATE_STR, MAX_RETRIES)

# Iniciar ingestão de cards, coleção por coleção
print("Iniciando ingestão de cards por coleção...")

cards_df = ingest_cards_by_collection(set_codes, table_name="cards")

# Gerar relatório
print("=" * 50)
print("RELATÓRIO DE INGESTÃO DE CARDS (CORRIGIDO)")
print("=" * 50)

if cards_df:
    print("✅ Arquivos salvos com sucesso")
    print(f"📊 Total de registros: {cards_df.count()}")
    print(f"🗂️ Coleções processadas: {len(set_codes)} (últimos {YEARS_BACK} anos)")
    print("🎯 Particionamento: por ingestion_timestamp (ano/mês/dia da execução)")
else:
    print("❌ Falha na ingestão de cards")

print("=" * 50)
