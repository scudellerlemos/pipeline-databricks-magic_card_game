# Databricks notebook source
# =============================================================================
# CAMADA SILVER - PRECOS DE CARTAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_FATO_PRECOS_CARTAS.
Transformacao e limpeza de dados da Bronze para Silver.

CLASSIFICACAO DAMA-DMBOK: Fato - uma linha por coleta de preco de uma carta
(grao), com medidas quantitativas (Vlr_usd/Vlr_eur/Vlr_tix). Antes desta
tabela existir, preco vivia embutido em TB_FATO_CARTAS (uma unica fato
"fundida" cards+precos); a partir desta revisao as duas fontes sao
Fatos independentes, e quem precisar combinar carta com preco faz o join na
Gold por Nme_carta (ver docstring de TB_FATO_CARTAS).

MOTIVO DA SEPARACAO (SILVER, nesta revisao):
- Cards (Bronze cards) e precos (Bronze card_prices) vem de fontes
  diferentes, com grao diferente: cards e por IMPRESSAO (Id_carta), preco e
  por NOME (a Scryfall so responde preco por /cards/named?exact=<name>, sem
  granularidade de impressao). Fundir as duas na mesma tabela obrigava
  Id_carta a carregar Dt_ingestao_preco na chave so por causa do historico
  de preco, e qualquer consumidor que so queria "o que e essa carta" pagava
  o fan-out de preco por nada. Manter cada Fato no seu proprio grao natural
  e mais simples de entender e de consultar.

CHAVE UNICA: Nme_carta + Dt_ingestao (ver save_silver_table no fim do
notebook). A Bronze card_prices guarda so o preco mais recente por nome
(merge upsert por nome, sem historico proprio) - mas como esse "mais
recente" muda de data a cada execucao, cada run acrescenta uma nova linha
na Silver em vez de sobrescrever, e e assim que o historico diario de preco
se acumula aqui.

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

def transform_card_prices_silver(df):
    """
    Transformacao especifica para tabela Precos de Cartas, via SQL
    (spark.sql sobre temp views).
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformacoes especificas para Precos de Cartas...")

    df.createOrReplaceTempView("_prices_bronze")

    # Estagio 0: SELECT explicito Bronze crua -> nome PT-BR final (ver
    # docstring do modulo) - nenhuma coluna sobra sem traducao.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _prices_stage0 AS
        SELECT
            name AS Nme_carta,
            `set` AS Cod_colecao,
            rarity AS Nme_raridade,
            usd AS Vlr_usd,
            eur AS Vlr_eur,
            tix AS Vlr_tix,
            scryfall_uri AS Url_scryfall,
            image_url AS Url_imagem,
            releaseDate AS Dt_lancamento,
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _prices_bronze
    """)

    # Estagio 1: padronizacao (Title Case / upper), cast de tipo nas colunas
    # de preco (vem como string da Bronze) e derivacao de Ano_ingestao/
    # Mes_ingestao a partir de Dt_ingestao (a data da coleta em si, nao a de
    # lancamento da colecao) - usadas so como partition_cols na gravacao.
    # Sem coalesce para 0.0 nas colunas de preco: NULO aqui significa "sem
    # cotacao encontrada nesta coleta", nao "vale zero".
    df_final = spark.sql("""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (urls, linhagem etc.) ja saiu do Estagio 0 com nome PT-BR
            -- final e so passa direto.
            * EXCEPT (Nme_carta, Cod_colecao, Nme_raridade, Vlr_usd, Vlr_eur,
                      Vlr_tix, Dt_lancamento, Dt_ingestao, Nme_fonte),

            initcap(trim(Nme_carta)) AS Nme_carta,
            upper(Cod_colecao) AS Cod_colecao,
            initcap(trim(Nme_raridade)) AS Nme_raridade,
            cast(Vlr_usd AS float) AS Vlr_usd,
            cast(Vlr_eur AS float) AS Vlr_eur,
            cast(Vlr_tix AS float) AS Vlr_tix,
            to_date(Dt_lancamento) AS Dt_lancamento,
            to_timestamp(Dt_ingestao) AS Dt_ingestao,
            CASE WHEN Nme_fonte IS NULL OR Nme_fonte = '' THEN 'NA' ELSE initcap(trim(Nme_fonte)) END AS Nme_fonte,
            year(to_timestamp(Dt_ingestao)) AS Ano_ingestao,
            month(to_timestamp(Dt_ingestao)) AS Mes_ingestao
        FROM _prices_stage0
    """)

    logger.info(f"Transformacao Precos de Cartas concluida: {df_final.count()} registros")
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
processor = SilverTableProcessor("TB_FATO_PRECOS_CARTAS", config)

# Extracao da Bronze (nome real da tabela no catalog, minusculo)
df_bronze = processor.extract_from_bronze("card_prices")

# Aplicar transformacao especifica
df_silver = processor.transform_data(df_bronze, transform_card_prices_silver)

# Salvar na Silver com merge incremental por Nme_carta + Dt_ingestao (ver
# docstring da celula anterior - historico diario de preco).
# Sem order_by_col: Dt_ingestao ja esta na propria key_column, entao dentro
# de uma particao do dedup ela e constante - usa-la como criterio de recencia
# nao desempata nada (zero variancia). Duplicatas reais de (Nme_carta,
# Dt_ingestao) sao indistinguiveis aqui (mesma carta, mesma coleta exata) -
# dropDuplicates padrao resolve sem custo extra de Window/hash.
processor.save_silver_table(
    df_silver,
    partition_cols=["Ano_ingestao", "Mes_ingestao"],
    key_column=["Nme_carta", "Dt_ingestao"],
    table_comment=get_table_comment("TB_FATO_PRECOS_CARTAS"),
    column_comments=get_column_comments("TB_FATO_PRECOS_CARTAS")
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
