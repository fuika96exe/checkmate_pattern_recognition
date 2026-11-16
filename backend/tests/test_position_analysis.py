"""Position-analysis and pattern-dispatch infrastructure.

Checkmate pattern *labels* are no longer asserted here. The hand-written,
never-reviewed label expectations were removed on 2026-11-05; label coverage
now comes only from the human-confirmed frozen set (test_checkmate_frozen.py).
"""
import pytest

from app.board import position_analysis
from app.patterns import PATTERN_ORDER, analyze_patterns, recognize_pattern


def test_start_position_is_not_checkmate() -> None:
    result = position_analysis(
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    )
    assert result["is_check"] is False
    assert result["is_checkmate"] is False
    assert result["legal_moves"]


def test_analysis_exposes_legal_moves_and_checking_pieces() -> None:
    result = position_analysis(
        "4k4/9/9/9/4R4/9/9/9/9/4K4 b - - 0 1"
    )
    assert result["side_to_move"] == "black"
    assert result["king_square"] == "e9"
    assert result["is_check"] is True
    assert result["checking_pieces"]


def test_analyze_patterns_can_filter_to_single_debug_pattern() -> None:
    result = analyze_patterns(
        "3k5/9/1r4c2/4R4/9/9/9/9/9/4K4 w - - 0 1",
        ["e6d6"],
        "WHITE_FACE_GENERAL",
    )
    assert result["requested_pattern_id"] == "WHITE_FACE_GENERAL"
    assert result["best_match"] is None
    assert result["matches"] == []


def test_every_registered_pattern_dispatches() -> None:
    fen = "3k5/9/1r4c2/4R4/9/9/9/9/9/4K4 w - - 0 1"
    for pattern_id in PATTERN_ORDER:
        assert recognize_pattern(pattern_id, fen, ["e6d6"])["pattern_id"] in {pattern_id}


def test_removed_double_toast_pattern_is_not_supported() -> None:
    assert "DOUBLE_TOAST_CHECKMATE" not in PATTERN_ORDER
    with pytest.raises(ValueError):
        recognize_pattern("DOUBLE_TOAST_CHECKMATE", "3k5/9/9/4R4/9/9/9/9/9/4K4 w - - 0 1", [])
