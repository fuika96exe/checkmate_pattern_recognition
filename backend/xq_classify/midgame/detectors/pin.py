"""牽制 (pin): structural pins are tracked continuously and labelled only when exploited.

``detect_pins`` runs per solver move.  The insertion order of ``candidates``, and
which stage overwrites a key, decide the order of the emitted occurrences.
``detect_recapture_pins`` runs over the whole line, after every per-move detector.
"""

from typing import NamedTuple

from ...exchange import evaluate_exchange
from ..context import Analysis, Finding, MoveFrame
from ..position import MAIN, opened_by
from .pin_proofs import (
    absolute_pin_sacrifice,
    front_can_trade_pinner,
    functional_pin_capture,
    illegal_recapture_pin,
    pinned_front_won,
    relative_pin_front_capture,
    relative_recapture_pin,
)


class _Candidate(NamedTuple):
    relation: dict
    confirmed: int
    mode: str
    proof: dict | None


def _pin_proof(run: Analysis, relation: dict, ply: int) -> dict | None:
    positions, events = run.positions, run.events
    proof = functional_pin_capture(relation, positions, events, ply)
    if relation.get('absolute') and not proof:
        proof = absolute_pin_sacrifice(relation, positions, events, ply)
    if not relation.get('absolute') and not proof:
        proof = relative_pin_front_capture(relation, positions, events, ply)
    if not proof:
        proof = pinned_front_won(relation, positions, events, ply)
    return proof


def _newly_attacked(frame: MoveFrame, identity: str) -> bool:
    return any(r['profitable']
               and not (frame.before.relation(r['actor']['id'], identity) or {}).get('profitable', False)
               for r in frame.hits.get(identity, []))


def _collect_exploited(run: Analysis, frame: MoveFrame, candidates: dict) -> None:
    """Emit an existing pin only when this player move exploits it, including an actual capture."""
    p = frame.ply
    for key, relation in frame.after.pins.items():
        proof = _pin_proof(run, relation, p)
        if key not in frame.before.pins:
            candidates[key] = _Candidate(relation, p, 'created', proof)
        elif _newly_attacked(frame, key[1]):
            candidates[key] = _Candidate(relation, p, 'exploited', proof)
        elif proof and (proof['capturePly'] == p or _newly_attacked(frame, proof['defendedTarget']['id'])):
            candidates[key] = _Candidate(relation, p, 'defensive_duty_exploited', proof)


def _collect_captured(run: Analysis, frame: MoveFrame, candidates: dict) -> None:
    p, event = frame.ply, frame.event
    if not event.victim:
        return
    for key, relation in frame.before.pins.items():
        if key[1] == event.victim and relation['front']['piece'].upper() in MAIN:
            proof = functional_pin_capture(relation, run.positions, run.events, p - 1)
            candidates[key] = _Candidate(relation, p, 'pinned_piece_captured', proof)


def _blocker_recapture_proof(run: Analysis, frame: MoveFrame, key: tuple) -> dict | None:
    p, after, reply, response = frame.ply, frame.after, frame.reply, frame.response
    realized = next((e for e in run.events[p + 1:] if e.side == run.solver and e.actor == key[0]
                     and e.victim == key[2]), None)
    if not realized:
        return None
    gain = evaluate_exchange(run.positions[realized.ply - 1].fen, realized.move)
    if gain <= 0 or not opened_by(after, reply, key[0], key[2], response.move[:2]):
        return None
    return {'guard': after.ref(key[1]), 'defendedTarget': after.ref(key[2]),
            'capturePly': realized.ply, 'capture': realized.move, 'gain': gain,
            'mode': 'blocker_recapture', 'response': response.move}


def _collect_blocker_recaptures(run: Analysis, frame: MoveFrame, candidates: dict) -> None:
    """Actual recapture pulls a small blocker off an enemy cannon ray."""
    p, response = frame.ply, frame.response
    if not frame.reply:
        return
    for key, relation in frame.after.pins.items():
        if (relation.get('absolute') or relation['front']['piece'].upper() in MAIN or
                response.actor != key[1] or response.victim != frame.event.actor):
            continue
        proof = _blocker_recapture_proof(run, frame, key)
        if proof:
            candidates[key] = _Candidate(relation, p + 1, 'blocker_recapture', proof)


def _collect_formed_by_response(run: Analysis, frame: MoveFrame, candidates: dict) -> None:
    p, after, reply, response = frame.ply, frame.after, frame.reply, frame.response
    if not reply or not (after.checked or any(r['profitable'] for rows in frame.threats.values() for r in rows)):
        return
    for key, relation in reply.pins.items():
        # The actual response must move the restricted piece or the
        # protected rear target; unrelated preexisting pins do not count.
        if key not in after.pins and response.actor in {key[1], key[2]}:
            proof = functional_pin_capture(relation, run.positions, run.events, p + 1)
            candidates[key] = _Candidate(relation, p + 1, 'formed_by_response', proof)


def _only_while_in_check(frame: MoveFrame, key: tuple, candidate: _Candidate) -> bool:
    """v3.1 (ruling E2): a relation that holds only while the defender is in check is not a pin.

    A recapture is illegal until the check is answered; if the relation is gone
    after a reply that moved none of its pieces, it never restricted anything.
    """
    after, reply = frame.after, frame.reply
    return (candidate.mode in {'created', 'exploited', 'defensive_duty_exploited'} and
            candidate.confirmed == frame.ply and
            after.checked and reply is not None and key not in reply.pins and
            all(after.squares.get(x) == reply.squares.get(x) for x in key[:3]))


def _report_candidate(run: Analysis, frame: MoveFrame, key: tuple, candidate: _Candidate) -> None:
    p = frame.ply
    relation, confirmed, mode, proof = candidate
    if _only_while_in_check(frame, key, candidate):
        run.review('pin', p, 'pin_only_while_in_check', relation)
        return
    if not proof:
        return
    relation_pos = frame.before if mode == 'pinned_piece_captured' else run.positions[confirmed]
    if front_can_trade_pinner(relation_pos, relation):
        return
    run.emit(Finding('pin', p, max(confirmed, proof['capturePly']), [key[0]], [key[1], key[2]], key[3],
                     {'restriction': relation, 'use': mode, 'functionalCapture': proof,
                      'relationFen': run.positions[confirmed].fen,
                      'response': frame.response.move if confirmed == p + 1 else None}))


def detect_pins(run: Analysis, frame: MoveFrame) -> None:
    candidates: dict = {}
    _collect_exploited(run, frame, candidates)
    _collect_captured(run, frame, candidates)
    _collect_blocker_recaptures(run, frame, candidates)
    _collect_formed_by_response(run, frame, candidates)
    for key, candidate in candidates.items():
        _report_candidate(run, frame, key, candidate)


def detect_recapture_pins(run: Analysis) -> None:
    """v2.6: 借牽制得子 through an illegal recapture that the structural pin scan cannot key.

    Includes being pinned to the general by the facing-generals rule.  Stops at
    the first pin found anywhere in the line, this detector's own included.
    """
    for capture in run.events[1:]:
        if capture.side != run.solver or capture.victim_kind not in MAIN:
            continue
        if any(o['id'] == 'pin' for ply in run.plies for o in ply['occurrences']):
            break
        found = (illegal_recapture_pin(run.positions, capture)
                 or relative_recapture_pin(run.positions, run.events, capture))
        if found:
            pinner, guard, king, proof = found
            mode, position = proof['mode'], run.positions[capture.ply]
            run.emit(Finding('pin', capture.ply, capture.ply, [pinner], [guard, king], mode,
                             {'restriction': {'actor': position.ref(pinner), 'front': position.ref(guard),
                                              'rear': position.ref(king), 'kind': mode,
                                              'absolute': mode == 'illegal_recapture'},
                              'use': mode, 'functionalCapture': proof,
                              'relationFen': position.fen, 'response': None}))
