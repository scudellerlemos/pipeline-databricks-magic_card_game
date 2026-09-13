# ============================================================================
# SILVER UTILS - Módulo de Funções Utilitárias para Camada Silver
# ============================================================================
"""
Módulo centralizado com funções utilitárias (config, extract, load) para
scripts da camada Silver. Transformação de negócio fica em SQL, dentro de
cada notebook (spark.sql sobre temp views) - este módulo é só orquestração.

ADAPTADO PARA DATABRICKS NOTEBOOKS:
- dbutils e spark são disponíveis globalmente nos notebooks
- SparkSession obtido automaticamente do contexto global
- Requer infraestrutura comum (AUD-09) já carregada no notebook via:
  %run "../../00 - Common/Dev/base_utils"
- Use %run ./silver_utils para importar no notebook, DEPOIS do %run acima

EXEMPLO DE USO NO NOTEBOOK:

%run "../../00 - Common/Dev/base_utils"
%run ./silver_utils

config = create_manual_config("meu_catalog", "s3://meu-bucket")
processor = SilverTableProcessor("TB_FATO_SILVER_CARDS", config)

df_bronze = processor.extract_from_bronze("TB_BRONZE_CARDS")
df_silver = processor.transform_data(df_bronze, transform_function)
processor.save_silver_table(df_silver, partition_cols=["RELEASE_YEAR", "RELEASE_MONTH"],
                             key_column="ID_CARD", order_by_col="DT_INGESTION")
"""

from pyspark.sql.functions import col, hash, row_number
from pyspark.sql.window import Window
from delta.tables import DeltaTable

# ============================================================================
# INFRAESTRUTURA COMUM (Spark session, Unity Catalog, secrets) - AUD-09
# get_spark_session / setup_unity_catalog / get_secret vêm de base_utils.py,
# que o notebook chamador deve importar via %run ANTES deste arquivo
# (ver docstring acima). Não fazemos %run aninhado aqui: o lint estático de
# notebooks (AUD-10) só resolve %run um nível, então um %run dentro deste
# arquivo vira texto Python inválido quando inlined por ele.
# ============================================================================

# ============================================================================
# FUNÇÕES DE CONFIGURAÇÃO
# ============================================================================
def get_standard_config():
    """Retorna configuração padrão para scripts Silver com valores padrão seguros"""
    defaults = {
        'catalog_name': 'magic_the_gathering',
        's3_bucket': 's3://meu-bucket-default',
        's3_silver_prefix': 'magic_the_gathering/silver'
    }

    config = {key: get_secret(key, extra_safe_defaults=defaults) for key in defaults}

    config['schema_bronze'] = "bronze"
    config['schema_silver'] = "silver"

    return config

def create_manual_config(catalog_name, s3_bucket, s3_silver_prefix=None):
    """
    Cria configuração manual sem usar secrets (para testes/desenvolvimento)

    Example:
        config = create_manual_config("meu_catalog", "s3://meu-bucket")
        processor = SilverTableProcessor("TB_FATO_SILVER_CARDS", config)
    """
    return {
        'catalog_name': catalog_name,
        'schema_bronze': "bronze",
        'schema_silver': "silver",
        's3_bucket': s3_bucket,
        's3_silver_prefix': s3_silver_prefix or "magic_the_gathering/silver"
    }

# ============================================================================
# FUNÇÕES DE EXTRAÇÃO DA BRONZE
# ============================================================================
def extract_from_bronze(catalog, table_name_bronze):
    """EXTRACT: lê dados da camada Bronze"""
    spark_session = get_spark_session()
    try:
        bronze_table = f"{catalog}.bronze.{table_name_bronze}"
        df = spark_session.table(bronze_table)
        print(f"Extraídos {df.count()} registros da Bronze: {bronze_table}")
        return df
    except Exception as e:
        print(f"Erro no EXTRACT da Bronze: {e}")
        return None

# ============================================================================
# FUNÇÃO DE CARREGAMENTO DELTA/UNITY CATALOG
# ============================================================================
def save_to_silver(df_final, catalog, schema, table_name, s3_silver_path,
                    partition_cols=None, key_column=None, order_by_col=None):
    """
    LOAD: grava df_final na camada Silver (Delta + Unity Catalog).

    - Delta ainda não existe no caminho: cria os arquivos (primeira carga).
    - Delta já existe e key_column informado: MERGE INTO incremental via SQL puro.
    - Delta já existe e sem key_column: overwrite completo (uso explícito do chamador).
    - Em qualquer caso, garante o registro da tabela no Unity Catalog sem nunca
      sobrescrever dados já gravados (CREATE TABLE IF NOT EXISTS).

    Args:
        df_final (DataFrame): DataFrame final para salvar
        catalog, schema, table_name (str): identificação da tabela no Unity Catalog
        s3_silver_path (str): caminho/bucket S3 base para Silver (com ou sem "s3://")
        partition_cols (list, optional): colunas para particionamento
        key_column (str or list, optional): coluna(s) chave para merge incremental
        order_by_col (str, optional): coluna de recência usada para escolher
            deterministicamente qual linha sobrevive quando o lote tem mais de uma
            linha para a mesma key_column (AUD-09). Sem ela, duplicatas de chave no
            lote são resolvidas de forma não-determinística, mas ficam logadas.
    """
    if not s3_silver_path.startswith("s3://"):
        s3_silver_path = f"s3://{s3_silver_path}"
    delta_path = f"{s3_silver_path}/{table_name}"
    full_table_name = f"{catalog}.{schema}.{table_name}"
    spark_session = get_spark_session()

    spark_session.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    files_exist = DeltaTable.isDeltaTable(spark_session, delta_path)

    if not files_exist:
        print(f"Delta ainda não existe em {delta_path}. Criando (primeira carga).")
        writer = df_final.write.format("delta").mode("overwrite")
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
        writer.save(delta_path)
        print(f"Tabela criada com {df_final.count()} linhas.")

    elif key_column:
        key_cols = [key_column] if isinstance(key_column, str) else list(key_column)

        # comparação de schema é metadado (sem scan de dados) - só visibilidade;
        # autoMerge (abaixo) resolve colunas novas sozinho, remoções/mudanças de tipo
        # podem falhar o MERGE e aparecem no log em vez de silenciosas
        current_cols = set(f.name for f in DeltaTable.forPath(spark_session, delta_path).toDF().schema.fields)
        new_cols = set(df_final.columns)
        if current_cols != new_cols:
            print(f"⚠️ Schema de {full_table_name} mudou: colunas removidas={sorted(current_cols - new_cols)}, "
                  f"colunas novas={sorted(new_cols - current_cols)}.")

        if order_by_col and order_by_col in df_final.columns:
            # nulls last é proposital - order_by_col nulo nunca deve vencer um valor
            # não-nulo mais antigo por acidente.
            # tie-break: hash das colunas restantes garante escolha determinística mesmo
            # com order_by_col empatado; ponytail: colisão de hash é possível (não-única),
            # revisitar com um tie-break natural (ex. coluna de ingestão) se isso doer.
            tie_break_cols = [c for c in df_final.columns if c not in key_cols and c != order_by_col]
            order_cols = [col(order_by_col).desc_nulls_last()]
            if tie_break_cols:
                order_cols.append(hash(*tie_break_cols).desc())
            window = Window.partitionBy(*key_cols).orderBy(*order_cols)
            df_final = df_final.withColumn("_rn_dedup", row_number().over(window)) \
                                .filter(col("_rn_dedup") == 1).drop("_rn_dedup")
        else:
            df_final = df_final.dropDuplicates(key_cols)

        df_final.createOrReplaceTempView("_silver_merge_source")
        # <=> em vez de = : equality nula-segura, senão uma chave nula nunca daria
        # match e a linha seria reinserida a cada execução (duplicando o dado).
        merge_condition = " AND ".join(f"silver.{k} <=> novo.{k}" for k in key_cols)

        # ponytail: conf de autoMerge é escopo de sessão (não por statement) - salvar e
        # restaurar o valor anterior em vez de sempre limpar evita desabilitar autoMerge
        # de um MERGE concorrente de outro job na mesma sessão/cluster; isolar de verdade
        # exigiria sessão Spark dedicada por job, revisitar se isso doer.
        autoMerge_key = "spark.databricks.delta.schema.autoMerge.enabled"
        autoMerge_prev = spark_session.conf.get(autoMerge_key, None)
        spark_session.conf.set(autoMerge_key, "true")
        try:
            merge_result = spark_session.sql(f"""
                MERGE INTO delta.`{delta_path}` AS silver
                USING _silver_merge_source AS novo
                ON {merge_condition}
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)
        finally:
            if autoMerge_prev is None:
                spark_session.conf.unset(autoMerge_key)
            else:
                spark_session.conf.set(autoMerge_key, autoMerge_prev)

        print(f"Merge em {full_table_name}: {merge_result.collect()[0].asDict()}")

    else:
        print("Tabela Delta já existe mas sem key_column. Fazendo overwrite.")
        df_final.write.format("delta").mode("overwrite").save(delta_path)

    spark_session.sql(
        f"CREATE TABLE IF NOT EXISTS {full_table_name} USING DELTA LOCATION '{delta_path}'"
    )
    print("Dados salvos com sucesso na camada Silver!")

# ============================================================================
# CLASSE AUXILIAR
# ============================================================================
class SilverTableProcessor:
    """Classe para processar tabelas Silver com padrões comuns"""

    def __init__(self, table_name, config=None):
        self.table_name = table_name
        self.config = config or get_standard_config()
        self.spark = get_spark_session()
        self.s3_silver_path = f"{self.config['s3_bucket']}/{self.config['s3_silver_prefix']}"

        setup_unity_catalog(self.config['catalog_name'], self.config['schema_silver'])

    def extract_from_bronze(self, bronze_table_name):
        """Extrai dados da Bronze"""
        return extract_from_bronze(self.config['catalog_name'], bronze_table_name)

    def transform_data(self, df, transform_function, **kwargs):
        """Aplica função de transformação personalizada (lógica em SQL, no notebook)"""
        if transform_function:
            return transform_function(df, **kwargs)
        return df

    def save_silver_table(self, df, partition_cols=None, key_column=None, order_by_col=None):
        """Salva tabela na Silver com configurações padrão"""
        save_to_silver(
            df_final=df,
            catalog=self.config['catalog_name'],
            schema=self.config['schema_silver'],
            table_name=self.table_name,
            s3_silver_path=self.s3_silver_path,
            partition_cols=partition_cols,
            key_column=key_column,
            order_by_col=order_by_col
        )

        print(f"✅ {self.table_name} criada com sucesso!")
        print(f"Tabela criada: {self.config['catalog_name']}.{self.config['schema_silver']}.{self.table_name}")
