"""Checkmate pattern recognition for the lab: re-exported from ``xq_classify.checkmate``.

The recognisers moved into the portable package in phase 0 step 4.  Code that
must patch module globals (tests of the material fallback, audit scripts) uses
the ``xq_classify.checkmate`` submodules directly.
"""
from __future__ import annotations

from xq_classify.checkmate import (  # noqa: F401 - re-exported for the lab
    CHECKMATE_RULES_VERSION,
    PATTERN_ORDER,
    analyze_patterns,
    classify_mating_material,
    recognize_pattern,
)
