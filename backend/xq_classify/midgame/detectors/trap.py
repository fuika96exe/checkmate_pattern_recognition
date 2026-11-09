"""圍困 (trap): every legal escape of an attacked piece still loses it.

Runs last among the per-move detectors because it defers to pins and skewers
already labelled on this move.
"""

from ... import board as b
from ...exchange import piece_value
from ..context import Analysis, Finding, MoveFrame
from ..position import Position, other, view, without_pieces
from .pin_proofs import front_can_trade_pinner


def _best_gain(rows: list[dict]) -> int:
    return max((r['gain'] for r in rows if r['profitable']), default=0)


def _counter_value(realized: Position, old_counters: dict, newly_exposed: set[str], attack: dict) -> int:
    """The best new counter-capture available after the attack is carried out."""
    compensation = 0
    for counter_target, counters in realized.captures.items():
        prior = _best_gain(old_counters.get(counter_target, []))
        for counter in counters:
            if (counter['profitable'] and counter['actor']['id'] not in newly_exposed
                    and counter['target']['square'] != attack['target']['square']
                    and counter['gain'] > prior):
                compensation = max(compensation, counter['gain'])
    return compensation


def _net_loss(child: Position, attack: dict, old_counters: dict, newly_exposed: set[str], credit: int) -> int:
    realized = Position(b.apply_move(child.query, attack['ucci']),
                        b.move_piece_identity(child.ids, attack['ucci'][:2], attack['ucci'][2:]), other(child.side))
    compensation = _counter_value(realized, old_counters, newly_exposed, attack)
    recovered = max(0, piece_value(attack['target']['piece'], attack['target']['square']) - attack['gain'])
    return attack['gain'] - max(0, compensation - recovered) - credit


def _indirect_loss(pos: Position, child: Position, target: str, escape: tuple[str, int, int]) -> dict | None:
    """The escape saves the target but exposes something else for more than it was already losing."""
    move, credit, baseline = escape
    old_counters = Position(pos.fen, pos.ids, other(pos.side)).captures
    newly_exposed = {identity for identity, rows in child.captures.items()
                     if _best_gain(rows) > _best_gain(pos.captures.get(identity, []))}
    for identity, rows in child.captures.items():
        if identity == target or any(r['profitable'] for r in pos.captures.get(identity, [])):
            continue
        for attack in rows:
            if not attack['profitable'] or attack['gain'] <= baseline:
                continue
            net = _net_loss(child, attack, old_counters, newly_exposed, credit)
            if net > baseline:
                return {'escape': move, 'fen': child.fen, 'safe': False, 'reason': 'indirect_loss',
                        'capture': attack, 'previousLoss': 0, 'netLoss': net,
                        'originalLoss': baseline, 'captureCredit': credit}
    return None


def escape_assessment(pos: Position, target: str, move: str) -> dict:
    defender_fen = view(pos.fen, other(pos.side))
    child = Position(b.apply_move(defender_fen, move),
                     b.move_piece_identity(pos.ids, move[:2], move[2:]), pos.side)
    victim = pos.board.get(move[2:], '')
    credit = piece_value(victim, move[2:]) if victim else 0
    direct = [r for r in child.captures.get(target, []) if r['profitable']]
    if direct:
        return {'escape': move, 'fen': child.fen, 'safe': False, 'reason': 'direct_loss',
                'capture': max(direct, key=lambda r: r['gain']), 'captureCredit': credit}
    baseline = _best_gain(pos.captures.get(target, []))
    indirect = _indirect_loss(pos, child, target, (move, credit, baseline))
    return indirect or {'escape': move, 'fen': child.fen, 'safe': True, 'captureCredit': credit}


def trap_state(pos: Position, target: str, excluded=frozenset()) -> dict | None:
    initial = [r for r in pos.threats.get(target, []) if r['profitable'] and r['actor']['id'] not in excluded]
    if not initial or pos.checked:
        return None
    escapes = []
    for move in sorted(b.legal_moves(view(pos.fen, other(pos.side)))):
        if move[:2] != pos.squares[target]:
            continue
        assessment = escape_assessment(pos, target, move)
        if assessment['safe']:
            return None
        escapes.append(assessment)
    return {'initialAttack': initial[0], 'escapes': escapes}


def _pin_key(restriction: dict) -> tuple:
    return restriction['actor']['id'], restriction['front']['id'], restriction['rear']['id'], restriction['kind']


def _front_of_labelled_pin(run: Analysis, frame: MoveFrame, target: str) -> bool:
    """An actively labelled pin takes precedence over trapping its front piece."""
    active_pins = {_pin_key(r) for r in frame.after.pins.values()}
    return any(o['id'] == 'pin' and _pin_key(o['evidence']['restriction']) in active_pins
               and o['evidence']['restriction']['front']['id'] == target
               for o in run.occurrences_through(frame.ply))


def _judge_pinned_target(run: Analysis, frame: MoveFrame, target: str, pinned_by: dict) -> None:
    """v2.7 (expert ruling D4): an attacked piece that cannot escape because of the pin is labelled as a pin.

    Only a pin newly created by this move, with the moving piece as the
    pinner, is credited this way.
    """
    p, before, after = frame.ply, frame.before, frame.after
    run.review('trap', p, 'target_is_pinned_front', {'target': after.ref(target), 'restriction': pinned_by})
    created = next((r for key, r in after.pins.items() if r['front']['id'] == target
                    and key not in before.pins and key[0] == frame.event.actor), None)
    already = any(o['id'] == 'pin' and o['evidence']['targets'][0]['id'] == target
                  for o in run.occurrences_through(p))
    stuck = trap_state(after, target, frame.excluded) if created else None
    if stuck and not already and not front_can_trade_pinner(after, created):
        run.emit(Finding('pin', p, p, [created['actor']['id']], [target, created['rear']['id']], created['kind'],
                         {'restriction': created, 'use': 'pinned_target_cannot_escape', 'functionalCapture': None,
                          'escapeAnalysis': stuck, 'relationFen': after.fen, 'response': None}))


def _explained_by_absolute_pin(run: Analysis, frame: MoveFrame, target: str, trapped: dict) -> bool:
    """The target is stuck only because of an absolute pin: that is a pin's evidence, not a trap."""
    p, after = frame.ply, frame.after
    constraints = [(key, r) for key, r in after.pins.items() if key[1] == target and r.get('absolute')]
    if not constraints:
        return False
    relaxed = without_pieces(after, {key[0] for key, _ in constraints})
    if relaxed is not None and trap_state(relaxed, target):
        return False
    pins = [o for o in run.occurrences(p) if o['id'] == 'pin' and
            o['evidence']['restriction']['front']['id'] == target]
    if not pins:
        run.review('pin', p, 'absolute_pin_without_proven_gain', {'restriction': constraints[0][1]})
    for occurrence in pins:
        occurrence['evidence']['escapeAnalysis'] = trapped
    return True


def _is_skewer_target(run: Analysis, ply: int, target: str) -> bool:
    return any(o['id'] == 'skewer' and any(t['id'] == target for t in o['evidence']['targets'])
               for o in run.occurrences(ply))


def _judge_target(run: Analysis, frame: MoveFrame, target: str) -> None:
    p, before, after = frame.ply, frame.before, frame.after
    if _front_of_labelled_pin(run, frame, target):
        return
    if after.checked:
        run.review('trap', p, 'defender_in_check', {'target': after.ref(target)})
        return
    # v2.6 (expert review): a piece that cannot run because it is the
    # front of any pin relation is pinned, not trapped.
    pinned_by = next((r for pos in (before, after) for r in pos.pins.values()
                      if r['front']['id'] == target), None)
    if pinned_by:
        _judge_pinned_target(run, frame, target, pinned_by)
        return
    # v2.7 (ruling D2): only a same-move skewer target is excluded; a
    # discovered-attack target can still be trapped (q8Xlzq).
    if _is_skewer_target(run, p, target):
        run.review('trap', p, 'target_explained_by_line_tactic', {'target': after.ref(target)})
        return
    trapped = trap_state(after, target, frame.excluded)
    if not trapped or (target in before.squares and trap_state(before, target)):
        return
    if not _explained_by_absolute_pin(run, frame, target, trapped):
        run.emit(Finding('trap', p, p, [trapped['initialAttack']['actor']['id']], [target],
                         'all_legal_escapes', trapped))


def detect_traps(run: Analysis, frame: MoveFrame) -> None:
    for target, attacks in frame.threats.items():
        if any(r['profitable'] for r in attacks):
            _judge_target(run, frame, target)
