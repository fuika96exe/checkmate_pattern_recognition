"""The no-blunder entry (``blunder=None``): ply numbering, result shapes and input checks.

These tests never assert labels. Label coverage for this path comes only from a
human-frozen version (AGENTS.md); ``scripts/no_blunder_diff.py`` reports how its
labels differ from the frozen ones. The frozen files are read for inputs only.
"""
import json
from pathlib import Path

import pytest

from xq_classify import CheckmateResult, MidgameResult, ReplayError, board, classify_checkmate, classify_midgame
from xq_classify.checkmate.classify import EMPTY_LINE_ERROR

FIXTURES = Path(__file__).parent / "fixtures"


def _frozen_inputs(suite: str) -> list[dict]:
    return json.loads((FIXTURES / suite / "v1.json").read_text(encoding="utf-8"))["cases"][:25]


CHECKMATE_CASES = _frozen_inputs("checkmate_frozen")
MIDGAME_CASES = _frozen_inputs("midgame_frozen")
PASS_PLY = {"ply": 1, "ucci": None, "solver": False, "occurrences": []}


def _after_blunder(case: dict) -> str:
    return board.apply_move(case["initialFen"], case["blunderMove"])


def _through_json(record: dict) -> dict:
    return json.loads(json.dumps(record, ensure_ascii=False))


@pytest.mark.parametrize("case", MIDGAME_CASES, ids=lambda case: case["id"])
def test_midgame_pass_keeps_the_ply_numbering(case):
    start = _after_blunder(case)
    with_blunder = classify_midgame(case["initialFen"], case["blunderMove"], case["pv"], case["solverSide"])
    result = classify_midgame(start, None, case["pv"], case["solverSide"])
    assert result.plies[0] == PASS_PLY
    assert [p["ply"] for p in result.plies] == [p["ply"] for p in with_blunder.plies]
    assert [p["solver"] for p in result.plies] == [p["solver"] for p in with_blunder.plies]
    assert [p["ucci"] for p in result.plies[1:]] == case["pv"]
    assert result.fens[0] == result.fens[1] == start
    assert result.fens[1:] == with_blunder.fens[1:]
    assert all(o["evidence"]["triggerPly"] >= 2 for ply in result.plies for o in ply["occurrences"])
    assert MidgameResult.from_dict(_through_json(result.to_dict())) == result


def test_midgame_without_blunder_needs_the_solver_to_move():
    case = MIDGAME_CASES[0]
    with pytest.raises(ReplayError, match="first_turn mismatch") as caught:
        classify_midgame(case["initialFen"], None, case["pv"], case["solverSide"])
    assert (caught.value.ply, caught.value.fen, caught.value.move) == (1, case["initialFen"], None)


def test_midgame_without_blunder_still_needs_a_line():
    case = MIDGAME_CASES[0]
    with pytest.raises(ReplayError) as caught:
        classify_midgame(_after_blunder(case), None, [], case["solverSide"])
    assert caught.value.ply == 0


@pytest.mark.parametrize("case", CHECKMATE_CASES, ids=lambda case: case["id"])
def test_checkmate_without_blunder_plays_the_line_alone(case):
    start = _after_blunder(case)
    with_blunder = classify_checkmate(case["initialFen"], case["blunderMove"], case["pv"])
    result = classify_checkmate(start, None, case["pv"])
    assert [step["index"] for step in result.timeline] == list(range(len(case["pv"]) + 1))
    assert [step["move"] for step in result.timeline] == [None, *case["pv"]]
    assert result.timeline[0]["fen"] == start
    assert result.timeline[-1]["fen"] == with_blunder.timeline[-1]["fen"]
    record = result.to_dict()
    assert CheckmateResult.from_dict(_through_json(record)).to_dict() == record


def test_checkmate_without_blunder_counts_failed_moves_in_the_line():
    case = next(case for case in CHECKMATE_CASES if len(case["pv"]) >= 3)
    result = classify_checkmate(_after_blunder(case), None, [case["pv"][0], "a0a0"])
    assert (result.status, result.failed_move_index) == ("invalid", 2)
    assert result.error.startswith("第 2 手 a0a0")


def test_checkmate_without_blunder_rejects_an_empty_line():
    case = CHECKMATE_CASES[0]
    result = classify_checkmate(_after_blunder(case), None, [])
    assert (result.status, result.error) == ("invalid", EMPTY_LINE_ERROR)
    assert CheckmateResult.from_dict(_through_json(result.to_dict())).to_dict() == result.to_dict()
