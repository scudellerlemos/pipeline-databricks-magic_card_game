# ponytail: fetch_price_index/get_card_price live inside a notebook cell (not
# an importable .py), so this loads that cell's source straight out of the
# .ipynb JSON and execs it with a fake `requests` (bulk-data index + gzipped
# jsonl payload) - same "exercise the real code" spirit as
# test_base_utils_get_secret.py, just for a notebook cell instead of a .py
# module.

import gzip
import json
import os
import sys
import types

_NB_PATH = os.path.join(os.path.dirname(__file__), "card_prices.ipynb")


def _load_functions(fake_get):
    with open(_NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)
    cell_source = "".join(nb["cells"][1]["source"])  # cell-1: fetch_price_index / get_card_price

    ns = {
        "requests": types.SimpleNamespace(get=fake_get),
        "unicodedata": __import__("unicodedata"),
        "gzip": gzip,
        "json": json,
        "datetime": __import__("datetime").datetime,
        "SCRYFALL_API_URL": "https://api.scryfall.test",
        "SCRYFALL_HEADERS": {},
        "SCRYFALL_BULK_TYPE": "oracle_cards",
    }
    exec(cell_source, ns)
    return ns["fetch_price_index"], ns["get_card_price"]


class _Resp:
    def __init__(self, json_data=None, content=None):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def _fake_get_for(cards):
    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/bulk-data"):
            return _Resp(json_data={"data": [
                {"type": "oracle_cards", "jsonl_download_uri": "https://data.test/oracle.jsonl.gz"}
            ]})
        body = "\n".join(json.dumps(c) for c in cards).encode("utf-8")
        return _Resp(content=gzip.compress(body))
    return fake_get


def test_fetch_price_index_resolves_by_name():
    cards = [{
        "name": "Nissa, Worldsoul Speaker", "set": "drc", "rarity": "rare",
        "prices": {"usd": "0.25", "eur": "0.21", "tix": "1.04"},
        "scryfall_uri": "https://scryfall.com/x",
        "image_uris": {"normal": "https://img/x.jpg"},
    }]

    fetch_price_index, get_card_price = _load_functions(_fake_get_for(cards))
    index = fetch_price_index()
    result = get_card_price("Nissa, Worldsoul Speaker", index)

    assert result["usd"] == "0.25"
    assert result["set"] == "drc"


def test_double_faced_card_indexed_by_each_face():
    # A Scryfall indexa cartas de dupla face com o nome combinado "A // B",
    # mas a fonte de cards referencia só a face da frente - fetch_price_index
    # precisa indexar as duas formas.
    cards = [{
        "name": "Brightglass Gearhulk // Brightglass Gearhulk", "set": "eoe", "rarity": "mythic",
        "prices": {"usd": "3.50", "eur": None, "tix": None},
        "scryfall_uri": "https://scryfall.com/y", "image_uris": None,
    }]

    fetch_price_index, get_card_price = _load_functions(_fake_get_for(cards))
    index = fetch_price_index()
    result = get_card_price("Brightglass Gearhulk", index)

    assert result["usd"] == "3.50"


def test_unknown_card_returns_error_not_exception():
    fetch_price_index, get_card_price = _load_functions(_fake_get_for([]))
    index = fetch_price_index()
    result = get_card_price("Totally Fake Card", index)

    assert result == {"name": "Totally Fake Card", "error": "Not found in Scryfall bulk data"}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_fetch_price_index_resolves_by_name()
    test_double_faced_card_indexed_by_each_face()
    test_unknown_card_returns_error_not_exception()
    print("OK")
