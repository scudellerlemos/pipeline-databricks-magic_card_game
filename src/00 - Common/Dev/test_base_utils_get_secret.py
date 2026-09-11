# ponytail: pure-logic self-check for the fallback branches in get_secret()
# (base_utils.py, AUD-09). Can't import that module directly here (it requires
# a live Databricks dbutils session, not available outside a cluster), so this
# mirrors just the default-resolution logic under test.


def resolve_secret_default(secret_name, default_value=None, extra_safe_defaults=None):
    if default_value is not None:
        return default_value

    safe_defaults = {
        'catalog_name': 'magic_the_gathering',
        's3_bucket': 's3://meu-bucket-default'
    }
    safe_defaults.update(extra_safe_defaults or {})

    if secret_name in safe_defaults:
        return safe_defaults[secret_name]

    raise Exception(f"Secret '{secret_name}' not configured and no default available")


def test_explicit_default_wins():
    assert resolve_secret_default("s3_bucket", default_value="s3://explicit") == "s3://explicit"


def test_falls_back_to_common_safe_default():
    assert resolve_secret_default("catalog_name") == "magic_the_gathering"


def test_falls_back_to_layer_specific_default():
    assert resolve_secret_default(
        "s3_gold_prefix", extra_safe_defaults={"s3_gold_prefix": "magic_the_gathering/gold"}
    ) == "magic_the_gathering/gold"


def test_raises_when_no_default_available():
    try:
        resolve_secret_default("unknown_secret")
    except Exception as e:
        assert "unknown_secret" in str(e)
    else:
        raise AssertionError("expected Exception for secret with no default")


if __name__ == "__main__":
    test_explicit_default_wins()
    test_falls_back_to_common_safe_default()
    test_falls_back_to_layer_specific_default()
    test_raises_when_no_default_available()
    print("OK")
