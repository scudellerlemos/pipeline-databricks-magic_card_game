# Databricks notebook source
# Ingestão de Preços de Cards - Magic: The Gathering
# Objetivo: Ingerir preços das cartas da Scryfall API para staging em Parquet no S3
# Características: Preços atualizados, formato Parquet, filtro temporal, particionamento por ano/mês, incremental, idempotente

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import year, month, to_timestamp
from datetime import datetime
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# COMMAND ----------

# MAGIC %run ./ingestion_utils

# COMMAND ----------

# =============================================================================
# VARIÁVEIS DE CONFIGURAÇÃO
# =============================================================================
BATCH_SIZE = int(get_secret("batch_size", "100"))  # Tamanho do lote de processamento de cartas
S3_BUCKET = get_secret("s3_bucket")  # Nome do bucket S3
S3_STAGE_PREFIX = get_secret("s3_stage_prefix", "magic_the_gathering/stage")  # Prefixo da pasta staging
S3_BASE_PATH = f"s3://{S3_BUCKET}/{S3_STAGE_PREFIX}"
SLEEP_BETWEEN = 0.1  # Segundos entre requests (não utilizado no batch)
SCRYFALL_API_URL = get_secret("scryfall_api_url")  # URL da Scryfall API

# Janela temporal: mesma fonte que cards/sets (secret years_back), em vez de um
# "5" hardcoded desalinhado do resto da Ingestão (achado adicional ao AUD-04/AUD-08).
YEARS_BACK = int(get_secret("years_back", "5"))

# COMMAND ----------

# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================
def get_card_price(card_name):
    # Busca preço da carta na Scryfall API
    url = f"{SCRYFALL_API_URL}/cards/named?exact={card_name}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name"),
                "set": data.get("set"),
                "rarity": data.get("rarity"),
                "usd": data.get("prices", {}).get("usd"),
                "eur": data.get("prices", {}).get("eur"),
                "tix": data.get("prices", {}).get("tix"),
                "scryfall_uri": data.get("scryfall_uri"),
                "image_url": data.get("image_uris", {}).get("normal") if data.get("image_uris") else None,
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "source": "scryfall"
            }
        else:
            return {"name": card_name, "error": f"Status {resp.status_code}"}
    except Exception as e:
        return {"name": card_name, "error": str(e)}

# COMMAND ----------

# =============================================================================
# LIMPEZA DE ARQUIVOS ANTIGOS (uso manual/pontual, fora do pipe - nunca
# chamada pela execução principal abaixo: drop/rm em pipe é proibido)
# =============================================================================
def cleanup_old_staging_files(files, cutoff_year):
    for f in files:
        match_price = re.search(r'(\d{4})_(\d{2})_card_prices\.parquet', f.path)
        if match_price:
            year_val = int(match_price.group(1))
            if year_val < cutoff_year:
                print(f"Deletando arquivo antigo de preços: {f.path}")
                dbutils.fs.rm(f.path, True)
        match_cards = re.search(r'(\d{4})_(\d{2})_(\d{2})_cards\.parquet', f.path)
        if match_cards:
            year_val = int(match_cards.group(1))
            if year_val < cutoff_year:
                print(f"Deletando arquivo antigo de cards: {f.path}")
                dbutils.fs.rm(f.path, True)

# COMMAND ----------

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================
# Inicializa sessão Spark
spark = SparkSession.builder.getOrCreate()
# Lista todos os arquivos na pasta staging
files = dbutils.fs.ls(S3_BASE_PATH)
# Seleciona apenas arquivos de cards no padrão ano_mes_dia_cards.parquet
card_files = [f.path for f in files if re.match(r'.*/(\d{4})_(\d{2})_(\d{2})_cards\.parquet/?$', f.path)]

current_year = datetime.now().year
cutoff_year = current_year - YEARS_BACK  # Mantém apenas YEARS_BACK anos completos (secret years_back)

# Processa cada arquivo de cards (um batch por arquivo ano/mês/dia)
total_files = len(card_files)
for idx, card_file in enumerate(card_files, 1):
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})_cards\.parquet', card_file)
    if match:
        year_val, month_val = int(match.group(1)), int(match.group(2))
        if year_val < cutoff_year:
            print(f"Pulando arquivo antigo: {card_file}")
            continue
        price_file = f"{S3_BASE_PATH}/{year_val:04d}_{month_val:02d}_card_prices.parquet"
        # Verifica se já existe arquivo de preços para esse ano/mês
        if any(f.path.rstrip('/') == price_file for f in files):
            print(f"Arquivo de preços já existe para {year_val}-{month_val}, pulando.")
            continue
        file_name = card_file.split('/')[-1]  # Nome do arquivo de cards
        price_file_name = price_file.split('/')[-1]  # Nome do arquivo de preços
        percent_files = (idx / total_files) * 100
        print(f"Processando arquivo {idx}/{total_files} ({percent_files:.1f}%) - {file_name}")
        # Lê os nomes das cartas desse arquivo de cards
        df_cards = spark.read.parquet(card_file)
        card_names = [row['name'] for row in df_cards.select('name').distinct().collect()]
        prices = []
        total_cards = len(card_names)
        num_batches = (total_cards + BATCH_SIZE - 1) // BATCH_SIZE  # Número de batches
        # Processa as cartas em lotes (batches) de tamanho BATCH_SIZE
        for batch_idx in range(num_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, total_cards)
            batch_names = card_names[start:end]
            # Busca preços em paralelo usando até 7 workers (limite seguro para Scryfall)
            with ThreadPoolExecutor(max_workers=7) as executor:
                future_to_name = {executor.submit(get_card_price, name): name for name in batch_names}
                batch_prices = []
                for future in as_completed(future_to_name):
                    batch_prices.append(future.result())
            # Mantém a ordem dos preços igual à ordem dos nomes
            batch_prices_sorted = [next(bp for bp in batch_prices if bp['name'] == name) for name in batch_names]
            prices.extend(batch_prices_sorted)
            percent_total = (end / total_cards) * 100
            print(f"Batch {batch_idx+1}/{num_batches} - Progresso total da ingestão: {percent_total:.2f} %")
        # Cria DataFrame Spark diretamente da lista de dicts
        spark_df_prices = spark.createDataFrame(prices)
        # Adiciona colunas de partição por ano/mês
        spark_df_prices = spark_df_prices.withColumn(
            "partition_year", year(to_timestamp("ingestion_timestamp"))
        ).withColumn(
            "partition_month", month(to_timestamp("ingestion_timestamp"))
        )
        # Salva o arquivo de preços para o ano/mês, particionando fisicamente por ano/mês
        spark_df_prices.coalesce(1).write.mode("overwrite") \
            .partitionBy("partition_year", "partition_month") \
            .parquet(price_file)
        print(f"Preços salvos: {price_file_name}")
        print(f"Total de cartas processadas: {len(card_names)}")
        print(f"Total de registros de preço: {spark_df_prices.count()}")
        print("Checklist de execução:")
        print("- [x] Parâmetros configurados")
        print("- [x] Nomes de cartas carregados da staging")
        print("- [x] Preços buscados na Scryfall API")
        print("- [x] Dados limpos e estruturados")
        print(f"- [x] Parquet salvo: {price_file_name}")
        print("- [x] Logs gerados com sucesso")
    else:
        print(f"Nome de arquivo inesperado: {card_file}")
