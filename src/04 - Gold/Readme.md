# Camada Gold

Uma única tabela: `TB_GOLD_MERCADO_CARTAS` - visão de mercado de cartas de Magic: The Gathering pronta para consumo direto por analista, BI ou Genie, sem precisar conhecer Bronze/Silver.

- **Script:** `Dev/TB_GOLD_MERCADO_CARTAS.py`
- **Utilitários:** `Dev/gold_utils.py` (config/extract/load/auditoria, mesmo padrão de `silver_utils.py`)
- **Comentários de negócio:** `Dev/gold_column_docs.py` (fonte única, aplicada via `COMMENT ON TABLE`/`ALTER COLUMN...COMMENT`)
- **Documentação:** [`Documentação/TB_GOLD_MERCADO_CARTAS/Readme.md`](./Documentação/TB_GOLD_MERCADO_CARTAS/Readme.md)

As 3 tabelas Gold anteriores (schema pré-DAMA, colunas em inglês que não existem mais na Silver) foram removidas - sem valor de negócio, sem consumidor real.
