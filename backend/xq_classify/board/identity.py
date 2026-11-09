"""Stable piece identities (``'R:1'``, ``'n:2'``) that follow pieces through a move line."""

from .fen import parse_fen


def build_piece_identity(fen: str) -> dict[str, str]:
    """Number each piece letter in square order: the first Red chariot is ``R:1``."""
    board = parse_fen(fen)
    counters: dict[str, int] = {}
    identities: dict[str, str] = {}
    for square, piece in sorted(board.items()):
        counters[piece] = counters.get(piece, 0) + 1
        identities[square] = f'{piece}:{counters[piece]}'
    return identities


def move_piece_identity(identities: dict[str, str], from_square: str, to_square: str) -> dict[str, str]:
    """The identities after a move; a captured piece's identity disappears."""
    next_map = dict(identities)
    piece_id = next_map.pop(from_square, f'unknown:{from_square}')
    next_map.pop(to_square, None)
    next_map[to_square] = piece_id
    return next_map
