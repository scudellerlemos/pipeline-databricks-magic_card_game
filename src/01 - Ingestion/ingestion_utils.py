# ============================================================================
# INGESTION UTILS - Funções compartilhadas pelos notebooks de Ingestão
# ============================================================================
"""
Uso no notebook (Databricks):
    %run ./ingestion_utils

Consolida o boilerplate antes duplicado em cards/sets/formats/subtypes/
supertypes/types (AUD-08) e corrige o bug de cadência do save_to_parquet
(AUD-04): o nome do arquivo de staging passa a incluir o dia da execução,
então cada run diário grava seu próprio arquivo em vez de "pular" o mês
inteiro assim que o primeiro arquivo daquele mês existisse.
"""

import json
import time
from datetime import datetime

import requests
from pyspark.sql.functions import col, lit, current_timestamp, year, month, when
from pyspark.sql.types import StructType, StructField, StringType

# ponytail: em Serverless + Git source, %run às vezes executa este arquivo num
# namespace que não herda o `dbutils` implícito do notebook. Puxa do IPython
# quando isso acontece; fora de um notebook Databricks (ex.: pytest local),
# get_ipython() é None e o bloco é ignorado, preservando o NameError esperado
# pelos testes locais (ver test_base_utils_get_secret.py).
try:
    dbutils
except NameError:
    try:
        import IPython
        dbutils = IPython.get_ipython().user_ns["dbutils"]
    except Exception:
        pass


def get_secret(secret_name, default_value=None):
    try:
        return dbutils.secrets.get(scope="mtg-pipeline", key=secret_name)
    except Exception:
        if default_value is not None:
            print(f"Segredo '{secret_name}' não encontrado, usando valor padrão")
            return default_value
        print(f"Segredo obrigatório '{secret_name}' não encontrado")
        raise Exception(f"Segredo '{secret_name}' não configurado")


def setup_s3_storage(base_path):
    try:
        try:
            dbutils.fs.ls(base_path)
            print("Diretório do S3 já existe")
        except Exception:
            dbutils.fs.mkdirs(base_path)
            print("Diretório do S3 criado com sucesso")
        return True
    except Exception as e:
        print(f"Erro ao configurar S3 storage: {e}")
        return False


def make_api_request(endpoint, api_base_url, params=None, retries=3):
    url = f"{api_base_url}/{endpoint}"

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                wait_time = min((attempt + 1) * 5, 60)
                print(f"Rate limit atingido. Aguardando {wait_time}s...")
                time.sleep(wait_time)
            elif response.status_code == 503:  # Service unavailable
                wait_time = min((attempt + 1) * 10, 120)
                print(f"Serviço indisponível. Aguardando {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Erro {response.status_code} na API: {response.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(5)

        except requests.exceptions.Timeout:
            print(f"Timeout na tentativa {attempt + 1}")
            if attempt < retries - 1:
                time.sleep(10)
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                print(f"Erro na requisição para endpoint após {retries} tentativas: {e}")
                return None
            print(f"Tentativa {attempt + 1} falhou, tentando novamente...")
            time.sleep(1)
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON na tentativa {attempt + 1}: {e}")
            if attempt == retries - 1:
                return None
            time.sleep(1)

    return None


def get_filtered_set_codes(api_base_url, cutoff_date_str, retries=3):
    """Busca /sets (paginado - a API retorna no máx. 500 por página) e retorna
    os códigos das coleções lançadas a partir de cutoff_date_str."""
    all_sets = []
    page = 1
    while True:
        data = make_api_request("sets", api_base_url, params={"page": page, "pageSize": 500}, retries=retries)
        if not data or "sets" not in data or not data["sets"]:
            break
        all_sets.extend(data["sets"])
        if len(data["sets"]) < 500:
            break
        page += 1

    if not all_sets:
        print("Falha ao obter lista de sets para filtrar coleções")
        return []

    codes = [
        s["code"] for s in all_sets
        if s.get("code") and s.get("releaseDate") and s["releaseDate"] >= cutoff_date_str
    ]
    print(f"Coleções dentro da janela temporal (releaseDate >= {cutoff_date_str}): {len(codes)}/{len(all_sets)} sets")
    return codes


def save_to_parquet(spark, data, table_name, base_path, schema=None,
                     partition_source_col=None, cutoff_date_str=None):
    """
    partition_source_col: coluna já presente no dado (ex.: 'releaseDate') usada para
        derivar partition_year/partition_month. Se None, usa a data de ingestão (agora).
    cutoff_date_str: se informado, mantém apenas registros com partition_source_col >= cutoff_date_str.
    """
    if not data:
        print(f"Nenhum dado para salvar na tabela {table_name}")
        return None

    try:
        df = spark.createDataFrame(data, schema) if schema else spark.createDataFrame(data)

        df = df.withColumn("ingestion_timestamp", current_timestamp()) \
               .withColumn("source", lit("mtg_api")) \
               .withColumn("endpoint", lit(table_name))

        if partition_source_col and partition_source_col in df.columns:
            df = df.withColumn(
                "partition_year",
                when(col(partition_source_col).isNotNull(), year(col(partition_source_col)))
                .otherwise(lit(datetime.now().year))
            ).withColumn(
                "partition_month",
                when(col(partition_source_col).isNotNull(), month(col(partition_source_col)))
                .otherwise(lit(datetime.now().month))
            )
            if cutoff_date_str:
                total = df.count()
                df = df.filter(col(partition_source_col) >= lit(cutoff_date_str))
                print(f"{table_name} filtrados pela janela temporal: {df.count()}/{total}")
        else:
            df = df.withColumn("partition_year", year(col("ingestion_timestamp"))) \
                   .withColumn("partition_month", month(col("ingestion_timestamp")))

        run_date_str = datetime.now().strftime("%d")
        partition_combinations = df.select("partition_year", "partition_month").distinct().collect()

        for partition_row in partition_combinations:
            partition_year = partition_row["partition_year"]
            partition_month = partition_row["partition_month"]

            partition_df = df.filter(
                (col("partition_year") == partition_year) & (col("partition_month") == partition_month)
            )

            # Nome inclui o dia da execução: antes só tinha ano/mês, então a partir do
            # 2o run do mesmo mês o "arquivo já existe" pulava o dia inteiro (AUD-04).
            file_name = f"{partition_year}_{partition_month:02d}_{run_date_str}_{table_name}.parquet"
            file_path = f"{base_path}/{file_name}"

            try:
                existing_files = dbutils.fs.ls(file_path)
                if len(existing_files) > 0:
                    print(f"Arquivo {file_name} já existe - pulando (já ingerido hoje)")
                    continue
            except Exception:
                pass

            partition_df.drop("partition_year", "partition_month") \
                .write.mode("overwrite").format("parquet").save(file_path)
            print(f"Arquivo {file_name} criado com sucesso")

        print(f"Registros salvos como Parquet para {table_name}")
        return df

    except Exception as e:
        print(f"Erro ao salvar dados em {table_name}: {e}")
        return None


def clean_simple_list(data, field_name):
    """Endpoints de referência (formats/types/subtypes/supertypes) retornam uma lista plana de strings."""
    return [{field_name: item} for item in data if isinstance(item, str)]


def ingest_reference_table(spark, endpoint, table_name, field_name, api_base_url, base_path, retries=3):
    """
    Ingestão genérica para tabelas de referência estáticas (formats/types/subtypes/supertypes):
    sem filtro temporal, sem paginação, schema de coluna única.
    """
    print(f"Iniciando ingestão simples: {table_name}")

    data = make_api_request(endpoint, api_base_url, retries=retries)
    if not data or table_name not in data:
        print(f"Falha ao obter dados de {table_name}")
        if data:
            print(f"Chaves disponíveis nos dados: {list(data.keys())}")
        return None

    table_data = data[table_name]
    print(f"Dados obtidos para {table_name}: {len(table_data)} registros")

    print(f"Limpando dados de {table_name}...")
    cleaned_data = clean_simple_list(table_data, field_name)
    print(f"Dados limpos: {len(cleaned_data)} registros")

    if not cleaned_data:
        print(f"Nenhum dado válido para {table_name}")
        return None

    schema = StructType([StructField(field_name, StringType(), True)])
    df = save_to_parquet(spark, cleaned_data, table_name, base_path, schema=schema)

    if df:
        count = df.count()
        print(f"{table_name}: {count} registros processados")
        display(df.limit(5))
    return df
