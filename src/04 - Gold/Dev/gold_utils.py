# ============================================================================
# GOLD UTILS - Módulo de Funções Utilitárias para Camada Gold
# ============================================================================
"""
Módulo centralizado com funções utilitárias (config, load Silver, load Gold)
para scripts da camada Gold. Transformação de negócio fica em SQL, dentro de
cada notebook (spark.sql sobre temp views) - este módulo é só orquestração.

ADAPTADO PARA DATABRICKS NOTEBOOKS:
- dbutils e spark são disponíveis globalmente nos notebooks
- SparkSession obtido automaticamente do contexto global
- Requer infraestrutura comum (AUD-09) já carregada no notebook via:
  %run ../../00 - Common/Dev/base_utils
- Use %run ./gold_utils para importar no notebook, DEPOIS do %run acima

EXEMPLO DE USO NO NOTEBOOK:

%run ../../00 - Common/Dev/base_utils
%run ./gold_utils

config = create_manual_config("meu_catalog", "s3://meu-bucket")
processor = GoldTableProcessor("MINHA_TABELA", config)

dfs = processor.load_silver_data(['cards', 'prices'])
processor.save_gold_table(df_final, partition_cols=["DATA_REF"])
"""

from pyspark.sql.functions import col, row_number
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
    """Retorna configuração padrão para scripts Gold com valores padrão seguros"""
    defaults = {
        'catalog_name': 'magic_the_gathering',
        's3_bucket': 's3://meu-bucket-default',
        's3_gold_prefix': 'magic_the_gathering/gold'
    }

    config = {key: get_secret(key, extra_safe_defaults=defaults) for key in defaults}

    config['schema_silver'] = "silver"
    config['schema_gold'] = "gold"

    return config

def create_manual_config(catalog_name, s3_bucket, s3_gold_prefix=None):
    """
    Cria configuração manual sem usar secrets (para testes/desenvolvimento)

    Example:
        config = create_manual_config("meu_catalog", "s3://meu-bucket")
        processor = GoldTableProcessor("MINHA_TABELA", config)
    """
    return {
        'catalog_name': catalog_name,
        'schema_silver': "silver",
        'schema_gold': "gold",
        's3_bucket': s3_bucket,
        's3_gold_prefix': s3_gold_prefix or "magic_the_gathering/gold"
    }

# ============================================================================
# FUNÇÃO DE CARREGAMENTO DELTA/UNITY CATALOG
# ============================================================================
def save_to_gold(df_final, catalog, schema, table_name, s3_gold_path,
                  partition_cols=None, key_column=None, order_by_col=None):
    """
    LOAD: grava df_final na camada Gold (Delta + Unity Catalog).

    - Delta ainda não existe no caminho: cria os arquivos (primeira carga).
    - Delta já existe e key_column informado: MERGE INTO incremental via SQL puro
      (upsert - evita acumular linhas duplicadas em tabelas cumulativas, ex.: alertas).
    - Delta já existe e sem key_column: overwrite completo (uso explícito do chamador).
    - Em qualquer caso, garante o registro da tabela no Unity Catalog sem nunca
      sobrescrever dados já gravados (CREATE TABLE IF NOT EXISTS).

    Args:
        df_final (DataFrame): DataFrame final para salvar
        catalog, schema, table_name (str): identificação da tabela no Unity Catalog
        s3_gold_path (str): caminho/bucket S3 base para Gold (com ou sem "s3://")
        partition_cols (list, optional): colunas para particionamento
        key_column (str or list, optional): coluna(s) chave para merge incremental
        order_by_col (str, optional): coluna de recência usada para escolher
            deterministicamente qual linha sobrevive quando o lote tem mais de uma
            linha para a mesma key_column (AUD-09). Sem ela, duplicatas de chave no
            lote são resolvidas de forma não-determinística, mas ficam logadas.
    """
    if not s3_gold_path.startswith("s3://"):
        s3_gold_path = f"s3://{s3_gold_path}"
    delta_path = f"{s3_gold_path}/{table_name}"
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

        if order_by_col and order_by_col in df_final.columns:
            # ponytail: empates exatos em order_by_col ainda saem não-determinísticos;
            # adicionar tie-break secundário se isso doer.
            # nulls last é proposital - order_by_col nulo nunca deve vencer um valor
            # não-nulo mais antigo por acidente.
            window = Window.partitionBy(*key_cols).orderBy(col(order_by_col).desc_nulls_last())
            df_final = df_final.withColumn("_rn_dedup", row_number().over(window)) \
                                .filter(col("_rn_dedup") == 1).drop("_rn_dedup")
        else:
            df_final = df_final.dropDuplicates(key_cols)

        df_final.createOrReplaceTempView("_gold_merge_source")
        # <=> em vez de = : equality nula-segura, senão uma chave nula nunca daria
        # match e a linha seria reinserida a cada execução (reintroduzindo o acúmulo
        # de duplicatas que este merge existe para evitar - AUD-03).
        merge_condition = " AND ".join(f"gold.{k} <=> novo.{k}" for k in key_cols)

        # ponytail: conf de autoMerge é escopo de sessão (não por statement) - salvar e
        # restaurar o valor anterior em vez de sempre limpar evita desabilitar autoMerge
        # de um MERGE concorrente de outro job na mesma sessão/cluster; isolar de verdade
        # exigiria sessão Spark dedicada por job, revisitar se isso doer.
        autoMerge_key = "spark.databricks.delta.schema.autoMerge.enabled"
        autoMerge_prev = spark_session.conf.get(autoMerge_key, None)
        spark_session.conf.set(autoMerge_key, "true")
        try:
            merge_result = spark_session.sql(f"""
                MERGE INTO delta.`{delta_path}` AS gold
                USING _gold_merge_source AS novo
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
        df_final.write.format("delta").mode("overwrite") \
            .option("overwriteSchema", "true").save(delta_path)

    spark_session.sql(
        f"CREATE TABLE IF NOT EXISTS {full_table_name} USING DELTA LOCATION '{delta_path}'"
    )
    print("Dados salvos com sucesso!")

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS SILVER
# ============================================================================
def load_silver_tables(config, table_list=None):
    """
    Carrega tabelas Silver padrão com aliases

    Args:
        config (dict): Configuração com catalog e schemas
        table_list (list, optional): Lista específica de tabelas para carregar

    Returns:
        dict: Dicionário com DataFrames carregados
    """
    spark_session = get_spark_session()
    catalog = config['catalog_name']
    schema_silver = config['schema_silver']

    default_tables = {
        'cards': f"{catalog}.{schema_silver}.TB_FATO_SILVER_CARDS",
        'prices': f"{catalog}.{schema_silver}.TB_FATO_SILVER_CARDPRICES",
        'sets': f"{catalog}.{schema_silver}.TB_REF_SILVER_SETS",
    }

    if table_list:
        tables_to_load = {k: v for k, v in default_tables.items() if k in table_list}
    else:
        tables_to_load = default_tables

    dataframes = {}
    for alias, table_name in tables_to_load.items():
        try:
            dataframes[alias] = spark_session.table(table_name).alias(alias)
            print(f"Tabela carregada: {alias} -> {table_name}")
        except Exception as e:
            print(f"Erro ao carregar {table_name}: {e}")

    return dataframes

# ============================================================================
# CLASSE AUXILIAR
# ============================================================================
class GoldTableProcessor:
    """Classe para processar tabelas Gold com padrões comuns"""

    def __init__(self, table_name, config=None):
        self.table_name = table_name
        self.config = config or get_standard_config()
        self.spark = get_spark_session()
        self.s3_gold_path = f"{self.config['s3_bucket']}/{self.config['s3_gold_prefix']}"

        setup_unity_catalog(self.config['catalog_name'], self.config['schema_gold'])

    def load_silver_data(self, tables):
        """Carrega dados Silver necessários"""
        return load_silver_tables(self.config, tables)

    def save_gold_table(self, df, partition_cols=None, key_column=None, order_by_col=None):
        """Salva tabela na Gold com configurações padrão"""
        save_to_gold(
            df_final=df,
            catalog=self.config['catalog_name'],
            schema=self.config['schema_gold'],
            table_name=self.table_name,
            s3_gold_path=self.s3_gold_path,
            partition_cols=partition_cols,
            key_column=key_column,
            order_by_col=order_by_col
        )

        print(f"✅ {self.table_name} criada com sucesso!")
        print(f"Tabela criada: {self.config['catalog_name']}.{self.config['schema_gold']}.{self.table_name}")
