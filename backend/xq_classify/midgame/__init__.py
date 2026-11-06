"""Midgame tactic classification (``classify_midgame``).

Replay the line, detect the labels, then merge them with the suppression rules.
Phase 0 step 6 splits ``analysis`` into a replay context, one detector per
label and the merge step.
"""

from .analysis import (
    LABELS,
    RULES_VERSION,
    Position,
    ReplayError,
    analyze_midgame,
    material_result,
    profitable_capture,
    replay,
)
from .classify import classify_midgame

__all__ = [
    'LABELS',
    'RULES_VERSION',
    'Position',
    'ReplayError',
    'analyze_midgame',
    'classify_midgame',
    'material_result',
    'profitable_capture',
    'replay',
]
