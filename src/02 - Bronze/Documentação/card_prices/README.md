# card_prices (Bronze)

> Ver [`../README.md`](../README.md) para a arquitetura completa da camada
> Bronze (idempotência, controle de execução, schema, particionamento). Este
> arquivo cobre só o que é específico desta tabela.

- **Tabela Unity Catalog:** `{catalog}.bronze.card_prices`.
- **Origem (Stage):** tabela `card_prices`, gravada por [`src/01 - Ingestion/card_prices.ipynb`](<../../../01 - Ingestion/card_prices.ipynb>) a partir da API Scryfall.
- **Notebook Bronze:** [`../../Dev/card_prices.ipynb`](../../Dev/card_prices.ipynb).
- **Schema:** preservado 1:1 da Stage (não documentado aqui para não divergir - ver o notebook de origem acima para os campos atuais). A Bronze só adiciona `source_file`, `bronze_run_id`, `bronze_ingestion_timestamp`.
- **Histórico:** o preço de uma mesma carta em runs/dias diferentes gera linhas diferentes, todas preservadas - não há filtro por data/período nem `dropDuplicates` por carta. Nenhuma checagem de consistência contra `cards` acontece aqui (a antiga limpeza cruzada que apagava preços de cartas "ausentes" era regra de negócio e foi removida desta camada).
