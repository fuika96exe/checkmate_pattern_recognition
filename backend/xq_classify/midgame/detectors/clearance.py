"""消除阻隔 (clearance): forcing an enemy blocker away opens a previously unavailable attack.

The later profitable capture, the vacated obstruction and the pressure are all
identity-linked; voluntary unrelated moves cannot confirm it.
"""

from typing import NamedTuple

from ...exchange import evaluate_exchange
from ..context import Analysis, Finding
from ..position import Position, opened_by
from ..replay import Event


class _Departure(NamedTuple):
    trigger: Event
    response: Event
    before: Position
    pressure: Position
    release: Position
    new_pressure: list[dict]


def _held_until_realized(run: Analysis, case: _Departure, actor: str, target: str, realization: Event) -> bool:
    """Attacker and target stay put, and the capture stays profitable, up to the realization."""
    release = case.release
    return not any(
        pos.squares.get(actor) != release.squares[actor]
        or pos.squares.get(target) != release.squares[target]
        or not pos.relation(actor, target)
        or not pos.relation(actor, target)['profitable']
        for pos in run.positions[case.trigger.ply + 1 : realization.ply]
        if not pos.checked
    )


def _realization_of(run: Analysis, case: _Departure, attack: dict, target: str) -> Event | None:
    p, trigger, pressure, release = case.trigger.ply, case.trigger, case.pressure, case.release
    actor, blocker = attack['actor']['id'], case.response.actor
    if attack['check'] or not attack['profitable'] or actor == trigger.actor:
        return None
    if (
        case.before.relation(actor, target)
        or pressure.relation(actor, blocker)
        or not opened_by(pressure, release, actor, target, case.response.move[:2])
    ):
        return None
    realization = next(
        (e for e in run.events[p + 1 :] if e.side == run.solver and e.actor == actor and e.victim == target),
        None,
    )
    if not realization or evaluate_exchange(run.positions[realization.ply - 1].fen, realization.move) <= 0:
        return None
    return realization if _held_until_realized(run, case, actor, target, realization) else None


def _emit_clearance(run: Analysis, case: _Departure, attack: dict, target: str, realization: Event) -> None:
    trigger, response, pressure = case.trigger, case.response, case.pressure
    blocker = response.actor
    run.emit(
        Finding(
            'clearance',
            trigger.ply,
            realization.ply,
            [trigger.actor, attack['actor']['id']],
            [blocker, target],
            'forced_blocker_departure',
            {
                'blocker': pressure.ref(blocker),
                'vacated': response.move[:2],
                'pressure': case.new_pressure,
                'pressureFen': pressure.fen,
                'response': {'ply': response.ply, 'ucci': response.move},
                'releaseFen': case.release.fen,
                'openedAttack': attack,
                'realization': {
                    'ply': realization.ply,
                    'ucci': realization.move,
                    'gain': evaluate_exchange(run.positions[realization.ply - 1].fen, realization.move),
                },
            },
        )
    )


def _judge_trigger(run: Analysis, trigger: Event) -> None:
    p = trigger.ply
    response = run.events[p]
    before, pressure, release = run.positions[p - 1 : p + 2]
    blocker = response.actor
    new_pressure = [
        r
        for r in pressure.threats.get(blocker, [])
        if r['profitable'] and not (before.relation(r['actor']['id'], blocker) or {}).get('profitable', False)
    ]
    if not new_pressure and not pressure.checked:
        return
    case = _Departure(trigger, response, before, pressure, release, new_pressure)
    for target, relations in release.hits.items():
        if target == blocker:
            continue
        for attack in relations:
            realization = _realization_of(run, case, attack, target)
            if realization:
                _emit_clearance(run, case, attack, target, realization)


def detect_clearances(run: Analysis) -> None:
    for trigger in run.events[1:]:
        if trigger.side == run.solver and trigger.ply < len(run.events):
            _judge_trigger(run, trigger)
