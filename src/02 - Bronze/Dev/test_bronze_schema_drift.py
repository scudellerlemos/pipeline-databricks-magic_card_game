# ponytail: pure-logic self-check for bronze_utils.py's non-trivial bits -
# idempotency (which stage files are "new") and schema-diff logging. Can't
# import bronze_utils.py directly (pyspark + live dbutils/%run required), so
# this mirrors just the decision logic in plain Python.
#
# Superseded by the Bronze EL rewrite: the old GOV-renaming schema-drift
# checks this file used to test (TB_BRONZE_{FORMATS,SETS,SUBTYPES,CARDS})
# no longer exist - Bronze no longer renames columns at all.


def normalize_path(path):
    """Mirrors bronze_utils.normalize_path: strip URI scheme for comparison."""
    return path.split("://", 1)[-1]


def find_new_files(all_stage_files, already_loaded_files):
    """Mirrors run_bronze_ingestion's idempotency filter: files present in
    Stage but not yet reflected by any source_file already in Bronze."""
    already = set(already_loaded_files)
    return [f for f in all_stage_files if normalize_path(f) not in already]


def diff_schema(existing_fields, incoming_fields):
    """Mirrors log_schema_diff's classification: new/missing/type-changed."""
    new_cols = sorted(c for c in incoming_fields if c not in existing_fields)
    missing_cols = sorted(c for c in existing_fields if c not in incoming_fields)
    type_changed = sorted(
        c for c in incoming_fields
        if c in existing_fields and incoming_fields[c] != existing_fields[c]
    )
    return {"new": new_cols, "missing": missing_cols, "type_changed": type_changed}


def test_no_new_files_when_everything_already_loaded():
    # already_loaded_files espelha o retorno (já normalizado, sem esquema de
    # URI) de get_already_loaded_files.
    all_files = ["s3://b/stage/2026_09_14_cards.parquet"]
    already = {"b/stage/2026_09_14_cards.parquet"}
    assert find_new_files(all_files, already) == []


def test_only_unseen_files_are_new():
    all_files = [
        "s3://b/stage/2026_09_13_cards.parquet",
        "s3://b/stage/2026_09_14_cards.parquet",
    ]
    already = {"b/stage/2026_09_13_cards.parquet"}
    assert find_new_files(all_files, already) == ["s3://b/stage/2026_09_14_cards.parquet"]


def test_rerun_same_day_is_noop():
    # 2nd run same day: Stage's save_to_parquet já pulou a escrita de um
    # arquivo novo (AUD-04, nome do arquivo inclui o dia), então a Bronze
    # também não vê arquivo novo.
    all_files = ["s3://b/stage/2026_09_14_cards.parquet"]
    already = {"b/stage/2026_09_14_cards.parquet"}
    assert find_new_files(all_files, already) == []


def test_scheme_mismatch_does_not_cause_reprocessing():
    # dbutils.fs.ls() pode devolver s3:// enquanto input_file_name() (já
    # normalizado em get_already_loaded_files) devolveu s3a:// pro mesmo
    # arquivo - sem normalize_path, isto reprocessaria e duplicaria histórico.
    all_files = ["s3://b/stage/2026_09_14_cards.parquet"]
    already = {"b/stage/2026_09_14_cards.parquet"}  # já normalizado (sem esquema)
    assert find_new_files(all_files, already) == []


def test_schema_diff_detects_new_and_missing_columns():
    existing = {"id": "StringType()", "name": "StringType()"}
    incoming = {"id": "StringType()", "set": "StringType()"}
    result = diff_schema(existing, incoming)
    assert result["new"] == ["set"]
    assert result["missing"] == ["name"]
    assert result["type_changed"] == []


def test_schema_diff_detects_type_change():
    existing = {"cmc": "DoubleType()"}
    incoming = {"cmc": "StringType()"}
    result = diff_schema(existing, incoming)
    assert result["type_changed"] == ["cmc"]


def test_schema_diff_first_load_is_all_new():
    result = diff_schema({}, {"id": "StringType()", "name": "StringType()"})
    assert result["new"] == ["id", "name"]
    assert result["missing"] == []


if __name__ == "__main__":
    test_no_new_files_when_everything_already_loaded()
    test_only_unseen_files_are_new()
    test_rerun_same_day_is_noop()
    test_scheme_mismatch_does_not_cause_reprocessing()
    test_schema_diff_detects_new_and_missing_columns()
    test_schema_diff_detects_type_change()
    test_schema_diff_first_load_is_all_new()
    print("OK")
