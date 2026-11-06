"""Lab board: ``xq_classify.board`` plus the native pyffish engine.

The move generator itself lives in ``xq_classify.board``; this module adds no
second one.  It adds the pyffish adapter, the UCCI <-> engine move conversion
(engine ranks 1-10), and the lab's backend choice:

* Locally pyffish stays the default.  ``public/data`` was generated with it,
  and its FEN halfmove clock and move order differ from the pure generator.
* On Cloudflare pyffish cannot load, and the pure generator is used.

Two switches exist until phase 0 step 5:

* Importing this module installs the pyffish adapter as the package's move
  generator when pyffish loads (``xq_classify.board.use_backend``).  Code that
  runs inside the package (checkmate classification since step 4) follows it.
* This module's own ``legal_moves``, ``apply_move`` and ``position_analysis``,
  still used by the lab's midgame and tactic modules, read the module attribute
  ``pyffish`` on every call.  The frozen midgame gate switches boards with
  ``monkeypatch.setattr(board, "pyffish", None)`` until step 5.
"""
from __future__ import annotations

import re
from functools import lru_cache

from xq_classify.board import (  # noqa: F401 - re-exported for the lab modules
    FILES,
    PURE_BACKEND,
    START_FEN,
    UCCI_RE,
    BoardError,
    MoveGenerator,
    analyze_position,
    attacked_squares,
    board_to_fen,
    build_piece_identity,
    check_ucci,
    coords,
    has_both_generals,
    is_square_attacked,
    move_piece_identity,
    parse_fen,
    pseudo_legal_targets,
    side_to_move,
    square_at,
    squares_between,
    use_backend,
)
from xq_classify.board.fen import _parse_fen_cached  # noqa: F401 - cleared by the frozen gates until steps 4-5

try:  # Native locally; unavailable in Cloudflare's WebAssembly Python runtime.
    import pyffish
except ImportError:  # pragma: no cover - exercised by the Cloudflare deployment
    pyffish = None

VARIANT = "xiangqi"

# The frozen gates build variant FENs with this name until phase 0 steps 4-5.
_board_to_fen = board_to_fen


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
    """``xq_classify`` MoveGenerator on the native engine.

    It reads this module's ``pyffish`` at call time, so a test that replaces
    the attribute replaces the engine.
    """

    name = "pyffish"

    def legal_moves(self, fen: str) -> list[str]:
        # Hypothetical tactical captures can remove a general.  Such positions
        # are terminal; passing them to the native engine can corrupt its state
        # and crash a later get_fen call instead of raising a Python exception.
        if not has_both_generals(parse_fen(fen)):
            return []
        try:
            return [engine_to_ucci(move) for move in pyffish.legal_moves(VARIANT, fen, [])]
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"局面不能產生合法着法：{exc}") from exc

    def apply_move(self, fen: str, ucci: str) -> str:
        engine_move = ucci_to_engine(ucci)
        try:
            return pyffish.get_fen(VARIANT, fen, [engine_move])
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"無法套用着法：{exc}") from exc


NATIVE_BACKEND = PyffishMoveGenerator()

if pyffish is not None:
    use_backend(NATIVE_BACKEND)  # the lab's default; public/data was generated with pyffish


def active_backend() -> MoveGenerator:
    return NATIVE_BACKEND if pyffish is not None else PURE_BACKEND


@lru_cache(maxsize=512)
def legal_moves(fen: str) -> list[str]:
    if not has_both_generals(parse_fen(fen)):
        return []
    return active_backend().legal_moves(fen)


@lru_cache(maxsize=8192)
def apply_move(fen: str, ucci: str) -> str:
    check_ucci(ucci)
    # Through this module's legal_moves, so a test that replaces it sees every probe.
    if ucci not in legal_moves(fen):
        raise BoardError(f"非法着法：{ucci}")
    return active_backend().apply_move(fen, ucci)


@lru_cache(maxsize=256)
def position_analysis(fen: str) -> dict:
    return analyze_position(fen, legal_moves)
