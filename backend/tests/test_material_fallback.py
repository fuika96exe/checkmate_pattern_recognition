import asyncio
import json
from pathlib import Path

import pytest

from app.board import position_analysis
from app.main import api_analyze_puzzle_line
from app.models import PuzzleLineRequest
from app.patterns import classify_mating_material
import app.patterns as pattern_module
from scripts.generate_puzzle_recognition import recognize_puzzle


@pytest.mark.parametrize("code", ["RN", "RC", "RP", "RNC", "RNP", "RCP", "NC", "NCP", "NP", "CP"])
def test_all_supported_combinations_are_exact(monkeypatch, code):
    fen = "4k4/9/9/9/9/9/9/9/9/RNCPK4 b - - 0 1"
    squares = {"R": "a0", "N": "b0", "C": "c0", "P": "d0"}
    analysis = {"is_checkmate": True, "side_to_move": "black", "king_square": "e9", "checking_pieces": [{"square": squares[code[0]]}]}
    monkeypatch.setattr(pattern_module, "attacked_squares", lambda board, side: {"e8": [{"square": squares[piece]} for piece in code[1:]]})
    result = classify_mating_material(fen, analysis)
    assert result and result["id"] == code


@pytest.mark.parametrize("code,label", [("R", "车杀"), ("N", "马杀"), ("C", "炮杀"), ("P", "兵杀")])
def test_single_piece_type_combinations(monkeypatch, code, label):
    fen = "4k4/9/9/9/9/9/9/9/9/RNCPK4 b - - 0 1"
    squares = {"R": "a0", "N": "b0", "C": "c0", "P": "d0"}
    analysis = {"is_checkmate": True, "side_to_move": "black", "king_square": "e9", "checking_pieces": [{"square": squares[code]}]}
    monkeypatch.setattr(pattern_module, "attacked_squares", lambda board, side: {})
    result = classify_mating_material(fen, analysis)
    assert result and result["id"] == code and result["label_zh"] == label


def test_four_piece_combination_is_not_reduced_to_a_subset(monkeypatch):
    fen = "4k4/9/9/9/9/9/9/9/9/RNCPK4 b - - 0 1"
    analysis = {"is_checkmate": True, "side_to_move": "black", "king_square": "e9", "checking_pieces": [{"square": "a0"}]}
    monkeypatch.setattr(pattern_module, "attacked_squares", lambda board, side: {"e8": [{"square": square} for square in ("b0", "c0", "d0")]})
    assert classify_mating_material(fen, analysis) is None


@pytest.mark.parametrize("fen,expected", [
    ("2Ra1kc2/4a4/4R4/p3p3p/6C2/1NP6/P3P1n1P/9/4N1c2/2BK1r3 w - - 1 25", "RC"),
    ("2bR5/9/3k2N2/p7p/2P2Nb2/3C5/P3P3P/4B4/5K1c1/3A5 b - - 0 40", "RN"),
    ("1R1k1ab2/9/3P4n/2p6/6b1p/2P1C4/8P/4C4/r2cA4/c1BAK1B2 b - - 4 34", "RCP"),
    ("3a1kc2/9/9/p3p3p/6p2/2P6/P3P3P/N8/5nc2/3KCr3 w - - 3 31", "NC"),
])
def test_material_combinations_from_mate_positions(fen, expected):
    analysis = position_analysis(fen)
    assert analysis["is_checkmate"]
    result = classify_mating_material(fen, analysis)
    assert result and result["id"] == expected


def test_cannon_control_simulates_the_king_entering_an_empty_square():
    fen = "2Ra1kc2/4a4/4R4/p3p3p/6C2/1NP6/P3P1n1P/9/4N1c2/2BK1r3 w - - 1 25"
    result = classify_mating_material(fen, position_analysis(fen))
    assert result is not None
    assert {"square": "g1", "piece": "C", "targets": ["d1"]} in result["controlling_pieces"]
    assert result["checking_pieces"] == [{"square": "f0", "piece": "R"}]


def test_blocked_horse_is_not_counted_as_a_controller():
    fen = "R3kab2/2Nn5/4b1N2/6n2/4p3p/9/4P3P/1C7/3RA4/2BAK1B2 b - - 4 29"
    result = classify_mating_material(fen, position_analysis(fen))
    assert result is not None
    assert "c8" not in {piece["square"] for piece in result["controlling_pieces"]}
    assert "g7" in {piece["square"] for piece in result["controlling_pieces"]}


def test_capture_simulation_removes_attacker_on_destination(monkeypatch):
    fen = "4k4/4R4/9/9/9/9/9/9/9/RN2K4 b - - 0 1"
    analysis = {"is_checkmate": True, "side_to_move": "black", "king_square": "e9", "checking_pieces": [{"square": "a0"}]}
    examined = []
    def attacks(board, side):
        if board.get("e8") == "k":
            examined.append(board.copy())
            return {"e8": [{"square": "b0"}]}
        return {}
    monkeypatch.setattr(pattern_module, "attacked_squares", attacks)
    result = classify_mating_material(fen, analysis)
    assert result and result["id"] == "RN"
    assert examined and "e9" not in examined[0] and examined[0]["e8"] == "k"


def test_nonmate_is_not_classified_and_rook_only_is_classified():
    nonmate = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    assert classify_mating_material(nonmate, position_analysis(nonmate)) is None
    single = "1R2k1b2/4c4/4c4/9/9/9/9/4B4/4A4/2BAK4 b - - 0 1"
    assert position_analysis(single)["is_checkmate"]
    result = classify_mating_material(single, position_analysis(single))
    assert result and result["id"] == "R" and result["label_zh"] == "车杀"


@pytest.fixture(scope="module")
def puzzles():
    path = Path(__file__).resolve().parents[2] / "public/data/checkmate-puzzles.json"
    return {p["key"]: p for p in json.loads(path.read_text(encoding="utf8"))["puzzles"]}


def test_fallback_in_api_and_generated_summary(puzzles):
    puzzle = puzzles["o74w5P"]
    response = asyncio.run(api_analyze_puzzle_line(PuzzleLineRequest(fen=puzzle["initialFen"], blunder_move=puzzle["blunderMove"], pv=puzzle["pv"])))
    assert response.valid and response.analysis is not None
    assert not response.analysis.matches and response.analysis.material_fallback.id == "RC"
    summary = asyncio.run(recognize_puzzle(puzzle))
    assert summary["status"] == "matched" and summary["materialId"] == "RC" and not summary["patternIds"]


def test_existing_pattern_and_stalemate_do_not_get_fallback(puzzles):
    for key in ["LxN1ej", "Ll62Kn"]:
        puzzle = puzzles[key]
        response = asyncio.run(api_analyze_puzzle_line(PuzzleLineRequest(fen=puzzle["initialFen"], blunder_move=puzzle["blunderMove"], pv=puzzle["pv"])))
        assert response.valid and response.analysis is not None
        assert response.analysis.matches and response.analysis.material_fallback is None
