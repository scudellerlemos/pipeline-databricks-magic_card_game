# ponytail: exercises the real get_secret() from base_utils.py.
# dbutils isn't defined outside a Databricks cluster, so the call inside
# get_secret's try block raises NameError - caught by its own bare except,
# which is exactly the fallback path this test wants to cover.

import importlib.util
import os
import sys

_PATH = os.path.join(os.path.dirname(__file__), "base_utils.py")
_SPEC = importlib.util.spec_from_file_location("base_utils", _PATH)
base_utils = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base_utils)


def test_explicit_default_wins():
    assert base_utils.get_secret("s3_bucket", default_value="s3://explicit") == "s3://explicit"


def test_falls_back_to_common_safe_default():
    assert base_utils.get_secret("catalog_name") == "mtg_dev"


def test_falls_back_to_layer_specific_default():
    assert base_utils.get_secret(
        "s3_gold_prefix", extra_safe_defaults={"s3_gold_prefix": "magic_the_gathering/gold"}
    ) == "magic_the_gathering/gold"


def test_raises_when_no_default_available():
    try:
        base_utils.get_secret("unknown_secret")
    except Exception as e:
        assert "unknown_secret" in str(e)
    else:
        raise AssertionError("expected Exception for secret with no default")


def test_s3_bucket_has_no_silent_fallback():
    # s3_bucket é o destino real de leitura/escrita de todas as camadas - não
    # pode cair silenciosamente num bucket placeholder quando o secret falha.
    try:
        base_utils.get_secret("s3_bucket")
    except Exception as e:
        assert "s3_bucket" in str(e)
    else:
        raise AssertionError("expected Exception for s3_bucket with no default")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_explicit_default_wins()
    test_falls_back_to_common_safe_default()
    test_falls_back_to_layer_specific_default()
    test_raises_when_no_default_available()
    test_s3_bucket_has_no_silent_fallback()
    print("OK")
