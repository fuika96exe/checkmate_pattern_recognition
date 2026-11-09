"""A position seen from the solver's side, and the attacks and pins derived from it.

Pieces are tracked by identity (``'R:1'``), not by square, so a relation can be
followed along the line.  Evidence keeps its exact key order: it is part of
the output contract.
"""

from dataclasses import dataclass
from functools import cached_property

from .. import board as b
from ..exchange import evaluate_exchange, piece_value

MAIN = frozenset('RNC')
VALUES = {'R': 9, 'N': 4, 'C': 4, 'K': 99999}
LINES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def other(side: str) -> str:
    return 'black' if side == 'red' else 'red'


def own(piece: str, side: str) -> bool:
    return bool(piece) and piece.isupper() == (side == 'red')


def view(fen: str, side: str) -> str:
    """*fen* with *side* to move."""
    parts = fen.split()
    parts[1] = 'w' if side == 'red' else 'b'
    return ' '.join(parts)


def profitable_capture(fen: str, move: str) -> tuple[bool, int | None]:
    """Legal is_capturing_move adapter, including upstream's pawn policy.

    None means inapplicable/illegal, never evidence of an even exchange.
    Signed exchange gains are retained for audit (upstream clamps its output).
    """
    board = b.parse_fen(fen)
    if move not in b.legal_moves(fen):
        return False, None
    src, dst = move[:2], move[2:]
    victim = board.get(dst, '')
    if not victim or victim.upper() == 'K':
        return False, None
    red = sum(p in 'RNC' for p in board.values())
    black = sum(p in 'rnc' for p in board.values())
    endgame = (red <= 2 and black <= 2) or not any(p.upper() == 'R' for p in board.values())
    crossed = int(dst[1]) >= 5 if victim.isupper() else int(dst[1]) <= 4
    if victim.upper() == 'P' and not crossed and not endgame and board[src].upper() != 'P':
        return False, None
    gain = evaluate_exchange(fen, move)
    return gain > 0, gain


@dataclass
class Position:
    fen: str
    ids: dict[str, str]
    side: str

    @cached_property
    def board(self) -> dict[str, str]:
        return b.parse_fen(self.fen)

    @cached_property
    def squares(self) -> dict[str, str]:
        return {identity: square for square, identity in self.ids.items()}

    @cached_property
    def query(self) -> str:
        return view(self.fen, self.side)

    def ref(self, identity: str) -> dict:
        square = self.squares.get(identity)
        return {'id': identity, 'square': square, 'piece': self.board.get(square, '')}

    @cached_property
    def captures(self) -> dict:
        """All ordinary legal captures; local losses include minor pieces."""
        result = {}
        for move in sorted(b.legal_moves(self.query)):
            src, dst = move[:2], move[2:]
            victim = self.board.get(dst, '')
            if not victim or own(victim, self.side) or victim.upper() == 'K':
                continue
            ok, gain = profitable_capture(self.query, move)
            relation = {'actor': self.ref(self.ids[src]), 'target': self.ref(self.ids[dst]),
                        'ucci': move, 'gain': gain, 'profitable': ok, 'check': False,
                        'fen': self.query}
            result.setdefault(self.ids[dst], []).append(relation)
        return result

    def _gives_safe_check(self, source: str, piece: str, king: str) -> bool:
        if not own(piece, self.side) or king not in b.pseudo_legal_targets(self.board, source, piece):
            return False
        # Occupancy-only safety check; never send a missing-king FEN to pyffish.
        trial = dict(self.board)
        trial[king] = trial.pop(source)
        own_king = next(s for s, p in trial.items() if p == ('K' if self.side == 'red' else 'k'))
        return not b.is_square_attacked(trial, own_king, self.side != 'red')

    @cached_property
    def hits(self) -> dict:
        """Major targets and actual checking sources, separately from capture values."""
        result = {t: list(rows) for t, rows in self.captures.items()
                  if rows[0]['target']['piece'].upper() in MAIN}
        # A check is an actual attack on the general, never an exchange input.
        king = next((s for s, p in self.board.items() if p == ('k' if self.side == 'red' else 'K')), None)
        if king:
            for source, piece in sorted(self.board.items()):
                if self._gives_safe_check(source, piece, king):
                    result.setdefault(self.ids[king], []).append({
                        'actor': self.ref(self.ids[source]), 'target': self.ref(self.ids[king]),
                        'ucci': None, 'gain': None, 'profitable': False, 'check': True,
                    })
        return result

    @cached_property
    def threats(self) -> dict:
        return {t: [r for r in rows if r['profitable'] or r['check']]
                for t, rows in self.hits.items() if any(r['profitable'] or r['check'] for r in rows)}

    @cached_property
    def guards(self) -> dict:
        """(attacker ID,target ID) -> guard ID -> legal recapture evidence."""
        result = {}
        for target, relations in self.hits.items():
            for r in relations:
                if r['check']:
                    continue
                child = b.apply_move(self.query, r['ucci'])
                guards = {}
                for reply in sorted(b.legal_moves(child)):
                    if reply[2:] == r['target']['square']:
                        identity = self.ids[reply[:2]]
                        guards[identity] = {'guard': self.ref(identity), 'capture': r['ucci'], 'recapture': reply}
                result[(r['actor']['id'], target)] = guards
        return result

    def relation(self, actor: str, target: str) -> dict | None:
        return next((r for r in self.hits.get(target, []) if r['actor']['id'] == actor), None)

    @cached_property
    def checked(self) -> bool:
        king = next(s for s, p in self.board.items() if p == ('k' if self.side == 'red' else 'K'))
        return b.is_square_attacked(self.board, king, self.side == 'red')

    @cached_property
    def pins(self) -> dict:
        return scan_pins(self)


def opened_by(before: Position, after: Position, actor: str, target: str, vacated: str) -> bool:
    """The vacated source must be a necessary blocker, using occupancy only."""
    src, dst = after.squares[actor], after.squares[target]
    piece = after.board[src]
    if src != before.squares.get(actor) or dst != before.squares.get(target):
        return False
    if dst in b.pseudo_legal_targets(before.board, src, piece):
        return False
    trial = dict(after.board)
    trial[vacated] = before.board[vacated]
    return dst not in b.pseudo_legal_targets(trial, src, piece)


def occupied_along(board: dict[str, str], src: str, direction: tuple[int, int]) -> list[str]:
    """Every occupied square from *src* to the edge of the board, nearest first."""
    x, y = b.coords(src)
    dx, dy = direction
    occupied = []
    cx, cy = x + dx, y + dy
    while (square := b.square_at(cx, cy)) is not None:
        if square in board:
            occupied.append(square)
        cx, cy = cx + dx, cy + dy
    return occupied


def exposed_relation(pos: Position, actor: str, front: str, rear: str) -> bool:
    """Occupancy-only removal, never a missing-general FEN."""
    trial = dict(pos.board)
    trial.pop(pos.squares[front])
    src, dst = pos.squares[actor], pos.squares[rear]
    if dst not in b.pseudo_legal_targets(trial, src, trial[src]):
        return False
    trial[dst] = trial.pop(src)
    king = next((s for s, p in trial.items() if p == ('K' if pos.side == 'red' else 'k')), None)
    return bool(king and not b.is_square_attacked(trial, king, pos.side != 'red'))


def without_pieces(pos: Position, identities) -> Position | None:
    """Counterfactual proof only. Both generals must remain; never a PV frame."""
    board, ids = dict(pos.board), dict(pos.ids)
    for identity in identities:
        square = pos.squares.get(identity)
        if square:
            if board[square].upper() == 'K':
                return None
            board.pop(square)
            ids.pop(square)
    parts = pos.fen.split()
    parts[0] = b.board_to_fen(board)
    return Position(' '.join(parts), ids, pos.side)


def profitable_after_removal(pos: Position, actor: str, front: str, rear: str) -> dict | None:
    trial = without_pieces(pos, {front})
    if not trial:
        return None
    relation = trial.relation(actor, rear)
    return relation if relation and relation['profitable'] else None


# --- Pin scan: what each own piece restricts in this position ------------------


def _absolute_line_pins(pos: Position, src: str, occupied: list[str], result: dict) -> None:
    """Absolute cannon pins: either of the two blockers may be pinned."""
    enemy_general = 'k' if pos.side == 'red' else 'K'
    king_index = next((i for i, sq in enumerate(occupied) if pos.board[sq] == enemy_general), None)
    required = 2 if pos.board[src].upper() == 'C' else 1
    if king_index != required:
        return
    rear = occupied[king_index]
    for front in occupied[:king_index]:
        if own(pos.board[front], pos.side):
            continue
        actor, guard, target = pos.ids[src], pos.ids[front], pos.ids[rear]
        if not exposed_relation(pos, actor, guard, target):
            continue
        screen = next((sq for sq in occupied[:king_index] if sq != front), None)
        result[(actor, guard, target, 'ray')] = {
            'actor': pos.ref(actor), 'front': pos.ref(guard), 'rear': pos.ref(target),
            'screen': pos.ref(pos.ids[screen]) if screen else None,
            'kind': 'ray', 'absolute': True,
        }


def _relative_line_pin(pos: Position, src: str, occupied: list[str], result: dict) -> None:
    offset = int(pos.board[src].upper() == 'C')
    if len(occupied) < offset + 2:
        return
    front, rear = occupied[offset:offset + 2]
    fp, rp = pos.board[front], pos.board[rear]
    if (own(fp, pos.side) or own(rp, pos.side) or fp.upper() not in 'RNCBAP' or
            rp.upper() not in MAIN or piece_value(rp, rear) <= piece_value(fp, front)):
        return
    actor, guard, target = pos.ids[src], pos.ids[front], pos.ids[rear]
    if exposed_relation(pos, actor, guard, target) and profitable_after_removal(pos, actor, guard, target):
        result[(actor, guard, target, 'ray')] = {
            'actor': pos.ref(actor), 'front': pos.ref(guard), 'rear': pos.ref(target),
            'screen': pos.ref(pos.ids[occupied[0]]) if offset else None,
            'kind': 'ray', 'absolute': False,
        }


def _horse_leg_pin(pos: Position, src: str, dst: str, victim: str, result: dict) -> None:
    if own(victim, pos.side) or victim.upper() not in VALUES:
        return
    sx, sy = b.coords(src)
    tx, ty = b.coords(dst)
    dx, dy = tx - sx, ty - sy
    if sorted((abs(dx), abs(dy))) != [1, 2]:
        return
    leg = b.square_at(sx + (dx // 2 if abs(dx) == 2 else 0), sy + (dy // 2 if abs(dy) == 2 else 0))
    blocker = pos.board.get(leg, '')
    if not blocker or own(blocker, pos.side) or blocker.upper() == 'K':
        return
    actor, front, rear = pos.ids[src], pos.ids[leg], pos.ids[dst]
    if exposed_relation(pos, actor, front, rear) and (
            victim.upper() == 'K' or profitable_after_removal(pos, actor, front, rear)):
        result[(actor, front, rear, 'horse_leg')] = {
            'actor': pos.ref(actor), 'front': pos.ref(front), 'rear': pos.ref(rear),
            'kind': 'horse_leg', 'absolute': victim.upper() == 'K',
            'review': False,
        }


def _elephant_eye_pin(pos: Position, src: str, dst: str, victim: str, result: dict) -> None:
    """An opposing eye blocker can restrict a rook just as a horse leg does."""
    if own(victim, pos.side) or victim.upper() not in MAIN:
        return
    sx, sy = b.coords(src)
    tx, ty = b.coords(dst)
    if abs(tx - sx) != 2 or abs(ty - sy) != 2:
        return
    eye = b.square_at((sx + tx) // 2, (sy + ty) // 2)
    if eye not in pos.board or own(pos.board[eye], pos.side) or pos.board[eye].upper() == 'K':
        return
    actor, front, rear = pos.ids[src], pos.ids[eye], pos.ids[dst]
    if exposed_relation(pos, actor, front, rear) and profitable_after_removal(pos, actor, front, rear):
        result[(actor, front, rear, 'elephant_eye')] = {
            'actor': pos.ref(actor), 'front': pos.ref(front), 'rear': pos.ref(rear),
            'kind': 'elephant_eye', 'absolute': False, 'review': False}


def _flying_general_pin(pos: Position, result: dict) -> None:
    kings = [s for s, p in pos.board.items() if p.upper() == 'K']
    if len(kings) != 2 or kings[0][0] != kings[1][0]:
        return
    occupied = [s for s in b.squares_between(*kings) if s in pos.board]
    if len(occupied) != 1 or own(pos.board[occupied[0]], pos.side):
        return
    front = occupied[0]
    actor = next(s for s in kings if own(pos.board[s], pos.side))
    rear = next(s for s in kings if s != actor)
    result[(pos.ids[actor], pos.ids[front], pos.ids[rear], 'flying_general')] = {
        'actor': pos.ref(pos.ids[actor]), 'front': pos.ref(pos.ids[front]),
        'rear': pos.ref(pos.ids[rear]), 'kind': 'flying_general', 'absolute': True,
    }


def scan_pins(pos: Position) -> dict:
    """Every pin the side to attack holds here, keyed ``(actor, front, rear, kind)``; the order is observable."""
    result: dict = {}
    for src, piece in sorted(pos.board.items()):
        if own(piece, pos.side) and piece.upper() in {'R', 'C'}:
            for direction in LINES:
                occupied = occupied_along(pos.board, src, direction)
                _absolute_line_pins(pos, src, occupied, result)
                _relative_line_pin(pos, src, occupied, result)
    for letter, scan in (('N', _horse_leg_pin), ('B', _elephant_eye_pin)):
        for src, piece in pos.board.items():
            if own(piece, pos.side) and piece.upper() == letter:
                for dst, victim in pos.board.items():
                    scan(pos, src, dst, victim, result)
    _flying_general_pin(pos, result)
    return result
