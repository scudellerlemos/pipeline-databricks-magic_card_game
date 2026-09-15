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
_resolve_id_chain), anexando Id_scryfall_canonico direto na tabela de cartas.
Com a separacao de Fatos por fonte (ver docstring de TB_FATO_PRECOS_CARTAS),
essa logica passa a viver aqui, na propria tabela de migracoes - Gold junta
por Id_carta_antigo/Id_carta_canonico quando precisar resolver uma migracao
no meio de uma janela de analise.

RESOLUCAO EM CADEIA: A mesma migracoes pode encadear (A funde em B, B funde
em C) - _resolve_id_chain segue a cadeia ate o id final. Puro Python sobre um
dict pequeno (historico de migracoes, nao dado de carta) - sem exigir SQL
recursivo, que esta versao do Spark nao suporta via CTE. Testado isoladamente
em test_migration_chain.py.

CHAVE UNICA: Id_migracao (id do proprio registro de migracao na Scryfall -
sempre presente e nunca nulo na fonte, ver save_silver_table no fim do
notebook) - diferente de TB_FATO_CARTAS, aqui a chave e uma unica coluna NOT
NULL, Unity Catalog consegue declarar a constraint PRIMARY KEY de verdade.

REGRA "SEM ( ) { } NO DADO SILVER": Desc_nota e texto livre da Scryfall e
pode conter parenteses - mesma conversao pra colchete ([...]) usada em
TB_FATO_CARTAS, por consistencia em toda a camada Silver.

CONVENCAO DE NOME/CASE DE COLUNA: mesma de TB_FATO_CARTAS (ver docstring de
la) - prefixo semantico + primeira letra maiuscula, resto minusculo, sem
acento, 100% PT-BR a partir da Silver.
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
    Segue a cadeia de merges Id_carta_antigo -> Id_carta_novo ate o id final
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
            id AS Id_migracao,
            uri AS Url_scryfall,
            performed_at AS Dt_execucao,
            migration_strategy AS Nme_estrategia_migracao,
            old_scryfall_id AS Id_carta_antigo,
            new_scryfall_id AS Id_carta_novo,
            note AS Desc_nota,
            metadata_id AS Id_carta_associada,
            metadata_lang AS Cod_idioma,
            metadata_name AS Nme_carta_associada,
            metadata_set_code AS Cod_colecao_associada,
            metadata_oracle_id AS Id_oracle_associado,
            metadata_collector_number AS Num_colecionador_associado,
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _migrations_bronze
    """)

    # Estagio 1: traducao de Nme_estrategia_migracao pra termo de negocio,
    # limpeza de Desc_nota (NA quando vazio + parenteses -> colchete, mesma
    # regra de TB_FATO_CARTAS), cast de data e derivacao de Ano_execucao/
    # Mes_execucao a partir de Dt_execucao - usadas so como partition_cols.
    df_final = spark.sql(r"""
        SELECT
            -- so as colunas com transformacao real ficam explicitas (mesmo
            -- precedente de TB_FATO_CARTAS.ipynb _cards_stage2); o resto
            -- (ids/colunas associadas, linhagem etc.) ja saiu do Estagio 0
            -- com nome PT-BR final e so passa direto.
            * EXCEPT (Dt_execucao, Nme_estrategia_migracao, Desc_nota,
                      Dt_ingestao, Nme_fonte),

            to_date(Dt_execucao) AS Dt_execucao,
            CASE
                WHEN Nme_estrategia_migracao = 'merge' THEN 'Unificacao'
                WHEN Nme_estrategia_migracao = 'delete' THEN 'Remocao'
                ELSE Nme_estrategia_migracao
            END AS Nme_estrategia_migracao,
            CASE
                WHEN Desc_nota IS NULL OR Desc_nota = '' THEN 'NA'
                ELSE regexp_replace(regexp_replace(trim(Desc_nota), '\\(([^)]*)\\)', '[$1]'), '\\{([^}]*)\\}', '[$1]')
            END AS Desc_nota,
            to_timestamp(Dt_ingestao) AS Dt_ingestao,
            CASE WHEN Nme_fonte IS NULL OR Nme_fonte = '' THEN 'NA' ELSE initcap(trim(Nme_fonte)) END AS Nme_fonte,
            year(to_date(Dt_execucao)) AS Ano_execucao,
            month(to_date(Dt_execucao)) AS Mes_execucao
        FROM _migrations_stage0
    """)

    logger.info(f"Transformacao Migracoes de Id de Cartas concluida: {df_final.count()} registros")
    return df_final

def attach_canonical_id(df_migrations):
    """
    Resolve a cadeia de unificacoes (Id_carta_antigo -> Id_carta_novo) e
    anexa Id_carta_canonico - o id final apos seguir merges sucessivos.
    Estrategia 'Remocao' fica fora do mapa de resolucao (sem Id_carta_novo,
    nao ha pra onde apontar) - essas linhas mantem
    Id_carta_canonico = Id_carta_antigo, unico comportamento possivel sem
    inventar um id que a Scryfall nao forneceu.
    """
    logger = logging.getLogger(__name__)

    # orderBy antes do collect(): sem ordem explicita, collect() nao garante a
    # mesma ordem de linhas entre runs - se uma carta migrar mais de uma vez
    # (Id_carta_antigo repetido com Id_carta_novo diferente), o dict abaixo
    # pegaria um Id_carta_novo diferente a cada execucao. Ordenando por
    # Dt_execucao (+ Id_migracao como desempate estavel), a migracao mais
    # recente sempre vence de forma deterministica.
    merge_rows = (
        df_migrations
        .filter("Nme_estrategia_migracao = 'Unificacao' AND Id_carta_novo IS NOT NULL")
        .select("Id_carta_antigo", "Id_carta_novo", "Dt_execucao", "Id_migracao")
        .distinct()
        .orderBy("Id_carta_antigo", "Dt_execucao", "Id_migracao")
        .collect()
    )
    direct_map = {}
    for r in merge_rows:
        direct_map[r["Id_carta_antigo"]] = r["Id_carta_novo"]
    resolved_map = _resolve_id_chain(direct_map)

    if not resolved_map:
        return df_migrations.withColumn("Id_carta_canonico", col("Id_carta_antigo"))

    df_map = spark.createDataFrame(
        list(resolved_map.items()), ["_old_id", "_canonical_id"]
    )
    df_map.createOrReplaceTempView("_migration_resolved_map")
    df_migrations.createOrReplaceTempView("_migrations_pre_canonical")

    df_result = spark.sql("""
        SELECT
            mig.*,
            coalesce(map._canonical_id, mig.Id_carta_antigo) AS Id_carta_canonico
        FROM _migrations_pre_canonical mig
        LEFT JOIN _migration_resolved_map map
            ON mig.Id_carta_antigo = map._old_id
    """)
    logger.info(f"Id_carta_canonico resolvido para {len(resolved_map)} ids migrados.")
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

# Salvar na Silver com merge incremental por Id_migracao
processor.save_silver_table(
    df_silver,
    partition_cols=["Ano_execucao", "Mes_execucao"],
    key_column="Id_migracao",
    order_by_col="Dt_ingestao",
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
