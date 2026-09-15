# Databricks notebook source
# =============================================================================
# CAMADA SILVER - MIGRACOES DE ID DE CARTAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_MOV_MIGRACOES_CARTAS.
Transformacao e limpeza de dados da Bronze para Silver.

CLASSIFICACAO DAMA-DMBOK: MOV (movimento) - cada linha registra um
identificador de carta MUDANDO de valor ao longo do tempo (a Scryfall unifica
duas cartas ou remove uma do catalogo, trocando o scryfall_id). Nao e Fato
(nao ha medida de negocio, so um evento de mudanca de identificador) nem
Dimensao/DOM (nao descreve uma entidade estavel) - daí o prefixo TB_MOV_.

ORIGEM (AUD-20 / #135, relocado nesta revisao): esta logica de resolucao de
cadeia de migracao vivia em TB_FATO_CARTAS.ipynb (attach_canonical_id /
_resolve_id_chain), anexando ID_SCRYFALL_CANONICO direto na tabela de cartas.
Com a separacao de Fatos por fonte (ver docstring de TB_FATO_PRECOS_CARTAS),
essa logica passa a viver aqui, na propria tabela de migracoes - Gold junta
por ID_CARTA_ANTIGO/ID_CARTA_CANONICO quando precisar resolver uma migracao
no meio de uma janela de analise.

RESOLUCAO EM CADEIA: A mesma migracoes pode encadear (A funde em B, B funde
em C) - _resolve_id_chain segue a cadeia ate o id final. Puro Python sobre um
dict pequeno (historico de migracoes, nao dado de carta) - sem exigir SQL
recursivo, que esta versao do Spark nao suporta via CTE. Testado isoladamente
em test_migration_chain.py.

CHAVE UNICA: ID_MIGRACAO (id do proprio registro de migracao na Scryfall -
sempre presente e nunca nulo na fonte, ver save_silver_table no fim do
notebook) - diferente de TB_FATO_CARTAS, aqui a chave e uma unica coluna NOT
NULL, Unity Catalog consegue declarar a constraint PRIMARY KEY de verdade.

REGRA "SEM ( ) { } NO DADO SILVER": DESC_NOTA e texto livre da Scryfall e
pode conter parenteses - mesma conversao pra colchete ([...]) usada em
TB_FATO_CARTAS, por consistencia em toda a camada Silver.

CONVENCAO DE NOME/CASE DE COLUNA (pedido do usuario): mesma de TB_FATO_CARTAS
(ver docstring de la) - nome de coluna 100% MAIUSCULO, valor de atributo em
Title_Case por palavra sem acento (normalizar_valor() em silver_utils.py),
exceto COD_/ID_/URL_* e texto livre longo.
"""

# =============================================================================
# BIBLIOTECAS UTILIZADAS
# =============================================================================
import logging
from pyspark.sql.functions import col

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

def _resolve_id_chain(direct_map):
    """
    Segue a cadeia de merges ID_CARTA_ANTIGO -> ID_CARTA_NOVO ate o id final
    (A mergeou em B, B mergeou em C -> A resolve pra C). Puro Python sobre um
    dict pequeno (historico de migracoes da Scryfall, nao dado de carta) - sem
    exigir SQL recursivo, que esta versao do Spark nao suporta via CTE.
    Testado isoladamente em test_migration_chain.py.
    """
    resolved = {}
    for start in direct_map:
        current = start
        seen = {start}
        hops = 0
        while current in direct_map and hops < 10:
            nxt = direct_map[current]
            if nxt in seen:
                # ciclo (nao deveria acontecer em dado real da Scryfall) - para
                # na melhor resolucao encontrada em vez de girar pra sempre
                break
            current = nxt
            seen.add(current)
            hops += 1
        resolved[start] = current
    return resolved

def transform_migrations_silver(df):
    """
    Transformacao especifica para tabela Migracoes de Id de Cartas, via SQL
    (spark.sql sobre temp views) seguida da resolucao de cadeia em Python.
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformacoes especificas para Migracoes de Id de Cartas...")

    df.createOrReplaceTempView("_migrations_bronze")

    # Estagio 0: SELECT explicito Bronze crua -> nome PT-BR final (ver
    # docstring do modulo) - nenhuma coluna sobra sem traducao.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _migrations_stage0 AS
        SELECT
            id AS ID_MIGRACAO,
            uri AS URL_SCRYFALL,
            performed_at AS DT_EXECUCAO,
            migration_strategy AS NME_ESTRATEGIA_MIGRACAO,
            old_scryfall_id AS ID_CARTA_ANTIGO,
            new_scryfall_id AS ID_CARTA_NOVO,
            note AS DESC_NOTA,
            metadata_id AS ID_CARTA_ASSOCIADA,
            metadata_lang AS COD_IDIOMA,
            metadata_name AS NME_CARTA_ASSOCIADA,
            metadata_set_code AS COD_COLECAO_ASSOCIADA,
            metadata_oracle_id AS ID_ORACLE_ASSOCIADO,
            metadata_collector_number AS NUM_COLECIONADOR_ASSOCIADO,
            ingestion_timestamp AS DT_INGESTAO,
            source AS NME_FONTE,
            endpoint AS DESC_URL_ORIGEM,
            source_file AS DESC_ARQUIVO_ORIGEM,
            bronze_run_id AS ID_EXECUCAO_BRONZE,
            bronze_ingestion_timestamp AS DT_INGESTAO_BRONZE
        FROM _migrations_bronze
    """)

    # Estagio 1: traducao de NME_ESTRATEGIA_MIGRACAO pra termo de negocio,
    # limpeza de DESC_NOTA (NA quando vazio + parenteses -> colchete, mesma
    # regra de TB_FATO_CARTAS), cast de data e derivacao de ANO_EXECUCAO/
    # MES_EXECUCAO a partir de DT_EXECUCAO - usadas so como partition_cols.
    df_final = spark.sql(r"""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (ids/colunas associadas, linhagem etc.) ja saiu do Estagio 0
            -- com nome PT-BR final e so passa direto.
            * EXCEPT (DT_EXECUCAO, NME_ESTRATEGIA_MIGRACAO, DESC_NOTA,
                      DT_INGESTAO, NME_FONTE, NME_CARTA_ASSOCIADA),

            to_date(DT_EXECUCAO) AS DT_EXECUCAO,
            CASE
                WHEN NME_ESTRATEGIA_MIGRACAO = 'merge' THEN 'Unificacao'
                WHEN NME_ESTRATEGIA_MIGRACAO = 'delete' THEN 'Remocao'
                ELSE NME_ESTRATEGIA_MIGRACAO
            END AS NME_ESTRATEGIA_MIGRACAO,
            CASE
                WHEN DESC_NOTA IS NULL OR DESC_NOTA = '' THEN 'NA'
                ELSE regexp_replace(regexp_replace(trim(DESC_NOTA), '\\(([^)]*)\\)', '[$1]'), '\\{([^}]*)\\}', '[$1]')
            END AS DESC_NOTA,
            to_timestamp(DT_INGESTAO) AS DT_INGESTAO,
            CASE WHEN NME_FONTE IS NULL OR NME_FONTE = '' THEN 'NA' ELSE normalizar_valor(NME_FONTE) END AS NME_FONTE,
            normalizar_valor(NME_CARTA_ASSOCIADA) AS NME_CARTA_ASSOCIADA,
            year(to_date(DT_EXECUCAO)) AS ANO_EXECUCAO,
            month(to_date(DT_EXECUCAO)) AS MES_EXECUCAO
        FROM _migrations_stage0
    """)

    logger.info(f"Transformacao Migracoes de Id de Cartas concluida: {df_final.count()} registros")
    return df_final

def attach_canonical_id(df_migrations):
    """
    Resolve a cadeia de unificacoes (ID_CARTA_ANTIGO -> ID_CARTA_NOVO) e
    anexa ID_CARTA_CANONICO - o id final apos seguir merges sucessivos.
    Estrategia 'Remocao' fica fora do mapa de resolucao (sem ID_CARTA_NOVO,
    nao ha pra onde apontar) - essas linhas mantem
    ID_CARTA_CANONICO = ID_CARTA_ANTIGO, unico comportamento possivel sem
    inventar um id que a Scryfall nao forneceu.
    """
    logger = logging.getLogger(__name__)

    # orderBy antes do collect(): sem ordem explicita, collect() nao garante a
    # mesma ordem de linhas entre runs - se uma carta migrar mais de uma vez
    # (ID_CARTA_ANTIGO repetido com ID_CARTA_NOVO diferente), o dict abaixo
    # pegaria um ID_CARTA_NOVO diferente a cada execucao. Ordenando por
    # DT_EXECUCAO (+ ID_MIGRACAO como desempate estavel), a migracao mais
    # recente sempre vence de forma deterministica.
    merge_rows = (
        df_migrations
        .filter("NME_ESTRATEGIA_MIGRACAO = 'Unificacao' AND ID_CARTA_NOVO IS NOT NULL")
        .select("ID_CARTA_ANTIGO", "ID_CARTA_NOVO", "DT_EXECUCAO", "ID_MIGRACAO")
        .distinct()
        .orderBy("ID_CARTA_ANTIGO", "DT_EXECUCAO", "ID_MIGRACAO")
        .collect()
    )
    direct_map = {}
    for r in merge_rows:
        direct_map[r["ID_CARTA_ANTIGO"]] = r["ID_CARTA_NOVO"]
    resolved_map = _resolve_id_chain(direct_map)

    if not resolved_map:
        return df_migrations.withColumn("ID_CARTA_CANONICO", col("ID_CARTA_ANTIGO"))

    df_map = spark.createDataFrame(
        list(resolved_map.items()), ["_old_id", "_canonical_id"]
    )
    df_map.createOrReplaceTempView("_migration_resolved_map")
    df_migrations.createOrReplaceTempView("_migrations_pre_canonical")

    df_result = spark.sql("""
        SELECT
            mig.*,
            coalesce(map._canonical_id, mig.ID_CARTA_ANTIGO) AS ID_CARTA_CANONICO
        FROM _migrations_pre_canonical mig
        LEFT JOIN _migration_resolved_map map
            ON mig.ID_CARTA_ANTIGO = map._old_id
    """)
    logger.info(f"ID_CARTA_CANONICO resolvido para {len(resolved_map)} ids migrados.")
    return df_result

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
processor = SilverTableProcessor("TB_MOV_MIGRACOES_CARTAS", config)

# Extracao da Bronze (nome real da tabela no catalog, minusculo)
df_bronze = processor.extract_from_bronze("migrations")

# Aplicar transformacao especifica e resolucao de cadeia (AUD-20 / #135,
# relocada de TB_FATO_CARTAS.ipynb - ver docstring da celula anterior)
df_silver_stage = processor.transform_data(df_bronze, transform_migrations_silver)
df_silver = attach_canonical_id(df_silver_stage)

# Salvar na Silver com merge incremental por ID_MIGRACAO
processor.save_silver_table(
    df_silver,
    partition_cols=["ANO_EXECUCAO", "MES_EXECUCAO"],
    key_column="ID_MIGRACAO",
    order_by_col="DT_INGESTAO",
    table_comment=get_table_comment("TB_MOV_MIGRACOES_CARTAS"),
    column_comments=get_column_comments("TB_MOV_MIGRACOES_CARTAS")
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
