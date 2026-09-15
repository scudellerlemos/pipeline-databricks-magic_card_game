# Databricks notebook source
# =============================================================================
# CAMADA SILVER - COLEÇÕES (SETS) - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_DIM_COLECOES.
Transformação e limpeza de dados da Bronze para Silver.

CLASSIFICAÇÃO DAMA-DMBOK (#116): Dimensão - descreve a entidade de negócio
"coleção/edição" (nome, tipo, data de lançamento, bloco...), sem medida
quantitativa própria além de contagens descritivas (Qtd_cartas). É
referenciada por Cod_colecao a partir de TB_FATO_CARTAS - não é uma lista de
domínio estática pequena (REF), é uma dimensão real que cresce a cada
lançamento. Daí TB_DIM_ e não TB_REF_.

CHAVE ÚNICA: Cod_colecao (código curto do set - sempre presente e nunca nulo
na fonte, ver save_silver_table no fim do notebook). Diferente de
TB_FATO_CARTAS, aqui a chave é uma única coluna NOT NULL - Unity Catalog
consegue declarar a constraint PRIMARY KEY de verdade (não só o comentário
de tabela), ver silver_utils.save_to_silver.

CONVENÇÃO DE NOME/CASE DE COLUNA: mesma de TB_FATO_CARTAS (ver docstring de
lá) - prefixo semântico + primeira letra maiúscula, resto minúsculo, sem
acento, 100% PT-BR a partir da Silver.

CORREÇÃO DE BUGS (achados nesta revisão, escopo #116):
- Este notebook nunca teve um Estágio 0 de renomeação: a SQL abaixo
  referenciava direto COD_SET/NME_SET/... contra a Bronze crua, que tem
  colunas em inglês (code/name/type/releaseDate/onlineOnly...) - nunca
  rodou com sucesso (UNRESOLVED_COLUMN). O SELECT abaixo agora traduz
  explicitamente toda coluna da Bronze sets pro nome PT-BR final.
- processor.extract_from_bronze("TB_BRONZE_SETS") (célula seguinte)
  referenciava uma tabela que nunca existiu no catalog real - nome correto é
  "sets" (minúsculo), mesmo padrão já corrigido em TB_FATO_CARTAS (#135).
"""

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import logging

# =============================================================================
# CARREGAMENTO DO MÓDULO UTILITÁRIO
# =============================================================================
# Importar infraestrutura comum e funções do silver_utils usando %run (Databricks)

# COMMAND ----------

# MAGIC %run "../../00 - Common/Dev/base_utils"

# COMMAND ----------

# MAGIC %run ./silver_utils

# COMMAND ----------

# MAGIC %run ./silver_column_docs

# COMMAND ----------

# =============================================================================
# CONFIGURAÇÃO INICIAL
# =============================================================================
def setup_logging():
    """Configura logging para o script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def transform_sets_silver(df):
    """
    Transformação específica para tabela Coleções, via SQL (spark.sql sobre temp views)
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformações específicas para Coleções...")

    df.createOrReplaceTempView("_sets_bronze")

    # onlineOnly pode não existir em alguma carga da Bronze - cai pra NULL
    # tipado em vez de estourar AnalysisException (coluna é boolean, ver
    # README Bronze).
    online_only_select = "onlineOnly AS Flg_somente_online" if "onlineOnly" in df.columns \
        else "CAST(NULL AS BOOLEAN) AS Flg_somente_online"

    # booster_0..19: a Stage explode a lista "booster" da fonte em 1 coluna
    # por posição (ver bronze_column_docs.py) - repassa aqui com nome PT-BR,
    # sem mudar o formato.
    booster_cols_select = ", ".join(f"booster_{i} AS Desc_booster_slot_{i}" for i in range(20))

    # Estágio 0: SELECT explícito Bronze crua -> nome PT-BR final (ver
    # docstring do módulo) - nenhuma coluna sobra sem tradução.
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _sets_stage0 AS
        SELECT
            upper(code) AS Cod_colecao,  -- normaliza case: TB_FATO_CARTAS tambem faz upper() em Cod_colecao, join entre as duas depende do mesmo case
            name AS Nme_colecao,
            type AS Nme_tipo_colecao,
            border AS Nme_cor_borda,
            mkm_id AS Id_cardmarket,
            mkm_name AS Nme_cardmarket,
            releaseDate AS Dt_lancamento,
            gathererCode AS Cod_gatherer,
            magicCardsInfoCode AS Cod_magiccardsinfo,
            oldCode AS Cod_antigo,
            {online_only_select},
            card_count AS Qtd_cartas,
            parent_set_code AS Cod_colecao_pai,
            block AS Nme_bloco,
            icon_svg_uri AS Url_icone,
            {booster_cols_select},
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _sets_bronze
    """)

    # Estágio 1: padronização de nomes (Title Case), Nme_fonte como 'NA' se
    # nulo/vazio, conversão de data, e derivação de Ano_lancamento/
    # Mes_lancamento (#115: RELEASE_YEAR/RELEASE_MONTH -> PT-BR) a partir de
    # Dt_lancamento já convertida - antes essas duas colunas nunca existiram
    # de fato nesta tabela (vinham direto, sem existir na Bronze).
    df_final = spark.sql("""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (booster_0..19, ids externos, linhagem etc.) ja saiu do
            -- Estagio 0 com nome PT-BR final e so passa direto.
            * EXCEPT (Nme_colecao, Nme_tipo_colecao, Dt_lancamento, Nme_fonte),

            initcap(trim(Nme_colecao)) AS Nme_colecao,
            initcap(trim(Nme_tipo_colecao)) AS Nme_tipo_colecao,
            to_date(Dt_lancamento) AS Dt_lancamento,
            CASE WHEN Nme_fonte IS NULL OR Nme_fonte = '' THEN 'NA' ELSE initcap(trim(Nme_fonte)) END AS Nme_fonte,
            year(to_date(Dt_lancamento)) AS Ano_lancamento,
            month(to_date(Dt_lancamento)) AS Mes_lancamento
        FROM _sets_stage0
    """)

    logger.info(f"Transformação Coleções concluída: {df_final.count()} registros")
    return df_final

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

# Configuração manual. catalog_name vem do mesmo secret que a Bronze usa
# (get_secret("catalog_name")).
config = create_manual_config(get_secret("catalog_name"), get_secret("s3_bucket"))

# Setup Unity Catalog
setup_unity_catalog(config['catalog_name'], config['schema_silver'])

# COMMAND ----------

# =============================================================================
# PROCESSAMENTO USANDO SILVER_UTILS
# =============================================================================
# Criar processor
processor = SilverTableProcessor("TB_DIM_COLECOES", config)

# Extração da Bronze (nome real da tabela no catalog, minúsculo)
df_bronze = processor.extract_from_bronze("sets")

# Aplicar transformação específica
df_silver = processor.transform_data(df_bronze, transform_sets_silver)

# Salvar na Silver com merge incremental
processor.save_silver_table(
    df_silver,
    partition_cols=["Ano_lancamento", "Mes_lancamento"],
    key_column="Cod_colecao",
    table_comment=get_table_comment("TB_DIM_COLECOES"),
    column_comments=get_column_comments("TB_DIM_COLECOES")
)

# =============================================================================
# VALIDAÇÃO E LOGS
# =============================================================================
if df_silver:
    print(f"Processamento concluído com sucesso!")
    print(f"Registros processados: {df_silver.count()}")
    print(f"Colunas finais: {df_silver.columns}")
else:
    print("Falha no processamento - DataFrame vazio")
