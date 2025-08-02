# ============================================================================
# GOLD UTILS - Módulo de Funções Utilitárias para Camada Gold
# ============================================================================
"""
Módulo centralizado com funções reutilizáveis para scripts da camada Gold.
Inclui funções para Unity Catalog, Secrets, carregamento Delta e logging.

ADAPTADO PARA DATABRICKS NOTEBOOKS:
- dbutils e spark são disponíveis globalmente nos notebooks
- SparkSession obtido automaticamente do contexto global
- Use %run ./gold_utils para importar no notebook

EXEMPLO DE USO NO NOTEBOOK:

OPÇÃO 1 - Com Secrets configurados:
%run ./gold_utils
processor = GoldTableProcessor("MINHA_TABELA")

OPÇÃO 2 - Configuração manual (sem secrets):
%run ./gold_utils
config = create_manual_config("meu_catalog", "s3://meu-bucket")
processor = GoldTableProcessor("MINHA_TABELA", config)

# Usar normalmente:
dfs = processor.load_silver_data(['cards', 'prices'])
processor.save_gold_table(df_final, partition_cols=["DATA_REF"])
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
class GoldConfig:
    """Configurações globais para a camada Gold"""
    
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
                's3_gold_prefix': 'magic_the_gathering/gold'
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
    Retorna configuração padrão para scripts Gold com valores padrão seguros
    
    Returns:
        dict: Dicionário com configurações padrão
    """
    # Valores padrão seguros para desenvolvimento/teste
    defaults = {
        'catalog_name': 'magic_the_gathering',
        's3_bucket': 's3://meu-bucket-default',
        's3_gold_prefix': 'magic_the_gathering/gold'
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
    config['schema_silver'] = "silver"
    config['schema_gold'] = "gold"
    
    return config

def create_manual_config(catalog_name, s3_bucket, s3_gold_prefix=None):
    """
    Cria configuração manual sem usar secrets (para testes/desenvolvimento)
    
    Args:
        catalog_name (str): Nome do catalog Unity
        s3_bucket (str): Bucket S3 (com s3://)
        s3_gold_prefix (str, optional): Prefixo para Gold layer
        
    Returns:
        dict: Configuração manual
        
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
# FUNÇÕES DE CARREGAMENTO DELTA/UNITY CATALOG
# ============================================================================
def load_to_gold_unity_incremental(df_final, catalog, schema, table_name, s3_gold_path, 
                                  partition_cols=None, mode="overwrite"):
    """
    Carrega dados na camada Gold com suporte a Unity Catalog e Delta Lake
    
    Args:
        df_final (DataFrame): DataFrame final para salvar
        catalog (str): Nome do catalog Unity
        schema (str): Nome do schema Unity
        table_name (str): Nome da tabela
        s3_gold_path (str): Caminho S3 base para Gold
        partition_cols (list, optional): Colunas para particionamento
        mode (str): Modo de escrita (overwrite, append)
    """
    delta_path = f"s3://{s3_gold_path}/{table_name}"
    full_table_name = f"{catalog}.{schema}.{table_name}"
    
    print(f"Salvando dados em: {delta_path}")
    print(f"Qtd linhas df_final: {df_final.count()}")
    
    try:
        # Configurar writer
        writer = df_final.write.format("delta") \
                        .mode(mode) \
                        .option("overwriteSchema", "true")
        
        # Adicionar particionamento se especificado
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
            
        # Salvar dados
        writer.save(delta_path)
        
        # Criar/atualizar tabela Unity Catalog
        spark_session = get_spark_session()
        try:
            spark_session.sql(f"SELECT 1 FROM {full_table_name} LIMIT 1")
            print(f"Tabela Unity Catalog '{full_table_name}' já existe")
        except:
            spark_session.sql(f"CREATE TABLE {full_table_name} USING DELTA LOCATION '{delta_path}'")
            print(f"Tabela Unity Catalog criada: {full_table_name}")
        
        print("Dados salvos com sucesso!")
        
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")
        raise

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
    
    # Tabelas padrão
    default_tables = {
        'cards': f"{catalog}.{schema_silver}.TB_FATO_SILVER_CARDS",
        'prices': f"{catalog}.{schema_silver}.TB_FATO_SILVER_CARDPRICES", 
        'sets': f"{catalog}.{schema_silver}.TB_REF_SILVER_SETS",
        'types': f"{catalog}.{schema_silver}.TB_REF_SILVER_TYPES",
        'subtypes': f"{catalog}.{schema_silver}.TB_REF_SILVER_SUBTYPES",
        'supertypes': f"{catalog}.{schema_silver}.TB_REF_SILVER_SUPERTYPES"
    }
    
    # Usar lista específica se fornecida
    if table_list:
        tables_to_load = {k: v for k, v in default_tables.items() if k in table_list}
    else:
        tables_to_load = default_tables
    
    # Carregar tabelas com aliases
    dataframes = {}
    for alias, table_name in tables_to_load.items():
        try:
            dataframes[alias] = spark_session.table(table_name).alias(alias)
            print(f"Tabela carregada: {alias} -> {table_name}")
        except Exception as e:
            print(f"Erro ao carregar {table_name}: {e}")
            
    return dataframes

# ============================================================================
# FUNÇÕES DE TRANSFORMAÇÃO COMUM
# ============================================================================
def resolve_column_ambiguity(df, ambiguous_cols_map):
    """
    Resolve ambiguidades de colunas selecionando explicitamente
    
    Args:
        df (DataFrame): DataFrame com possíveis ambiguidades
        ambiguous_cols_map (dict): Mapeamento de colunas ambíguas
        
    Returns:
        DataFrame: DataFrame com colunas resolvidas
        
    Example:
        ambiguous_cols_map = {
            'NME_RARITY': 'cards.NME_RARITY',
            'DT_INGESTION': 'prices.DT_INGESTION'
        }
    """
    select_cols = []
    for col_name in df.columns:
        if col_name in ambiguous_cols_map:
            # Usar mapeamento específico
            select_cols.append(col(ambiguous_cols_map[col_name]).alias(col_name))
        else:
            # Usar coluna direta
            select_cols.append(col_name)
    
    return df.select(*select_cols)

def add_data_reference(df, ref_type="current", year_col=None, month_col=None):
    """
    Adiciona coluna DATA_REF baseada no tipo especificado
    
    Args:
        df (DataFrame): DataFrame base
        ref_type (str): Tipo de referência ('current', 'release', 'ingestion')
        year_col (str): Nome da coluna de ano (para ref_type='release')
        month_col (str): Nome da coluna de mês (para ref_type='release')
        
    Returns:
        DataFrame: DataFrame com DATA_REF adicionado
    """
    if ref_type == "current":
        return df.withColumn("DATA_REF", current_date())
    elif ref_type == "release" and year_col and month_col:
        return df.withColumn("DATA_REF", make_date(col(year_col), col(month_col), lit(1)))
    elif ref_type == "ingestion":
        return df.withColumn("DATA_REF", to_date(col("DT_INGESTION")))
    else:
        raise ValueError(f"Tipo de referência inválido: {ref_type}")

# ============================================================================
# CLASSES AUXILIARES
# ============================================================================
class GoldTableProcessor:
    """
    Classe para processar tabelas Gold com padrões comuns
    """
    
    def __init__(self, table_name, config=None):
        self.table_name = table_name
        self.config = config or get_standard_config()
        self.spark = get_spark_session()
        self.s3_gold_path = f"{self.config['s3_bucket']}/{self.config['s3_gold_prefix']}"
        
        # Setup Unity Catalog
        setup_unity_catalog(self.config['catalog_name'], self.config['schema_gold'])
    
    def load_silver_data(self, tables):
        """Carrega dados Silver necessários"""
        return load_silver_tables(self.config, tables)
    
    def save_gold_table(self, df, partition_cols=None):
        """Salva tabela na Gold com configurações padrão"""
        load_to_gold_unity_incremental(
            df_final=df,
            catalog=self.config['catalog_name'],
            schema=self.config['schema_gold'],
            table_name=self.table_name,
            s3_gold_path=self.s3_gold_path,
            partition_cols=partition_cols
        )
        
        print(f"✅ {self.table_name} criada com sucesso!")
        print(f"Tabela criada: {self.config['catalog_name']}.{self.config['schema_gold']}.{self.table_name}")