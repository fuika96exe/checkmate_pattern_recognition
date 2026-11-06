"""Portable Xiangqi puzzle classifiers: midgame tactics and checkmate patterns.

The package uses the standard library only.  It does not import pyffish,
FastAPI or Pydantic, starts no threads or processes, and does no I/O.
Modules inside the package import each other relatively, so it also works
when vendored under another package; xiangqi-server imports it as
``xiangqi_server.vendor.xq_classify``.

Public entry points: ``classify_checkmate``, ``classify_midgame`` and
``clear_caches``.  ``board.use_backend`` swaps the move generator.
"""

from .board import clear_caches
from .checkmate import classify_checkmate
from .contracts import CheckmateResult, MidgameResult
from .midgame import ReplayError, classify_midgame
from .version import CHECKMATE_RULES_VERSION, MIDGAME_RULES_VERSION, PACKAGE_VERSION, SCHEMA_VERSION

__version__ = PACKAGE_VERSION

__all__ = [
    'CHECKMATE_RULES_VERSION',
    'MIDGAME_RULES_VERSION',
    'PACKAGE_VERSION',
    'SCHEMA_VERSION',
    'CheckmateResult',
    'MidgameResult',
    'ReplayError',
    '__version__',
    'classify_checkmate',
    'classify_midgame',
    'clear_caches',
]
