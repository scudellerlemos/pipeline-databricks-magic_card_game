# TB_BRONZE_SETS

> Ver [`../README.md`](../README.md) para a arquitetura completa da camada
> Bronze (idempotência, controle de execução, schema, particionamento). Este
> arquivo cobre só o que é específico desta tabela.

- **Origem (Stage):** tabela `sets`, gravada por [`src/01 - Ingestion/sets.ipynb`](<../../../01 - Ingestion/sets.ipynb>) a partir da API Scryfall (`/sets`).
- **Notebook Bronze:** [`../../Dev/TB_BRONZE_SETS.ipynb`](../../Dev/TB_BRONZE_SETS.ipynb).
- **Schema:** preservado 1:1 da Stage (não documentado aqui para não divergir - ver o notebook de origem acima para os campos atuais). A Bronze só adiciona `source_file`, `bronze_run_id`, `bronze_ingestion_timestamp`.
- **Histórico:** um mesmo set pode aparecer em runs diferentes com dados diferentes; cada run é preservada, sem deduplicação.
