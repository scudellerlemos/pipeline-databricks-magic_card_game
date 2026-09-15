# Camada Bronze - Magic: The Gathering

## Visão geral

A camada Bronze faz **EL (Extract & Load)**: lê os arquivos Parquet gravados
pela Stage em S3 e grava um Delta append-only por tabela no Unity Catalog,
preservando o schema de origem 1:1. Nenhuma regra de negócio, renomeação de
coluna, deduplicação por chave de negócio ou MERGE/upsert acontece aqui -
isso é responsabilidade da Silver.

Documentação completa (arquitetura, idempotência, controle de execução,
schema, particionamento): [`Documentação/README.md`](./Documentação/README.md).

## Tabelas

6 tabelas, uma por origem da Stage: `TB_BRONZE_CARDS`, `TB_BRONZE_SETS`,
`TB_BRONZE_CARDPRICES`, `TB_BRONZE_SYMBOLOGY`, `TB_BRONZE_RULINGS`,
`TB_BRONZE_MIGRATIONS`. Cada uma tem um notebook em
[`Dev/`](./Dev) que só configura os parâmetros da tabela e chama
`run_bronze_ingestion(...)`, definida em [`Dev/bronze_utils.py`](./Dev/bronze_utils.py).

## Como executar

Cada notebook é independente e idempotente - pode ser reexecutado a
qualquer momento sem duplicar dados (só processa arquivos novos da Stage):

```
TB_BRONZE_CARDS.ipynb
TB_BRONZE_SETS.ipynb
TB_BRONZE_CARDPRICES.ipynb
TB_BRONZE_SYMBOLOGY.ipynb
TB_BRONZE_RULINGS.ipynb
TB_BRONZE_MIGRATIONS.ipynb
```

Não há ordem de dependência entre eles (cada um lê só sua própria origem na
Stage). No pipeline (`.github/DAGs/magic.yml`), cada `bronze_*` depende
apenas do `stage_*` correspondente.

## Segredos necessários (scope `mtg-pipeline`)

```
catalog_name       # catálogo Unity Catalog
s3_bucket          # bucket S3
s3_stage_prefix    # prefixo da camada Stage
s3_bronze_prefix   # prefixo da camada Bronze
```
