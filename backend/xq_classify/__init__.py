"""Portable Xiangqi puzzle classifiers: midgame tactics and checkmate patterns.

The package uses the standard library only.  It does not import pyffish,
FastAPI or Pydantic, starts no threads or processes, and does no I/O.
Modules inside the package import each other relatively, so it also works
when vendored under another package; xiangqi-server imports it as
``xiangqi_server.vendor.xq_classify``.

Public entry points: ``classify_checkmate`` and ``clear_caches``;
``classify_midgame`` follows in phase 0 step 5.
"""

from .board import clear_caches
from .checkmate import classify_checkmate
from .contracts import CheckmateResult
from .version import CHECKMATE_RULES_VERSION, MIDGAME_RULES_VERSION, PACKAGE_VERSION, SCHEMA_VERSION

__version__ = PACKAGE_VERSION

__all__ = [
    'CHECKMATE_RULES_VERSION',
    'MIDGAME_RULES_VERSION',
    'PACKAGE_VERSION',
    'SCHEMA_VERSION',
    'CheckmateResult',
    '__version__',
    'classify_checkmate',
    'clear_caches',
]
