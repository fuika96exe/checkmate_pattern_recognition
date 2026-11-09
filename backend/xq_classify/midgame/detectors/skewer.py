"""串打 (skewer): a line attack on a front piece that, once it moves, wins the piece behind it."""

from typing import NamedTuple

from ... import board as b
from ..context import Analysis, Finding, MoveFrame
from ..position import LINES, MAIN, VALUES, Position, occupied_along, other, own, view
from ..replay import Event


def _add_rays(pos: Position, src: str, piece: str, result: dict) -> None:
    for dx, dy in LINES:
        occupied = occupied_along(pos.board, src, (dx, dy))
        offset = int(piece.upper() == 'C')
        if len(occupied) < offset + 2:
            continue
        front, rear = occupied[offset:offset + 2]
        if any(own(pos.board[s], pos.side) or pos.board[s].upper() not in VALUES for s in (front, rear)):
            continue
        key = (pos.ids[src], pos.ids[front], pos.ids[rear], dx, dy)
        result[key] = {'actor': pos.ref(pos.ids[src]), 'front': pos.ref(pos.ids[front]),
                       'rear': pos.ref(pos.ids[rear]),
                       'screen': pos.ref(pos.ids[occupied[0]]) if offset else None,
                       'direction': [dx, dy]}


def ray_relations(pos: Position) -> dict:
    """Geometric front/rear/screen candidates; legal checks happen separately."""
    result: dict = {}
    for src, piece in sorted(pos.board.items()):
        if own(piece, pos.side) and piece.upper() in {'R', 'C'}:
            _add_rays(pos, src, piece, result)
    return result


def skewer_confirmation(pos: Position, actor: str, front: str, rear: str, front_attack: dict) -> dict | None:
    # A front piece that can take the attacker immediately breaks the skewer.
    if pos.squares[front] + pos.squares[actor] in b.legal_moves(view(pos.fen, other(pos.side))):
        return None
    if not front_attack['profitable'] and not front_attack['check']:
        return None
    for move in sorted(b.legal_moves(view(pos.fen, other(pos.side)))):
        if move[:2] != pos.squares[front] or move[2:] in {pos.squares[actor], pos.squares[rear]}:
            continue
        ids = b.move_piece_identity(pos.ids, move[:2], move[2:])
        child = Position(b.apply_move(view(pos.fen, other(pos.side)), move), ids, pos.side)
        rear_attack = child.relation(actor, rear)
        if rear_attack and rear_attack['profitable']:
            return {'frontAttack': front_attack, 'escape': move, 'fen': child.fen, 'rearAttack': rear_attack}
    return None


class _Line(NamedTuple):
    key: tuple
    line: dict
    front_attack: dict


def _line_intact(run: Analysis, later: Event, ray: _Line) -> bool:
    current_line = ray_relations(run.positions[later.ply - 1]).get(ray.key)
    return bool(current_line) and current_line['screen'] == ray.line['screen']


def _rear_attack(pos: Position, actor: str, rear: str) -> dict | None:
    relation = pos.relation(actor, rear) if actor in pos.squares and rear in pos.squares else None
    return relation if relation and relation['profitable'] else None


def _played_out(run: Analysis, frame: MoveFrame, ray: _Line, confirmation: dict) -> tuple[dict, int]:
    """Prefer the line's actual continuation: the front piece really moves and the rear is then attacked."""
    actor, front, rear = ray.key[:3]
    for later in run.events[frame.ply:]:
        if not _line_intact(run, later, ray):
            break
        if later.actor == front:
            pos = run.positions[later.ply]
            relation = _rear_attack(pos, actor, rear)
            if relation:
                return {'frontAttack': ray.front_attack, 'escape': later.move,
                        'fen': pos.fen, 'rearAttack': relation}, later.ply
            break
        if later.actor in {actor, rear} or later.victim in {actor, front, rear}:
            break
    return confirmation, frame.ply


def _judge_ray(run: Analysis, frame: MoveFrame, ray: _Line) -> None:
    p = frame.ply
    actor, front, rear = ray.key[:3]
    confirmation = skewer_confirmation(frame.after, actor, front, rear, ray.front_attack)
    if not confirmation:
        run.review('skewer', p, 'no_profitable_two_stage_confirmation', ray.line)
        return
    confirmation, confirmed = _played_out(run, frame, ray, confirmation)
    # v2.6 (expert review): a skewer must actually win one of the
    # two line pieces in the PV; a blockable check or a protected
    # rear is not a real skewer.
    won = next((e for e in run.events[p:] if e.side == run.solver and e.victim in {front, rear}
                and e.victim_kind in MAIN), None)
    if not won:
        run.review('skewer', p, 'skewer_not_realized', ray.line)
        return
    run.emit(Finding('skewer', p, confirmed, [actor], [front, rear], 'ray',
                     {'line': ray.line, 'continuation': confirmation}))


def detect_skewers(run: Analysis, frame: MoveFrame) -> None:
    response = frame.response
    old_rays = ray_relations(frame.before)
    for key, line in ray_relations(frame.after).items():
        actor, front = key[:2]
        if (key in old_rays or actor in frame.excluded or (response and response.victim == actor) or
                VALUES[line['front']['piece'].upper()] < VALUES[line['rear']['piece'].upper()]):
            continue
        front_attack = next((r for r in frame.hits.get(front, []) if r['actor']['id'] == actor), None)
        if front_attack:
            _judge_ray(run, frame, _Line(key, line, front_attack))
