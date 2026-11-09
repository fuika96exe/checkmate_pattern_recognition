# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""Public board interface: FEN parsing, legal moves, checks, attacks and square helpers.

Callers outside this subpackage use only the names exported here.  Legal moves
and move application go through the active ``MoveGenerator``: pure Python by
default; ``use_backend`` installs another one (the lab's pyffish adapter, for
parity tests) and clears the caches.  Whatever the backend, a position without
both generals has no legal moves and never reaches it.
"""

from collections.abc import Callable
from functools import lru_cache

from . import backend as _backend
from . import fen as _fen
from .backend import MoveGenerator
from .errors import BoardError
from .fen import START_FEN, UCCI_RE, board_to_fen, check_ucci, has_both_generals, parse_fen, side_to_move
from .geometry import FILES, coords, inside_palace, is_red, square_at, squares_between
from .identity import build_piece_identity, move_piece_identity
from .pure import (
    PURE_BACKEND,
    PureMoveGenerator,
    apply_legal_move,
    attacked_squares,
    generate_legal_moves,
    is_square_attacked,
    pseudo_legal_targets,
)

__all__ = [
    'FILES',
    'PURE_BACKEND',
    'START_FEN',
    'UCCI_RE',
    'BoardError',
    'MoveGenerator',
    'PureMoveGenerator',
    'analyze_position',
    'apply_legal_move',
    'apply_move',
    'attacked_squares',
    'board_to_fen',
    'build_piece_identity',
    'check_ucci',
    'clear_caches',
    'coords',
    'current_backend',
    'generate_legal_moves',
    'has_both_generals',
    'inside_palace',
    'is_red',
    'is_square_attacked',
    'legal_moves',
    'move_piece_identity',
    'parse_fen',
    'position_analysis',
    'pseudo_legal_targets',
    'register_dependent_cache',
    'side_to_move',
    'square_at',
    'squares_between',
    'use_backend',
]


_DEPENDENT_CACHES: list[Callable[[], None]] = []


def register_dependent_cache(clear: Callable[[], None]) -> None:
    """Register the clear function of a cache built on board results (moves, FENs).

    ``use_backend`` and ``clear_caches`` call it too: FEN strings differ between
    move generators (the halfmove clock), so such caches must not outlive a switch.
    """
    _DEPENDENT_CACHES.append(clear)


def current_backend() -> MoveGenerator:
    return _backend.current()


def use_backend(generator: MoveGenerator) -> MoveGenerator:
    """Make *generator* the move generator and clear the board caches; return the previous generator."""
    previous = _backend.replace(generator)
    clear_caches()
    return previous


@lru_cache(maxsize=512)
def legal_moves(fen: str) -> list[str]:
    if not has_both_generals(parse_fen(fen)):
        return []
    return _backend.current().legal_moves(fen)


@lru_cache(maxsize=8192)
def apply_move(fen: str, ucci: str) -> str:
    check_ucci(ucci)
    if ucci not in legal_moves(fen):
        raise BoardError(f'非法着法：{ucci}')
    return _backend.current().apply_move(fen, ucci)


def analyze_position(fen: str, moves_of: Callable[[str], list[str]]) -> dict:
    """Check, checkmate and stalemate of *fen*, with the legal moves taken from *moves_of*.

    ``is_check`` and the attack map come from the pure attack geometry for every backend.
    """
    board = parse_fen(fen)
    moving = side_to_move(fen)
    opponent = 'black' if moving == 'red' else 'red'
    king_piece = 'K' if moving == 'red' else 'k'
    king_square = next((s for s, p in board.items() if p == king_piece), None)
    if king_square is None:
        raise BoardError('FEN 找不到行棋方的將帥')
    attacks = attacked_squares(board, opponent)
    checking = attacks.get(king_square, [])
    moves = moves_of(fen)
    in_check = bool(checking)
    return {
        'side_to_move': moving,
        'king_square': king_square,
        'is_check': in_check,
        'is_checkmate': in_check and not moves,
        'is_stalemate': not in_check and not moves,
        'legal_moves': moves,
        'checking_pieces': checking,
        'attacked_squares': attacks,
    }


@lru_cache(maxsize=256)
def position_analysis(fen: str) -> dict:
    return analyze_position(fen, legal_moves)


def clear_caches() -> None:
    """Clear the board caches and every registered dependent cache."""
    _fen.clear_cache()
    for cached in (legal_moves, apply_move, position_analysis):
        cached.cache_clear()
    for clear in _DEPENDENT_CACHES:
        clear()
