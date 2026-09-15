# Documentação da Camada Bronze

## Visão geral

A Bronze faz **EL puro** (Extract & Load): lê os arquivos Parquet gravados
pela Stage em S3 e grava um Delta append-only por tabela no Unity Catalog,
preservando o schema de origem 1:1. Nenhuma regra de negócio, renomeação de
coluna, deduplicação por chave de negócio ou MERGE/upsert acontece aqui -
isso é responsabilidade da Silver.

Toda a lógica compartilhada vive em
[`../Dev/bronze_utils.py`](../Dev/bronze_utils.py). Cada notebook por tabela
só declara a configuração (nome da tabela, nome da tabela de origem na
Stage) e chama `run_bronze_ingestion(...)`.

## Tabelas

| Tabela Bronze | Tabela de origem (Stage) | Notebook | Schema (fonte) |
|---|---|---|---|
| `TB_BRONZE_CARDS` | `cards` | [`TB_BRONZE_CARDS.ipynb`](../Dev/TB_BRONZE_CARDS.ipynb) | [`src/01 - Ingestion/cards.ipynb`](<../../01 - Ingestion/cards.ipynb>) |
| `TB_BRONZE_SETS` | `sets` | [`TB_BRONZE_SETS.ipynb`](../Dev/TB_BRONZE_SETS.ipynb) | [`src/01 - Ingestion/sets.ipynb`](<../../01 - Ingestion/sets.ipynb>) |
| `TB_BRONZE_CARDPRICES` | `card_prices` | [`TB_BRONZE_CARDPRICES.ipynb`](../Dev/TB_BRONZE_CARDPRICES.ipynb) | [`src/01 - Ingestion/card_prices.ipynb`](<../../01 - Ingestion/card_prices.ipynb>) |
| `TB_BRONZE_SYMBOLOGY` | `symbology` | [`TB_BRONZE_SYMBOLOGY.ipynb`](../Dev/TB_BRONZE_SYMBOLOGY.ipynb) | [`src/01 - Ingestion/symbology.ipynb`](<../../01 - Ingestion/symbology.ipynb>) |
| `TB_BRONZE_RULINGS` | `rulings` | [`TB_BRONZE_RULINGS.ipynb`](../Dev/TB_BRONZE_RULINGS.ipynb) | [`src/01 - Ingestion/rulings.ipynb`](<../../01 - Ingestion/rulings.ipynb>) |
| `TB_BRONZE_MIGRATIONS` | `migrations` | [`TB_BRONZE_MIGRATIONS.ipynb`](../Dev/TB_BRONZE_MIGRATIONS.ipynb) | [`src/01 - Ingestion/migrations.ipynb`](<../../01 - Ingestion/migrations.ipynb>) |

Não há doc de schema por coluna aqui de propósito: a Bronze não altera o
schema que a Stage produz (ver notebook de origem na tabela acima para a
lista de campos), só adiciona 3 colunas técnicas por cima:

| Coluna adicionada | Descrição |
|---|---|
| `source_file` | Caminho completo do arquivo Parquet de origem na Stage (`input_file_name()`) - é a chave de idempotência: um arquivo só é lido de novo se seu `source_file` ainda não existir na tabela Bronze. |
| `bronze_run_id` | Id da execução da Bronze que gravou a linha (controle de execução). |
| `bronze_ingestion_timestamp` | Timestamp em que a Bronze processou o registro (distinto do `ingestion_timestamp` que já vem da Stage no dado de origem). |

## Carga inicial vs. incremental

Não há distinção de código entre a 1ª carga e as execuções seguintes: o
`write.format("delta").mode("append")` cria a tabela Delta automaticamente
se ela não existir. Toda execução segue o mesmo fluxo:

1. Lista os arquivos Parquet da Stage para a tabela (`*_{stage_table_name}.parquet`).
2. Descobre quais já foram carregados (via `source_file` distinto já presente na Bronze).
3. Lê só os arquivos novos, adiciona as 3 colunas técnicas.
4. Append no Delta com `mergeSchema=true` (evolução aditiva de schema).
5. Garante a tabela no Unity Catalog (`CREATE TABLE IF NOT EXISTS ... LOCATION`, nunca `DROP`/`ALTER` automático).
6. Grava o controle de execução em `{s3_bronze_path}/_control/{tabela}/{run_id}.json`.

Se não há arquivo novo (ex.: 2ª execução no mesmo dia, já que a Stage não
gera arquivo novo nesse caso), a run fecha como `SUCCESS` sem escrever nada -
idempotência por identidade de arquivo, não por `SELECT DISTINCT` em dado de
negócio.

## Histórico preservado (sem deduplicação)

A mesma carta/preço/regra pode aparecer em mais de um arquivo/execução da
Stage ao longo do tempo (ex.: preço de uma carta em dois dias diferentes).
A Bronze preserva as duas linhas - não há `dropDuplicates` nem `MERGE` por
chave de negócio. Decidir o que é "estado atual" vs. "histórico" é трabalho
da Silver.

## Particionamento

Nenhuma tabela Bronze é particionada. O volume atual não justifica, e
particionar preventivamente sem necessidade real é a complexidade que este
redesenho removeu (as tabelas antigas particionavam por `RELEASE_YEAR`/
`RELEASE_MONTH` derivados de um JOIN com `sets` dentro da Bronze - regra de
negócio que não deveria estar aqui).
