"""Typed classifier results (dataclasses with ``to_dict()`` and ``from_dict()``).

``to_dict()`` keeps the field names and key order of the lab output it replaces,
so the golden comparison stays valid.  For the same reason ``schema_version`` is
a field of the result and not a key of the record: whoever stores records stores
the version next to them.
"""

from dataclasses import dataclass, field
from typing import Self

from .version import SCHEMA_VERSION


@dataclass(frozen=True)
class CheckmateResult:
    """Outcome of ``classify_checkmate``.

    ``status`` is ``'matched'`` (a pattern or a mating-material code), ``'unmatched'``
    or ``'invalid'``.  An invalid result has an ``error``: a move that cannot be
    played (then ``failed_move_index``, 1-based over blunder + pv, or over pv
    alone when there is no blunder), an empty line, a failed analysis, or a
    line that does not end in checkmate or stalemate.
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
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        """The puzzle-index record: ``status``, ``patternIds`` and ``error`` or ``materialId``."""
        if self.status == 'invalid':
            return {'status': 'invalid', 'patternIds': [], 'error': self.error}
        return {'status': self.status, 'patternIds': list(self.pattern_ids), 'materialId': self.material_id}

    @classmethod
    def from_dict(cls, record: dict) -> Self:
        """Rebuild a result from a ``to_dict()`` record, which carries no timeline or analysis."""
        return cls(
            status=record['status'],
            pattern_ids=list(record['patternIds']),
            material_id=record.get('materialId'),
            error=record.get('error'),
        )


@dataclass(frozen=True)
class MidgameResult:
    """Outcome of ``classify_midgame`` for a line that replays (an invalid line raises ``ReplayError``).

    ``status`` is ``'matched'`` when ``tactics`` is non-empty, else ``'unmatched'``.
    ``tactics`` lists label IDs in the fixed label order; ``material`` holds
    ``kind`` (``'gain'`` / ``'no_gain'``), ``start``, ``end`` and ``delta``.
    ``plies`` carries the per-move occurrences with their evidence.  Ply 1 is
    the blunder; without one it is a pass with ``ucci`` ``None`` and ``fens[1]``
    repeats ``fens[0]``, so the solver's first move is ply 2 either way.
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
    schema_version: str = SCHEMA_VERSION

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

    @classmethod
    def from_dict(cls, record: dict) -> Self:
        """Rebuild a result from a ``to_dict()`` record."""
        return cls(
            status=record['status'],
            solver=record['solver'],
            tactics=record['tactics'],
            fens=record['fens'],
            plies=record['plies'],
            material=record['material'],
            supporting_evidence=record['supportingEvidence'],
            review_reasons=record['reviewReasons'],
        )
