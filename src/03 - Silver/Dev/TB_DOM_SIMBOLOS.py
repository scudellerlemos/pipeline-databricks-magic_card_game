# Databricks notebook source
# =============================================================================
# CAMADA SILVER - SIMBOLOS DE MANA - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_DOM_SIMBOLOS.
Transformacao e limpeza de dados da Bronze para Silver.

CLASSIFICACAO DAMA-DMBOK: DOM/REF - lista de referencia pequena e
praticamente estatica (catalogo de simbolos de mana/custo da Scryfall,
raramente ganha item novo), sem grao de evento nem medida de negocio. Daí o
prefixo TB_DOM_ (dominio) e nao TB_DIM_ (que e reservado a entidades que
crescem organicamente, como TB_DIM_COLECOES).

CHAVE UNICA: Cod_simbolo (notacao do simbolo - sempre presente e nunca nula
na fonte, ver save_silver_table no fim do notebook) - coluna unica NOT NULL,
Unity Catalog consegue declarar a constraint PRIMARY KEY de verdade.

REGRA "SEM ( ) { } NO DADO SILVER" - APLICADA SEM EXCECAO A Cod_simbolo:
- A notacao nativa de simbolo de mana da Scryfall usa chaves (ex.: "{W}",
  "{2/U}") - e notacao legitima do dominio, nao um artefato de serializacao
  como em outras colunas. Mesmo assim, esta tabela segue a MESMA conversao
  pra colchete ([W], [2/U]) que TB_FATO_CARTAS ja aplica aos mesmos simbolos
  quando eles aparecem embutidos em Desc_custo_mana/Desc_carta - sem essa
  consistencia, o mesmo simbolo apareceria com notacao diferente em cada
  tabela, e a Gold nao conseguiria juntar um token extraido do texto da
  carta contra Cod_simbolo sem antes reconverter a notacao.

CONVENCAO DE NOME/CASE DE COLUNA: mesma de TB_FATO_CARTAS (ver docstring de
la) - prefixo semantico + primeira letra maiuscula, resto minusculo, sem
acento, 100% PT-BR a partir da Silver.

SEM partition_cols: tabela pequena e estatica (uma linha por simbolo de
mana conhecido, algumas dezenas de linhas) - particionamento fisico nao
traz beneficio aqui.
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

def transform_symbology_silver(df):
    """
    Transformacao especifica para tabela Simbolos de Mana, via SQL
    (spark.sql sobre temp views).
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformacoes especificas para Simbolos de Mana...")

    df.createOrReplaceTempView("_symbology_bronze")

    # Estagio 0: SELECT explicito Bronze crua -> nome PT-BR final (ver
    # docstring do modulo) - nenhuma coluna sobra sem traducao.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _symbology_stage0 AS
        SELECT
            symbol AS Cod_simbolo,
            svg_uri AS Url_icone,
            loose_variant AS Desc_variante_livre,
            english AS Desc_simbolo,
            transposable AS Flg_transponivel,
            represents_mana AS Flg_representa_mana,
            appears_in_mana_costs AS Flg_aparece_custo_mana,
            mana_value AS Qtd_valor_mana,
            hybrid AS Flg_hibrido,
            phyrexian AS Flg_phyrexiano,
            cmc AS Qtd_custo_convertido,
            funny AS Flg_humoristico,
            colors AS Cod_cores,
            gatherer_alternates AS Desc_grafias_gatherer,
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _symbology_bronze
    """)

    # Estagio 1: conversao de chave pra colchete em Cod_simbolo (ver
    # docstring do modulo - regra sem excecao), limpeza de array
    # serializado em Cod_cores/Desc_grafias_gatherer (mesma regra de
    # TB_FATO_CARTAS) e NA para texto livre vazio.
    df_final = spark.sql(r"""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (flags/quantidades booleanas, linhagem etc.) ja saiu do
            -- Estagio 0 com nome PT-BR final e so passa direto.
            * EXCEPT (Cod_simbolo, Desc_variante_livre, Desc_simbolo,
                      Cod_cores, Desc_grafias_gatherer, Dt_ingestao, Nme_fonte),

            regexp_replace(regexp_replace(Cod_simbolo, '\\{', '['), '\\}', ']') AS Cod_simbolo,
            CASE WHEN Desc_variante_livre IS NULL OR Desc_variante_livre = '' THEN 'NA' ELSE trim(Desc_variante_livre) END AS Desc_variante_livre,
            CASE WHEN Desc_simbolo IS NULL OR Desc_simbolo = '' THEN 'NA' ELSE trim(Desc_simbolo) END AS Desc_simbolo,
            regexp_replace(Cod_cores, '\\[|\\]|"', '') AS Cod_cores,
            regexp_replace(Desc_grafias_gatherer, '\\[|\\]|"', '') AS Desc_grafias_gatherer,
            to_timestamp(Dt_ingestao) AS Dt_ingestao,
            CASE WHEN Nme_fonte IS NULL OR Nme_fonte = '' THEN 'NA' ELSE initcap(trim(Nme_fonte)) END AS Nme_fonte
        FROM _symbology_stage0
    """)

    logger.info(f"Transformacao Simbolos de Mana concluida: {df_final.count()} registros")
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
processor = SilverTableProcessor("TB_DOM_SIMBOLOS", config)

# Extracao da Bronze (nome real da tabela no catalog, minusculo)
df_bronze = processor.extract_from_bronze("symbology")

# Aplicar transformacao especifica
df_silver = processor.transform_data(df_bronze, transform_symbology_silver)

# Salvar na Silver com merge incremental por Cod_simbolo. Sem partition_cols
# (ver docstring da celula anterior - tabela pequena e estatica).
processor.save_silver_table(
    df_silver,
    key_column="Cod_simbolo",
    table_comment=get_table_comment("TB_DOM_SIMBOLOS"),
    column_comments=get_column_comments("TB_DOM_SIMBOLOS")
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
