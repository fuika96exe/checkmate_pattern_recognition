"""Which move generator the board uses.

The package always ships the pure-Python generator and uses it by default.  A
host may install another implementation of ``MoveGenerator`` (the lab installs
pyffish for parity tests).  Callers switch through ``xq_classify.board.use_backend``,
which also clears the board caches; this module only holds the current choice.
"""

from typing import Protocol

from .pure import PURE_BACKEND


class MoveGenerator(Protocol):
    """Legal moves and move application for one position, in UCCI with ranks 0-9."""

    def legal_moves(self, fen: str) -> list[str]:
        """Every legal move of the side to move.  Only called when both generals are on the board."""
        ...

    def apply_move(self, fen: str, ucci: str) -> str:
        """The FEN after *ucci*.  Only called with a move that ``legal_moves`` returned."""
        ...


class _Active:
    generator: MoveGenerator = PURE_BACKEND


def current() -> MoveGenerator:
    return _Active.generator


def replace(generator: MoveGenerator) -> MoveGenerator:
    """Install *generator*; return the one it replaces.  Use ``board.use_backend``, which also clears caches."""
    previous = _Active.generator
    _Active.generator = generator
    return previous
