"""消除保護 (remove defender): a move strips a guard, and a capture that was not profitable becomes one.

Ruling D7: it needs an actual profitable realization, with the same attacker and
target and an uninterrupted release, so independent later blunders cannot confirm it.
"""

from typing import NamedTuple

from ... import board as b
from ..context import Analysis, Finding
from ..position import MAIN, Position, other
from ..replay import Event


class _Case(NamedTuple):
    capture: Event  # the realized capture
    realized: dict
    trigger: Event
    before: Position
    old: dict  # the attack as it stood before the trigger
    guards: dict


def guard_line_squares(pos: Position, guard: str, target: str) -> set[str]:
    """Squares whose occupancy decides whether `guard` can recapture on `target`:
    the rook/cannon line between them, a horse leg, or an elephant eye."""
    gs, ts = pos.squares.get(guard), pos.squares.get(target)
    if not gs or not ts:
        return set()
    kind = pos.board[gs].upper()
    if kind in {'R', 'C'}:
        return set(b.squares_between(gs, ts))
    gx, gy = b.coords(gs)
    tx, ty = b.coords(ts)
    dx, dy = tx - gx, ty - gy
    if kind == 'N' and sorted((abs(dx), abs(dy))) == [1, 2]:
        leg = b.square_at(gx + (dx // 2 if abs(dx) == 2 else 0), gy + (dy // 2 if abs(dy) == 2 else 0))
        return {leg} if leg else set()
    if kind == 'B' and abs(dx) == 2 and abs(dy) == 2:
        eye = b.square_at(gx + dx // 2, gy + dy // 2)
        return {eye} if eye else set()
    return set()


def checking_interception(before: Position, release: Position, move: str, pieces: tuple[str, str, str]) -> bool:
    """v3.1 (ruling E1): `move` checks and, in the same move, blocks the
    guard's recapture line (rook/cannon line, horse leg, elephant eye) or
    removes its cannon screen. Guard, attacker and target stay put through
    the forced reply, so the reply did not restore or cause the loss."""
    guard, _, target = pieces
    if any(before.squares.get(x) is None or before.squares.get(x) != release.squares.get(x) for x in pieces):
        return False
    line = guard_line_squares(before, guard, target)
    return move[:2] in line or move[2:4] in line


def _is_causal(run: Analysis, case: _Case, guard: str, release_ply: int) -> bool:
    """Did the trigger really take this guard away?"""
    trigger, before = case.trigger, case.before
    p, actor, target = trigger.ply, case.capture.actor, case.capture.victim
    release = run.positions[release_ply]
    if trigger.victim == guard:
        return True
    if release_ply == p:
        # Direct removal or demonstrable interception of the
        # same guard's recapture line, with both targets alive.
        return (guard in release.squares and
                before.squares[guard] == release.squares[guard] and
                before.squares[actor] == release.squares[actor] and
                before.squares[target] == release.squares[target])
    if run.positions[p].checked and checking_interception(before, release, trigger.move, (guard, actor, target)):
        # v3.1 (E1): the trigger position was skipped because it
        # is check; the line it cut is still cut after the reply.
        return True
    if run.events[p].actor == guard:
        pressure = run.positions[p]
        return pressure.checked or guard in pressure.threats
    return False


def _uninterrupted(run: Analysis, case: _Case, release_ply: int, causal: list[str]) -> bool:
    actor, target = case.capture.actor, case.capture.victim
    for intermediate in run.positions[release_ply:case.capture.ply]:
        if intermediate.checked:
            continue
        rel = intermediate.relation(actor, target)
        if not rel or not rel['profitable'] or any(g in intermediate.guards.get((actor, target), {}) for g in causal):
            return False
    return True


def _try_release(run: Analysis, case: _Case, release_ply: int) -> bool:
    """Report a removed defender released at *release_ply*; True stops looking at later plies."""
    capture, trigger, before = case.capture, case.trigger, case.before
    q, actor, target, p = capture.ply, capture.actor, capture.victim, trigger.ply
    if release_ply >= q:
        return False
    release = run.positions[release_ply]
    new = release.relation(actor, target)
    if release.checked or not new or not new['profitable']:
        return False
    remaining = release.guards.get((actor, target), {})
    lost = set(case.guards) - set(remaining)
    if not lost:
        return False
    causal = [guard for guard in sorted(lost) if _is_causal(run, case, guard, release_ply)]
    if not causal:
        run.review('remove_defender', p, 'release_not_proven_forced',
                   {'target': before.ref(target), 'guards': sorted(lost), 'realizationPly': q})
        return False
    if not _uninterrupted(run, case, release_ply, causal):
        return False
    run.emit(Finding('remove_defender', p, q, [trigger.actor, actor], [target], 'profitable_release',
                     {'beforeFen': before.fen, 'releaseFen': release.fen, 'releasePly': release_ply,
                      'guardsBefore': list(case.guards.values()), 'guardsAfter': list(remaining.values()),
                      'removedGuards': [before.ref(g) for g in causal], 'beforeAttack': case.old,
                      'releaseAttack': new, 'realization': {'ply': q, 'ucci': capture.move, 'attack': case.realized}}))
    return True


def _review_without_prior_attack(run: Analysis, capture: Event, trigger: Event, before: Position) -> None:
    """A geometric protector is only a review candidate: no earlier legal attack proves the recapture."""
    target = capture.victim
    if not trigger.victim or target not in before.squares:
        return
    protectors = b.attacked_squares(before.board, other(run.solver)).get(before.squares[target], [])
    if any(before.ids[r['square']] == trigger.victim for r in protectors):
        run.review('remove_defender', trigger.ply, 'no_prior_legal_attack', {
            'target': before.ref(target), 'removedGuard': before.ref(trigger.victim),
            'realizationPly': capture.ply})


def _judge_trigger(run: Analysis, capture: Event, realized: dict, trigger: Event) -> None:
    p, actor, target = trigger.ply, capture.actor, capture.victim
    before = run.positions[p - 1]
    old = before.relation(actor, target)
    if not old:
        _review_without_prior_attack(run, capture, trigger, before)
        return
    guards = before.guards.get((actor, target), {})
    if old['profitable'] or not guards:
        return
    case = _Case(capture, realized, trigger, before, old, guards)
    for release_ply in (p, p + 1):
        if _try_release(run, case, release_ply):
            break


def detect_removed_defenders(run: Analysis) -> None:
    for capture in run.events[1:]:
        if capture.side != run.solver or capture.victim_kind not in MAIN:
            continue
        realized = run.positions[capture.ply - 1].relation(capture.actor, capture.victim)
        if not realized or not realized['profitable']:
            continue
        for trigger in run.events[1:capture.ply - 1]:
            if trigger.side == run.solver:
                _judge_trigger(run, capture, realized, trigger)
