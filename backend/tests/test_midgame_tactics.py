"""Midgame infrastructure tests (scoring, replay, I/O, exchange value). Puzzle-label expectations live only in
the human-frozen set (test_midgame_frozen.py); batch output must never rewrite fixtures."""
import csv
import json
from pathlib import Path

import pytest

from backend.app import board as b
from backend.app.midgame_tactics import (
    LABELS, Position, ReplayError, material_result, profitable_capture, replay,
)
from backend.scripts.generate_capturing_tactics import label_puzzle, row_from_existing_record

FIXTURES = Path(__file__).parent / "fixtures"
# Input only (puzzle ovMw1a); infrastructure tests below assert replay/IO behaviour, not tactic labels.
REPLAY_CASE = {"fen": "3a5/4k4/5a2C/4N1c1p/pn2r1b2/7R1/P3P3P/4B4/9/3AKAB2 w - - 1 27",
               "blunder": "h4e4", "pv": ["e5e4", "e3e4", "g5i7", "e6c5"]}


def fen_of(pieces, side="red"):
    return f"{b.board_to_fen({'d0': 'K', 'f9': 'k', **pieces})} {'w' if side == 'red' else 'b'} - - 0 1"


@pytest.mark.parametrize("initial,final,delta,kind", [
    ({"a0":"C","a5":"r"}, {}, 5, "gain"),
    ({"a5":"n","c3":"P","g3":"P"}, {}, 4, "gain"),
    ({"a0":"N","a5":"c","d9":"a"}, {}, 0, "no_gain"),
    ({"a0":"R","a5":"n","b5":"c"}, {}, -1, "no_gain"),
    ({"a0":"N","a5":"n"}, {}, 0, "no_gain"),
])
def test_material_vectors_both_colors(initial, final, delta, kind):
    for side in ("red", "black"):
        start, end = fen_of(initial), fen_of(final)
        if side == "black":
            start, end = swap_colors(start), swap_colors(end)
        result = material_result(start, end, side)
        assert result["delta"] == delta
        assert result["kind"] == kind
        assert result["end"] - result["start"] == delta


def swap_colors(fen):
    board = {f"{chr(ord('i') - (ord(s[0]) - ord('a')))}{9-int(s[1])}": p.swapcase() for s, p in b.parse_fen(fen).items()}
    return f"{b.board_to_fen(board)} {'b' if b.side_to_move(fen) == 'red' else 'w'} - - 0 1"


def test_replay_ids_captures_and_invalid_ply():
    c = REPLAY_CASE
    positions, events = replay(c["fen"], c["blunder"], c["pv"], "black")
    assert events[0].actor == positions[1].ids["e4"]
    assert positions[1].ids["e4"] not in positions[2].squares
    assert events[1].actor == positions[2].ids["e4"]
    assert events[1].actor not in positions[3].squares
    assert len({id(p.ids) for p in positions}) == len(positions)
    with pytest.raises(ReplayError) as caught:
        replay(c["fen"], c["blunder"], [*c["pv"], "a0a9"], "black")
    assert caught.value.ply == 6
    assert caught.value.fen == positions[-1].fen


@pytest.mark.parametrize("change", [{"pv":"[]"}, {"pv":"oops"}, {"pv":"None"}, {"pv":"{}"}, {"first_turn":"red"}, {"fen_before":"invalid"}, {"pv":"['a0a9']"}])
def test_invalid_is_never_no_gain(change):
    c = REPLAY_CASE
    row = {"fen_before": c["fen"], "blunder_move": c["blunder"], "pv":repr(c["pv"]),
           "first_turn":"black", "url":"https://www.xiangqi.com/puzzles/test/P", "rating":"1000", **change}
    result = label_puzzle(row)
    assert result["status"] == "invalid"
    assert result["id"] == "test"
    assert result["material"] is None and not result["tactics"]
    assert isinstance(result["pv"], list)
    assert isinstance(result["errorPly"], int) and result["errorFen"]


def test_import_and_existing_dataset_agree():
    root = Path(__file__).parents[2]
    with (root / "data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))[:3]
    for row in rows:
        imported = label_puzzle(row)
        assert imported == label_puzzle(row_from_existing_record(imported))


@pytest.mark.parametrize("case", json.loads((FIXTURES / "fake_human_exchange.json").read_text(encoding="utf-8"))["cases"])
def test_profit_upstream_reference(case):
    ok, gain = profitable_capture(case["fen"], case["move"])
    if case["move"][2:] not in b.parse_fen(case["fen"]):
        assert (ok, gain) == (False, None)  # quiet evaluator probes are not captures
        return
    assert gain == case["gain"]
    assert ok == (case["gain"] > 0)


def test_profit_one_not_threat_threshold_and_illegal_not_zero():
    fen = fen_of({"a4":"R", "a5":"p"})
    assert profitable_capture(fen, "a4a5") == (True, 1)
    assert profitable_capture(fen, "a4b5") == (False, None)
    fen = fen_of({"a4":"R", "a5":"p", "b0":"R", "c0":"C", "g8":"r", "h8":"r", "i8":"c"})
    assert profitable_capture(fen, "a4a5") == (False, None)


def test_pinned_capture_not_a_legal_threat():
    fen = fen_of({"d3":"R", "d8":"r", "h3":"n"})
    assert profitable_capture(fen, "d3h3") == (False, None)
    pos = Position(fen, b.build_piece_identity(fen), "red")
    assert pos.ids["h3"] not in pos.threats


def test_labels_are_only_the_ten_midgame_ids():
    assert len(LABELS) == 10 and "clearance" in LABELS and "cannon_pawn_breakthrough" not in LABELS


def test_partial_relabel_is_independent_and_public_index_is_guarded(tmp_path):
    import subprocess
    import sys
    stored = tmp_path / "old.json"
    stored.write_text(json.dumps({"puzzles":[{},{}], "eligibleRows":2}), encoding="utf-8")
    script = str(Path(__file__).parents[1] / "scripts/generate_capturing_tactics.py")
    command = [sys.executable, script, "--existing-dataset", str(stored), "--start", "1", "--limit", "0"]
    denied = subprocess.run(command, capture_output=True, text=True)
    assert denied.returncode != 0 and "Partial relabels" in denied.stderr
    output = tmp_path / "partial.json"
    allowed = subprocess.run([*command, "--output", str(output)], capture_output=True, text=True)
    assert allowed.returncode == 0, allowed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["partial"] and payload["schemaVersion"] == "2.1" and payload["puzzles"] == []


def test_detector_failure_propagates_without_becoming_invalid(monkeypatch):
    from backend.scripts import generate_capturing_tactics as generator
    c = REPLAY_CASE
    row = {"fen_before":c["fen"], "blunder_move":c["blunder"], "pv":repr(c["pv"]),
           "first_turn":"black", "url":"https://example.com/test/P", "rating":"1000"}
    def broken(*args):
        raise ValueError("detector bug")
    monkeypatch.setattr(generator, "analyze_midgame_categories", broken)
    with pytest.raises(ValueError, match="detector bug"):
        label_puzzle(row)


def test_invalid_raw_input_survives_existing_dataset_relabel():
    row = {"fen_before":"bad fen", "blunder_move":"a0a1", "pv":"unparseable",
           "first_turn":"black", "url":"https://example.com/test/P", "rating":"1000"}
    invalid = label_puzzle(row)
    assert label_puzzle(row_from_existing_record(invalid)) == invalid
