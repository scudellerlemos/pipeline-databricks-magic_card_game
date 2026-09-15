# ponytail: pure-logic self-check for _resolve_id_chain() in TB_MOV_MIGRACOES_CARTAS.ipynb
# (issue #135 / AUD-20; relocated from TB_FATO_CARTAS.ipynb when price/migration data was
# split out into their own Silver tables). Can't import the notebook directly (not a .py
# module, and its other functions need a live Databricks spark session), so this mirrors
# just the chain-resolution function under test.


def _resolve_id_chain(direct_map):
    resolved = {}
    for start in direct_map:
        current = start
        seen = {start}
        hops = 0
        while current in direct_map and hops < 10:
            nxt = direct_map[current]
            if nxt in seen:
                break
            current = nxt
            seen.add(current)
            hops += 1
        resolved[start] = current
    return resolved


def test_no_migrations():
    assert _resolve_id_chain({}) == {}


def test_single_merge():
    # A mergeou em B
    assert _resolve_id_chain({"A": "B"}) == {"A": "B"}


def test_chained_merge_resolves_to_final_id():
    # A mergeou em B, B mergeou em C -> A deve resolver direto pra C
    direct_map = {"A": "B", "B": "C"}
    assert _resolve_id_chain(direct_map) == {"A": "C", "B": "C"}


def test_cycle_stops_instead_of_looping_forever():
    # não deveria acontecer em dado real da Scryfall, mas não pode travar
    direct_map = {"A": "B", "B": "A"}
    resolved = _resolve_id_chain(direct_map)
    assert resolved["A"] in ("A", "B")
    assert resolved["B"] in ("A", "B")


def test_independent_chains_dont_interfere():
    direct_map = {"A": "B", "B": "C", "X": "Y"}
    resolved = _resolve_id_chain(direct_map)
    assert resolved["A"] == "C"
    assert resolved["X"] == "Y"


if __name__ == "__main__":
    test_no_migrations()
    test_single_merge()
    test_chained_merge_resolves_to_final_id()
    test_cycle_stops_instead_of_looping_forever()
    test_independent_chains_dont_interfere()
    print("OK")
