# Databricks notebook source
# Ingestão de Sets - Magic: The Gathering (Scryfall)
# Objetivo: Ingerir dados de sets via Scryfall API para staging em Parquet no S3
# Características: Dados brutos, formato Parquet, filtro temporal, particionamento, incremental, tratamento de campos complexos

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import json
import logging
import requests
from datetime import datetime
from pyspark.sql.types import *

# COMMAND ----------

# MAGIC %run ./ingestion_utils

# COMMAND ----------

# =============================================================================
# CONFIGURAÇÕES GLOBAIS
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# issue #127: troca /sets da magicthegathering.io (ingest_simple_data chamava
# sem paginação - só a 1a página, 500 de 773 sets, 35% perdidos em silêncio)
# pelo /sets da Scryfall, que devolve o catálogo inteiro (has_more=false) em
# 1 request só - mesmo padrão já usado em cards.ipynb/card_prices.ipynb (#121/#123).
SCRYFALL_API_URL = get_secret("scryfall_api_url")
SCRYFALL_HEADERS = {"User-Agent": "MTGPipeline/1.0"}

# Configurações do S3
S3_BUCKET = get_secret("s3_bucket")
S3_STAGE_PREFIX = get_secret("s3_stage_prefix", "stage")
S3_BASE_PATH = f"s3://{S3_BUCKET}/{S3_STAGE_PREFIX}"

# Configurações de período
YEARS_BACK = int(get_secret("years_back", "5"))
current_year = datetime.now().year
cutoff_year = current_year - YEARS_BACK
CUTOFF_DATE = datetime(cutoff_year, 1, 1)
CUTOFF_DATE_STR = CUTOFF_DATE.strftime("%Y-%m-%d")

# Log das configurações
print("=" * 60)
print("CONFIGURAÇÕES PARA INGESTÃO DE SETS")
print("=" * 60)
print("S3_BASE_PATH: [CONFIGURADO]")
print(f"YEARS_BACK: {YEARS_BACK}")
print(f"CUTOFF_DATE_STR: {CUTOFF_DATE_STR}")
print("=" * 60)

# COMMAND ----------

# =============================================================================
# FUNÇÕES ESPECÍFICAS DE SETS
# =============================================================================

SETS_SCHEMA = StructType(
    [
        StructField("code", StringType(), True),
        StructField("name", StringType(), True),
        StructField("type", StringType(), True),
        StructField("border", StringType(), True),
        StructField("mkm_id", IntegerType(), True),
        StructField("mkm_name", StringType(), True),
        StructField("releaseDate", StringType(), True),
        StructField("gathererCode", StringType(), True),
        StructField("magicCardsInfoCode", StringType(), True),
        StructField("booster", StringType(), True),  # Campo original como JSON
        StructField("oldCode", StringType(), True),
        StructField("onlineOnly", BooleanType(), True),
        StructField("source", StringType(), True),
    ]
    # Colunas booster explodidas (até 20 posições para cobrir a maioria dos casos)
    + [StructField(f"booster_{i}", StringType(), True) for i in range(20)]
)


def clean_sets_data(data):
    cleaned_data = []
    for item in data:
        if isinstance(item, dict):
            cleaned_item = {}

            # Mapear campos conhecidos com tipos seguros
            field_mappings = {
                'code': str,
                'name': str,
                'type': str,
                'border': str,
                'mkm_id': int,
                'mkm_name': str,
                'releaseDate': str,
                'gathererCode': str,
                'magicCardsInfoCode': str,
                'oldCode': str,
                'onlineOnly': bool,
                'source': str
            }

            # Processar campos conhecidos
            for field, field_type in field_mappings.items():
                if field in item:
                    try:
                        if item[field] is not None:
                            cleaned_item[field] = field_type(item[field])
                        else:
                            cleaned_item[field] = None
                    except (ValueError, TypeError):
                        cleaned_item[field] = str(item[field]) if item[field] is not None else None
                else:
                    cleaned_item[field] = None

            # Tratar campo booster complexo - EXPLODIR EM MÚLTIPLAS COLUNAS
            if 'booster' in item and item['booster'] is not None:
                booster_data = item['booster']

                if isinstance(booster_data, list):
                    for i, booster_item in enumerate(booster_data):
                        if isinstance(booster_item, list):
                            cleaned_item[f'booster_{i}'] = json.dumps(booster_item)
                        else:
                            cleaned_item[f'booster_{i}'] = str(booster_item)

                    cleaned_item['booster'] = json.dumps(booster_data)
                else:
                    cleaned_item['booster'] = str(booster_data)
            else:
                cleaned_item['booster'] = None

            cleaned_data.append(cleaned_item)

    return cleaned_data


def _to_set_record(s):
    # Campos exclusivos da magicthegathering.io (border/mkm_id/mkm_name/
    # gathererCode/magicCardsInfoCode/oldCode/booster) não têm equivalente na
    # Scryfall - ficam None, mesmo padrão já aceito em #123/#125 pra
    # foreignNames/printings/etc. em cards.ipynb (colunas seguem existindo,
    # só ficam null - Bronze/Silver não quebram).
    return {
        "code": s.get("code"),
        "name": s.get("name"),
        "type": s.get("set_type"),
        "releaseDate": s.get("released_at"),
        "onlineOnly": s.get("digital"),
    }


def fetch_all_sets():
    resp = requests.get(f"{SCRYFALL_API_URL}/sets", headers=SCRYFALL_HEADERS, timeout=30)
    resp.raise_for_status()
    return [_to_set_record(s) for s in resp.json()["data"]]


def ingest_sets():
    print("Iniciando ingestão simples: sets")

    table_data = fetch_all_sets()
    print(f"Sets obtidos da Scryfall: {len(table_data)}")

    print("Limpando dados de sets...")
    table_data = clean_sets_data(table_data)

    if table_data:
        example_item = table_data[0]
        booster_fields = [k for k in example_item.keys() if k.startswith('booster_')]
        print(f"Campo booster explodido em {len(booster_fields)} colunas: {booster_fields[:5]}...")

    df = save_to_parquet(
        spark, table_data, "sets", S3_BASE_PATH,
        schema=SETS_SCHEMA,
        partition_source_col="releaseDate",
        cutoff_date_str=CUTOFF_DATE_STR,
    )

    if df:
        count = df.count()
        print(f"sets: {count} registros processados")
        display(df.limit(5))
    return df


# Configurar S3 Storage
setup_success = setup_s3_storage(S3_BASE_PATH)
if not setup_success:
    raise Exception("Falha ao configurar S3 storage")

print("Setup concluído com sucesso")

# COMMAND ----------

# Iniciar ingestão de sets
print("Iniciando ingestão de sets...")

sets_df = ingest_sets()



# Gerar relatório
print("=" * 50)
print("RELATÓRIO DE INGESTÃO DE SETS")
print("=" * 50)

if sets_df:
    print("Arquivos salvos")

else:
    print("Falha na ingestão de sets")

print("=" * 50)
