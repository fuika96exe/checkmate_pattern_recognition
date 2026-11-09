"""Lab board: ``xq_classify.board`` plus the native pyffish engine.

The board, including its move generator, lives in ``xq_classify.board``; this
module re-exports it for the lab and adds no second implementation.  It adds:

* ``PyffishMoveGenerator``, an ``xq_classify`` move generator on the native
  engine, and the UCCI <-> engine move conversion (engine ranks 1-10);
* the lab's default: importing this module installs the pyffish adapter with
  ``xq_classify.board.use_backend`` when pyffish loads.  ``public/data`` was
  generated with pyffish, and its FEN halfmove clock and move order differ from
  the pure generator.  On
  Cloudflare pyffish cannot load, and the package keeps its pure generator.

Every board switch, in tests and scripts alike, goes through
``xq_classify.board.use_backend``.  The lab imports this module under two names
(``app.board`` and ``backend.app.board``), and each installs pyffish on its first
import: choose another backend only after both are imported.
"""
from __future__ import annotations

import re

from xq_classify.board import (  # noqa: F401 - re-exported for the lab modules
    FILES,
    PURE_BACKEND,
    START_FEN,
    UCCI_RE,
    BoardError,
    MoveGenerator,
    analyze_position,
    apply_move,
    attacked_squares,
    board_to_fen,
    build_piece_identity,
    check_ucci,
    clear_caches,
    coords,
    current_backend,
    has_both_generals,
    is_square_attacked,
    legal_moves,
    move_piece_identity,
    parse_fen,
    position_analysis,
    pseudo_legal_targets,
    side_to_move,
    square_at,
    squares_between,
    use_backend,
)

try:  # Native locally; unavailable in Cloudflare's WebAssembly Python runtime.
    import pyffish
except ImportError:  # pragma: no cover - exercised by the Cloudflare deployment
    pyffish = None

VARIANT = "xiangqi"


def ucci_to_engine(move: str) -> str:
    check_ucci(move)
    return f"{move[0]}{int(move[1]) + 1}{move[2]}{int(move[3]) + 1}"


def engine_to_ucci(move: str) -> str:
    match = re.fullmatch(r"([a-i])(10|[1-9])([a-i])(10|[1-9])", move)
    if not match:
        raise BoardError(f"無法轉換引擎着法：{move}")
    return (
        f"{match.group(1)}{int(match.group(2)) - 1}"
        f"{match.group(3)}{int(match.group(4)) - 1}"
    )


class PyffishMoveGenerator:
    """``xq_classify`` MoveGenerator on a pyffish-compatible *engine* (``legal_moves``, ``get_fen``)."""

    name = "pyffish"

    def __init__(self, engine) -> None:
        self.engine = engine

    def legal_moves(self, fen: str) -> list[str]:
        # Hypothetical tactical captures can remove a general.  Such positions
        # are terminal; passing them to the native engine can corrupt its state
        # and crash a later get_fen call instead of raising a Python exception.
        # xq_classify.board.legal_moves already filters them; this guards direct calls.
        if not has_both_generals(parse_fen(fen)):
            return []
        try:
            return [engine_to_ucci(move) for move in self.engine.legal_moves(VARIANT, fen, [])]
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"局面不能產生合法着法：{exc}") from exc

    def apply_move(self, fen: str, ucci: str) -> str:
        engine_move = ucci_to_engine(ucci)
        try:
            return self.engine.get_fen(VARIANT, fen, [engine_move])
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"無法套用着法：{exc}") from exc


NATIVE_BACKEND = PyffishMoveGenerator(pyffish) if pyffish is not None else None

if NATIVE_BACKEND is not None:
    use_backend(NATIVE_BACKEND)  # the lab's default; public/data was generated with pyffish
