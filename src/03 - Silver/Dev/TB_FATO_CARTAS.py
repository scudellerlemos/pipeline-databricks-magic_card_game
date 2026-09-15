# Databricks notebook source
# =============================================================================
# CAMADA SILVER - CARTAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_FATO_CARTAS.
Transformação e limpeza de dados da Bronze para Silver.

CLASSIFICAÇÃO DAMA-DMBOK (#116): Fato - uma linha por impressão de carta
(grão), com medidas quantitativas (Qtd_custo_mana, Qtd_cores) e chaves
estrangeiras implícitas pra dimensões (Cod_colecao -> TB_DIM_COLECOES). Daí o
prefixo TB_FATO_ e o nome sem o segmento redundante "SILVER" (já implícito no
schema silver.* do Unity Catalog).

CHAVE ÚNICA: Id_carta (ver save_silver_table no fim do notebook) - NOT NULL
por natureza, então a constraint PRIMARY KEY no Unity Catalog é aplicada com
sucesso (além do COMMENT ON TABLE sempre gravado).

CONVENÇÃO DE NOME/CASE DE COLUNA: prefixo semântico já usado no projeto
(Id_/Nme_/Desc_/Cod_/Dt_/Qtd_/Num_/Url_) + primeira letra maiúscula, resto
minúsculo, sem acento - todas as colunas 100% PT-BR a partir da Silver
(pedido do usuário; Bronze/Ingestion continuam passthrough 1:1 da fonte).

USO DE SILVER_UTILS.PY:
- Centralização de funções comuns
- Padronização de processamento
- Redução de código duplicado

TRANSFORMAÇÃO DE NEGÓCIO EM SQL:
- Toda a lógica de limpeza/derivação roda via spark.sql() sobre temp views,
  em vez de encadear .withColumn() no DataFrame API.
- Cada view representa um estágio da transformação.

ESTÁGIO 0 (PADRONIZAÇÃO DE NOMES) - AUD-20 (#135) / #115:
- Bronze é passthrough 1:1 da Scryfall/legado (id, name, manaCost, set...).
  O Estágio 0 faz o SELECT explícito de toda coluna da Bronze cards pro nome
  PT-BR final (ver CONVENÇÃO acima) - nenhuma coluna sobra sem tradução.
- Correção de bug (achado nesta revisão, não fazia parte do pedido original):
  os estágios seguintes (herdados) tinham um bloco de fallback que checava
  `nome_pt_br in df.columns`, onde `df` é o DataFrame CRU da Bronze (colunas
  em inglês/camelCase). Essa checagem NUNCA era verdadeira (ex.: "NME_CARD"
  nunca está em ["id","name","manaCost",...]), então TODA coluna de negócio
  (nome, artista, raridade, tipo, custo de mana...) caía sempre no fallback
  NULL, silenciosamente, em toda execução. Como o Estágio 0 agora garante
  (via CARDS_SCHEMA da Ingestion) que toda coluna renomeada sempre existe, o
  bloco de fallback foi removido - ele resolvia um schema-drift que o
  contrato da Ingestion já impede, e escondia esse bug em vez de proteger
  contra ele. Único fallback condicional mantido: Id_oracle (oracle_id é
  novo - #135 - pode faltar em partição gravada antes da mudança).

SEPARAÇÃO DE PREÇO E MIGRAÇÃO (#115): até esta revisão, esta tabela também
carregava o histórico diário de preço (junção por Nme_carta com a Bronze
card_prices) e o id canônico pós-migração da Scryfall (Bronze migrations),
o que forçava a chave única a incluir Dt_ingestao_preco (coluna que podia
ser NULA) e degradava a constraint PRIMARY KEY pra comentário best-effort.
Preço e migração têm grão e cadência de atualização próprios - viraram
tabelas Silver dedicadas (TB_FATO_PRECOS_CARTAS, TB_MOV_MIGRACOES_CARTAS),
e esta tabela voltou a ter grão só de "impressão de carta", chave simples
(Id_carta) e sem essas duas fontes na extração. Consumidores Gold que
precisam de preço ou do id canônico pós-migração devem juntar essas tabelas
por Nme_carta / Id_carta, respectivamente.

REGRA "SEM ( ) { } NO DADO SILVER" (pedido do usuário):
- Texto de carta/custo de mana/legalidades vêm da Scryfall com notação de
  símbolo entre chaves (ex.: "{2}{U}{U}") e texto de lembrete entre
  parênteses (ex.: "(Add one mana of any color.)"), e legalities é um dict
  serializado. Todos convertidos pra notação com colchetes ([...]) no
  Estágio 3 - símbolos comuns viram um rótulo legível (ex.: "[White]"), o
  resto (custo genérico, mana híbrida/phyrexiana, loyalty, parênteses) usa um
  catch-all genérico que preserva o conteúdo trocando só o delimitador.
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

def transform_cards_silver(df):
    """
    Transformação específica para tabela Cartas, via SQL (spark.sql sobre temp views)
    """
    if not df:
        return None

    logger = logging.getLogger(__name__)
    logger.info("Iniciando transformações específicas para Cartas...")

    df.createOrReplaceTempView("_cards_bronze")

    # Estágio 0: SELECT explícito Bronze crua -> nome PT-BR final (ver
    # docstring do módulo). oracle_id é a única coluna aqui que pode não
    # existir ainda em partições antigas da Bronze (capturada a partir de
    # #135 na Ingestion) - fallback NULL tipado, sem quebrar o resto do
    # pipeline; todas as outras colunas vêm do CARDS_SCHEMA da Ingestion e
    # sempre existem (valor pode ser NULL, a coluna nunca falta).
    if "oracle_id" in df.columns:
        oracle_id_select = "oracle_id AS Id_oracle"
    else:
        logger.warning("Coluna oracle_id ausente na Bronze cards - Id_oracle ficará NULL (ver #135).")
        oracle_id_select = "CAST(NULL AS STRING) AS Id_oracle"

    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _cards_stage0 AS
        SELECT
            id AS Id_carta,
            {oracle_id_select},
            name AS Nme_carta,
            manaCost AS Desc_custo_mana,
            cmc AS Qtd_custo_mana,
            colors AS Cod_cores,
            colorIdentity AS Cod_identidade_cor,
            type AS Nme_tipo_carta,
            types AS Desc_tipos,
            subtypes AS Desc_subtipos,
            rarity AS Nme_raridade,
            `set` AS Cod_colecao,
            setName AS Nme_colecao,
            text AS Desc_carta,
            artist AS Nme_artista,
            number AS Num_colecionador,
            power AS Nme_forca,
            toughness AS Nme_resistencia,
            layout AS Nme_disposicao_carta,
            multiverseid AS Id_multiverso,
            imageUrl AS Url_imagem,
            variations AS Cod_variacoes,
            foreignNames AS Desc_nomes_estrangeiros,
            printings AS Desc_impressoes,
            originalText AS Desc_carta_original,
            originalType AS Nme_tipo_original,
            legalities AS Desc_legalidades,
            ingestion_timestamp AS Dt_ingestao,
            source AS Nme_fonte,
            endpoint AS Desc_url_origem,
            source_file AS Desc_arquivo_origem,
            bronze_run_id AS Id_execucao_bronze,
            bronze_ingestion_timestamp AS Dt_ingestao_bronze
        FROM _cards_bronze
    """)

    # Estágio 1: filtro temporal (últimos 5 anos). Dt_ingestao sempre existe
    # (coluna técnica obrigatória da Bronze) - sem fallback aqui: um NULL
    # nela zeraria silenciosamente o filtro (WHERE NULL >= ...) e descartaria
    # o lote inteiro sem erro, pior que um crash.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _cards_stage1 AS
        SELECT *
        FROM _cards_stage0
        WHERE Dt_ingestao >= add_months(current_date(), -60)
    """)

    # Estágio 2: limpeza/derivação de negócio. \\[ \\] no literal SQL: Spark
    # desfaz um backslash simples antes de um caractere sem escape
    # reconhecido (aqui viraria '[|]|"', uma regex válida mas errada - classe
    # de caracteres, não escape literal). Dobrar o backslash na fonte Python
    # garante que sobra um só depois do unescaping do Spark.
    spark.sql(r"""
        CREATE OR REPLACE TEMP VIEW _cards_stage2 AS
        SELECT
            * EXCEPT (Nme_carta, Nme_artista, Nme_raridade, Nme_colecao, Desc_carta,
                      Desc_custo_mana, Qtd_custo_mana, Nme_forca, Nme_resistencia,
                      Cod_colecao, Desc_impressoes, Cod_variacoes, Cod_cores,
                      Cod_identidade_cor, Desc_subtipos, Desc_tipos, Nme_tipo_carta,
                      Dt_ingestao),

            initcap(trim(Nme_carta)) AS Nme_carta,
            initcap(trim(Nme_artista)) AS Nme_artista,
            initcap(trim(Nme_raridade)) AS Nme_raridade,
            initcap(trim(Nme_colecao)) AS Nme_colecao,
            CASE WHEN Desc_carta IS NULL OR Desc_carta = '' THEN 'NA' ELSE trim(Desc_carta) END AS Desc_carta,
            CASE WHEN Desc_custo_mana IS NULL OR Desc_custo_mana = '' THEN 'NA' ELSE trim(Desc_custo_mana) END AS Desc_custo_mana,
            coalesce(Qtd_custo_mana, 0) AS Qtd_custo_mana,
            -- Nme_forca/Nme_resistencia são STRING na Bronze e podem legitimamente
            -- valer "*", "1+*" etc. (poder/resistência variável - ex.: Tarmogoyf).
            -- Fallback como string ('0'), não int: coalesce(STRING_COL, 0) força
            -- um implicit cast pra BIGINT, que quebra (CAST_INVALID_INPUT) no
            -- primeiro valor não-numérico.
            coalesce(Nme_forca, '0') AS Nme_forca,
            coalesce(Nme_resistencia, '0') AS Nme_resistencia,
            upper(Cod_colecao) AS Cod_colecao,
            regexp_replace(Desc_impressoes, '\\[|\\]|"', '') AS Desc_impressoes,
            regexp_replace(Cod_variacoes, '\\[|\\]|"', '') AS Cod_variacoes,
            regexp_replace(Cod_cores, '\\[|\\]|"', '') AS Cod_cores,
            regexp_replace(Cod_identidade_cor, '\\[|\\]|"', '') AS Cod_identidade_cor,
            regexp_replace(Desc_subtipos, '\\[|\\]|"', '') AS Desc_subtipos,
            CASE WHEN Desc_tipos IS NULL OR Desc_tipos = '' THEN 'NA' ELSE Desc_tipos END AS Desc_tipos,

            -- Nme_tipo_carta / Desc_detalhe_tipo_carta: Planeswalker é tipo
            -- isolado; "—" (em dash) separa tipo principal de subtipo
            -- descritivo. As duas colunas saem da mesma origem.
            CASE
                WHEN Nme_tipo_carta IS NULL THEN NULL
                WHEN lower(Nme_tipo_carta) LIKE '%planeswalker%' THEN 'Planeswalker'
                WHEN instr(Nme_tipo_carta, '—') > 0 THEN trim(split(Nme_tipo_carta, '—', 2)[0])
                ELSE trim(Nme_tipo_carta)
            END AS Nme_tipo_carta,
            CASE
                WHEN Nme_tipo_carta IS NULL THEN NULL
                WHEN lower(Nme_tipo_carta) LIKE '%planeswalker%' THEN Nme_tipo_carta
                WHEN instr(Nme_tipo_carta, '—') > 0 THEN trim(split(Nme_tipo_carta, '—', 2)[1])
                ELSE 'NA'
            END AS Desc_detalhe_tipo_carta,

            to_timestamp(Dt_ingestao) AS Dt_ingestao
        FROM _cards_stage1
    """)

    # Estágio 3: Cod_cores/Desc_subtipos colorless-default (pós-limpeza) e
    # eliminação de "(" ")" "{" "}" do dado Silver (pedido do usuário - esses
    # caracteres sinalizam dado ainda não transformado). \\{ \\} \\( \\) no
    # literal SQL pelo mesmo motivo do Estágio 2 (Spark desfaz backslash
    # simples antes de escape não reconhecido).
    spark.sql(r"""
        CREATE OR REPLACE TEMP VIEW _cards_stage3 AS
        SELECT
            * EXCEPT (Cod_cores, Desc_subtipos, Desc_carta, Desc_custo_mana,
                      Desc_carta_original, Desc_legalidades, Desc_nomes_estrangeiros),

            CASE WHEN Cod_cores IS NULL OR Cod_cores = '' THEN 'Colorless' ELSE Cod_cores END AS Cod_cores,
            CASE WHEN Desc_subtipos IS NULL OR Desc_subtipos = '' THEN 'NA' ELSE Desc_subtipos END AS Desc_subtipos,

            -- Desc_carta: substituições nomeadas pros símbolos de mana mais
            -- comuns (mais legível que colchete genérico), seguidas de dois
            -- catch-alls genéricos: qualquer "{...}" restante (custo
            -- numérico, mana híbrida {W/U}, phyrexiana {W/P}, loyalty
            -- {+1}/{-1} - fora da lista nomeada) e qualquer "(...)" (texto
            -- de lembrete). ponytail: não trata "{" ou "(" aninhados dentro
            -- do mesmo tipo (não ocorre em texto de carta real da Scryfall).
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(
            regexp_replace(Desc_carta, '\\{W\\}', '[White]'),
                                '\\{U\\}', '[Blue]'),
                                '\\{B\\}', '[Black]'),
                                '\\{R\\}', '[Red]'),
                                '\\{G\\}', '[Green]'),
                                '\\{C\\}', '[Colorless]'),
                                '\\{X\\}', '[X]'),
                                '\\{T\\}', '[Tap]'),
                                '\\{Q\\}', '[Untap]'),
                                '\\{S\\}', '[Snow]'),
                                '\\{E\\}', '[Energy]'),
                                '\\{([^}]*)\\}', '[$1]'),
                                '\\(([^)]*)\\)', '[$1]') AS Desc_carta,

            -- Desc_custo_mana: notação puramente simbólica (ex.: "{2}{U}{U}") -
            -- só o catch-all genérico já resolve, sem precisar da lista nomeada.
            regexp_replace(
            regexp_replace(Desc_custo_mana, '\\{([^}]*)\\}', '[$1]'),
                                             '\\(([^)]*)\\)', '[$1]') AS Desc_custo_mana,

            -- Desc_carta_original: texto pré-errata, mesma notação de Desc_carta.
            regexp_replace(
            regexp_replace(Desc_carta_original, '\\{([^}]*)\\}', '[$1]'),
                                                  '\\(([^)]*)\\)', '[$1]') AS Desc_carta_original,

            -- Desc_legalidades: dict serializado (json.dumps) vindo direto da
            -- Bronze - chaves de dict viram colchete pela mesma regra.
            regexp_replace(
            regexp_replace(Desc_legalidades, '\\{([^}]*)\\}', '[$1]'),
                                              '\\(([^)]*)\\)', '[$1]') AS Desc_legalidades,

            -- Desc_nomes_estrangeiros: lista de dicts serializada (um dict por
            -- idioma, sem aninhamento) - mesma regra.
            regexp_replace(
            regexp_replace(Desc_nomes_estrangeiros, '\\{([^}]*)\\}', '[$1]'),
                                                      '\\(([^)]*)\\)', '[$1]') AS Desc_nomes_estrangeiros
        FROM _cards_stage2
    """)

    # Estágio 4: Nme_categoria_cor/Qtd_cores (derivados de Cod_cores e
    # Desc_custo_mana já resolvidos nos estágios anteriores) e
    # Ano_ingestao/Mes_ingestao (partição física, derivados de Dt_ingestao -
    # #115, no lugar de Ano/Mes_ingestao_preco removidos com attach_prices).
    df_silver = spark.sql("""
        SELECT
            *,
            CASE
                WHEN Cod_cores = 'Colorless' THEN 'Colorless'
                WHEN size(split(Cod_cores, ',')) = 1 THEN 'Mono'
                WHEN size(split(Cod_cores, ',')) = 2 THEN 'Dual Color'
                WHEN size(split(Cod_cores, ',')) >= 3 THEN 'Multicolor'
                ELSE 'Mono'
            END AS Nme_categoria_cor,
            CASE
                WHEN Desc_custo_mana IS NULL OR Desc_custo_mana = 'NA' THEN 0
                ELSE length(regexp_replace(upper(Desc_custo_mana), '[^WUBRG]', ''))
            END AS Qtd_cores,
            year(Dt_ingestao) AS Ano_ingestao,
            month(Dt_ingestao) AS Mes_ingestao
        FROM _cards_stage3
    """)

    logger.info(f"Transformação Cartas concluída: {df_silver.count()} registros")
    return df_silver

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
# Criar processor - #116: TB_FATO_CARTAS (Fato, ver docstring da célula anterior)
processor = SilverTableProcessor("TB_FATO_CARTAS", config)

# Extração da Bronze (cards) e transformação específica.
df_cards_bronze = processor.extract_from_bronze("cards")
df_silver = processor.transform_data(df_cards_bronze, transform_cards_silver)

# Salvar na Silver com particionamento e merge incremental por Id_carta - #115:
# chave voltou a ser só Id_carta (identificador único por impressão) desde
# que preço e migração saíram desta tabela (ver docstring da célula
# anterior). partition_cols por Ano_ingestao/Mes_ingestao (data de coleta do
# dado de carta, não mais de preço).
# order_by_col=Dt_ingestao: se o lote tiver mais de uma linha para a mesma
# chave (reprocessamento), mantém a linha da ingestão mais recente em vez de
# uma linha arbitrária (AUD-09).
processor.save_silver_table(
    df_silver,
    partition_cols=["Ano_ingestao", "Mes_ingestao"],
    key_column="Id_carta",
    order_by_col="Dt_ingestao",
    table_comment=get_table_comment("TB_FATO_CARTAS"),
    column_comments=get_column_comments("TB_FATO_CARTAS")
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
