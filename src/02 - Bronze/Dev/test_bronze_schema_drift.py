# ponytail: pure-logic self-check for the schema-drift detection added to
# check_and_fix_delta_schema() in TB_BRONZE_{FORMATS,SETS,SUBTYPES,CARDS}.ipynb (AUD-07).
# Can't import the notebooks directly (pyspark + live dbutils required), so this mirrors
# just the decision logic: raise on drift instead of dbutils.fs.rm + silent recreate.


def check_schema_missing_incorrect(schema_fields, expected_schema):
    """FORMATS/SETS/SUBTYPES variant: raises if expected columns are missing or legacy
    column names are present."""
    missing = [c for c in expected_schema if c not in schema_fields]
    incorrect = [c for c in schema_fields if c in ['endpoint', 'source', 'ingestion_timestamp']]
    if missing or incorrect:
        raise Exception(f"drift: missing={missing} incorrect={incorrect}")
    return True


def check_schema_old_columns(schema_fields, required_columns):
    """CARDS variant: raises only if legacy columns are present (missing required
    columns are logged, not fatal, matching pre-existing behavior)."""
    old_columns = ["foreignNames", "printings", "originalText", "originalType", "legalities"]
    found_old = [c for c in old_columns if c in schema_fields]
    if found_old:
        raise Exception(f"drift: old_columns={found_old}")
    return True


def test_no_drift_passes():
    assert check_schema_missing_incorrect(
        ['NME_FORMAT', 'DT_INGESTION', 'NME_SOURCE', 'NME_ENDPOINT', 'INGESTION_YEAR', 'INGESTION_MONTH'],
        ['NME_FORMAT', 'DT_INGESTION', 'NME_SOURCE', 'NME_ENDPOINT', 'INGESTION_YEAR', 'INGESTION_MONTH'],
    ) is True
    assert check_schema_old_columns(['ID_CARD', 'NME_CARD', 'DT_INGESTION'], ['ID_CARD', 'NME_CARD']) is True


def test_missing_column_raises():
    try:
        check_schema_missing_incorrect(['NME_FORMAT'], ['NME_FORMAT', 'DT_INGESTION'])
        assert False, "expected raise"
    except Exception as e:
        assert "missing=['DT_INGESTION']" in str(e)


def test_legacy_column_name_raises():
    try:
        check_schema_missing_incorrect(['endpoint', 'source'], [])
        assert False, "expected raise"
    except Exception as e:
        assert "endpoint" in str(e) and "source" in str(e)


def test_cards_old_column_raises():
    try:
        check_schema_old_columns(['ID_CARD', 'legalities'], ['ID_CARD'])
        assert False, "expected raise"
    except Exception as e:
        assert "legalities" in str(e)


def test_cards_missing_required_does_not_raise():
    # Matches pre-existing behavior: missing required columns are only logged for CARDS.
    assert check_schema_old_columns(['ID_CARD'], ['ID_CARD', 'NME_CARD']) is True


if __name__ == "__main__":
    test_no_drift_passes()
    test_missing_column_raises()
    test_legacy_column_name_raises()
    test_cards_old_column_raises()
    test_cards_missing_required_does_not_raise()
    print("OK")
