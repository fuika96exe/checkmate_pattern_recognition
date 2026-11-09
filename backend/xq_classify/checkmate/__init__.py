"""Checkmate pattern classification (``classify_checkmate``).

Apply the line, require a final checkmate or stalemate, recognise the patterns,
then fall back to the mating-material code.  Phase 0 step 7 splits
``recognition`` into one module per pattern.
"""

from .classify import NOT_MATE_ERROR, classify_checkmate
from .geometry import clear_caches
from .material import classify_mating_material
from .recognition import CHECKMATE_RULES_VERSION, PATTERN_ORDER, analyze_patterns, recognize_pattern

__all__ = [
    'CHECKMATE_RULES_VERSION',
    'NOT_MATE_ERROR',
    'PATTERN_ORDER',
    'analyze_patterns',
    'classify_checkmate',
    'classify_mating_material',
    'clear_caches',
    'recognize_pattern',
]
