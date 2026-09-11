# ============================================================================
# SILVER UTILS - Módulo de Funções Utilitárias para Camada Silver
# ============================================================================
"""
Módulo centralizado com funções reutilizáveis para scripts da camada Silver.
Inclui funções para Unity Catalog, Secrets, carregamento Delta e transformações comuns.

ADAPTADO PARA DATABRICKS NOTEBOOKS:
- dbutils e spark são disponíveis globalmente nos notebooks
- SparkSession obtido automaticamente do contexto global
- Use %run ./silver_utils para importar no notebook

EXEMPLO DE USO NO NOTEBOOK:

OPÇÃO 1 - Com Secrets configurados:
%run ./silver_utils
processor = SilverTableProcessor("TB_REF_SILVER_TYPES")

OPÇÃO 2 - Configuração manual (sem secrets):
%run ./silver_utils
config = create_manual_config("meu_catalog", "s3://meu-bucket")
processor = SilverTableProcessor("TB_REF_SILVER_TYPES", config)

# Usar normalmente:
df_bronze = processor.extract_from_bronze("TB_BRONZE_TYPES")
df_silver = processor.transform_data(df_bronze, transform_function)
processor.save_silver_table(df_silver, partition_cols=["RELEASE_YEAR", "RELEASE_MONTH"])
"""

import logging
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window
from delta.tables import DeltaTable
from pyspark.sql.utils import AnalysisException

# ============================================================================
# INICIALIZAÇÃO PARA DATABRICKS
# ============================================================================
def get_spark_session():
    """Obtém SparkSession do contexto global do Databricks"""
    try:
        return spark  # Disponível globalmente no Databricks
    except:
        from pyspark.sql import SparkSession
        return SparkSession.builder.getOrCreate()

# ============================================================================
# CONFIGURAÇÃO GLOBAL
# ============================================================================
class SilverConfig:
    """Configurações globais para a camada Silver"""
    
    def __init__(self):
        self.spark = get_spark_session()
        self.setup_logging()
        
    def setup_logging(self):
        """Configura logging padrão"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

# ============================================================================
# FUNÇÕES DE SECRETS E CONFIGURAÇÃO
# ============================================================================
def get_secret(secret_name, default_value=None):
    """
    Obtém segredos do Databricks Secret Scope
    
    Args:
        secret_name (str): Nome do secret
        default_value (str, optional): Valor padrão se secret não for encontrado
        
    Returns:
        str: Valor do secret
        
    Raises:
        Exception: Se secret obrigatório não for encontrado
    """
    try:
        return dbutils.secrets.get(scope="mtg-pipeline", key=secret_name)
    except:
        if default_value is not None:
            print(f"Secret '{secret_name}' não encontrado, usando valor padrão: {default_value}")
            return default_value
        else:
            # Valores padrão seguros para secrets comuns
            safe_defaults = {
                'catalog_name': 'magic_the_gathering',
                's3_bucket': 's3://meu-bucket-default',
                's3_silver_prefix': 'magic_the_gathering/silver'
            }
            
            if secret_name in safe_defaults:
                print(f"Secret '{secret_name}' não encontrado, usando valor padrão: {safe_defaults[secret_name]}")
                return safe_defaults[secret_name]
            else:
                print(f"⚠️ Secret '{secret_name}' não encontrado e sem valor padrão")
                print(f"💡 Configure o secret ou use create_manual_config()")
                raise Exception(f"Secret '{secret_name}' not configured and no default available")

def setup_unity_catalog(catalog, schema):
    """
    Configura Unity Catalog criando catalog e schema se necessário
    
    Args:
        catalog (str): Nome do catalog
        schema (str): Nome do schema
        
    Returns:
        bool: True se configuração foi bem-sucedida
    """
    spark_session = get_spark_session()
    try:
        spark_session.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
        spark_session.sql(f"USE CATALOG {catalog}")
        spark_session.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        spark_session.sql(f"USE SCHEMA {schema}")
        print(f"Schema {catalog}.{schema} configurado com sucesso")
        return True
    except Exception as e:
        print(f"Erro ao configurar Unity Catalog: {e}")
        return False

def get_standard_config():
    """
    Retorna configuração padrão para scripts Silver com valores padrão seguros
    
    Returns:
        dict: Dicionário com configurações padrão
    """
    # Valores padrão seguros para desenvolvimento/teste
    defaults = {
        'catalog_name': 'magic_the_gathering',
        's3_bucket': 's3://meu-bucket-default',
        's3_silver_prefix': 'magic_the_gathering/silver'
    }
    
    config = {}
    for key, default_value in defaults.items():
        try:
            config[key] = dbutils.secrets.get(scope="mtg-pipeline", key=key)
            print(f"Secret '{key}' configurado: {config[key]}")
        except:
            config[key] = default_value
            print(f"Secret '{key}' não encontrado, usando padrão: {default_value}")
    
    # Configurações fixas
    config['schema_bronze'] = "bronze"
    config['schema_silver'] = "silver"
    
    return config

def create_manual_config(catalog_name, s3_bucket, s3_silver_prefix=None):
    """
    Cria configuração manual sem usar secrets (para testes/desenvolvimento)
    
    Args:
        catalog_name (str): Nome do catalog Unity
        s3_bucket (str): Bucket S3 (com s3://)
        s3_silver_prefix (str, optional): Prefixo para Silver layer
        
    Returns:
        dict: Configuração manual
        
    Example:
        config = create_manual_config("meu_catalog", "s3://meu-bucket")
        processor = SilverTableProcessor("TB_REF_SILVER_TYPES", config)
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
    """
    EXTRACT: Lê dados da camada Bronze
    
    Args:
        catalog (str): Nome do catalog Unity
        table_name_bronze (str): Nome da tabela na Bronze
        
    Returns:
        DataFrame: DataFrame com dados da Bronze ou None se erro
    """
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
# FUNÇÕES DE TRANSFORMAÇÃO COMUM
# ============================================================================
def apply_standard_cleaning(df, name_columns=None, desc_columns=None, numeric_columns=None):
    """
    Aplica limpeza padrão para colunas de nomes, descrições e números
    
    Args:
        df (DataFrame): DataFrame para limpeza
        name_columns (list): Lista de colunas de nomes para aplicar title case
        desc_columns (list): Lista de colunas de descrição para limpeza
        numeric_columns (list): Lista de colunas numéricas para tratamento de nulos
        
    Returns:
        DataFrame: DataFrame com limpeza aplicada
    """
    if not df:
        return None
    
    # Padronização de nomes (Title Case)
    if name_columns:
        for col_name in name_columns:
            if col_name in df.columns:
                df = df.withColumn(col_name, initcap(trim(col(col_name))))
    
    # Limpeza de descrições (substituir nulos/vazios por "NA")
    if desc_columns:
        for col_name in desc_columns:
            if col_name in df.columns:
                df = df.withColumn(
                    col_name, 
                    when(col(col_name).isNull() | (col(col_name) == ""), lit("NA"))
                    .otherwise(trim(col(col_name)))
                )
    
    # Tratamento de colunas numéricas (substituir nulos por 0)
    if numeric_columns:
        for col_name in numeric_columns:
            if col_name in df.columns:
                df = df.withColumn(col_name, coalesce(col(col_name), lit(0)))
    
    return df

def apply_temporal_filter(df, months_back=60):
    """
    Aplica filtro temporal (últimos X meses)
    
    Args:
        df (DataFrame): DataFrame para filtrar
        months_back (int): Número de meses para voltar
        
    Returns:
        DataFrame: DataFrame filtrado
    """
    if not df:
        return None
    
    return df.filter(col("DT_INGESTION") >= add_months(current_date(), -months_back))

def clean_array_json_columns(df, array_columns=None):
    """
    Limpa colunas tipo array/JSON para string simples
    
    Args:
        df (DataFrame): DataFrame para limpeza
        array_columns (list): Lista de colunas array/JSON para limpar
        
    Returns:
        DataFrame: DataFrame com colunas limpas
    """
    if not array_columns:
        return df
    
    for col_name in array_columns:
        if col_name in df.columns:
            df = df.withColumn(col_name, regexp_replace(col(col_name), r'\[|\]|"', ""))
    
    return df

def add_partition_columns(df, year_col="RELEASE_YEAR", month_col="RELEASE_MONTH"):
    """
    Adiciona colunas de particionamento baseadas em ano e mês
    
    Args:
        df (DataFrame): DataFrame base
        year_col (str): Nome da coluna de ano
        month_col (str): Nome da coluna de mês
        
    Returns:
        DataFrame: DataFrame com colunas de particionamento
    """
    if not df:
        return None
    
    df = df.withColumn("ANO_PART", col(year_col))
    df = df.withColumn("MES_PART", col(month_col))
    
    return df

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DELTA/UNITY CATALOG
# ============================================================================
def delta_table_exists_and_schema_ok(spark, delta_path, df_final):
    """
    Verifica se tabela Delta existe e se o schema é compatível
    
    Args:
        spark: SparkSession
        delta_path (str): Caminho da tabela Delta
        df_final (DataFrame): DataFrame com schema de referência
        
    Returns:
        tuple: (exists, delta_table) - existe e objeto DeltaTable se existir
    """
    try:
        delta_table = DeltaTable.forPath(spark, delta_path)
        current_schema = set([f.name for f in delta_table.toDF().schema.fields])
        new_schema = set([f.name for f in df_final.schema.fields])
        if current_schema != new_schema:
            return False, None
        return True, delta_table
    except Exception:
        return False, None

def load_to_silver_unity_incremental(df_final, catalog, schema, table_name, s3_silver_path,
                                   partition_cols=None, key_column=None, order_by_col=None):
    """
    Carrega dados na camada Silver com suporte a Unity Catalog e Delta Lake
    Suporta merge incremental se key_column for especificado

    Args:
        df_final (DataFrame): DataFrame final para salvar
        catalog (str): Nome do catalog Unity
        schema (str): Nome do schema Unity
        table_name (str): Nome da tabela
        s3_silver_path (str): Caminho S3 base para Silver
        partition_cols (list, optional): Colunas para particionamento
        key_column (str or list, optional): Coluna(s) chave para merge incremental
        order_by_col (str, optional): Coluna de recência (ex.: timestamp de
            atualização) usada para escolher deterministicamente qual linha
            sobrevive quando o lote tem mais de uma linha para a mesma
            key_column (AUD-09). Sem ela, duplicatas de chave no lote ainda
            são resolvidas de forma não-determinística, mas passam a ser logadas.
    """
    delta_path = f"s3://{s3_silver_path}/{table_name}"
    full_table_name = f"{catalog}.{schema}.{table_name}"
    
    print(f"Salvando dados em: {delta_path}")
    print(f"Qtd linhas df_final: {df_final.count()}")
    print(f"Colunas df_final: {df_final.columns}")
    
    spark_session = get_spark_session()
    exists, delta_table = delta_table_exists_and_schema_ok(spark_session, delta_path, df_final)
    
    if not exists:
        print("Tabela Delta não existe ou schema mudou. Salvando com overwrite.")
        try:
            writer = df_final.write.format("delta") \
                            .mode("overwrite") \
                            .option("overwriteSchema", "true")
            
            if partition_cols:
                writer = writer.partitionBy(*partition_cols)
                
            writer.save(delta_path)
            print("Write Delta concluído com sucesso!")
        except Exception as e:
            print(f"Erro no write Delta: {e}")
            raise
    else:
        if key_column:
            key_cols = [key_column] if isinstance(key_column, str) else list(key_column)
            print(f"Tabela Delta já existe. Executando merge incremental por {key_cols}.")
            count_antes = delta_table.toDF().count()

            total_antes_dedup = df_final.count()
            if order_by_col and order_by_col in df_final.columns:
                window = Window.partitionBy(*key_cols).orderBy(col(order_by_col).desc())
                df_final = df_final.withColumn("_rn_dedup", row_number().over(window)) \
                                    .filter(col("_rn_dedup") == 1) \
                                    .drop("_rn_dedup")
            else:
                df_final = df_final.dropDuplicates(key_cols)
            total_depois_dedup = df_final.count()
            if total_antes_dedup != total_depois_dedup:
                if order_by_col and order_by_col in df_final.columns:
                    print(f"⚠️ {total_antes_dedup - total_depois_dedup} duplicata(s) de chave {key_cols} "
                          f"no lote; mantida a linha mais recente por {order_by_col}.")
                else:
                    print(f"⚠️ {total_antes_dedup - total_depois_dedup} duplicata(s) de chave {key_cols} "
                          f"no lote resolvida(s) de forma não-determinística (informe order_by_col para "
                          f"escolher a linha mais recente).")

            update_cols = [c for c in df_final.columns if c not in key_cols]
            set_expr = {col: f"novo.{col}" for col in update_cols}
            merge_condition = " AND ".join(f"silver.{k} = novo.{k}" for k in key_cols)

            merge_result = delta_table.alias("silver").merge(
                df_final.alias("novo"),
                merge_condition
            ).whenMatchedUpdate(set=set_expr) \
             .whenNotMatchedInsertAll() \
             .execute()
            
            count_depois = delta_table.toDF().count()
            print(f"Linhas antes do merge: {count_antes}")
            print(f"Linhas depois do merge: {count_depois}")
            print(f"Linhas adicionadas: {count_depois - count_antes}")
        else:
            print("Tabela Delta já existe mas sem key_column. Fazendo overwrite.")
            df_final.write.format("delta").mode("overwrite").save(delta_path)
    
    # Criação/atualização da tabela no Unity Catalog
    try:
        spark_session.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        print(f"Schema {catalog}.{schema} criado ou já existente.")
    except Exception as e:
        print(f"Erro ao criar schema: {e}")
    
    try:
        # Verifica se a tabela já existe
        if spark_session.catalog.tableExists(full_table_name):
            existing_schema = spark_session.table(full_table_name).schema
            def schema_to_set(schema):
                return set((f.name.lower(), str(f.dataType).lower()) for f in schema.fields)
            
            if schema_to_set(existing_schema) == schema_to_set(df_final.schema):
                print(f"Tabela {full_table_name} já existe e schema é igual.")
            else:
                print(f"Tabela {full_table_name} existe mas schema é diferente. Recriando.")
                spark_session.sql(f"DROP TABLE IF EXISTS {full_table_name}")
                spark_session.sql(f"CREATE TABLE {full_table_name} USING DELTA LOCATION '{delta_path}'")
        else:
            spark_session.sql(f"CREATE TABLE {full_table_name} USING DELTA LOCATION '{delta_path}'")
            print(f"Tabela Unity Catalog criada: {full_table_name}")
    except Exception as e:
        print(f"Erro ao criar/atualizar tabela Unity Catalog: {e}")
    
    print("Dados salvos com sucesso na camada Silver!")

# ============================================================================
# FUNÇÕES ESPECÍFICAS PARA TIPOS DE TABELA
# ============================================================================
def transform_reference_table(df, name_column, source_column="NME_SOURCE"):
    """
    Transformação padrão para tabelas de referência (Types, Subtypes, Supertypes)
    
    Args:
        df (DataFrame): DataFrame da Bronze
        name_column (str): Nome da coluna principal (ex: NME_TYPE)
        source_column (str): Nome da coluna de origem
        
    Returns:
        DataFrame: DataFrame transformado
    """
    if not df:
        return None
    
    print("Iniciando transformações para tabela de referência...")
    
    # Aplicar limpeza padrão
    df = apply_standard_cleaning(
        df, 
        name_columns=[name_column, source_column],
        numeric_columns=["INGESTION_YEAR", "INGESTION_MONTH"]
    )
    
    # Conversão de datas
    df = df.withColumn("DT_INGESTION", to_timestamp(col("DT_INGESTION")))
    
    # Remover duplicatas baseadas na coluna principal
    total_before = df.count()
    df = df.dropDuplicates([name_column])
    total_after = df.count()
    print(f"Removidas {total_before - total_after} duplicatas baseadas em {name_column}")
    
    return df

def transform_fact_table(df, name_columns=None, desc_columns=None, numeric_columns=None):
    """
    Transformação padrão para tabelas de fato (Cards, CardPrices)
    
    Args:
        df (DataFrame): DataFrame da Bronze
        name_columns (list): Lista de colunas de nomes
        desc_columns (list): Lista de colunas de descrição
        numeric_columns (list): Lista de colunas numéricas
        
    Returns:
        DataFrame: DataFrame transformado
    """
    if not df:
        return None
    
    print("Iniciando transformações para tabela de fato...")
    
    # Filtro temporal (últimos 5 anos)
    df = apply_temporal_filter(df, months_back=60)
    
    # Aplicar limpeza padrão
    df = apply_standard_cleaning(df, name_columns, desc_columns, numeric_columns)
    
    # Conversão de datas
    df = df.withColumn("DT_INGESTION", to_timestamp(col("DT_INGESTION")))
    
    return df

# ============================================================================
# CLASSES AUXILIARES
# ============================================================================
class SilverTableProcessor:
    """
    Classe para processar tabelas Silver com padrões comuns
    """
    
    def __init__(self, table_name, config=None):
        self.table_name = table_name
        self.config = config or get_standard_config()
        self.spark = get_spark_session()
        self.s3_silver_path = f"{self.config['s3_bucket']}/{self.config['s3_silver_prefix']}"
        
        # Setup Unity Catalog
        setup_unity_catalog(self.config['catalog_name'], self.config['schema_silver'])
    
    def extract_from_bronze(self, bronze_table_name):
        """Extrai dados da Bronze"""
        return extract_from_bronze(self.config['catalog_name'], bronze_table_name)
    
    def transform_data(self, df, transform_function, **kwargs):
        """Aplica função de transformação personalizada"""
        if transform_function:
            return transform_function(df, **kwargs)
        return df
    
    def save_silver_table(self, df, partition_cols=None, key_column=None, order_by_col=None):
        """Salva tabela na Silver com configurações padrão"""
        load_to_silver_unity_incremental(
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
    
    def process_reference_table(self, bronze_table_name, name_column, source_column="NME_SOURCE"):
        """Processa tabela de referência completa"""
        df_bronze = self.extract_from_bronze(bronze_table_name)
        df_silver = transform_reference_table(df_bronze, name_column, source_column)
        self.save_silver_table(df_silver, key_column=name_column)
        return df_silver
    
    def process_fact_table(self, bronze_table_name, name_columns=None, desc_columns=None, 
                          numeric_columns=None, partition_cols=None):
        """Processa tabela de fato completa"""
        df_bronze = self.extract_from_bronze(bronze_table_name)
        df_silver = transform_fact_table(df_bronze, name_columns, desc_columns, numeric_columns)
        self.save_silver_table(df_silver, partition_cols=partition_cols)
        return df_silver 