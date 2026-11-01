"""Destination-square exchange evaluation used by the Fake Human move labels.

Follow ``xiangqi_server/api/util/exchange.py``: consider every legal recapturer,
rebuild the position after each capture, allow declining an unfavourable
recapture unless every legal answer to check recaptures here, and carry each
piece's value from its origin square. Moves use this project's 0–9 UCCI ranks.
"""
from __future__ import annotations

from functools import lru_cache

from .board import apply_move, legal_moves, parse_fen, position_analysis


MATERIAL_VALUES = {"R": 9, "N": 4, "C": 4, "B": 2, "A": 2, "P": 1}


def piece_value(piece: str, square: str) -> int:
    if piece.upper() == "P":
        crossed = int(square[1]) >= 5 if piece.isupper() else int(square[1]) <= 4
        return 2 if crossed else 1
    return MATERIAL_VALUES.get(piece.upper(), 0)


@lru_cache(maxsize=8192)
def _evaluate_square(fen: str, square: str, occupant_value: int) -> int:
    """Best net gain from recapturing here, including the option to stop."""
    if occupant_value <= 0:
        return 0
    board = parse_fen(fen)
    moves = legal_moves(fen)
    recaptures = sorted(
        (piece_value(board[move[:2]], move[:2]), move)
        for move in moves if move[2:] == square
    )
    if not recaptures:
        return 0
    best = max(
        occupant_value - _evaluate_square(apply_move(fen, move), square, value)
        for value, move in recaptures
    )
    if best < 0:
        forced = len(recaptures) == len(moves) and position_analysis(fen)["is_check"]
        if not forced:
            return 0
    return best


@lru_cache(maxsize=8192)
def evaluate_exchange(fen: str, move: str) -> int:
    """Net gain after optimal captures on the move's destination have resolved.

    The first move is mandatory; subsequent captures may be declined. Positive
    gains material, zero is even, and negative loses material. Quiet moves are
    supported. Invalid moves and king captures return zero, so callers must
    establish a legal non-king capture before interpreting zero as a trade.
    """
    if not fen or not move or move not in legal_moves(fen):
        return 0
    board = parse_fen(fen)
    source, target = move[:2], move[2:]
    victim = board.get(target, "")
    if victim.upper() == "K":
        return 0
    return piece_value(victim, target) - _evaluate_square(
        apply_move(fen, move), target, piece_value(board[source], source),
    )
