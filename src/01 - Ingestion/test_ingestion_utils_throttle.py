# ponytail: exercises the real _throttle_request/make_api_request from
# ingestion_utils.py (issue #117 follow-up: STAGE_CARDS silently lost 63/132
# collections because make_api_request had no pacing between calls, only the
# per-page sleep inside cards.ipynb's own loop). Same "load the real module"
# approach as test_base_utils_get_secret.py.

import importlib.util
import os
import sys
import time as _realtime
import types

_PATH = os.path.join(os.path.dirname(__file__), "ingestion_utils.py")
_SPEC = importlib.util.spec_from_file_location("ingestion_utils", _PATH)
ingestion_utils = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ingestion_utils)


def test_throttle_spaces_out_consecutive_calls():
    ingestion_utils.REQUEST_SLEEP_BETWEEN = 0.05
    ingestion_utils._last_request_time[0] = 0.0

    start = _realtime.monotonic()
    for _ in range(3):
        ingestion_utils._throttle_request()
    elapsed = _realtime.monotonic() - start

    assert elapsed >= 0.1, f"expected >= 0.1s for 3 throttled calls at 0.05s spacing, got {elapsed:.3f}s"


def test_make_api_request_throttles_between_attempts():
    ingestion_utils.REQUEST_SLEEP_BETWEEN = 0.1
    ingestion_utils._last_request_time[0] = 0.0
    calls = {"n": 0}

    class _Resp:
        status_code = 200

        def json(self):
            return {"ok": True}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        return _Resp()

    ingestion_utils.requests = types.SimpleNamespace(get=fake_get, exceptions=ingestion_utils.requests.exceptions)

    start = _realtime.monotonic()
    ingestion_utils.make_api_request("sets", "https://api.test")
    ingestion_utils.make_api_request("sets", "https://api.test")
    elapsed = _realtime.monotonic() - start

    assert calls["n"] == 2
    assert elapsed >= 0.08, f"expected the 2nd call to wait for the throttle, got {elapsed:.3f}s"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_throttle_spaces_out_consecutive_calls()
    test_make_api_request_throttles_between_attempts()
    print("OK")
