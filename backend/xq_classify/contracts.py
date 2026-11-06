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
