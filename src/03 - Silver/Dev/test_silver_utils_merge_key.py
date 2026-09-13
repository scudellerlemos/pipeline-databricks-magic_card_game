# ponytail: pure-logic self-check for the key_column/dedup branch in save_to_silver()
# (silver_utils.py). Can't import that module directly here (it requires pyspark + a
# live Databricks spark/dbutils session, neither available outside a cluster), so this
# mirrors just the merge-condition logic under test.


def build_merge_plan(key_column):
    key_cols = [key_column] if isinstance(key_column, str) else list(key_column)
    # <=> (null-safe equality): a plain "=" never matches when a key column is
    # NULL, which would reinsert that row on every run.
    merge_condition = " AND ".join(f"silver.{k} <=> novo.{k}" for k in key_cols)
    return key_cols, merge_condition


def test_single_key_column_string():
    key_cols, condition = build_merge_plan("ID_CARD")
    assert key_cols == ["ID_CARD"]
    assert condition == "silver.ID_CARD <=> novo.ID_CARD"


def test_composite_key_cardprices_preserves_history():
    key_cols, condition = build_merge_plan(["ID_CARD", "DT_INGESTION"])
    assert key_cols == ["ID_CARD", "DT_INGESTION"]
    assert condition == "silver.ID_CARD <=> novo.ID_CARD AND silver.DT_INGESTION <=> novo.DT_INGESTION"


if __name__ == "__main__":
    test_single_key_column_string()
    test_composite_key_cardprices_preserves_history()
    print("OK")
