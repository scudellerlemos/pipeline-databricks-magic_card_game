# Databricks notebook source
# =============================================================================
# CAMADA SILVER - ESCLARECIMENTOS DE REGRAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_FATO_ESCLARECIMENTOS_CARTAS.
Transformacao e limpeza de dados da Bronze para Silver.

CLASSIFICACAO DAMA-DMBOK: Fato sem medida (factless fact) - uma linha por
esclarecimento oficial de regra (ruling) publicado para uma carta, grao de
evento (publicacao de um esclarecimento), sem medida quantitativa propria.
Ainda assim e Fato e nao DOM/REF: cresce continuamente (a Wizards publica
esclarecimento novo a cada carta lancada) e nao e uma lista de opcoes fixa.

CHAVE UNICA - Id_esclarecimento (SURROGATE): a Bronze rulings nao traz um id
proprio de registro (Scryfall so garante oracle_id + source + published_at +
comment) - Id_esclarecimento e gerado por hash determinístico
(sha2(concat_ws('|', ...), 256)) sobre essas 4 colunas, garantindo o mesmo id
em reprocessamentos do mesmo dado e permitindo declarar PRIMARY KEY de
verdade (coluna sempre NOT NULL, diferente de derivar a chave de colunas que
podem faltar).

REGRA "SEM ( ) { } NO DADO SILVER": Desc_esclarecimento e texto de regras
livre e pode conter parenteses/chaves de notacao de simbolo - mesma
conversao pra colchete ([...]) usada em TB_FATO_CARTAS, por consistencia em
toda a camada Silver.

CONVENCAO DE NOME/CASE DE COLUNA: mesma de TB_FATO_CARTAS (ver docstring de
la) - prefixo semantico + primeira letra maiuscula, resto minusculo, sem
acento, 100% PT-BR a partir da Silver.
"""

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import logging

# =============================================================================
# CARREGAMENTO DO MODULO UTILITARIO
# =============================================================================
# Importar infraestrutura comum e funcoes do silver_utils usando %run (Databricks)

# COMMAND ----------

# MAGIC %run "../../00 - Common/Dev/base_utils"

# COMMAND ----------

# MAGIC %run ./silver_utils

# COMMAND ----------

# MAGIC %run ./silver_column_docs

# COMMAND ----------

# =============================================================================
# CONFIGURACAO INICIAL
# =============================================================================
def setup_logging():
    """Configura logging para o script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def transform_rulings_silver(df):
    """
    Transformacao especifica para tabela Esclarecimentos de Regras, via SQL
    (spark.sql sobre temp views).
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformacoes especificas para Esclarecimentos de Regras...")

    df.createOrReplaceTempView("_rulings_bronze")

    # Estagio 0: SELECT explicito Bronze crua -> nome PT-BR final (ver
    # docstring do modulo) - nenhuma coluna sobra sem traducao.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _rulings_stage0 AS
        SELECT
            oracle_id AS Id_oracle,
            source AS Nme_emissor,
            published_at AS Dt_publicacao,
            comment AS Desc_esclarecimento,
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _rulings_bronze
    """)

    # Estagio 1: traducao de Nme_emissor pra nome de negocio, limpeza de
    # Desc_esclarecimento (parenteses/chaves -> colchete, mesma regra de
    # TB_FATO_CARTAS), cast de data e derivacao de Ano_publicacao/
    # Mes_publicacao a partir de Dt_publicacao - usadas so como
    # partition_cols. Id_esclarecimento: hash deterministico sobre as 4
    # colunas de negocio (ver docstring do modulo - a fonte nao fornece id
    # proprio de registro).
    df_final = spark.sql(r"""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (Id_oracle, linhagem etc.) ja saiu do Estagio 0 com nome
            -- PT-BR final e so passa direto.
            * EXCEPT (Nme_emissor, Dt_publicacao, Desc_esclarecimento,
                      Dt_ingestao, Nme_fonte),

            sha2(
                concat_ws('|',
                    coalesce(Id_oracle, ''),
                    coalesce(Nme_emissor, ''),
                    coalesce(cast(to_date(Dt_publicacao) AS STRING), ''),
                    coalesce(Desc_esclarecimento, '')
                ),
                256
            ) AS Id_esclarecimento,
            CASE
                WHEN Nme_emissor = 'wotc' THEN 'Wizards'
                WHEN Nme_emissor = 'scryfall' THEN 'Scryfall'
                ELSE initcap(trim(Nme_emissor))
            END AS Nme_emissor,
            to_date(Dt_publicacao) AS Dt_publicacao,
            CASE
                WHEN Desc_esclarecimento IS NULL OR Desc_esclarecimento = '' THEN 'NA'
                ELSE regexp_replace(regexp_replace(trim(Desc_esclarecimento), '\\{([^}]*)\\}', '[$1]'), '\\(([^)]*)\\)', '[$1]')
            END AS Desc_esclarecimento,
            to_timestamp(Dt_ingestao) AS Dt_ingestao,
            CASE WHEN Nme_fonte IS NULL OR Nme_fonte = '' THEN 'NA' ELSE initcap(trim(Nme_fonte)) END AS Nme_fonte,
            year(to_date(Dt_publicacao)) AS Ano_publicacao,
            month(to_date(Dt_publicacao)) AS Mes_publicacao
        FROM _rulings_stage0
    """)

    logger.info(f"Transformacao Esclarecimentos de Regras concluida: {df_final.count()} registros")
    return df_final

# =============================================================================
# CONFIGURACAO
# =============================================================================

# Configuracao manual. catalog_name vem do mesmo secret que a Bronze usa
# (get_secret("catalog_name")).
config = create_manual_config(get_secret("catalog_name"), get_secret("s3_bucket"))

# Setup Unity Catalog
setup_unity_catalog(config['catalog_name'], config['schema_silver'])

# COMMAND ----------

# =============================================================================
# PROCESSAMENTO USANDO SILVER_UTILS
# =============================================================================
# Criar processor
processor = SilverTableProcessor("TB_FATO_ESCLARECIMENTOS_CARTAS", config)

# Extracao da Bronze (nome real da tabela no catalog, minusculo)
df_bronze = processor.extract_from_bronze("rulings")

# Aplicar transformacao especifica
df_silver = processor.transform_data(df_bronze, transform_rulings_silver)

# Salvar na Silver com merge incremental por Id_esclarecimento (surrogate
# hash - ver docstring da celula anterior)
processor.save_silver_table(
    df_silver,
    partition_cols=["Ano_publicacao", "Mes_publicacao"],
    key_column="Id_esclarecimento",
    order_by_col="Dt_ingestao",
    table_comment=get_table_comment("TB_FATO_ESCLARECIMENTOS_CARTAS"),
    column_comments=get_column_comments("TB_FATO_ESCLARECIMENTOS_CARTAS")
)

# =============================================================================
# VALIDACAO E LOGS
# =============================================================================
if df_silver:
    print(f"Processamento concluido com sucesso!")
    print(f"Registros processados: {df_silver.count()}")
    print(f"Colunas finais: {df_silver.columns}")
else:
    print("Falha no processamento - DataFrame vazio")
