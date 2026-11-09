"""Midgame tactic classification (``classify_midgame``).

Replay the line, detect the labels, then merge them with the suppression rules.
Phase 0 step 6 splits ``analysis`` into a replay context, one detector per
label and the merge step.
"""

from .analysis import RULES_VERSION, analyze_midgame
from .classify import classify_midgame
from .context import LABELS
from .material import material_result
from .position import Position, profitable_capture
from .replay import ReplayError, replay

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
