"""Midgame tactic classification (``classify_midgame``).

Replay the line (``replay``), run one detector per label in a fixed order
(``analysis``, ``detectors/``), then merge them with the suppression rules (``merge``).
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
