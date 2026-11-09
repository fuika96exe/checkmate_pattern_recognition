"""What the checkmate recognisers share: replaying the line, naming the two sides, palace geometry."""

from functools import lru_cache

from .. import board as _board
from ..board import apply_move, build_piece_identity, move_piece_identity, parse_fen, position_analysis


@lru_cache(maxsize=2048)
def _apply_moves_cached(fen: str, moves: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    current_fen = fen
    for move in moves:
        current_fen = apply_move(current_fen, move)
    return current_fen, moves


def apply_moves(fen: str, moves: list[str] | None) -> tuple[str, list[str]]:
    """The final FEN of the line, and the moves as a fresh list."""
    current_fen, applied = _apply_moves_cached(fen, tuple(moves or ()))
    return current_fen, list(applied)


@lru_cache(maxsize=1024)
def _move_trace_cached(fen: str, moves: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    current_fen = fen
    identities = build_piece_identity(fen)
    trace: list[dict[str, object]] = []
    for ply, move in enumerate(moves, start=1):
        board = parse_fen(current_fen)
        from_square = move[:2]
        to_square = move[2:]
        piece = board[from_square]
        piece_id = identities[from_square]
        next_fen = apply_move(current_fen, move)
        next_analysis = position_analysis(next_fen)
        trace.append(
            {
                'ply': ply,
                'move': move,
                'piece': piece,
                'piece_id': piece_id,
                'from_square': from_square,
                'to_square': to_square,
                'analysis': next_analysis,
            }
        )
        identities = move_piece_identity(identities, from_square, to_square)
        current_fen = next_fen
    return tuple(trace)


def move_trace(fen: str, moves: list[str] | None) -> list[dict[str, object]]:
    """Per-ply detail of the line: the mover's identity, squares and the analysis after the move."""
    return list(_move_trace_cached(fen, tuple(moves or ())))


def attacker_and_defender_trace(
    fen: str, moves: list[str] | None, attacker: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """The line's trace, split into the attacker's plies and the defender's."""
    trace = move_trace(fen, moves)
    initial_side = (fen.split()[1] if len(fen.split()) > 1 else 'w')
    initial_attacker = 'red' if initial_side == 'w' else 'black'
    attacker_offset = 0 if attacker == initial_attacker else 1
    return trace[attacker_offset::2], trace[1 - attacker_offset::2]


def infer_sides(current_fen: str) -> tuple[dict[str, str], dict, str, str, str | None, str | None]:
    """``(board, analysis, attacker, defender, attacker_king, defender_king)``; the side to move is the defender."""
    board = parse_fen(current_fen)
    analysis = position_analysis(current_fen)
    defender = analysis['side_to_move']
    attacker = 'red' if defender == 'black' else 'black'
    defender_piece = 'k' if defender == 'black' else 'K'
    attacker_piece = 'K' if attacker == 'red' else 'k'
    defender_king = next((s for s, p in board.items() if p == defender_piece), None)
    attacker_king = next((s for s, p in board.items() if p == attacker_piece), None)
    return board, analysis, attacker, defender, attacker_king, defender_king


def palace_contains(square: str, side: str) -> bool:
    file_ok = square[0] in 'def'
    rank = int(square[1])
    if side == 'red':
        return file_ok and 0 <= rank <= 2
    return file_ok and 7 <= rank <= 9


def orthogonal_palace_neighbors(square: str, side: str) -> list[str]:
    x = ord(square[0]) - ord('a')
    y = int(square[1])
    neighbors: list[str] = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = x + dx
        ny = y + dy
        if 0 <= nx < 9 and 0 <= ny <= 9:
            target = f"{chr(ord('a') + nx)}{ny}"
            if palace_contains(target, side):
                neighbors.append(target)
    return neighbors


def home_rank_of(side: str) -> str:
    return '0' if side == 'red' else '9'


def is_attacker_piece(piece: str, attacker: str) -> bool:
    return piece.isupper() if attacker == 'red' else piece.islower()


def clear_caches() -> None:
    _apply_moves_cached.cache_clear()
    _move_trace_cached.cache_clear()


# Both caches hold FENs produced by the active move generator; a backend switch must drop them.
_board.register_dependent_cache(clear_caches)
