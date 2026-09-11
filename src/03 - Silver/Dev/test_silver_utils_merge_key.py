# ponytail: pure-logic self-check for the key_column normalization added to
# load_to_silver_unity_incremental() in silver_utils.py. Can't import that module
# directly here (it requires pyspark + a live Databricks spark/dbutils session,
# neither available outside a cluster), so this mirrors just the branch under test.


def build_merge_plan(columns, key_column):
    key_cols = [key_column] if isinstance(key_column, str) else list(key_column)
    update_cols = [c for c in columns if c not in key_cols]
    merge_condition = " AND ".join(f"silver.{k} = novo.{k}" for k in key_cols)
    return key_cols, update_cols, merge_condition


def test_single_key_column_string():
    key_cols, update_cols, condition = build_merge_plan(
        ["NME_TYPE", "NME_SOURCE", "DT_INGESTION"], "NME_TYPE"
    )
    assert key_cols == ["NME_TYPE"]
    assert update_cols == ["NME_SOURCE", "DT_INGESTION"]
    assert condition == "silver.NME_TYPE = novo.NME_TYPE"


def test_composite_key_cards():
    key_cols, update_cols, condition = build_merge_plan(
        ["NME_CARD", "COD_SET", "DESC_CARD"], ["NME_CARD", "COD_SET"]
    )
    assert key_cols == ["NME_CARD", "COD_SET"]
    assert update_cols == ["DESC_CARD"]
    assert condition == "silver.NME_CARD = novo.NME_CARD AND silver.COD_SET = novo.COD_SET"


def test_composite_key_cardprices_preserves_history_column():
    key_cols, update_cols, condition = build_merge_plan(
        ["ID_CARD", "DT_INGESTION", "VLR_USD"], ["ID_CARD", "DT_INGESTION"]
    )
    assert key_cols == ["ID_CARD", "DT_INGESTION"]
    assert "DT_INGESTION" not in update_cols
    assert update_cols == ["VLR_USD"]
    assert condition == "silver.ID_CARD = novo.ID_CARD AND silver.DT_INGESTION = novo.DT_INGESTION"


if __name__ == "__main__":
    test_single_key_column_string()
    test_composite_key_cards()
    test_composite_key_cardprices_preserves_history_column()
    print("OK")
