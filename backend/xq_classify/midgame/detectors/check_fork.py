"""抽將 (check fork): a fork, discovered attack or skewer that gives check and still wins material.

Derived from this move's parent occurrences, so it runs after them, once dead
actors are rejected and the pending check is resolved.
"""

from ..context import Analysis, Finding, MoveFrame
from ..position import MAIN

_PARENTS = {'fork', 'discovered_attack', 'skewer'}


def _is_checking_parent(frame: MoveFrame, parent: dict) -> bool:
    event, after = frame.event, frame.after
    evidence = parent['evidence']
    targets = evidence['targets'][:1] if parent['id'] == 'skewer' else evidence['targets']
    # v2.9 (expert ruling on R0g40E): a discovered attack whose moving
    # piece itself gives check is a checking parent as well.
    mover_checks = parent['id'] == 'discovered_attack' and any(
        r['check'] and r['actor']['id'] == event.actor for rs in after.hits.values() for r in rs
    )
    return mover_checks or any(t['piece'].upper() == 'K' for t in targets)


def _judge_parent(run: Analysis, frame: MoveFrame, parent: dict) -> None:
    p, event, after, reply = frame.ply, frame.event, frame.after, frame.reply
    evidence = parent['evidence']
    # v2.7 (expert ruling D3): after the actual reply to the check
    # the player must have a profitable capture of a major piece,
    # or the discovering piece itself captured a major piece.
    options = [
        r
        for rows in (reply.captures.values() if reply else [])
        for r in rows
        if r['profitable'] and r['target']['piece'].upper() in MAIN
    ]
    mover_capture = parent['id'] == 'discovered_attack' and event.victim_kind in MAIN
    if not options and not mover_capture:
        run.review('check_fork', p, 'no_profitable_capture_after_check', {'parentKey': evidence['key']})
        return
    run.emit(
        Finding(
            'check_fork',
            p,
            evidence['confirmedPly'],
            [r['id'] for r in evidence['actors']],
            [r['id'] for r in evidence['targets']],
            'checking_parent',
            {
                'parentKey': evidence['key'],
                'checks': [r for rs in after.hits.values() for r in rs if r['check']],
                'gainOptions': options[:4],
                'moverCapture': event.move if mover_capture else None,
            },
        )
    )


def detect_check_forks(run: Analysis, frame: MoveFrame) -> None:
    if not frame.after.checked:
        return
    for parent in list(run.occurrences(frame.ply)):  # a copy: emitting appends to the same ply
        if parent['id'] in _PARENTS and _is_checking_parent(frame, parent):
            _judge_parent(run, frame, parent)
