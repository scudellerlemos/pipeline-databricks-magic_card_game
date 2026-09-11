# ponytail: pure-logic self-check for the key_column merge branch added to
# load_to_gold_unity_incremental() in gold_utils.py (AUD-03). Can't import that module
# directly here (it requires pyspark + a live Databricks spark/dbutils session,
# neither available outside a cluster), so this mirrors just the branch under test.


def build_merge_plan(columns, key_column):
    key_cols = [key_column] if isinstance(key_column, str) else list(key_column)
    update_cols = [c for c in columns if c not in key_cols]
    # <=> (null-safe equality): a plain "=" never matches when a key column is
    # NULL, which would reinsert that row on every run (AUD-03 regression).
    merge_condition = " AND ".join(f"gold.{k} <=> novo.{k}" for k in key_cols)
    return key_cols, update_cols, merge_condition


def test_single_key_column_string():
    key_cols, update_cols, condition = build_merge_plan(
        ["NME_SET", "VLR_TOTAL", "DATA_REF"], "NME_SET"
    )
    assert key_cols == ["NME_SET"]
    assert update_cols == ["VLR_TOTAL", "DATA_REF"]
    assert condition == "gold.NME_SET <=> novo.NME_SET"


def test_composite_key_alertas_executivos():
    key_cols, update_cols, condition = build_merge_plan(
        ["NME_CARD", "DATA_REF", "TIPO_ALERTA", "SEVERIDADE", "IMPACTO_FINANCEIRO"],
        ["NME_CARD", "DATA_REF", "TIPO_ALERTA"],
    )
    assert key_cols == ["NME_CARD", "DATA_REF", "TIPO_ALERTA"]
    assert update_cols == ["SEVERIDADE", "IMPACTO_FINANCEIRO"]
    assert condition == (
        "gold.NME_CARD <=> novo.NME_CARD AND gold.DATA_REF <=> novo.DATA_REF "
        "AND gold.TIPO_ALERTA <=> novo.TIPO_ALERTA"
    )


if __name__ == "__main__":
    test_single_key_column_string()
    test_composite_key_alertas_executivos()
    print("OK")
