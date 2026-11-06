"""Portable Xiangqi puzzle classifiers: midgame tactics and checkmate patterns.

The package uses the standard library only.  It does not import pyffish,
FastAPI or Pydantic, starts no threads or processes, and does no I/O.
Modules inside the package import each other relatively, so it also works
when vendored under another package; xiangqi-server imports it as
``xiangqi_server.vendor.xq_classify``.

The public entry points ``classify_midgame``, ``classify_checkmate`` and
``clear_caches`` are added as the lab code moves in (phase 0, steps 4 and 5).
"""

from .version import CHECKMATE_RULES_VERSION, MIDGAME_RULES_VERSION, PACKAGE_VERSION, SCHEMA_VERSION

__version__ = PACKAGE_VERSION

__all__ = [
    'CHECKMATE_RULES_VERSION',
    'MIDGAME_RULES_VERSION',
    'PACKAGE_VERSION',
    'SCHEMA_VERSION',
    '__version__',
]
