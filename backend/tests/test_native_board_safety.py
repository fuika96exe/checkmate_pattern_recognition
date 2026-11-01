"""Regression coverage for the native crash in the tactical upload batch."""
from types import SimpleNamespace

import pytest

from backend.app import board
from backend.app.tactical_categories import _captures, analyze_tactical_categories


@pytest.mark.parametrize("general", ["K", "k"])
def test_terminal_position_never_reaches_native_engine(monkeypatch, general):
    def native_must_not_run(*args):
        pytest.fail("Kingless positions must not reach Pyffish")

    monkeypatch.setattr(board, "pyffish", SimpleNamespace(legal_moves=native_must_not_run))
    fen = board.START_FEN.replace(general, "1")
    board.legal_moves.cache_clear()
    try:
        assert board.legal_moves(fen) == []
        with pytest.raises(board.BoardError, match="非法着法"):
            board.apply_move(fen, "a0a1")
    finally:
        board.legal_moves.cache_clear()


def test_tactical_material_captures_exclude_the_general():
    fen = "4k4/4R4/9/9/9/9/9/9/9/4K4 w - - 0 1"
    assert "e8e9" not in _captures(fen)


def test_qayl8d_tactical_line_finishes_without_kingless_probes(monkeypatch):
    # The old trap analysis replayed a pseudo capture of Red's general,
    # then passed that kingless FEN to get_fen, causing an access violation.
    original_legal_moves = board.legal_moves

    def require_both_generals(fen):
        pieces = board.parse_fen(fen).values()
        assert "K" in pieces and "k" in pieces, fen
        return original_legal_moves(fen)

    monkeypatch.setattr(board, "legal_moves", require_both_generals)
    fen = "4kabr1/4a4/4b4/p7p/2prpR3/6R2/n1P1c1p1P/N3C3B/2C1A3N/2BA1K1c1 b - - 4 22"
    moves = ["h0d0", "e2e5", "h9h0", "i2g0", "e9d9", "g4g3", "d0d1"]
    annotations = analyze_tactical_categories(fen, moves)
    assert [item["ucci"] for item in annotations] == moves
