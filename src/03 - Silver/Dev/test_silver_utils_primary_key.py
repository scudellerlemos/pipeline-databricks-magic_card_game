# ponytail: pure-logic self-check for _declare_primary_key() (silver_utils.py).
# Can't import that module directly here (it requires pyspark + a live Databricks
# spark/dbutils session, neither available outside a cluster), so this mirrors just
# the PK-declaration logic under test, same convention as test_silver_utils_merge_key.py.


class FakeSpark:
    """Records every spark.sql() call; answers the combined NULL-count SELECT from a
    canned {column: null_count} map, everything else is a no-op DDL call."""

    def __init__(self, null_counts=None):
        self.null_counts = null_counts or {}
        self.calls = []

    def sql(self, query):
        self.calls.append(query)
        if "sum(case when" in query:
            return _FakeResult(self.null_counts)
        return _FakeResult(None)


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def collect(self):
        return [self._row]


def declare_primary_key(spark, full_table_name, table_name, key_cols):
    """Mirror of silver_utils._declare_primary_key."""
    pk_name = f"pk_{table_name.lower()}"

    sums = ", ".join(f"sum(case when `{k}` is null then 1 else 0 end) as `{k}`" for k in key_cols)
    null_counts = spark.sql(f"SELECT {sums} FROM {full_table_name}").collect()[0]
    for k in key_cols:
        null_count = null_counts.get(k) or 0
        if null_count > 0:
            raise RuntimeError(
                f"Coluna chave '{k}' de {full_table_name} tem {null_count} linha(s) "
                f"com valor NULO - viola a premissa de chave única desta tabela. "
                f"Corrija a fonte/transformação antes de declarar PRIMARY KEY."
            )

    for k in key_cols:
        spark.sql(f"ALTER TABLE {full_table_name} ALTER COLUMN `{k}` SET NOT NULL")

    spark.sql(f"ALTER TABLE {full_table_name} DROP CONSTRAINT IF EXISTS {pk_name}")
    spark.sql(
        f"ALTER TABLE {full_table_name} ADD CONSTRAINT {pk_name} "
        f"PRIMARY KEY ({', '.join(key_cols)})"
    )


def test_null_key_raises_with_exact_count_and_skips_constraint():
    spark = FakeSpark(null_counts={"Id_carta": 3})
    try:
        declare_primary_key(spark, "cat.silver.TB_FATO_CARTAS", "TB_FATO_CARTAS", ["Id_carta"])
        assert False, "esperava RuntimeError"
    except RuntimeError as e:
        assert "3 linha(s)" in str(e)
        assert "Id_carta" in str(e)
    # só a query combinada de soma de NULOs foi chamada - nenhum SET NOT NULL/DROP/ADD CONSTRAINT
    assert len(spark.calls) == 1
    assert "sum(case when" in spark.calls[0]


def test_no_null_declares_constraint_in_order():
    spark = FakeSpark(null_counts={"Cod_colecao": 0})
    declare_primary_key(spark, "cat.silver.TB_DIM_COLECOES", "TB_DIM_COLECOES", ["Cod_colecao"])
    # 1 SELECT combinado, SET NOT NULL, DROP CONSTRAINT, ADD CONSTRAINT, nesta ordem.
    assert len(spark.calls) == 4
    assert "sum(case when" in spark.calls[0]
    assert "SET NOT NULL" in spark.calls[1]
    assert "DROP CONSTRAINT IF EXISTS pk_tb_dim_colecoes" in spark.calls[2]
    assert "ADD CONSTRAINT pk_tb_dim_colecoes" in spark.calls[3]
    assert "PRIMARY KEY (Cod_colecao)" in spark.calls[3]


def test_composite_key_checks_all_columns_in_a_single_scan():
    spark = FakeSpark(null_counts={"Nme_carta": 0, "Dt_ingestao": 0})
    declare_primary_key(
        spark, "cat.silver.TB_FATO_PRECOS_CARTAS", "TB_FATO_PRECOS_CARTAS",
        ["Nme_carta", "Dt_ingestao"],
    )
    # 1 SELECT combinado (não 2) + 2 SET NOT NULL + DROP + ADD = 5
    assert len(spark.calls) == 5
    assert spark.calls[0].count("sum(case when") == 2
    assert "Nme_carta" in spark.calls[0] and "Dt_ingestao" in spark.calls[0]


def test_composite_key_second_column_null_stops_before_any_ddl():
    spark = FakeSpark(null_counts={"Nme_carta": 0, "Dt_ingestao": 1})
    try:
        declare_primary_key(
            spark, "cat.silver.TB_FATO_PRECOS_CARTAS", "TB_FATO_PRECOS_CARTAS",
            ["Nme_carta", "Dt_ingestao"],
        )
        assert False, "esperava RuntimeError"
    except RuntimeError as e:
        assert "Dt_ingestao" in str(e)
    # a checagem falha antes de qualquer SET NOT NULL/DROP/ADD CONSTRAINT rodar,
    # mesmo com a 1a coluna limpa.
    assert len(spark.calls) == 1


if __name__ == "__main__":
    test_null_key_raises_with_exact_count_and_skips_constraint()
    test_no_null_declares_constraint_in_order()
    test_composite_key_checks_all_columns_in_a_single_scan()
    test_composite_key_second_column_null_stops_before_any_ddl()
    print("OK")
