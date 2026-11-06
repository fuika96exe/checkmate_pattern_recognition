"""Destination-square exchange evaluation used by the Fake Human move labels and midgame tactics.

The evaluation lives in ``xq_classify.exchange``.  The lab binds it to its own
board functions, which choose pyffish or the pure generator from the module
attribute ``app.board.pyffish`` on each call.  That keeps the native and python
runs of the frozen gates and ``test_exchange.py`` on their own boards until
phase 0 steps 4 and 5 move them to ``xq_classify.board.use_backend``.
"""
from __future__ import annotations

from xq_classify.exchange import MATERIAL_VALUES, ExchangeEvaluator, piece_value  # noqa: F401 - re-exported

from .board import apply_move, legal_moves, position_analysis

_LAB_BOARD = ExchangeEvaluator(legal_moves, apply_move, position_analysis)
evaluate_exchange = _LAB_BOARD.evaluate_exchange
# The frozen midgame gate and test_exchange.py clear this cache by its old private name.
_evaluate_square = _LAB_BOARD.evaluate_square
