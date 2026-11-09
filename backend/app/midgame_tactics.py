"""Midgame tactic rules for the lab: re-exported from ``xq_classify.midgame``.

The rules moved into the portable package in phase 0 step 5.  New code calls
``xq_classify.classify_midgame``.
"""
from __future__ import annotations

from xq_classify.midgame import (  # noqa: F401 - re-exported for the lab
    LABELS,
    RULES_VERSION,
    Position,
    ReplayError,
    analyze_midgame,
    material_result,
    profitable_capture,
    replay,
)
