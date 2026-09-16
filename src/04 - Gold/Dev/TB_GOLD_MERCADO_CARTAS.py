# Databricks notebook source
# =============================================================================
# CAMADA GOLD - MERCADO DE CARTAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para construção da tabela Gold TB_GOLD_MERCADO_CARTAS.
Junta Silver -> Gold: uma única tabela de consumo (analista/BI/Genie) sobre
mercado de cartas, sem precisar conhecer Bronze/Silver.

GRAO: uma linha por cotação de preço de uma impressão de carta
(ID_CARTA, DT_COTACAO). Chave: (ID_CARTA, DT_COTACAO).

TABELAS SILVER USADAS (4 de 6):
- TB_FATO_CARTAS (driver): 1 linha por impressão de carta.
- TB_FATO_PRECOS_CARTAS (INNER JOIN por NME_CARTA): histórico de cotação de
  preço, mesmo grão de junção já documentado na origem (ver docstring de
  TB_FATO_PRECOS_CARTAS.py: "quem precisar combinar carta com preco faz o
  join na Gold por NME_CARTA"). INNER porque DT_COTACAO é parte da chave
  desta tabela Gold - carta sem nenhuma cotação de preço não tem linha
  possível aqui (não há valor artificial pra DT_COTACAO sem mascarar a
  chave). Ver seção de Data Quality abaixo para a contagem de cartas
  excluídas por este motivo.
- TB_DIM_COLECOES (LEFT JOIN por COD_COLECAO): nome/bloco/data de lançamento
  da coleção, denormalizados pro consumidor não precisar de um 2º join.
- TB_FATO_ESCLARECIMENTOS_CARTAS (agregada por ID_ORACLE, LEFT JOIN):
  quantidade e data do esclarecimento de regras mais recente por carta -
  proxy de o quanto uma carta é discutida/tem regra complexa.

TABELAS SILVER *NÃO* USADAS (2 de 6) - desvio deliberado, documentado:
- TB_DOM_SIMBOLOS: lista de referência de símbolos de mana pra decodificar
  texto de carta (DESC_CUSTO_MANA/DESC_CARTA) - não tem chave de junção
  própria pro grão desta Gold (não é FK de carta/preço, é tabela de apoio
  pra quem for parsear texto livre). Incluir aqui exigiria inventar uma
  junção nova sem benefício analítico.
- TB_MOV_MIGRACOES_CARTAS: log de troca de id da Scryfall, já resolvido
  dentro da própria Silver (TB_FATO_CARTAS.ID_CARTA já é o id vigente pra
  cada linha). Não tem grão compatível com "1 carta x 1 cotação de preço" -
  juntar aqui só pra "usar todas as tabelas" seria modelagem forçada sem
  necessidade analítica real (ver regra do prompt: não force modelagem sem
  benefício claro).

REGRA DE NULO (GOLD): categórico/descritivo NULO -> literal 'Nao_Identificado'
(nunca 'NA'/vazio/hífen). Medida (VLR_USD/EUR/TIX) NULA continua NULA - 0
não é válido pra "sem cotação" (mesma semântica já documentada na Silver).
QTD_ESCLARECIMENTOS NULO -> 0 (zero é valor real: carta nunca teve ruling).
Data NULA -> sentinela 1001-01-01. PK (ID_CARTA, DT_COTACAO) nunca é
mascarada - se vier NULA, a run falha em _declare_primary_key (gold_utils.py).
"""

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import logging

# =============================================================================
# CARREGAMENTO DO MODULO UTILITARIO
# =============================================================================

# COMMAND ----------

# MAGIC %run "../../00 - Common/Dev/base_utils"

# COMMAND ----------

# MAGIC %run ./gold_utils

# COMMAND ----------

# MAGIC %run ./gold_column_docs

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


def transform_mercado_cartas_gold(df_cartas, df_colecoes, df_precos, df_esclarecimentos):
    """
    Transformação Gold via SQL (spark.sql sobre temp views) - join das 4
    tabelas Silver descritas na docstring do notebook.
    """
    logger = logging.getLogger(__name__)
    logger.info("Iniciando join Gold - TB_GOLD_MERCADO_CARTAS...")

    df_cartas.createOrReplaceTempView("_cartas")
    df_colecoes.createOrReplaceTempView("_colecoes")
    df_precos.createOrReplaceTempView("_precos")
    df_esclarecimentos.createOrReplaceTempView("_esclarecimentos")

    # DATA QUALITY - join-caused exclusion: cartas sem NENHUMA cotação de
    # preço são excluídas pelo INNER JOIN abaixo (grão exige DT_COTACAO não
    # nula). Contagem logada aqui, antes do join, pra não depender da tabela
    # final já gravada.
    qtd_cartas_sem_cotacao = spark.sql("""
        SELECT COUNT(DISTINCT c.ID_CARTA)
        FROM _cartas c
        LEFT JOIN _precos p ON c.NME_CARTA = p.NME_CARTA
        WHERE p.NME_CARTA IS NULL
    """).collect()[0][0] or 0
    nivel = "⚠️" if qtd_cartas_sem_cotacao > 0 else "✅"
    print(f"{nivel} DQ [pré-join] cartas_excluidas_sem_cotacao_de_preco: {qtd_cartas_sem_cotacao}")

    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _esclarecimentos_agg AS
        SELECT
            ID_ORACLE,
            COUNT(*) AS QTD_ESCLARECIMENTOS,
            MAX(DT_PUBLICACAO) AS DT_ULTIMO_ESCLARECIMENTO
        FROM _esclarecimentos
        GROUP BY ID_ORACLE
    """)

    df_final = spark.sql("""
        SELECT
            c.ID_CARTA,
            c.ID_ORACLE,
            c.NME_CARTA,
            c.NME_TIPO_CARTA,
            c.NME_RARIDADE,
            c.NME_CATEGORIA_COR,
            c.COD_CORES,
            c.QTD_CUSTO_MANA,
            c.COD_COLECAO,
            COALESCE(col.NME_COLECAO, 'Nao_Identificado') AS NME_COLECAO,
            COALESCE(col.NME_BLOCO, 'Nao_Identificado') AS NME_BLOCO,
            COALESCE(col.DT_LANCAMENTO, DATE'1001-01-01') AS DT_LANCAMENTO_COLECAO,
            p.DT_INGESTAO AS DT_COTACAO,
            p.VLR_USD,
            p.VLR_EUR,
            p.VLR_TIX,
            COALESCE(e.QTD_ESCLARECIMENTOS, 0) AS QTD_ESCLARECIMENTOS,
            COALESCE(e.DT_ULTIMO_ESCLARECIMENTO, DATE'1001-01-01') AS DT_ULTIMO_ESCLARECIMENTO,
            YEAR(p.DT_INGESTAO) AS ANO_COTACAO,
            MONTH(p.DT_INGESTAO) AS MES_COTACAO
        FROM _cartas c
        INNER JOIN _precos p ON c.NME_CARTA = p.NME_CARTA
        LEFT JOIN _colecoes col ON c.COD_COLECAO = col.COD_COLECAO
        LEFT JOIN _esclarecimentos_agg e ON c.ID_ORACLE = e.ID_ORACLE
    """)

    logger.info(f"Transformação Gold concluída: {df_final.count()} registros")
    return df_final


# =============================================================================
# CONFIGURACAO
# =============================================================================
config = create_manual_config(get_secret("catalog_name"), get_secret("s3_bucket"))
setup_unity_catalog(config['catalog_name'], config['schema_gold'])

# COMMAND ----------

# =============================================================================
# AUDITORIA - INICIO DO RUN
# =============================================================================
audit_run = start_audit_run()
audit_status = "SUCESSO"

# COMMAND ----------

# =============================================================================
# PROCESSAMENTO USANDO GOLD_UTILS
# =============================================================================
processor = GoldTableProcessor("TB_GOLD_MERCADO_CARTAS", config)

df_cartas = processor.extract_from_silver("TB_FATO_CARTAS")
df_colecoes = processor.extract_from_silver("TB_DIM_COLECOES")
df_precos = processor.extract_from_silver("TB_FATO_PRECOS_CARTAS")
df_esclarecimentos = processor.extract_from_silver("TB_FATO_ESCLARECIMENTOS_CARTAS")

qtd_lidos = df_cartas.count() + df_colecoes.count() + df_precos.count() + df_esclarecimentos.count()

df_gold = transform_mercado_cartas_gold(df_cartas, df_colecoes, df_precos, df_esclarecimentos)
qtd_processados = df_gold.count()

try:
    processor.save_gold_table(
        df_gold,
        partition_cols=["ANO_COTACAO", "MES_COTACAO"],
        key_column=["ID_CARTA", "DT_COTACAO"],
        table_comment=get_table_comment("TB_GOLD_MERCADO_CARTAS"),
        column_comments=get_column_comments("TB_GOLD_MERCADO_CARTAS")
    )
except RuntimeError:
    audit_status = "FALHA_DQ_PK"
    raise

# COMMAND ----------

# =============================================================================
# DATA QUALITY (pós-carga) E AUDITORIA - FIM DO RUN
# =============================================================================
full_table_name = f"{config['catalog_name']}.{config['schema_gold']}.TB_GOLD_MERCADO_CARTAS"

dq_resultados = run_data_quality_checks(spark, full_table_name, {
    "fk_null_id_oracle": f"SELECT COUNT(*) FROM {full_table_name} WHERE ID_ORACLE IS NULL",
    "fk_colecao_nao_encontrada": f"SELECT COUNT(*) FROM {full_table_name} WHERE NME_COLECAO = 'Nao_Identificado'",
    "valor_negativo_preco": f"""SELECT COUNT(*) FROM {full_table_name}
        WHERE VLR_USD < 0 OR VLR_EUR < 0 OR VLR_TIX < 0""",
    "null_residual_categorico": f"""SELECT COUNT(*) FROM {full_table_name}
        WHERE NME_CARTA IS NULL OR NME_TIPO_CARTA IS NULL OR NME_RARIDADE IS NULL
           OR NME_CATEGORIA_COR IS NULL OR COD_CORES IS NULL
           OR NME_COLECAO IS NULL OR NME_BLOCO IS NULL""",
})

record_gold_audit(
    spark, config['catalog_name'], config['schema_gold'], "TB_GOLD_MERCADO_CARTAS",
    audit_run,
    qtd_lidos=qtd_lidos,
    qtd_processados=qtd_processados,
    qtd_inseridos_atualizados=qtd_processados,
    dq_resultados=dq_resultados,
    status=audit_status
)

# =============================================================================
# VALIDACAO E LOGS
# =============================================================================
print(f"Processamento concluído com sucesso!")
print(f"Registros processados: {qtd_processados}")
print(f"Colunas finais: {df_gold.columns}")
