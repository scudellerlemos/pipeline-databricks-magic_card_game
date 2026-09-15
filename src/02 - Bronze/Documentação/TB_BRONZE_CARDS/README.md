# TB_BRONZE_CARDS

> Ver [`../README.md`](../README.md) para a arquitetura completa da camada
> Bronze (idempotência, controle de execução, schema, particionamento). Este
> arquivo cobre só o que é específico desta tabela.

- **Origem (Stage):** tabela `cards`, gravada por [`src/01 - Ingestion/cards.ipynb`](<../../../01 - Ingestion/cards.ipynb>) a partir da API Scryfall (`/bulk-data` → `default_cards`).
- **Notebook Bronze:** [`../../Dev/TB_BRONZE_CARDS.ipynb`](../../Dev/TB_BRONZE_CARDS.ipynb).
- **Schema:** preservado 1:1 da Stage (não documentado aqui para não divergir - ver o notebook de origem acima para os campos atuais). A Bronze só adiciona `source_file`, `bronze_run_id`, `bronze_ingestion_timestamp`.
- **Histórico:** uma mesma carta (mesmo `id`) pode aparecer em runs diferentes com dados diferentes (ex.: `legalities` mudou) - cada run é preservada, sem deduplicação.
