import json
import asyncio
from pathlib import Path

import pytest

from app.patterns import analyze_patterns, recognize_pattern
from app.main import api_analyze_puzzle_line
from app.models import PuzzleLineRequest


@pytest.fixture(scope="module")
def puzzles():
    path = Path(__file__).resolve().parents[2] / "public/data/checkmate-puzzles.json"
    return {p["key"]: p for p in json.loads(path.read_text(encoding="utf-8"))["puzzles"]}


def analyze(puzzles, key):
    puzzle = puzzles[key]
    fen = puzzle["initialFen"]
    moves = [puzzle["blunderMove"], *puzzle["pv"]]
    return fen, moves, analyze_patterns(fen, moves)


def test_elbow_horse_takes_precedence_over_discovered_horse(puzzles):
    fen, moves, result = analyze(puzzles, "LxN1ej")
    labels = {match["pattern_id"] for match in result["matches"]}
    assert "ELBOW_HORSE_CHECKMATE" in labels
    assert "DISCOVERED_HORSE_CHECKMATE" not in labels
    assert not analyze_patterns(fen, moves, "DISCOVERED_HORSE_CHECKMATE")["matches"]


def test_elbow_horse_must_control_king_or_escape(puzzles):
    for key, expected in [("q8pw6b", {"e9"}), ("L3Wg61", {"e0"})]:
        fen, moves, _ = analyze(puzzles, key)
        match = recognize_pattern("ELBOW_HORSE_CHECKMATE", fen, moves)
        assert match["detected"]
        assert any(expected <= set(targets) for targets in match["features"]["elbow_horse_control"].values())
    fen, moves, _ = analyze(puzzles, "RWyWQP")
    match = recognize_pattern("ELBOW_HORSE_CHECKMATE", fen, moves)
    assert match["analysis"]["is_checkmate"]
    assert match["features"]["static_elbow_horse_squares"] == ["c8"]
    assert match["features"]["elbow_horse_control"] == {"c8": []}
    assert not match["detected"]


@pytest.mark.parametrize("key, preferred", [
    ("oX0npX", "CENTROID_CHECKMATE"),
    ("Ll62lJ", "CROWNED_CHECKMATE"),
])
def test_specific_patterns_take_precedence_over_double_chariots(puzzles, key, preferred):
    fen, moves, result = analyze(puzzles, key)
    labels = {match["pattern_id"] for match in result["matches"]}
    assert recognize_pattern("DOUBLE_CHARIOTS_CHECKMATE", fen, moves)["detected"]
    assert preferred in labels and "DOUBLE_CHARIOTS_CHECKMATE" not in labels
    assert not analyze_patterns(fen, moves, "DOUBLE_CHARIOTS_CHECKMATE")["matches"]


def test_double_rooks_in_elephant_eyes_no_longer_count_as_two_pawns(puzzles):
    fen, moves, result = analyze(puzzles, "RPx5nB")
    assert not recognize_pattern("TWO_DEVILS_KNOCKING_CHECKMATE", fen, moves)["detected"]
    assert "DOUBLE_CHARIOTS_CHECKMATE" in {match["pattern_id"] for match in result["matches"]}


def test_removed_double_horses_pattern_is_not_available(puzzles):
    fen, moves, result = analyze(puzzles, "LJXVW4")
    assert "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE" not in {match["pattern_id"] for match in result["matches"]}
    with pytest.raises(ValueError):
        recognize_pattern("DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE", fen, moves)


def test_horse_cannon_takes_precedence_over_palcorner(puzzles):
    fen, moves, result = analyze(puzzles, "Ll62NB")
    assert recognize_pattern("PALCORNER_HORSE_CHECKMATE", fen, moves)["detected"]
    assert recognize_pattern("HORSE_CANNON_CHECKMATE", fen, moves)["detected"]
    labels = {match["pattern_id"] for match in result["matches"]}
    assert "HORSE_CANNON_CHECKMATE" in labels and "PALCORNER_HORSE_CHECKMATE" not in labels
    assert not analyze_patterns(fen, moves, "PALCORNER_HORSE_CHECKMATE")["matches"]


def test_sandwiching_cannons_require_all_three_in_opponent_camp_ranks(puzzles):
    fen, moves, _ = analyze(puzzles, "L3WgA1")
    assert recognize_pattern("CANNONS_SANDWICHING_CHARIOT_CHECKMATE", fen, moves)["detected"]
    fen, moves, _ = analyze(puzzles, "LDjOxb")
    match = recognize_pattern("CANNONS_SANDWICHING_CHARIOT_CHECKMATE", fen, moves)
    assert match["analysis"]["is_checkmate"] and not match["detected"]


def test_removed_pattern_is_not_available_or_classified(puzzles):
    fen, moves, result = analyze(puzzles, "ojl2Q0")
    assert "EUNUCHS_CHASING_EMPEROR_CHECKMATE" not in {match["pattern_id"] for match in result["matches"]}
    with pytest.raises(ValueError):
        recognize_pattern("EUNUCHS_CHASING_EMPEROR_CHECKMATE", fen, moves)


def test_drawer_after_defender_opening_move(puzzles):
    _, _, result = analyze(puzzles, "L3WgPJ")
    assert "DRAWER_CHECKMATE" in {match["pattern_id"] for match in result["matches"]}


@pytest.mark.parametrize("key", ["ojl2M5", "RV5wxE"])
def test_unprotected_center_advisor_does_not_qualify(puzzles, key):
    fen, moves, result = analyze(puzzles, key)
    assert "THROAT_CUTTING_CHECKMATE" not in {match["pattern_id"] for match in result["matches"]}
    assert not recognize_pattern("THROAT_CUTTING_CHECKMATE", fen, moves)["features"]["qualifying_captures"]


def test_cannon_rook_double_check_yields_to_specific_pattern(puzzles):
    fen, moves, result = analyze(puzzles, "RPx5Pw")
    raw = recognize_pattern("DOUBLE_CHECK_CHECKMATE", fen, moves)
    assert set(raw["features"]["checking_piece_types"]) == {"C", "R"}
    assert "DOUBLE_CHARIOTS_CHECKMATE" in {match["pattern_id"] for match in result["matches"]}
    assert "DOUBLE_CHECK_CHECKMATE" not in {match["pattern_id"] for match in result["matches"]}
    assert not analyze_patterns(fen, moves, "DOUBLE_CHECK_CHECKMATE")["matches"]


def test_cannon_rook_double_check_remains_when_no_other_pattern(puzzles):
    _, _, result = analyze(puzzles, "oM0bnE")
    assert [match["pattern_id"] for match in result["matches"]] == ["DOUBLE_CHECK_CHECKMATE"]


def test_cannon_pawn_double_check_yields_to_specific_pattern(puzzles):
    fen, moves, result = analyze(puzzles, "ojl2Q0")
    raw = recognize_pattern("DOUBLE_CHECK_CHECKMATE", fen, moves)
    assert set(raw["features"]["checking_piece_types"]) == {"C", "P"}
    assert result["matches"]
    assert "DOUBLE_CHECK_CHECKMATE" not in {match["pattern_id"] for match in result["matches"]}


def test_stationary_palcorner_horse_supports_rook_mate(puzzles):
    fen, moves, result = analyze(puzzles, "Lb0e1w")
    match = recognize_pattern("PALCORNER_HORSE_CHECKMATE", fen, moves)
    assert match["detected"]
    assert match["features"]["stationary_horse_candidates"] == [{"square": "d7", "controlled_squares": ["e9"]}]
    assert "PALCORNER_HORSE_CHECKMATE" in {match["pattern_id"] for match in result["matches"]}


def test_smothered_perpendicular_blocker_excludes_screen_advisor(puzzles):
    fen, moves, result = analyze(puzzles, "LNl7XN")
    match = recognize_pattern("SMOTHERED_CHECKMATE", fen, moves)
    assert match["detected"]
    assert match["features"]["perpendicular_groups"][0]["blockers"] == ["e1"]
    assert "SMOTHERED_CHECKMATE" in {match["pattern_id"] for match in result["matches"]}


def test_stalemate_puzzle_is_valid_and_labeled(puzzles):
    puzzle = puzzles["Ll62Kn"]
    result = asyncio.run(api_analyze_puzzle_line(PuzzleLineRequest(fen=puzzle["initialFen"], blunder_move=puzzle["blunderMove"], pv=puzzle["pv"])))
    assert result.valid and result.analysis is not None
    assert result.analysis.analysis.is_stalemate and not result.analysis.analysis.is_checkmate
    assert "STALEMATE" in {match.pattern_id for match in result.analysis.matches}
