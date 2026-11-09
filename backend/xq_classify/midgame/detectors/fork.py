"""捉雙 (fork): one move creating two new threats.

Three shapes, run at different points of a move's detector order:
``detect_forks`` and ``detect_screen_forks`` first, ``detect_two_threat_forks``
after the discovered-attack and skewer detectors, because it stands down when
either of those already explains the move.
"""

from itertools import combinations

from ... import board as b
from ...exchange import evaluate_exchange, piece_value
from ..context import Analysis, Finding, MoveFrame
from ..position import MAIN, Position, opened_by, other, own, view


def fork_defences(pos: Position, actor: str) -> str | None:
    """Only a legal non-losing immediate capture of the attacker refutes a fork.

    v2.9 (expert, R20g7j): a capture by the front piece of a pin does not
    count when the pinned rear piece is worth more than the attacker, because
    leaving the line loses that piece.
    """
    fen = view(pos.fen, other(pos.side))
    square = pos.squares[actor]
    attacker_value = piece_value(pos.board[square], square)
    pinned = {}
    for (_, front, rear, _), relation in pos.pins.items():
        rear_square = pos.squares.get(rear)
        if rear_square and piece_value(pos.board[rear_square], rear_square) > attacker_value:
            pinned[front] = relation
    for move in b.legal_moves(fen):
        if move[2:] == square and pos.ids.get(move[:2]) not in pinned and evaluate_exchange(fen, move) >= 0:
            return move
    return None


def _threatens(relation: dict, actor: str) -> bool:
    return relation['actor']['id'] == actor and (relation['profitable'] or relation['check'])


def _existed(before: Position, actor: str, target: str) -> bool:
    if actor not in before.squares or target not in before.squares:
        return False
    src, dst = before.squares[actor], before.squares[target]
    old = before.relation(actor, target)
    return bool(old and (old['profitable'] or old['check'])) or (
        b.position_analysis(before.query)['is_check']
        and dst in b.pseudo_legal_targets(before.board, src, before.board[src]))


def _is_general(pos: Position, target: str) -> bool:
    return pos.board.get(pos.squares[target], '').upper() == 'K'


def _pair_rejected(run: Analysis, frame: MoveFrame, actor: str, pair: tuple[str, str]) -> bool:
    p, before, after, reply = frame.ply, frame.before, frame.after, frame.reply
    if all(_existed(before, actor, t) for t in pair):
        return True
    # v2.6: a new check alone does not make a fork; the non-king
    # target must also be newly attacked by this move.
    if any(_is_general(after, t) for t in pair) and any(
            _existed(before, actor, t) for t in pair if not _is_general(after, t)):
        run.review('fork', p, 'check_with_preexisting_attack', {'actor': after.ref(actor)})
        return True
    defence = fork_defences(after, actor)
    if defence:
        run.review('fork', p, 'defensible', {'reply': defence, 'actor': after.ref(actor)})
        return True
    # v2.8 (expert, R18wlL): while the opponent is in check, a
    # non-king target is confirmed only in the position after the
    # actual reply, like every other label (no free second move).
    # Applies to forks of two non-king targets made while another
    # check is pending; check forks are judged by ruling D3.
    if after.checked and reply is not None and not any(_is_general(after, t) for t in pair) and any(
            not (reply.relation(actor, t) or {}).get('profitable') for t in pair):
        run.review('fork', p, 'target_not_confirmed_after_check', {'actor': after.ref(actor)})
        return True
    return False


def _threatened_by(threats: dict, actor: str) -> list[str]:
    return sorted(t for t, rows in threats.items() if any(_threatens(r, actor) for r in rows))


def _report_pair(run: Analysis, frame: MoveFrame, actor: str, pair: tuple[str, str]) -> None:
    if _pair_rejected(run, frame, actor, pair):
        return
    p, after, response, threats = frame.ply, frame.after, frame.response, frame.fork_threats
    attacks = [next(r for r in threats[t] if _threatens(r, actor)) for t in pair]
    run.emit(Finding('fork', p, p, [actor], list(pair), 'new_target_pair',
                     {'attacks': attacks, 'response': response.move if after.checked and response else None}))


def detect_forks(run: Analysis, frame: MoveFrame) -> None:
    """One piece newly threatening two targets.

    Forks have their own immediate-capture test: a losing capture of the
    attacker must not be rejected by the general PV recapture filter.
    """
    threats = frame.fork_threats
    for actor in {r['actor']['id'] for rows in threats.values() for r in rows}:
        for pair in combinations(_threatened_by(threats, actor), 2):
            _report_pair(run, frame, actor, pair)


def _checking_screen(frame: MoveFrame, king: str, check: dict) -> tuple[str, str] | None:
    """The (cannon, screen) of a cannon check through a friendly screen, if this move played either piece."""
    after = frame.after
    cannon = check['actor']['id']
    if not check['check'] or after.board.get(after.squares.get(cannon, ''), '').upper() != 'C':
        return None
    between = [sq for sq in b.squares_between(after.squares[cannon], after.squares[king]) if sq in after.board]
    if len(between) != 1 or not own(after.board[between[0]], after.side):
        return None
    screen = after.ids[between[0]]
    return (cannon, screen) if frame.event.actor in {cannon, screen} else None


def _new_screen_attacks(frame: MoveFrame, screen: str):
    """The screen's own profitable attacks that this move created."""
    before = frame.before
    for target, attacks in frame.fork_threats.items():
        for attack in attacks:
            if attack['actor']['id'] != screen or not attack['profitable']:
                continue
            old = before.relation(screen, target) if screen in before.squares and target in before.squares else None
            if not (old and old['profitable']):
                yield target, attack


def _emit_screen_forks(run: Analysis, frame: MoveFrame, checked: tuple[str, dict], pieces: tuple[str, str]) -> None:
    p, after = frame.ply, frame.after
    king, check = checked
    cannon, screen = pieces
    for target, attack in _new_screen_attacks(frame, screen):
        if fork_defences(after, cannon) or fork_defences(after, screen):
            continue
        run.emit(Finding('fork', p, p, [cannon, screen], [king, target], 'friendly_cannon_screen_check',
                         {'attacks': [check, attack], 'screen': after.ref(screen)}))


def detect_screen_forks(run: Analysis, frame: MoveFrame) -> None:
    """A cannon check through a friendly screen, where the screen itself newly attacks another piece.

    v2.9 (expert, RPx5jO): either the checking cannon or its screen may be the
    piece that just moved.
    """
    if not frame.after.checked:
        return
    for king, rows in frame.fork_threats.items():
        for check in rows:
            pieces = _checking_screen(frame, king, check)
            if pieces:
                _emit_screen_forks(run, frame, (king, check), pieces)


def _is_fresh_threat(frame: MoveFrame, target: str, relation: dict) -> bool:
    before, after, event = frame.before, frame.after, frame.event
    actor = relation['actor']['id']
    if relation['check'] or not relation['profitable']:
        return False
    old = before.relation(actor, target) if actor in before.squares and target in before.squares else None
    if old and old['profitable']:
        return False
    return not (actor != event.actor and opened_by(before, after, actor, target, event.move[:2]))


def _fresh_threats(frame: MoveFrame) -> dict:
    after = frame.after
    fresh: dict = {}
    for target, relations in frame.hits.items():
        if after.board.get(after.squares.get(target, ''), '').upper() not in MAIN:
            continue
        for relation in relations:
            if _is_fresh_threat(frame, target, relation):
                fresh.setdefault(target, relation)
    return fresh


def detect_two_threat_forks(run: Analysis, frame: MoveFrame) -> None:
    """v3.0 (expert ruling on qGXnbL): two new effective threats on two different non-king majors.

    The threats may come from different pieces, provided the moving piece makes
    one of them and the move is not already a discovered attack or skewer (those
    labels explain it instead).  A capturing move is excluded: its threats are
    the aftermath of the capture.
    """
    p, event = frame.ply, frame.event
    if event.victim or any(o['id'] in {'fork', 'discovered_attack', 'skewer'} for o in run.occurrences(p)):
        return
    fresh = _fresh_threats(frame)
    actors = {r['actor']['id'] for r in fresh.values()}
    if len(fresh) < 2 or len(actors) < 2 or event.actor not in actors:
        return
    pair = sorted(fresh)[:2] if len(fresh) == 2 else sorted(
        fresh, key=lambda t: (fresh[t]['actor']['id'] != event.actor, t))[:2]
    run.emit(Finding('fork', p, p, list(dict.fromkeys(fresh[t]['actor']['id'] for t in pair)), list(pair),
                     'two_new_threats', {'attacks': [fresh[t] for t in pair]}))
