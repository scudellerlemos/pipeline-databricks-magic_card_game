# ponytail: pure-logic self-check for _declare_primary_key() (silver_utils.py).
# Can't import that module directly here (it requires pyspark + a live Databricks
# spark/dbutils session, neither available outside a cluster), so this mirrors just
# the PK-declaration logic under test, same convention as test_silver_utils_merge_key.py.

import re


class FakeSpark:
    """Records every spark.sql() call; answers COUNT(*) NULL-check queries from a
    canned {column: null_count} map, everything else is a no-op DDL call."""

    def __init__(self, null_counts=None):
        self.null_counts = null_counts or {}
        self.calls = []

    def sql(self, query):
        self.calls.append(query)
        match = re.search(r"count\(\*\) AS n FROM .+ WHERE `(.+?)` IS NULL", query)
        if match:
            return _FakeResult(self.null_counts.get(match.group(1), 0))
        return _FakeResult(None)


class _FakeResult:
    def __init__(self, n):
        self._n = n

    def collect(self):
        return [{"n": self._n}]


def declare_primary_key(spark, full_table_name, table_name, key_cols):
    """Mirror of silver_utils._declare_primary_key."""
    pk_name = f"pk_{table_name.lower()}"
    for k in key_cols:
        null_count = spark.sql(
            f"SELECT count(*) AS n FROM {full_table_name} WHERE `{k}` IS NULL"
        ).collect()[0]["n"]
        if null_count > 0:
            raise RuntimeError(
                f"Coluna chave '{k}' de {full_table_name} tem {null_count} linha(s) "
                f"com valor NULO - viola a premissa de chave única desta tabela. "
                f"Corrija a fonte/transformação antes de declarar PRIMARY KEY."
            )
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
    # só a query de COUNT foi chamada - nenhum SET NOT NULL/DROP/ADD CONSTRAINT
    assert len(spark.calls) == 1
    assert "count(*)" in spark.calls[0]


def test_no_null_declares_constraint_in_order():
    spark = FakeSpark(null_counts={})
    declare_primary_key(spark, "cat.silver.TB_DIM_COLECOES", "TB_DIM_COLECOES", ["Cod_colecao"])
    # COUNT, SET NOT NULL, DROP CONSTRAINT, ADD CONSTRAINT, nesta ordem.
    assert len(spark.calls) == 4
    assert "count(*)" in spark.calls[0]
    assert "SET NOT NULL" in spark.calls[1]
    assert "DROP CONSTRAINT IF EXISTS pk_tb_dim_colecoes" in spark.calls[2]
    assert "ADD CONSTRAINT pk_tb_dim_colecoes" in spark.calls[3]
    assert "PRIMARY KEY (Cod_colecao)" in spark.calls[3]


def test_composite_key_checks_each_column_before_any_ddl():
    spark = FakeSpark(null_counts={})
    declare_primary_key(
        spark, "cat.silver.TB_FATO_PRECOS_CARTAS", "TB_FATO_PRECOS_CARTAS",
        ["Nme_carta", "Dt_ingestao"],
    )
    # por coluna: COUNT depois SET NOT NULL, nesta ordem -> 2x(COUNT+SET NOT NULL) + DROP + ADD = 6
    assert len(spark.calls) == 6
    assert "count(*)" in spark.calls[0] and "Nme_carta" in spark.calls[0]
    assert "SET NOT NULL" in spark.calls[1] and "Nme_carta" in spark.calls[1]
    assert "count(*)" in spark.calls[2] and "Dt_ingestao" in spark.calls[2]
    assert "SET NOT NULL" in spark.calls[3] and "Dt_ingestao" in spark.calls[3]


def test_composite_key_second_column_null_stops_before_first_column_set_not_null_persists():
    # 1a coluna limpa (já teria virado NOT NULL), 2a coluna com NULO: deve parar
    # ali, sem tentar DROP/ADD CONSTRAINT com a PK incompleta.
    spark = FakeSpark(null_counts={"Dt_ingestao": 1})
    try:
        declare_primary_key(
            spark, "cat.silver.TB_FATO_PRECOS_CARTAS", "TB_FATO_PRECOS_CARTAS",
            ["Nme_carta", "Dt_ingestao"],
        )
        assert False, "esperava RuntimeError"
    except RuntimeError as e:
        assert "Dt_ingestao" in str(e)
    # COUNT(Nme_carta), SET NOT NULL(Nme_carta), COUNT(Dt_ingestao) -> para aqui
    assert len(spark.calls) == 3
    assert not any("CONSTRAINT" in c for c in spark.calls)


if __name__ == "__main__":
    test_null_key_raises_with_exact_count_and_skips_constraint()
    test_no_null_declares_constraint_in_order()
    test_composite_key_checks_each_column_before_any_ddl()
    test_composite_key_second_column_null_stops_before_first_column_set_not_null_persists()
    print("OK")
