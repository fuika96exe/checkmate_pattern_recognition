"""閃擊 (discovered attack): the moved piece was the blocker of another piece's new attack."""

from ...exchange import evaluate_exchange
from ..context import Analysis, Finding, MoveFrame
from ..position import opened_by


def _report_revealed(run: Analysis, frame: MoveFrame, target: str, relation: dict) -> None:
    p, before, after, event = frame.ply, frame.before, frame.after, frame.event
    actor = relation['actor']['id']
    # v2.7 (expert ruling D1): the revealed attack must be a
    # real check or a capture with exchange value > 0. An even
    # trade offer still counts when the same move gives check,
    # because the opponent must answer the check first.
    if not (relation['check'] or relation['profitable'] or after.checked):
        run.review(
            'discovered_attack', p, 'revealed_attack_not_profitable', {'attack': relation, 'vacated': event.move[:2]}
        )
        return
    run.emit(
        Finding(
            'discovered_attack',
            p,
            p + int(after.checked and not relation['check']),
            [event.actor, actor],
            [target],
            'vacated_blocker',
            {'vacated': event.move[:2], 'attack': relation, 'beforeFen': before.fen},
        )
    )


def detect_discovered_attacks(run: Analysis, frame: MoveFrame) -> None:
    before, after, event = frame.before, frame.after, frame.event
    for target, relations in frame.hits.items():
        for relation in relations:
            actor = relation['actor']['id']
            if actor == event.actor or before.relation(actor, target):
                continue
            if opened_by(before, after, actor, target, event.move[:2]):
                _report_revealed(run, frame, target, relation)


def detect_escaped_discovered_attacks(run: Analysis, frame: MoveFrame) -> None:
    """v2.8 (expert, o7PaGq): the target escapes by answering a pending check, then is won anyway.

    A revealed attack whose target escapes by answering the check (e.g. capturing
    the checker) still counts when the player then wins that piece on its new square.
    """
    p, before, after, event, response = frame.ply, frame.before, frame.after, frame.event, frame.response
    if not (after.checked and frame.reply is not None and response.actor in after.squares):
        return
    target = response.actor
    follow = run.events[p + 1] if p + 1 < len(run.events) else None
    for relation in after.hits.get(target, []):
        actor = relation['actor']['id']
        if (
            relation['check']
            or actor == event.actor
            or before.relation(actor, target)
            or any(r['actor']['id'] == actor for r in frame.hits.get(target, []))
            or not opened_by(before, after, actor, target, event.move[:2])
        ):
            continue
        if follow and follow.victim == target and evaluate_exchange(run.positions[p + 1].fen, follow.move) > 0:
            run.emit(
                Finding(
                    'discovered_attack',
                    p,
                    follow.ply,
                    [event.actor, actor],
                    [target],
                    'vacated_blocker',
                    {
                        'vacated': event.move[:2],
                        'attack': relation,
                        'beforeFen': before.fen,
                        'escapedBy': response.move,
                        'wonOn': follow.move,
                    },
                )
            )
