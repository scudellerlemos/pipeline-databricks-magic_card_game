# ponytail: same approach as test_cards.py - the notebook cell isn't an
# importable .py, so load its source straight out of the .ipynb JSON and exec
# it with a fake `requests` (single Scryfall /sets response).

import json
import os
import sys
import types

_NB_PATH = os.path.join(os.path.dirname(__file__), "sets.ipynb")


def _load_functions(fake_get):
    with open(_NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)
    cell_source = "".join(nb["cells"][1]["source"])  # cell-1: sets-specific functions

    ns = {
        "json": json,
        "requests": types.SimpleNamespace(get=fake_get),
        "StructType": lambda fields: None,
        "StructField": lambda *a, **k: None,
        "StringType": lambda: None,
        "IntegerType": lambda: None,
        "BooleanType": lambda: None,
        "SCRYFALL_API_URL": "https://api.scryfall.test",
        "SCRYFALL_HEADERS": {},
        "setup_s3_storage": lambda *a, **k: True,
        "S3_BASE_PATH": "s3://test-bucket/stage",
    }
    exec(cell_source, ns)
    return ns["_to_set_record"], ns["fetch_all_sets"], ns["clean_sets_data"]


class _Resp:
    def __init__(self, json_data):
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def _fake_get_for(sets_data):
    def fake_get(url, headers=None, timeout=None):
        assert url.endswith("/sets")
        return _Resp({"object": "list", "has_more": False, "data": sets_data})
    return fake_get


def test_fetch_all_sets_maps_fields_in_single_request():
    sets_data = [
        {"code": "lea", "name": "Limited Edition Alpha", "set_type": "core",
         "released_at": "1993-08-05", "digital": False},
        {"code": "trc", "name": "Star Trek Commander", "set_type": "commander",
         "released_at": "2026-11-13", "digital": False},
    ]

    _, fetch_all_sets, _ = _load_functions(_fake_get_for(sets_data))
    records = fetch_all_sets()

    assert len(records) == 2
    assert records[0]["code"] == "lea"
    assert records[0]["type"] == "core"
    assert records[0]["releaseDate"] == "1993-08-05"
    assert records[0]["onlineOnly"] is False


def test_fetch_all_sets_no_pagination_needed():
    # bug #127: magicthegathering.io /sets sem params devolvia só a 1a
    # página (500 de 773). A Scryfall devolve o catálogo inteiro em 1
    # request só (has_more: false) - sem loop de paginação necessário.
    sets_data = [{"code": f"s{i}", "name": f"Set {i}", "set_type": "expansion",
                  "released_at": "2020-01-01", "digital": False} for i in range(1049)]

    _, fetch_all_sets, _ = _load_functions(_fake_get_for(sets_data))
    records = fetch_all_sets()

    assert len(records) == 1049


def test_magicthegathering_only_fields_become_none_after_clean():
    # border/mkm_id/mkm_name/gathererCode/magicCardsInfoCode/oldCode/booster
    # não têm equivalente na Scryfall - clean_sets_data já trata ausência
    # como None (comportamento existente, não alterado).
    to_set_record, _, clean_sets_data = _load_functions(_fake_get_for([]))
    record = to_set_record({"code": "lea", "name": "Alpha", "set_type": "core",
                             "released_at": "1993-08-05", "digital": False})

    cleaned = clean_sets_data([record])[0]
    assert cleaned["border"] is None
    assert cleaned["mkm_id"] is None
    assert cleaned["gathererCode"] is None
    assert cleaned["oldCode"] is None
    assert cleaned["booster"] is None
    assert cleaned["code"] == "lea"
    assert cleaned["onlineOnly"] is False


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_fetch_all_sets_maps_fields_in_single_request()
    test_fetch_all_sets_no_pagination_needed()
    test_magicthegathering_only_fields_become_none_after_clean()
    print("OK")
