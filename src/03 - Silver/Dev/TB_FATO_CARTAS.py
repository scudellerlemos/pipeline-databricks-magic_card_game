# Databricks notebook source
# =============================================================================
# CAMADA SILVER - CARTAS - MAGIC: THE GATHERING
# =============================================================================
"""
Script Python para processamento da tabela TB_FATO_CARTAS.
Transformação e limpeza de dados da Bronze para Silver.

CLASSIFICAÇÃO DAMA-DMBOK (#116): Fato - uma linha por impressão de carta
(grão), com medidas quantitativas (QTD_CUSTO_MANA, QTD_CORES) e chaves
estrangeiras implícitas pra dimensões (COD_COLECAO -> TB_DIM_COLECOES). Daí o
prefixo TB_FATO_ e o nome sem o segmento redundante "SILVER" (já implícito no
schema silver.* do Unity Catalog).

CHAVE ÚNICA: ID_CARTA (ver save_silver_table no fim do notebook) - NOT NULL
por natureza, então a constraint PRIMARY KEY no Unity Catalog é aplicada com
sucesso (além do COMMENT ON TABLE sempre gravado).

CONVENÇÃO DE NOME/CASE DE COLUNA (pedido do usuário): nome de coluna 100%
MAIÚSCULO (prefixo semântico já usado no projeto - ID_/NME_/DESC_/COD_/DT_/
QTD_/NUM_/URL_ - + resto do nome, ex.: NME_CARTA). Valor de atributo (colunas
de nome/categoria) em Title_Case por palavra, sem acento, espaço virando "_"
(ex.: "mana vermelha" -> "Mana_Vermelha") - ver normalizar_valor() em
silver_utils.py. Exceção: ID_/COD_/URL_* e texto livre longo (regras/
legalidades/nomes estrangeiros serializados) mantêm sua própria convenção de
case - ver colunas específicas abaixo. Bronze/Ingestion continuam passthrough
1:1 da fonte.

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
  contra ele. Único fallback condicional mantido: ID_ORACLE (oracle_id é
  novo - #135 - pode faltar em partição gravada antes da mudança).

SEPARAÇÃO DE PREÇO E MIGRAÇÃO (#115): até esta revisão, esta tabela também
carregava o histórico diário de preço (junção por NME_CARTA com a Bronze
card_prices) e o id canônico pós-migração da Scryfall (Bronze migrations),
o que forçava a chave única a incluir DT_INGESTAO_PRECO (coluna que podia
ser NULA) e degradava a constraint PRIMARY KEY pra comentário best-effort.
Preço e migração têm grão e cadência de atualização próprios - viraram
tabelas Silver dedicadas (TB_FATO_PRECOS_CARTAS, TB_MOV_MIGRACOES_CARTAS),
e esta tabela voltou a ter grão só de "impressão de carta", chave simples
(ID_CARTA) e sem essas duas fontes na extração. Consumidores Gold que
precisam de preço ou do id canônico pós-migração devem juntar essas tabelas
por NME_CARTA / ID_CARTA, respectivamente.

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
        oracle_id_select = "oracle_id AS ID_ORACLE"
    else:
        logger.warning("Coluna oracle_id ausente na Bronze cards - ID_ORACLE ficará NULL (ver #135).")
        oracle_id_select = "CAST(NULL AS STRING) AS ID_ORACLE"

    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW _cards_stage0 AS
        SELECT
            id AS ID_CARTA,
            {oracle_id_select},
            name AS NME_CARTA,
            manaCost AS DESC_CUSTO_MANA,
            cmc AS QTD_CUSTO_MANA,
            colors AS COD_CORES,
            colorIdentity AS COD_IDENTIDADE_COR,
            type AS NME_TIPO_CARTA,
            types AS DESC_TIPOS,
            subtypes AS DESC_SUBTIPOS,
            rarity AS NME_RARIDADE,
            `set` AS COD_COLECAO,
            setName AS NME_COLECAO,
            text AS DESC_CARTA,
            artist AS NME_ARTISTA,
            number AS NUM_COLECIONADOR,
            power AS NME_FORCA,
            toughness AS NME_RESISTENCIA,
            layout AS NME_DISPOSICAO_CARTA,
            multiverseid AS ID_MULTIVERSO,
            imageUrl AS URL_IMAGEM,
            variations AS COD_VARIACOES,
            foreignNames AS DESC_NOMES_ESTRANGEIROS,
            printings AS DESC_IMPRESSOES,
            originalText AS DESC_CARTA_ORIGINAL,
            originalType AS NME_TIPO_ORIGINAL,
            legalities AS DESC_LEGALIDADES,
            ingestion_timestamp AS DT_INGESTAO,
            source AS NME_FONTE,
            endpoint AS DESC_URL_ORIGEM,
            source_file AS DESC_ARQUIVO_ORIGEM,
            bronze_run_id AS ID_EXECUCAO_BRONZE,
            bronze_ingestion_timestamp AS DT_INGESTAO_BRONZE
        FROM _cards_bronze
    """)

    # Estágio 1: filtro temporal (últimos 5 anos). DT_INGESTAO sempre existe
    # (coluna técnica obrigatória da Bronze) - sem fallback aqui: um NULL
    # nela zeraria silenciosamente o filtro (WHERE NULL >= ...) e descartaria
    # o lote inteiro sem erro, pior que um crash.
    spark.sql("""
        CREATE OR REPLACE TEMP VIEW _cards_stage1 AS
        SELECT *
        FROM _cards_stage0
        WHERE DT_INGESTAO >= add_months(current_date(), -60)
    """)

    # Estágio 2: limpeza/derivação de negócio. \\[ \\] no literal SQL: Spark
    # desfaz um backslash simples antes de um caractere sem escape
    # reconhecido (aqui viraria '[|]|"', uma regex válida mas errada - classe
    # de caracteres, não escape literal). Dobrar o backslash na fonte Python
    # garante que sobra um só depois do unescaping do Spark.
    spark.sql(r"""
        CREATE OR REPLACE TEMP VIEW _cards_stage2 AS
        SELECT
            * EXCEPT (NME_CARTA, NME_ARTISTA, NME_RARIDADE, NME_COLECAO, DESC_CARTA,
                      DESC_CUSTO_MANA, QTD_CUSTO_MANA, NME_FORCA, NME_RESISTENCIA,
                      COD_COLECAO, DESC_IMPRESSOES, COD_VARIACOES, COD_CORES,
                      COD_IDENTIDADE_COR, DESC_SUBTIPOS, DESC_TIPOS, NME_TIPO_CARTA,
                      NME_TIPO_ORIGINAL, DT_INGESTAO),

            normalizar_valor(NME_CARTA) AS NME_CARTA,
            normalizar_valor(NME_ARTISTA) AS NME_ARTISTA,
            normalizar_valor(NME_RARIDADE) AS NME_RARIDADE,
            normalizar_valor(NME_COLECAO) AS NME_COLECAO,
            CASE WHEN DESC_CARTA IS NULL OR DESC_CARTA = '' THEN 'NA' ELSE trim(DESC_CARTA) END AS DESC_CARTA,
            CASE WHEN DESC_CUSTO_MANA IS NULL OR DESC_CUSTO_MANA = '' THEN 'NA' ELSE trim(DESC_CUSTO_MANA) END AS DESC_CUSTO_MANA,
            coalesce(QTD_CUSTO_MANA, 0) AS QTD_CUSTO_MANA,
            -- NME_FORCA/NME_RESISTENCIA são STRING na Bronze e podem legitimamente
            -- valer "*", "1+*" etc. (poder/resistência variável - ex.: Tarmogoyf).
            -- Fallback como string ('0'), não int: coalesce(STRING_COL, 0) força
            -- um implicit cast pra BIGINT, que quebra (CAST_INVALID_INPUT) no
            -- primeiro valor não-numérico. normalizar_valor() é inofensivo aqui
            -- (sem espaço/acento pra tratar) - mantido só por consistência do
            -- prefixo NME_.
            normalizar_valor(coalesce(NME_FORCA, '0')) AS NME_FORCA,
            normalizar_valor(coalesce(NME_RESISTENCIA, '0')) AS NME_RESISTENCIA,
            upper(COD_COLECAO) AS COD_COLECAO,  -- normaliza case: TB_DIM_COLECOES tambem faz upper() em COD_COLECAO, join entre as duas depende do mesmo case
            regexp_replace(DESC_IMPRESSOES, '\\[|\\]|"', '') AS DESC_IMPRESSOES,
            regexp_replace(COD_VARIACOES, '\\[|\\]|"', '') AS COD_VARIACOES,
            regexp_replace(COD_CORES, '\\[|\\]|"', '') AS COD_CORES,
            regexp_replace(COD_IDENTIDADE_COR, '\\[|\\]|"', '') AS COD_IDENTIDADE_COR,
            normalizar_valor(regexp_replace(DESC_SUBTIPOS, '\\[|\\]|"', '')) AS DESC_SUBTIPOS,
            CASE WHEN DESC_TIPOS IS NULL OR DESC_TIPOS = '' THEN 'NA' ELSE normalizar_valor(DESC_TIPOS) END AS DESC_TIPOS,

            -- NME_TIPO_CARTA / DESC_DETALHE_TIPO_CARTA: Planeswalker é tipo
            -- isolado; "—" (em dash) separa tipo principal de subtipo
            -- descritivo. As duas colunas saem da mesma origem.
            normalizar_valor(CASE
                WHEN NME_TIPO_CARTA IS NULL THEN NULL
                WHEN lower(NME_TIPO_CARTA) LIKE '%planeswalker%' THEN 'Planeswalker'
                WHEN instr(NME_TIPO_CARTA, '—') > 0 THEN trim(split(NME_TIPO_CARTA, '—', 2)[0])
                ELSE trim(NME_TIPO_CARTA)
            END) AS NME_TIPO_CARTA,
            CASE
                WHEN NME_TIPO_CARTA IS NULL THEN NULL
                WHEN lower(NME_TIPO_CARTA) LIKE '%planeswalker%' THEN normalizar_valor(NME_TIPO_CARTA)
                WHEN instr(NME_TIPO_CARTA, '—') > 0 THEN normalizar_valor(trim(split(NME_TIPO_CARTA, '—', 2)[1]))
                ELSE 'NA'
            END AS DESC_DETALHE_TIPO_CARTA,

            normalizar_valor(NME_TIPO_ORIGINAL) AS NME_TIPO_ORIGINAL,

            to_timestamp(DT_INGESTAO) AS DT_INGESTAO
        FROM _cards_stage1
    """)

    # Estágio 3: COD_CORES/DESC_SUBTIPOS colorless-default (pós-limpeza) e
    # eliminação de "(" ")" "{" "}" do dado Silver (pedido do usuário - esses
    # caracteres sinalizam dado ainda não transformado). \\{ \\} \\( \\) no
    # literal SQL pelo mesmo motivo do Estágio 2 (Spark desfaz backslash
    # simples antes de escape não reconhecido).
    spark.sql(r"""
        CREATE OR REPLACE TEMP VIEW _cards_stage3 AS
        SELECT
            * EXCEPT (COD_CORES, DESC_SUBTIPOS, DESC_CARTA, DESC_CUSTO_MANA,
                      DESC_CARTA_ORIGINAL, DESC_LEGALIDADES, DESC_NOMES_ESTRANGEIROS),

            CASE WHEN COD_CORES IS NULL OR COD_CORES = '' THEN 'Colorless' ELSE COD_CORES END AS COD_CORES,
            CASE WHEN DESC_SUBTIPOS IS NULL OR DESC_SUBTIPOS = '' THEN 'NA' ELSE DESC_SUBTIPOS END AS DESC_SUBTIPOS,

            -- DESC_CARTA: substituições nomeadas pros símbolos de mana mais
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
            regexp_replace(DESC_CARTA, '\\{W\\}', '[White]'),
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
                                '\\(([^)]*)\\)', '[$1]') AS DESC_CARTA,

            -- DESC_CUSTO_MANA: notação puramente simbólica (ex.: "{2}{U}{U}") -
            -- só o catch-all genérico já resolve, sem precisar da lista nomeada.
            regexp_replace(
            regexp_replace(DESC_CUSTO_MANA, '\\{([^}]*)\\}', '[$1]'),
                                             '\\(([^)]*)\\)', '[$1]') AS DESC_CUSTO_MANA,

            -- DESC_CARTA_ORIGINAL: texto pré-errata, mesma notação de DESC_CARTA.
            regexp_replace(
            regexp_replace(DESC_CARTA_ORIGINAL, '\\{([^}]*)\\}', '[$1]'),
                                                  '\\(([^)]*)\\)', '[$1]') AS DESC_CARTA_ORIGINAL,

            -- DESC_LEGALIDADES: dict serializado (json.dumps) vindo direto da
            -- Bronze - chaves de dict viram colchete pela mesma regra.
            regexp_replace(
            regexp_replace(DESC_LEGALIDADES, '\\{([^}]*)\\}', '[$1]'),
                                              '\\(([^)]*)\\)', '[$1]') AS DESC_LEGALIDADES,

            -- DESC_NOMES_ESTRANGEIROS: lista de dicts serializada (um dict por
            -- idioma, sem aninhamento) - mesma regra.
            regexp_replace(
            regexp_replace(DESC_NOMES_ESTRANGEIROS, '\\{([^}]*)\\}', '[$1]'),
                                                      '\\(([^)]*)\\)', '[$1]') AS DESC_NOMES_ESTRANGEIROS
        FROM _cards_stage2
    """)

    # Estágio 4: NME_CATEGORIA_COR/QTD_CORES (derivados de COD_CORES e
    # DESC_CUSTO_MANA já resolvidos nos estágios anteriores) e
    # ANO_INGESTAO/MES_INGESTAO (partição física, derivados de DT_INGESTAO -
    # #115, no lugar de ANO/MES_INGESTAO_PRECO removidos com attach_prices).
    df_silver = spark.sql("""
        SELECT
            *,
            normalizar_valor(CASE
                WHEN COD_CORES = 'Colorless' THEN 'Colorless'
                WHEN size(split(COD_CORES, ',')) = 1 THEN 'Mono'
                WHEN size(split(COD_CORES, ',')) = 2 THEN 'Dual Color'
                WHEN size(split(COD_CORES, ',')) >= 3 THEN 'Multicolor'
                ELSE 'Mono'
            END) AS NME_CATEGORIA_COR,
            CASE
                WHEN DESC_CUSTO_MANA IS NULL OR DESC_CUSTO_MANA = 'NA' THEN 0
                ELSE length(regexp_replace(upper(DESC_CUSTO_MANA), '[^WUBRG]', ''))
            END AS QTD_CORES,
            year(DT_INGESTAO) AS ANO_INGESTAO,
            month(DT_INGESTAO) AS MES_INGESTAO
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

# Salvar na Silver com particionamento e merge incremental por ID_CARTA - #115:
# chave voltou a ser só ID_CARTA (identificador único por impressão) desde
# que preço e migração saíram desta tabela (ver docstring da célula
# anterior). partition_cols por ANO_INGESTAO/MES_INGESTAO (data de coleta do
# dado de carta, não mais de preço).
# order_by_col=DT_INGESTAO: se o lote tiver mais de uma linha para a mesma
# chave (reprocessamento), mantém a linha da ingestão mais recente em vez de
# uma linha arbitrária (AUD-09).
processor.save_silver_table(
    df_silver,
    partition_cols=["ANO_INGESTAO", "MES_INGESTAO"],
    key_column="ID_CARTA",
    order_by_col="DT_INGESTAO",
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
