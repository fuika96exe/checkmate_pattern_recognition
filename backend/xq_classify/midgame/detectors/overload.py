"""過載 (overload): a guard that recaptures on one square leaves another piece undefended.

Ruling D8 uses the actual recapture chain.  v2.1 intentionally removed the
sole-legal-response gate; it does not claim exhaustive proof over alternative replies.
"""

from ..context import Analysis, Finding
from ..position import MAIN
from ..replay import Event


def _realization(run: Analysis, trigger: Event, duty: tuple[str, str], guard: str) -> Event | None:
    """The later capture on the guard's other duty, if the release held all the way to it."""
    p = trigger.ply
    actor, target = duty
    realization = next(
        (e for e in run.events[p + 1:] if e.side == run.solver and e.actor == actor and e.victim == target), None,
    )
    if not realization:
        return None
    if any(not pos.relation(actor, target) or not pos.relation(actor, target)['profitable'] or
           guard in pos.guards.get(duty, {}) for pos in run.positions[p + 1:realization.ply] if not pos.checked):
        return None
    return realization


def _judge_other_duty(run: Analysis, trigger: Event, duty: tuple[str, str], guards2: dict) -> None:
    p = trigger.ply
    response = run.events[p]
    before, released = run.positions[p - 1], run.positions[p + 1]
    guard = response.actor
    old, new = before.relation(*duty), released.relation(*duty)
    if not old or old['profitable'] or not new or not new['profitable'] or guard in released.guards.get(duty, {}):
        return
    realization = _realization(run, trigger, duty, guard)
    if not realization:
        return
    guards1 = before.guards.get((trigger.actor, trigger.victim), {})
    run.emit(Finding('overload', p, realization.ply, [trigger.actor, duty[0]], [trigger.victim, duty[1]],
                     'actual_guard_response',
                     {'guard': before.ref(guard), 'guarding': [guards1[guard], guards2[guard]],
                      'actualResponse': {'ply': response.ply, 'ucci': response.move},
                      'beforeAttack': old, 'releaseAttack': new,
                      'realization': {'ply': realization.ply, 'ucci': realization.move}}))


def detect_overloads(run: Analysis) -> None:
    for trigger in run.events[1:]:
        p = trigger.ply
        if trigger.side != run.solver or trigger.victim_kind not in MAIN or p >= len(run.events):
            continue
        response = run.events[p]
        before = run.positions[p - 1]
        guards1 = before.guards.get((trigger.actor, trigger.victim), {})
        if response.actor not in guards1 or response.victim != trigger.actor or response.dst != trigger.dst:
            continue
        for duty, guards2 in before.guards.items():
            if duty[1] != trigger.victim and response.actor in guards2:
                _judge_other_duty(run, trigger, duty, guards2)
