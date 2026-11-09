"""Evidence that a pin really cost the defender something.

A structural pin alone earns no label: each function here looks in the actual
line for the concrete loss it caused.
"""

from ... import board as b
from ...exchange import evaluate_exchange, piece_value
from ..position import MAIN, VALUES, Position, other, own, view, without_pieces
from ..replay import Event


def front_can_trade_pinner(pos: Position, relation: dict) -> bool:
    actor, front = relation['actor']['id'], relation['front']['id']
    if actor not in pos.squares or front not in pos.squares:
        return False
    fen = view(pos.fen, other(pos.side))
    move = pos.squares[front] + pos.squares[actor]
    return move in b.legal_moves(fen) and evaluate_exchange(fen, move) >= 0


def _pin_key(relation: dict) -> tuple:
    return relation['actor']['id'], relation['front']['id'], relation['rear']['id'], relation['kind']


def _capture_proof(pre: Position, post: Position, capture: Event, guard: str, pinner: str) -> dict | None:
    if capture.victim == guard:
        gain = evaluate_exchange(pre.fen, capture.move)
        if gain > 0:
            return {'guard': pre.ref(guard), 'defendedTarget': pre.ref(guard),
                    'capturePly': capture.ply, 'capture': capture.move, 'gain': gain,
                    'mode': 'pinned_piece_captured'}
    if guard not in pre.squares or pinner not in pre.squares or pinner == capture.actor:
        return None
    gain = evaluate_exchange(pre.fen, capture.move)
    if gain <= 0:
        return None
    gs = post.squares.get(guard)
    if not gs:
        return None
    reply = gs + capture.dst
    if capture.dst not in b.pseudo_legal_targets(post.board, gs, post.board[gs]) or reply in b.legal_moves(post.fen):
        return None
    released_post, released_pre = without_pieces(post, [pinner]), without_pieces(pre, [pinner])
    if not released_post or not released_pre or reply not in b.legal_moves(released_post.fen):
        return None
    if capture.move not in b.legal_moves(released_pre.fen):
        return None
    without_gain = evaluate_exchange(released_pre.fen, capture.move)
    if without_gain > 0:
        return None
    return {'guard': pre.ref(guard), 'defendedTarget': pre.ref(capture.victim),
            'capturePly': capture.ply, 'capture': capture.move, 'captureFen': pre.fen,
            'gain': gain, 'preventedRecapture': reply, 'afterCaptureFen': post.fen,
            'releasedFen': released_post.fen, 'gainWithoutPin': without_gain}


def functional_pin_capture(relation: dict, positions: list[Position], events: list[Event], start_ply: int) -> dict | None:
    """Minor pins need an actual profitable major capture enabled by the pin."""
    guard, pinner = relation['front']['id'], relation['actor']['id']
    key = _pin_key(relation)
    for capture in events[start_ply - 1:]:
        if capture.side != positions[0].side or capture.victim_kind not in MAIN:
            continue
        pre, post = positions[capture.ply - 1:capture.ply + 1]
        if key not in pre.pins or any(key not in pos.pins for pos in positions[start_ply:capture.ply]):
            continue
        proof = _capture_proof(pre, post, capture, guard, pinner)
        if proof:
            return proof
    return None


def absolute_pin_sacrifice(relation: dict, positions: list[Position], events: list[Event], start_ply: int) -> dict | None:
    """The pinned piece captures its pinner and is then captured at a net loss."""
    guard, pinner = relation['front']['id'], relation['actor']['id']
    key = _pin_key(relation)
    for event in events[start_ply:]:
        if event.actor != guard or event.victim != pinner or key not in positions[event.ply - 1].pins:
            continue
        gain = -evaluate_exchange(positions[event.ply - 1].fen, event.move)
        if gain <= 0:
            continue
        realized = next((e for e in events[event.ply:] if e.actor in positions[e.ply - 1].squares
                         and e.side == positions[0].side and e.victim == guard), None)
        if realized:
            return {'guard': positions[event.ply - 1].ref(guard), 'defendedTarget': positions[event.ply - 1].ref(guard),
                    'capturePly': realized.ply, 'capture': realized.move, 'gain': gain,
                    'mode': 'pinner_sacrifice', 'response': event.move}
    return None


def _kept_their_squares(positions: list[Position], span: tuple[int, int], guard: str, pinner: str) -> bool:
    start, end = span
    home = positions[start].squares
    return all(positions[i].squares.get(guard) == home.get(guard) and
               positions[i].squares.get(pinner) == home.get(pinner) for i in range(start, end))


def _front_won_after_rear_left(
    positions: list[Position], events: list[Event], start_ply: int, capture: Event, key: tuple,
) -> dict | None:
    pinner, guard, rear = key[:3]
    history = events[start_ply - 1:capture.ply - 1]
    departure = next((e for e in history if e.actor == rear and e.side != positions[0].side), None)
    if not departure or key not in positions[departure.ply - 1].pins:
        return None
    if not _kept_their_squares(positions, (start_ply, capture.ply), guard, pinner):
        return None
    gain = evaluate_exchange(positions[capture.ply - 1].fen, capture.move)
    if gain <= 0:
        return None
    return {'guard': positions[start_ply].ref(guard), 'defendedTarget': positions[start_ply].ref(guard),
            'capturePly': capture.ply, 'capture': capture.move, 'gain': gain,
            'mode': 'rear_evades_front_captured', 'response': departure.move}


def relative_pin_front_capture(relation: dict, positions: list[Position], events: list[Event], start_ply: int) -> dict | None:
    """The defender saves the rear piece, then the pinned front is won."""
    if relation.get('absolute'):
        return None
    key = _pin_key(relation)
    for capture in events[start_ply - 1:]:
        if capture.side == positions[0].side and capture.victim == key[1]:
            proof = _front_won_after_rear_left(positions, events, start_ply, capture, key)
            if proof:
                return proof
    return None


def pinned_front_won(relation: dict, positions: list[Position], events: list[Event], start_ply: int) -> dict | None:
    """v2.6: the pinned front never moves again and is later won outright.

    Experts call this 借牽制得子 even when the defender first interposes or
    reinforces, so the relation itself need not survive until the capture.
    """
    pinner, guard = relation['actor']['id'], relation['front']['id']
    if relation['front']['piece'].upper() not in MAIN:
        return None
    home = positions[start_ply].squares.get(guard)
    for capture in events[start_ply:]:
        if capture.actor == guard:
            return None
        if capture.side != positions[0].side or capture.victim != guard:
            continue
        if positions[capture.ply - 1].squares.get(guard) != home:
            return None
        gain = evaluate_exchange(positions[capture.ply - 1].fen, capture.move)
        if gain > 0:
            return {'guard': positions[start_ply].ref(guard), 'defendedTarget': positions[start_ply].ref(guard),
                    'capturePly': capture.ply, 'capture': capture.move, 'gain': gain,
                    'mode': 'pinned_front_won', 'pinner': positions[start_ply].ref(pinner)}
        return None
    return None


def _general_of(pos: Position, red: bool) -> str | None:
    return next((s for s, p in pos.board.items() if p == ('K' if red else 'k')), None)


def _illegal_recapture_pinner(post: Position, trial: dict, kings: tuple[str, str], capture_dst: str) -> str | None:
    """Who makes the recapture illegal: the facing general, or the piece that would then check."""
    enemy_king, own_king = kings
    if enemy_king[0] == own_king[0] and not any(s in trial for s in b.squares_between(enemy_king, own_king)):
        return post.ids[own_king]
    for src, attacker in sorted(trial.items()):
        if own(attacker, post.side) and src != capture_dst and enemy_king in b.pseudo_legal_targets(trial, src, attacker):
            return post.ids[src]
    return None


def illegal_recapture_pin(positions: list[Position], capture: Event) -> tuple | None:
    """v2.6: a profitable capture whose natural recapture is illegal only
    because the recapturing piece is pinned to its own general (including the
    facing-generals rule). Returns (pinner, guard, king, proof) or None."""
    solver = positions[0].side
    pre, post = positions[capture.ply - 1:capture.ply + 1]
    gain = evaluate_exchange(pre.fen, capture.move)
    if gain <= 0 or piece_value(pre.board[capture.move[:2]], capture.move[:2]) < VALUES[capture.victim_kind]:
        return None
    legal = set(b.legal_moves(post.fen))
    enemy_king, own_king = _general_of(post, solver != 'red'), _general_of(post, solver == 'red')
    if not enemy_king or not own_king:
        return None
    for square, piece in sorted(post.board.items()):
        if own(piece, solver) or piece.upper() == 'K':
            continue
        if capture.dst not in b.pseudo_legal_targets(post.board, square, piece) or square + capture.dst in legal:
            continue
        trial = dict(post.board)
        trial[capture.dst] = trial.pop(square)
        pinner = _illegal_recapture_pinner(post, trial, (enemy_king, own_king), capture.dst)
        if pinner:
            return pinner, post.ids[square], post.ids[enemy_king], {
                'guard': post.ref(post.ids[square]), 'defendedTarget': pre.ref(capture.victim),
                'capturePly': capture.ply, 'capture': capture.move, 'gain': gain,
                'preventedRecapture': square + capture.dst, 'mode': 'illegal_recapture'}
    return None


def relative_recapture_pin(positions: list[Position], events: list[Event], capture: Event) -> tuple | None:
    """v2.8 (expert, Lb3VlR): the natural recapture is legal, but the
    recapturing piece is the front of a pin, so recapturing lets another
    player piece win the more valuable rear piece. Returns
    (pinner, guard, rear, proof) or None."""
    solver = positions[0].side
    pre, post = positions[capture.ply - 1:capture.ply + 1]
    capturer_value = piece_value(pre.board[capture.move[:2]], capture.move[:2])
    nxt = events[capture.ply] if capture.ply < len(events) else None
    legal = set(b.legal_moves(post.fen))
    for key, relation in sorted(post.pins.items()):
        pinner, guard, rear = key[:3]
        if relation.get('absolute') or pinner == capture.actor or guard not in post.squares:
            continue
        reply = post.squares[guard] + capture.dst
        if reply not in legal or (nxt and nxt.move == reply):
            continue
        rear_square = post.squares.get(rear)
        if not rear_square or piece_value(post.board[rear_square], rear_square) <= capturer_value:
            continue
        child = Position(b.apply_move(post.fen, reply), b.move_piece_identity(post.ids, reply[:2], reply[2:]), solver)
        punish = child.relation(pinner, rear)
        if not punish or not punish['profitable']:
            continue
        return pinner, guard, rear, {
            'guard': post.ref(guard), 'defendedTarget': pre.ref(capture.victim), 'capturePly': capture.ply,
            'capture': capture.move, 'gain': evaluate_exchange(pre.fen, capture.move),
            'deterredRecapture': reply, 'punishment': punish['ucci'], 'punishmentGain': punish['gain'],
            'mode': 'recapture_costs_rear'}
    return None
