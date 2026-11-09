"""The result contracts survive a round trip, and the display-name tables match their sources."""
import json
import re
from pathlib import Path

import pytest

from xq_classify import SCHEMA_VERSION, CheckmateResult, MidgameResult, classify_checkmate, classify_midgame
from xq_classify.checkmate import PATTERN_ORDER
from xq_classify.checkmate.material import _ALLOWED_CODES
from xq_classify.labels import CHECKMATE_PATTERNS_ZH_TW, MATING_MATERIAL_ZH_TW, MIDGAME_LABELS_ZH_TW

REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def _frozen_cases(suite: str) -> list[dict]:
    """Inputs only: these tests never read a frozen case's expected labels."""
    return json.loads((FIXTURES / suite / "v1.json").read_text(encoding="utf-8"))["cases"][:25]


CHECKMATE_CASES = _frozen_cases("checkmate_frozen")
MIDGAME_CASES = _frozen_cases("midgame_frozen")


def _through_json(record: dict) -> dict:
    return json.loads(json.dumps(record, ensure_ascii=False))


def _assert_same_record(actual: dict, expected: dict) -> None:
    """Equal values and equal key order, which a plain dict comparison would ignore."""
    assert json.dumps(actual, ensure_ascii=False) == json.dumps(expected, ensure_ascii=False)


@pytest.mark.parametrize("case", CHECKMATE_CASES, ids=lambda case: case["id"])
def test_checkmate_record_round_trips(case):
    record = classify_checkmate(case["initialFen"], case["blunderMove"], case["pv"]).to_dict()
    assert _through_json(record) == record
    _assert_same_record(CheckmateResult.from_dict(_through_json(record)).to_dict(), record)


@pytest.mark.parametrize(
    ("blunder", "pv"),
    [("a0a0", []), (CHECKMATE_CASES[0]["blunderMove"], [])],
    ids=["illegal_move", "line_does_not_end_in_mate"],
)
def test_invalid_checkmate_record_round_trips(blunder, pv):
    result = classify_checkmate(CHECKMATE_CASES[0]["initialFen"], blunder, pv)
    assert result.status == "invalid"
    _assert_same_record(CheckmateResult.from_dict(_through_json(result.to_dict())).to_dict(), result.to_dict())


@pytest.mark.parametrize("case", MIDGAME_CASES, ids=lambda case: case["id"])
def test_midgame_result_round_trips(case):
    result = classify_midgame(case["initialFen"], case["blunderMove"], case["pv"], case["solverSide"])
    record = result.to_dict()
    assert _through_json(record) == record
    rebuilt = MidgameResult.from_dict(_through_json(record))
    assert rebuilt == result
    _assert_same_record(rebuilt.to_dict(), record)


def test_schema_version_is_on_the_result_and_not_in_the_record():
    checkmate = CHECKMATE_CASES[0]
    midgame = MIDGAME_CASES[0]
    results = [
        classify_checkmate(checkmate["initialFen"], checkmate["blunderMove"], checkmate["pv"]),
        classify_midgame(midgame["initialFen"], midgame["blunderMove"], midgame["pv"], midgame["solverSide"]),
    ]
    for result in results:
        assert result.schema_version == SCHEMA_VERSION
        assert "schemaVersion" not in result.to_dict()


def test_midgame_names_and_order_match_the_published_index():
    index = json.loads((REPO / "public/data/capturing-tactics.json").read_text(encoding="utf-8"))
    assert list(index["labels"].items()) == list(MIDGAME_LABELS_ZH_TW.items())


def test_checkmate_names_match_the_rules_document():
    text = (REPO / "docs/checkmate-recognition-logic.zh-TW.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## \d+\. (.+?)\n+程式識別碼：`([A-Z_]+)`", text, flags=re.MULTILINE)
    assert {pattern: name.strip() for name, pattern in sections} == CHECKMATE_PATTERNS_ZH_TW


def test_checkmate_names_cover_every_recogniser_in_order():
    assert list(CHECKMATE_PATTERNS_ZH_TW) == PATTERN_ORDER


def test_material_names_follow_the_rules_document():
    pieces = {"R": "車", "N": "馬", "C": "炮", "P": "兵"}
    expected = {code: "".join(pieces[piece] for piece in code) + ("殺" if len(code) == 1 else "") for code in _ALLOWED_CODES}
    assert MATING_MATERIAL_ZH_TW == expected
