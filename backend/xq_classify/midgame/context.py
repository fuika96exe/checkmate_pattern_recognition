"""What the detectors of one puzzle share: the replay, the findings so far, and each solver move's frame.

The order of ``emit`` and ``review`` calls is observable.  An occurrence's
evidence key numbers it within its ply, and ``reviewReasons`` keeps call order,
so detectors must keep running in the order ``analysis.py`` lists them.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from ..exchange import evaluate_exchange
from .position import Position
from .replay import Event

LABELS = {
    'fork': '捉雙', 'discovered_attack': '閃擊', 'skewer': '串打',
    'pin': '牽制', 'check_fork': '抽將', 'trap': '圍困',
    'remove_defender': '消除保護', 'overload': '過載', 'exchange': '交換',
    'clearance': '消除阻隔',
}


@dataclass(frozen=True)
class Finding:
    """One tactic occurrence, triggered at ``ply`` and confirmed at ``confirmed``."""

    label: str
    ply: int
    confirmed: int
    actors: list[str]
    targets: list[str]
    kind: str
    evidence: dict


class Analysis:
    """One puzzle's replay plus the occurrences and review reasons found so far."""

    def __init__(self, positions: list[Position], events: list[Event], solver: str) -> None:
        self.positions = positions
        self.events = events
        self.solver = solver
        self.plies = [{'ply': e.ply, 'ucci': e.move, 'solver': e.ply >= 2 and e.side == solver,
                       'occurrences': []} for e in events]
        self.reviews: list[dict] = []

    def occurrences(self, ply: int) -> list[dict]:
        return self.plies[ply - 1]['occurrences']

    def occurrences_through(self, ply: int) -> Iterator[dict]:
        """Every occurrence on plies 1 to *ply*."""
        for entry in self.plies[:ply]:
            yield from entry['occurrences']

    def review(self, label: str, ply: int, reason: str, evidence: dict) -> None:
        self.reviews.append({'label': label, 'ply': ply, 'fen': self.positions[ply].fen,
                             'reason': reason, 'evidence': evidence})

    def _reference(self, identity: str, ply: int) -> dict:
        for snapshot in reversed(self.positions[:ply + 1]):
            if identity in snapshot.squares:
                return snapshot.ref(identity)
        # A future participant in an exchange still existed initially.
        return self.positions[0].ref(identity)

    def emit(self, finding: Finding) -> dict:
        label, ply = finding.label, finding.ply
        key = f'{label}:{ply}:{len(self.occurrences(ply))}'
        actors, targets = list(dict.fromkeys(finding.actors)), list(dict.fromkeys(finding.targets))
        refs = [self._reference(i, ply) for i in dict.fromkeys([*actors, *targets])]
        names = '、'.join(f"{r['id']}@{r['square']}" for r in refs)
        occurrence = {
            'id': label,
            'label_zh': LABELS[label],
            'squares': list(dict.fromkeys(r['square'] for r in refs if r['square'])),
            'detail': f'{LABELS[label]}：第 {ply} 手觸發，第 {finding.confirmed} 手確認；{names}',
            'evidence': {
                'key': key,
                'triggerPly': ply,
                'confirmedPly': finding.confirmed,
                'actors': [self._reference(i, ply) for i in actors],
                'targets': [self._reference(i, ply) for i in targets],
                'relationKind': finding.kind,
                **finding.evidence,
            },
        }
        self.occurrences(ply).append(occurrence)
        return occurrence


def verified_hits(pos: Position, reply: Position | None = None, excluded=frozenset()) -> dict:
    """A pending check cannot subsidize a hypothetical second consecutive move."""
    result: dict = {}
    for target, relations in pos.hits.items():
        for relation in relations:
            actor = relation['actor']['id']
            if actor in excluded:
                continue
            if relation['check'] or not pos.checked:
                result.setdefault(target, []).append(relation)
            elif reply is not None:
                confirmed = reply.relation(actor, target)
                if confirmed:
                    result.setdefault(target, []).append({**confirmed, 'triggerAttack': relation})
    return result


def threats_from(hits: dict) -> dict:
    return {t: [r for r in rows if r['profitable'] or r['check']]
            for t, rows in hits.items() if any(r['profitable'] or r['check'] for r in rows)}


@dataclass(frozen=True)
class MoveFrame:
    """One solver move and everything the per-move detectors read about it."""

    event: Event
    ply: int
    before: Position
    after: Position
    response: Event | None
    reply: Position | None
    excluded: set[str]
    hits: dict
    threats: dict
    fork_threats: dict


def move_frame(run: Analysis, event: Event) -> MoveFrame:
    p = event.ply
    before, after = run.positions[p - 1:p + 1]
    response = run.events[p] if p < len(run.events) else None
    reply = run.positions[p + 1] if response else None
    excluded: set[str] = set()
    if response and response.victim == event.actor and evaluate_exchange(before.fen, event.move) <= 0:
        excluded.add(event.actor)
        run.review('threat', p, 'nonpositive_mover_recaptured_next_ply', {
            'actor': before.ref(event.actor), 'move': event.move,
            'gain': evaluate_exchange(before.fen, event.move), 'response': response.move,
            'responsePly': response.ply})
    hits = verified_hits(after, reply, excluded)
    if after.checked and reply is None:
        run.review('check_fork', p, 'missing_actual_check_response', {})
    return MoveFrame(event, p, before, after, response, reply, excluded, hits, threats_from(hits),
                     threats_from(after.hits))
