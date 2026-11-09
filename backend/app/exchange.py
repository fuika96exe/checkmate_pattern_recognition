"""Destination-square exchange evaluation for the lab: re-exported from ``xq_classify.exchange``.

It runs on the package board, so it follows ``xq_classify.board.use_backend``
(pyffish in the lab once ``app.board`` is imported).
"""
from __future__ import annotations

from xq_classify.exchange import (  # noqa: F401 - re-exported for the lab
    MATERIAL_VALUES,
    ExchangeEvaluator,
    clear_caches,
    evaluate_exchange,
    evaluate_square,
    piece_value,
)
