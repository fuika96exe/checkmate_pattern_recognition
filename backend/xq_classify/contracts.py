"""Typed classifier results (dataclasses with ``to_dict()``).

``to_dict()`` keeps the field names and key order of the lab output it replaces,
so the golden comparison stays valid.  Phase 0 step 8 adds the schema version and
round-trip tests.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CheckmateResult:
    """Outcome of ``classify_checkmate``.

    ``status`` is ``'matched'`` (a pattern or a mating-material code), ``'unmatched'``
    or ``'invalid'``.  An invalid result has an ``error``: a move that cannot be
    played (then ``failed_move_index``, 1-based over blunder + pv), a failed
    analysis, or a line that does not end in checkmate or stalemate.
    ``timeline`` lists the positions reached (``index``, ``fen``, ``move``);
    ``analysis`` is the full pattern analysis (evidence), when one was made.
    """

    status: str
    pattern_ids: list[str] = field(default_factory=list)
    material_id: str | None = None
    error: str | None = None
    failed_move_index: int | None = None
    timeline: list[dict] = field(default_factory=list)
    analysis: dict | None = None

    def to_dict(self) -> dict:
        """The puzzle-index record: ``status``, ``patternIds`` and ``error`` or ``materialId``."""
        if self.status == 'invalid':
            return {'status': 'invalid', 'patternIds': [], 'error': self.error}
        return {'status': self.status, 'patternIds': list(self.pattern_ids), 'materialId': self.material_id}


@dataclass(frozen=True)
class MidgameResult:
    """Outcome of ``classify_midgame`` for a line that replays (an invalid line raises ``ReplayError``).

    ``status`` is ``'matched'`` when ``tactics`` is non-empty, else ``'unmatched'``.
    ``tactics`` lists label IDs in the fixed label order; ``material`` holds
    ``kind`` (``'gain'`` / ``'no_gain'``), ``start``, ``end`` and ``delta``.
    ``plies`` carries the per-move occurrences with their evidence;
    ``supporting_evidence`` keeps suppressed occurrences, ``review_reasons``
    the candidates a rule rejected and why.
    """

    status: str
    solver: str
    tactics: list[str]
    fens: list[str]
    plies: list[dict]
    material: dict
    supporting_evidence: list[dict] = field(default_factory=list)
    review_reasons: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """The lab's puzzle record fields, in the lab's key order."""
        return {
            'status': self.status,
            'solver': self.solver,
            'tactics': self.tactics,
            'fens': self.fens,
            'plies': self.plies,
            'material': self.material,
            'supportingEvidence': self.supporting_evidence,
            'reviewReasons': self.review_reasons,
        }
