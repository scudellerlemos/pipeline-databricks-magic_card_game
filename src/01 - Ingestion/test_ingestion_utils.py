# ponytail: exercises the real functions from ingestion_utils.py directly,
# same import-by-path pattern as test_base_utils_get_secret.py. dbutils isn't
# defined outside a Databricks cluster, so finish_run's control-file write is
# expected to fail silently (its own try/except) unless a fake dbutils is
# injected on the module.

import importlib.util
import json
import os
import sys
import types
from contextlib import contextmanager

# pyspark não está instalado no CI (nem em pytest local fora de um cluster
# Databricks) - só o import, nunca chamado pelos testes abaixo (o único uso
# real, save_to_parquet, não é exercitado aqui). Stub mínimo pra satisfazer
# o `from pyspark.sql.functions import ...` de nível de módulo.
if "pyspark" not in sys.modules:
    pyspark = types.ModuleType("pyspark")
    pyspark_sql = types.ModuleType("pyspark.sql")
    pyspark_sql_functions = types.ModuleType("pyspark.sql.functions")
    pyspark_sql_types = types.ModuleType("pyspark.sql.types")
    for name in ("col", "lit", "current_timestamp", "year", "month", "when"):
        setattr(pyspark_sql_functions, name, lambda *a, **k: None)
    for name in ("StructType", "StructField", "StringType", "IntegerType", "FloatType"):
        setattr(pyspark_sql_types, name, lambda *a, **k: None)
    pyspark.sql = pyspark_sql
    sys.modules["pyspark"] = pyspark
    sys.modules["pyspark.sql"] = pyspark_sql
    sys.modules["pyspark.sql.functions"] = pyspark_sql_functions
    sys.modules["pyspark.sql.types"] = pyspark_sql_types

_PATH = os.path.join(os.path.dirname(__file__), "ingestion_utils.py")
_SPEC = importlib.util.spec_from_file_location("ingestion_utils", _PATH)
ingestion_utils = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ingestion_utils)


class _Resp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@contextmanager
def _patch(fake_get):
    """Swap ingestion_utils.requests.get for fake_get and time.sleep for a no-op."""
    real_get, real_sleep = ingestion_utils.requests.get, ingestion_utils.time.sleep
    ingestion_utils.requests.get = fake_get
    ingestion_utils.time.sleep = lambda *_: None
    try:
        yield
    finally:
        ingestion_utils.requests.get = real_get
        ingestion_utils.time.sleep = real_sleep


def test_http_get_with_retry_returns_response_on_success():
    with _patch(lambda *a, **k: _Resp(200, {"ok": True})):
        resp = ingestion_utils.http_get_with_retry("https://x.test")
    assert resp.json() == {"ok": True}


def test_http_get_with_retry_retries_on_5xx_then_succeeds():
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _Resp(503) if calls["n"] < 2 else _Resp(200, {"ok": True})

    with _patch(fake_get):
        resp = ingestion_utils.http_get_with_retry("https://x.test", retries=3)

    assert resp.json() == {"ok": True}
    assert calls["n"] == 2


def test_http_get_with_retry_fails_fast_on_4xx():
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _Resp(404)

    try:
        with _patch(fake_get):
            ingestion_utils.http_get_with_retry("https://x.test", retries=3)
    except Exception:
        pass
    else:
        raise AssertionError("expected exception for 404")
    assert calls["n"] == 1  # 4xx nao tenta de novo


def test_http_get_with_retry_raises_after_exhausting_retries():
    try:
        with _patch(lambda *a, **k: _Resp(500)):
            ingestion_utils.http_get_with_retry("https://x.test", retries=2)
    except Exception:
        pass
    else:
        raise AssertionError("expected exception after exhausting retries")


def test_get_scryfall_set_codes_since_filters_by_date_and_lowercases():
    sets_data = {"data": [
        {"code": "LEA", "released_at": "1993-08-05"},
        {"code": "trc", "released_at": "2026-11-13"},
        {"code": "old", "released_at": "1990-01-01"},
    ]}
    with _patch(lambda *a, **k: _Resp(200, sets_data)):
        codes = ingestion_utils.get_scryfall_set_codes_since("https://api.scryfall.test", {}, "2000-01-01")

    # lea (1993) e old (1990) ficam fora da janela (cutoff 2000-01-01); trc
    # (2026) entra e o code vem normalizado pra minúsculo.
    assert codes == ["trc"]


def test_start_run_has_expected_shape():
    run = ingestion_utils.start_run("cards", endpoint="bulk-data/default_cards", params={"years_back": 5})
    assert run["table_name"] == "cards"
    assert run["status"] == "RUNNING"
    assert run["origem"] == "scryfall"
    assert len(run["run_id"]) == 12


def test_finish_run_without_dbutils_does_not_raise():
    # Fora de um cluster Databricks (pytest local) dbutils não existe - o
    # write do controle deve falhar em silêncio, sem mascarar o status real.
    run = ingestion_utils.start_run("cards", endpoint="bulk-data/default_cards")
    run["files_written"] = 3
    finished = ingestion_utils.finish_run(run, "s3://test-bucket/stage", "SUCCESS")
    assert finished["status"] == "SUCCESS"
    assert finished["files_written"] == 3
    assert "duration_seconds" in finished


def test_finish_run_writes_control_json_when_dbutils_available():
    written = {}

    class _FakeFs:
        def mkdirs(self, path):
            written["dir"] = path

        def put(self, path, content, overwrite=True):
            written["path"] = path
            written["content"] = content

    ingestion_utils.dbutils = types.SimpleNamespace(fs=_FakeFs())
    try:
        run = ingestion_utils.start_run("sets", endpoint="sets")
        ingestion_utils.finish_run(run, "s3://test-bucket/stage", "FAILED", error="boom")

        assert written["dir"] == "s3://test-bucket/stage/_control/sets"
        assert written["path"] == f"s3://test-bucket/stage/_control/sets/{run['run_id']}.json"
        payload = json.loads(written["content"])
        assert payload["status"] == "FAILED"
        assert payload["error"] == "boom"
    finally:
        del ingestion_utils.dbutils


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_http_get_with_retry_returns_response_on_success()
    test_http_get_with_retry_retries_on_5xx_then_succeeds()
    test_http_get_with_retry_fails_fast_on_4xx()
    test_http_get_with_retry_raises_after_exhausting_retries()
    test_get_scryfall_set_codes_since_filters_by_date_and_lowercases()
    test_start_run_has_expected_shape()
    test_finish_run_without_dbutils_does_not_raise()
    test_finish_run_writes_control_json_when_dbutils_available()
    print("OK")
