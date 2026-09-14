# ponytail: get_card_price lives inside a notebook cell (not an importable
# .py), so this loads that cell's source straight out of the .ipynb JSON and
# execs it with a fake `requests`/`time.sleep` - same "exercise the real code"
# spirit as test_base_utils_get_secret.py, just for a notebook cell instead of
# a .py module.

import json
import os
import sys
import threading
import time as _realtime
import types

_NB_PATH = os.path.join(os.path.dirname(__file__), "card_prices.ipynb")


def _load_get_card_price(fake_get, sleep_calls):
    with open(_NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)
    cell_source = "".join(nb["cells"][1]["source"])  # cell-1: get_card_price

    ns = {
        "requests": types.SimpleNamespace(get=fake_get),
        "unicodedata": __import__("unicodedata"),
        "quote": __import__("urllib.parse", fromlist=["quote"]).quote,
        "datetime": __import__("datetime").datetime,
        "threading": threading,
        # SLEEP_BETWEEN=0 disables the proactive throttle's own sleeping so
        # only the 429-backoff sleeps (asserted below) show up in sleep_calls.
        "time": types.SimpleNamespace(sleep=lambda s: sleep_calls.append(s), monotonic=_realtime.monotonic),
        "SCRYFALL_API_URL": "https://api.scryfall.test",
        "SCRYFALL_HEADERS": {},
        "SLEEP_BETWEEN": 0,
    }
    exec(cell_source, ns)
    return ns["get_card_price"]


class _Resp:
    def __init__(self, status_code, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self):
        return self._json


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}
    sleep_calls = []

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            return _Resp(429, headers={"Retry-After": "0"})
        return _Resp(200, {"name": "Bloodtithe Harvester", "prices": {"usd": "1.23"}})

    get_card_price = _load_get_card_price(fake_get, sleep_calls)
    result = get_card_price("Bloodtithe Harvester")

    assert result["usd"] == "1.23"
    assert calls["n"] == 3, "expected two 429 retries before the 200"
    assert len(sleep_calls) == 2, "expected a backoff sleep before each retry"


def test_gives_up_after_max_retries_as_error_not_exception():
    sleep_calls = []

    def fake_get(url, headers=None, timeout=None):
        return _Resp(429, headers={})

    get_card_price = _load_get_card_price(fake_get, sleep_calls)
    result = get_card_price("Anything", max_retries=3)

    assert result["error"] == "Status 429"
    assert len(sleep_calls) == 3


def test_throttle_spaces_out_concurrent_calls():
    # SLEEP_BETWEEN=0.05 here (not the module-level ns default of 0) so this
    # test can observe real spacing without slowing the suite down much.
    with open(_NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)
    cell_source = "".join(nb["cells"][1]["source"])
    ns = {
        "requests": types.SimpleNamespace(get=lambda *a, **k: _Resp(200, {"name": "x"})),
        "unicodedata": __import__("unicodedata"),
        "quote": __import__("urllib.parse", fromlist=["quote"]).quote,
        "datetime": __import__("datetime").datetime,
        "threading": threading,
        "time": _realtime,
        "SCRYFALL_API_URL": "https://api.scryfall.test",
        "SCRYFALL_HEADERS": {},
        "SLEEP_BETWEEN": 0.05,
    }
    exec(cell_source, ns)
    throttle = ns["_throttle"]

    start = _realtime.monotonic()
    for _ in range(3):
        throttle()
    elapsed = _realtime.monotonic() - start

    assert elapsed >= 0.1, f"expected >= 0.1s for 3 throttled calls at 0.05s spacing, got {elapsed:.3f}s"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_retries_on_429_then_succeeds()
    test_gives_up_after_max_retries_as_error_not_exception()
    test_throttle_spaces_out_concurrent_calls()
    print("OK")
