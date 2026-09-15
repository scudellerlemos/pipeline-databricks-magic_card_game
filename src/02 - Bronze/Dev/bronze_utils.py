# ============================================================================
# BRONZE UTILS - Funções compartilhadas pelos notebooks de Bronze
# ============================================================================
"""
Uso no notebook (Databricks):
    %run ./bronze_utils

Escopo desta camada (Bronze): EL puro (Extract & Load) da Stage (S3/Parquet)
para Delta, com metadados técnicos de rastreabilidade. Sem regra de negócio,
sem renomeação/padronização de colunas (isso é Silver), sem deduplicação por
chave de negócio (o mesmo card_id com price diferente em runs diferentes é
histórico legítimo, não duplicata) e sem MERGE/upsert (que colapsaria esse
histórico) - só APPEND. Preserva o schema de origem 1:1, adicionando apenas
source_file/bronze_run_id/bronze_ingestion_timestamp por cima.

Idempotência: identifica arquivos da Stage já carregados por identidade de
arquivo (source_file), não por SELECT DISTINCT nos dados de negócio - reprocessa
só o que a Stage gravou de novo desde a última execução da Bronze.
"""

import uuid
from datetime import datetime, timezone

from pyspark.sql.functions import input_file_name, current_timestamp, lit

# %run ../../00 - Common/Dev/base_utils -> get_secret / setup_unity_catalog
# (mesma infraestrutura já reaproveitada por Silver/Gold - AUD-09)
%run "../../00 - Common/Dev/base_utils"


# ============================================================================
# EXTRACT - IDENTIFICAÇÃO DE ARQUIVOS NOVOS NA STAGE
# ============================================================================

def list_stage_files(dbutils, s3_stage_path, stage_table_name):
    """Lista os arquivos Parquet da Stage pertencentes a stage_table_name.

    Os 6 arquivos das tabelas de Stage vivem juntos, no mesmo diretório flat
    (S3_STAGE_PATH), distinguidos só pelo sufixo do nome do arquivo
    (ver save_to_parquet em ingestion_utils.py) - por isso o filtro é por
    sufixo exato, não um glob solto que poderia casar "cards" dentro de
    "card_prices".
    """
    suffix = f"_{stage_table_name}.parquet"
    all_files = dbutils.fs.ls(s3_stage_path)
    return sorted(f.path for f in all_files if f.name.endswith(suffix))


def get_already_loaded_files(spark, delta_path):
    """Arquivos de Stage já carregados nesta tabela Bronze, via source_file.

    O DISTINCT aqui não é deduplicação de negócio (proibida na Bronze) - é a
    identificação explícita de arquivo/run exigida para idempotência: cada
    source_file representa 1 execução da Stage já processada, não um registro
    de negócio a ser colapsado.
    """
    try:
        df = spark.read.format("delta").load(delta_path)
    except Exception:
        return set()
    return {row.source_file for row in df.select("source_file").distinct().collect()}


# ============================================================================
# SCHEMA - LOG DE DIVERGÊNCIA (SEM BLOQUEAR EVOLUÇÃO ADITIVA)
# ============================================================================

def log_schema_diff(spark, delta_path, incoming_df):
    """Loga colunas novas/ausentes/com tipo diferente vs. a tabela Bronze atual.

    Não bloqueia a escrita: colunas novas são aceitas via mergeSchema (schema
    evolution aditiva), colunas ausentes neste lote ficam NULL nas linhas novas
    sem apagar as antigas. Incompatibilidade real de tipo é rejeitada pelo
    próprio Delta na escrita (AnalysisException) - aqui é só log para
    diagnóstico, sem duplicar essa validação.
    """
    try:
        existing_fields = {f.name: str(f.dataType) for f in spark.read.format("delta").load(delta_path).schema.fields}
    except Exception:
        existing_fields = {}

    incoming_fields = {f.name: str(f.dataType) for f in incoming_df.schema.fields}
    new_cols = sorted(c for c in incoming_fields if c not in existing_fields)
    missing_cols = sorted(c for c in existing_fields if c not in incoming_fields)
    type_changed = sorted(
        c for c in incoming_fields
        if c in existing_fields and incoming_fields[c] != existing_fields[c]
    )

    if not existing_fields:
        print(f"[schema] primeira carga - {len(incoming_fields)} colunas")
    if new_cols:
        print(f"[schema] colunas novas neste lote (schema evolution): {new_cols}")
    if missing_cols:
        print(f"[schema] colunas ausentes neste lote (preservadas como NULL nas linhas existentes): {missing_cols}")
    if type_changed:
        print(f"[schema] ALERTA tipos divergentes (a escrita falha se for incompatível de verdade): {type_changed}")


# ============================================================================
# LOAD - APPEND PURO (SEM MERGE/UPSERT) + REGISTRO NO UNITY CATALOG
# ============================================================================

def ensure_unity_catalog_table(spark, full_table_name, delta_path):
    """Registra a tabela externa Delta no Unity Catalog se ainda não existir.

    Só cria - nunca ALTER/DROP automático aqui. Se a tabela já existe, deixa
    como está (preserva qualquer modificação manual feita fora do pipe).
    """
    if not spark.catalog.tableExists(full_table_name):
        spark.sql(f"""
            CREATE TABLE {full_table_name}
            USING DELTA
            LOCATION '{delta_path}'
            COMMENT 'Camada Bronze - dado bruto da Stage, 1:1, sem regra de negócio'
        """)
        print(f"Tabela Unity Catalog criada: {full_table_name}")


def append_to_bronze(df, delta_path, full_table_name):
    """Escreve por APPEND (cria a tabela Delta automaticamente na 1a carga)."""
    (df.write
       .format("delta")
       .mode("append")
       .option("mergeSchema", "true")
       .save(delta_path))
    ensure_unity_catalog_table(df.sparkSession, full_table_name, delta_path)


# ============================================================================
# CONTROLE DE EXECUÇÃO
# ============================================================================
# Um JSON por run em {s3_bronze_path}/_control/{bronze_table_name}/{run_id}.json -
# mesmo padrão da Stage (ver ingestion_utils.py), com os campos pedidos para
# a Bronze: run_id, tabela, datas, registros lidos/gravados, arquivos
# processados, registros rejeitados (sempre 0 - Bronze nunca descarta nada),
# status e erro.

def start_bronze_run(table_name):
    return {
        "run_id": uuid.uuid4().hex[:12],
        "table": table_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING",
        "files_processed": 0,
        "records_read": 0,
        "records_written": 0,
        "rejected_records": 0,
    }


def finish_bronze_run(run, s3_bronze_path, status, error=None):
    import json
    started_at = datetime.fromisoformat(run["started_at"])
    finished_at = datetime.now(timezone.utc)

    run["finished_at"] = finished_at.isoformat()
    run["duration_seconds"] = round((finished_at - started_at).total_seconds(), 1)
    run["status"] = status
    run["error"] = error

    control_dir = f"{s3_bronze_path}/_control/{run['table']}"
    control_path = f"{control_dir}/{run['run_id']}.json"
    try:
        dbutils.fs.mkdirs(control_dir)
        dbutils.fs.put(control_path, json.dumps(run, default=str), overwrite=True)
    except Exception as e:
        print(f"Aviso: falha ao gravar controle de execução em {control_path}: {e}")

    print(
        f"[{run['table']}] run={run['run_id']} status={status} "
        f"arquivos_processados={run['files_processed']} "
        f"registros_lidos={run['records_read']} registros_gravados={run['records_written']}"
        + (f" erro={error}" if error else "")
    )
    return run


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_bronze_ingestion(spark, dbutils, catalog_name, schema_name,
                          bronze_table_name, stage_table_name,
                          s3_stage_path, s3_bronze_path):
    """EL completo: identifica arquivos novos da Stage -> lê -> adiciona
    metadados técnicos -> append na Bronze (schema evolution aditiva) ->
    garante a tabela no Unity Catalog -> grava o controle de execução.

    Idempotente: se não há arquivo novo da Stage desde a última execução,
    não escreve nada e a run fecha como SUCCESS com 0 registros.
    """
    run = start_bronze_run(bronze_table_name)
    delta_path = f"{s3_bronze_path}/{bronze_table_name}"
    full_table_name = f"{catalog_name}.{schema_name}.{bronze_table_name}"

    try:
        all_files = list_stage_files(dbutils, s3_stage_path, stage_table_name)
        already_loaded = get_already_loaded_files(spark, delta_path)
        new_files = [f for f in all_files if f not in already_loaded]
        run["files_processed"] = len(new_files)

        if not new_files:
            print(f"[{bronze_table_name}] Nenhum arquivo novo da Stage - nada a fazer (idempotente).")
            finish_bronze_run(run, s3_bronze_path, "SUCCESS")
            return None, run

        print(f"[{bronze_table_name}] Arquivos novos da Stage: {len(new_files)}")
        df = spark.read.parquet(*new_files) \
            .withColumn("source_file", input_file_name()) \
            .withColumn("bronze_run_id", lit(run["run_id"])) \
            .withColumn("bronze_ingestion_timestamp", current_timestamp())

        run["records_read"] = df.count()

        log_schema_diff(spark, delta_path, df)
        append_to_bronze(df, delta_path, full_table_name)

        run["records_written"] = run["records_read"]
        finish_bronze_run(run, s3_bronze_path, "SUCCESS")
        return df, run

    except Exception as e:
        finish_bronze_run(run, s3_bronze_path, "FAILED", error=str(e))
        raise
