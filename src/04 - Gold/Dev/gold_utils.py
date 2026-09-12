# ============================================================================
# GOLD UTILS - Módulo de Funções Utilitárias para Camada Gold
# ============================================================================
"""
Módulo centralizado com funções reutilizáveis para scripts da camada Gold.
Inclui funções para Unity Catalog, Secrets, carregamento Delta e logging.

ADAPTADO PARA DATABRICKS NOTEBOOKS:
- dbutils e spark são disponíveis globalmente nos notebooks
- SparkSession obtido automaticamente do contexto global
- Requer infraestrutura comum (AUD-09) já carregada no notebook via:
  %run ../../00 - Common/Dev/base_utils
- Use %run ./gold_utils para importar no notebook, DEPOIS do %run acima

EXEMPLO DE USO NO NOTEBOOK:

OPÇÃO 1 - Com Secrets configurados:
%run ../../00 - Common/Dev/base_utils
%run ./gold_utils
processor = GoldTableProcessor("MINHA_TABELA")

OPÇÃO 2 - Configuração manual (sem secrets):
%run ../../00 - Common/Dev/base_utils
%run ./gold_utils
config = create_manual_config("meu_catalog", "s3://meu-bucket")
processor = GoldTableProcessor("MINHA_TABELA", config)

# Usar normalmente:
dfs = processor.load_silver_data(['cards', 'prices'])
processor.save_gold_table(df_final, partition_cols=["DATA_REF"])
"""

from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window
from delta.tables import DeltaTable
from pyspark.sql.utils import AnalysisException

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

    config = {key: get_secret(key, extra_safe_defaults=defaults) for key in defaults}

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
                                  partition_cols=None, mode="overwrite", key_column=None,
                                  order_by_col=None):
    """
    Carrega dados na camada Gold com suporte a Unity Catalog e Delta Lake
    Suporta merge incremental (upsert) se key_column for especificado

    Args:
        df_final (DataFrame): DataFrame final para salvar
        catalog (str): Nome do catalog Unity
        schema (str): Nome do schema Unity
        table_name (str): Nome da tabela
        s3_gold_path (str): Caminho S3 base para Gold
        partition_cols (list, optional): Colunas para particionamento
        mode (str): Modo de escrita quando key_column não é usado (overwrite, append)
        key_column (str or list, optional): Coluna(s) chave para merge incremental.
            Quando informado e a tabela já existe, faz upsert em vez de overwrite/append,
            evitando acúmulo de linhas duplicadas em tabelas cumulativas (ex.: alertas).
        order_by_col (str, optional): Coluna de recência usada para escolher
            deterministicamente qual linha sobrevive quando o lote tem mais de
            uma linha para a mesma key_column (AUD-09). Sem ela, duplicatas de
            chave no lote são resolvidas de forma não-determinística.
    """
    delta_path = f"s3://{s3_gold_path}/{table_name}"
    full_table_name = f"{catalog}.{schema}.{table_name}"

    print(f"Salvando dados em: {delta_path}")
    print(f"Qtd linhas df_final: {df_final.count()}")

    try:
        spark_session = get_spark_session()

        if key_column:
            keys = [key_column] if isinstance(key_column, str) else list(key_column)
            total_antes_dedup = df_final.count()
            if order_by_col and order_by_col in df_final.columns:
                # ponytail: empates exatos em order_by_col ainda saem não-determinísticos;
                # adicionar tie-break secundário (ex.: coluna de ingestão) se isso doer.
                window = Window.partitionBy(*keys).orderBy(col(order_by_col).desc())
                df_final = df_final.withColumn("_rn_dedup", row_number().over(window)) \
                                    .filter(col("_rn_dedup") == 1) \
                                    .drop("_rn_dedup")
            else:
                df_final = df_final.dropDuplicates(keys)
            total_depois_dedup = df_final.count()
            print(f"Removidas {total_antes_dedup - total_depois_dedup} duplicatas baseadas em {keys}")

            if DeltaTable.isDeltaTable(spark_session, delta_path):
                print(f"Tabela Delta já existe. Executando merge incremental por {keys}.")
                delta_table = DeltaTable.forPath(spark_session, delta_path)
                count_antes = delta_table.toDF().count()

                update_cols = [c for c in df_final.columns if c not in keys]
                set_expr = {c: f"novo.{c}" for c in update_cols}
                # <=> em vez de = : equality nula-segura, senão uma chave nula nunca daria
                # match e a linha seria reinserida a cada execução (reintroduzindo o
                # acúmulo de duplicatas que este merge existe para evitar - AUD-03).
                match_condition = " AND ".join(f"gold.{k} <=> novo.{k}" for k in keys)

                delta_table.alias("gold").merge(
                    df_final.alias("novo"), match_condition
                ).whenMatchedUpdate(set=set_expr) \
                 .whenNotMatchedInsertAll() \
                 .execute()

                count_depois = delta_table.toDF().count()
                print(f"Linhas antes do merge: {count_antes}")
                print(f"Linhas depois do merge: {count_depois}")
                print(f"Linhas adicionadas: {count_depois - count_antes}")
            else:
                print("Tabela Delta não existe. Salvando com overwrite inicial.")
                writer = df_final.write.format("delta") \
                                .mode("overwrite") \
                                .option("overwriteSchema", "true")
                if partition_cols:
                    writer = writer.partitionBy(*partition_cols)
                writer.save(delta_path)
        else:
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
    
    def save_gold_table(self, df, partition_cols=None, key_column=None, order_by_col=None):
        """Salva tabela na Gold com configurações padrão"""
        load_to_gold_unity_incremental(
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