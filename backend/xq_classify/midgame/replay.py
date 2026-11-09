"""Replay a puzzle line into positions and events."""

from dataclasses import dataclass

from .. import board as b
from .position import Position


class ReplayError(ValueError):
    """The puzzle does not replay; carries where it stopped (``ply`` 0 is the input itself)."""

    def __init__(self, message: str, ply: int, fen: str, move: str | None = None) -> None:
        super().__init__(message)
        self.ply, self.fen, self.move = ply, fen, move


@dataclass(frozen=True)
class Event:
    ply: int
    side: str
    move: str
    actor: str
    victim: str | None
    victim_kind: str

    @property
    def dst(self) -> str:
        return self.move[2:]


def _checked_identities(fen: str, pv: list[str], solver: str) -> dict[str, str]:
    board = b.parse_fen(fen)
    if list(board.values()).count('K') != 1 or list(board.values()).count('k') != 1:
        raise ValueError('FEN requires exactly one general per side')
    if not isinstance(pv, list) or not pv or not all(isinstance(m, str) for m in pv):
        raise ValueError('PV must be a nonempty UCCI string list')
    if solver not in {'red', 'black'}:
        raise ValueError('first_turn must normalize to red or black')
    return b.build_piece_identity(fen)


def _play(before: Position, ply: int, move: str, solver: str) -> tuple[Event, Position]:
    if not isinstance(move, str) or not b.UCCI_RE.fullmatch(move) or move not in b.legal_moves(before.fen):
        raise ValueError(f'Illegal UCCI move: {move}')
    src, dst = move[:2], move[2:]
    if before.board.get(dst, '').upper() == 'K':
        raise ValueError('PV cannot capture a general')
    after = b.apply_move(before.fen, move)
    if ply == 1 and b.side_to_move(after) != solver:
        raise ValueError(f'first_turn mismatch: expected {b.side_to_move(after)}, got {solver}')
    event = Event(
        ply, b.side_to_move(before.fen), move, before.ids[src], before.ids.get(dst), before.board.get(dst, '').upper()
    )
    return event, Position(after, b.move_piece_identity(before.ids, src, dst), solver)


def replay(fen: str, blunder: str, pv: list[str], solver: str) -> tuple[list[Position], list[Event]]:
    try:
        ids = _checked_identities(fen, pv, solver)
    except (ValueError, TypeError) as error:
        raise ReplayError(str(error), 0, fen) from error
    positions = [Position(fen, ids, solver)]
    events = []
    for ply, move in enumerate([blunder, *pv], 1):
        before = positions[-1]
        try:
            event, after = _play(before, ply, move, solver)
        except (ValueError, TypeError) as error:
            raise ReplayError(str(error), ply, before.fen, move) from error
        events.append(event)
        positions.append(after)
    return positions, events
