from __future__ import annotations

import re

import pyffish


VARIANT = "xiangqi"
START_FEN = pyffish.start_fen(VARIANT)
UCCI_RE = re.compile(r"^[a-i][0-9][a-i][0-9]$")


class BoardError(ValueError):
    pass


def ucci_to_engine(move: str) -> str:
    if not UCCI_RE.fullmatch(move):
        raise BoardError("UCCI 着法格式不正確")
    return f"{move[0]}{int(move[1]) + 1}{move[2]}{int(move[3]) + 1}"


def engine_to_ucci(move: str) -> str:
    match = re.fullmatch(r"([a-i])(10|[1-9])([a-i])(10|[1-9])", move)
    if not match:
        raise BoardError(f"無法轉換引擎着法：{move}")
    return (
        f"{match.group(1)}{int(match.group(2)) - 1}"
        f"{match.group(3)}{int(match.group(4)) - 1}"
    )


def parse_fen(fen: str) -> dict[str, str]:
    parts = fen.strip().split()
    if len(parts) < 2:
        raise BoardError("FEN 必須包含棋盤及行棋方")
    ranks = parts[0].split("/")
    if len(ranks) != 10:
        raise BoardError("中國象棋 FEN 必須有 10 行")
    board: dict[str, str] = {}
    for fen_index, encoded in enumerate(ranks):
        rank = 9 - fen_index
        file_index = 0
        for char in encoded:
            if char.isdigit():
                file_index += int(char)
                continue
            if char not in "rnbakcpRNBAKCP":
                raise BoardError(f"FEN 包含不支援棋子：{char}")
            if file_index >= 9:
                raise BoardError("FEN 行超出 9 路")
            square = f"{chr(ord('a') + file_index)}{rank}"
            board[square] = char
            file_index += 1
        if file_index != 9:
            raise BoardError("FEN 每行必須正好 9 路")
    if parts[1] not in {"w", "b"}:
        raise BoardError("FEN 行棋方必須是 w 或 b")
    return board


def side_to_move(fen: str) -> str:
    return "red" if fen.split()[1] == "w" else "black"


def legal_moves(fen: str) -> list[str]:
    parse_fen(fen)
    try:
        return [engine_to_ucci(move) for move in pyffish.legal_moves(VARIANT, fen, [])]
    except Exception as exc:  # pragma: no cover - pyffish error text varies
        raise BoardError(f"局面不能產生合法着法：{exc}") from exc


def apply_move(fen: str, ucci: str) -> str:
    engine_move = ucci_to_engine(ucci)
    if ucci not in legal_moves(fen):
        raise BoardError(f"非法着法：{ucci}")
    try:
        return pyffish.get_fen(VARIANT, fen, [engine_move])
    except Exception as exc:  # pragma: no cover
        raise BoardError(f"無法套用着法：{exc}") from exc


def build_piece_identity(fen: str) -> dict[str, str]:
    board = parse_fen(fen)
    counters: dict[str, int] = {}
    identities: dict[str, str] = {}
    for square, piece in sorted(board.items()):
        counters[piece] = counters.get(piece, 0) + 1
        identities[square] = f"{piece}:{counters[piece]}"
    return identities


def move_piece_identity(
    identities: dict[str, str], from_square: str, to_square: str
) -> dict[str, str]:
    next_map = dict(identities)
    piece_id = next_map.pop(from_square, f"unknown:{from_square}")
    next_map.pop(to_square, None)
    next_map[to_square] = piece_id
    return next_map


# --- Position analysis ----------------------------------------------------
# These helpers deliberately operate on the normalized board dictionary.  The
# move generator remains pyffish's responsibility; this layer explains why a
# position is check/checkmate and provides reusable facts for future patterns.
FILES = "abcdefghi"


def _xy(square: str) -> tuple[int, int]:
    return FILES.index(square[0]), int(square[1])


def _square(x: int, y: int) -> str | None:
    if 0 <= x < 9 and 0 <= y <= 9:
        return f"{FILES[x]}{y}"
    return None


def _is_red(piece: str) -> bool:
    return piece.isupper()


def _between(board: dict[str, str], a: str, b: str) -> list[str]:
    ax, ay = _xy(a); bx, by = _xy(b)
    if ax != bx and ay != by:
        return []
    dx = (bx > ax) - (bx < ax); dy = (by > ay) - (by < ay)
    x, y = ax + dx, ay + dy
    result: list[str] = []
    while (x, y) != (bx, by):
        result.append(f"{FILES[x]}{y}")
        x, y = x + dx, y + dy
    return result


def attacked_squares(board: dict[str, str], by_side: str) -> dict[str, list[dict[str, str]]]:
    """Return target squares attacked by *by_side* with deterministic reasons."""
    red = by_side == "red"
    attacks: dict[str, list[dict[str, str]]] = {}

    def add(target: str, source: str, reason: str) -> None:
        attacks.setdefault(target, []).append({"square": source, "reason": reason})

    for source, piece in board.items():
        if _is_red(piece) != red:
            continue
        x, y = _xy(source)
        kind = piece.upper()
        if kind in {"R", "C"}:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cx, cy = x + dx, y + dy
                screens = 0
                while (target := _square(cx, cy)) is not None:
                    occupant = board.get(target)
                    if kind == "C":
                        if screens == 1 and occupant is not None:
                            add(target, source, "cannon_screen")
                            break
                        if occupant is not None:
                            screens += 1
                    else:
                        if screens == 0:
                            add(target, source, "line_attack")
                        if occupant is not None:
                            break
                    cx, cy = cx + dx, cy + dy
        if kind == "K":
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                target = _square(x + dx, y + dy)
                if target:
                    add(target, source, "general_attack")
            # Flying-general attack is represented as a direct line attack.
            for target, other in board.items():
                if (
                    other.upper() == "K"
                    and _is_red(other) != red
                    and source[0] == target[0]
                    and not _between(board, source, target)
                ):
                    add(target, source, "flying_general")
        elif kind == "N":
            for dx, dy, lx, ly in ((1,2,0,1),(-1,2,0,1),(1,-2,0,-1),(-1,-2,0,-1),(2,1,1,0),(2,-1,1,0),(-2,1,-1,0),(-2,-1,-1,0)):
                leg = _square(x + lx, y + ly); target = _square(x + dx, y + dy)
                if target and not (leg and leg in board):
                    add(target, source, "horse_attack")
        elif kind == "B":
            for dx, dy in ((2,2),(2,-2),(-2,2),(-2,-2)):
                eye = _square(x + dx // 2, y + dy // 2); target = _square(x + dx, y + dy)
                if target and eye not in board:
                    add(target, source, "elephant_attack")
        elif kind == "A":
            for dx, dy in ((1,1),(1,-1),(-1,1),(-1,-1)):
                target = _square(x + dx, y + dy)
                if target:
                    add(target, source, "advisor_attack")
        elif kind == "P":
            direction = 1 if red else -1
            for dx, dy in ((0, direction), (-1, 0), (1, 0)):
                target = _square(x + dx, y + dy)
                if target and (red and y >= 5 or not red and y <= 4 or dx == 0):
                    add(target, source, "pawn_attack")
    return attacks


def position_analysis(fen: str) -> dict:
    board = parse_fen(fen)
    moving = side_to_move(fen)
    opponent = "black" if moving == "red" else "red"
    king_piece = "K" if moving == "red" else "k"
    king_square = next((s for s, p in board.items() if p == king_piece), None)
    if king_square is None:
        raise BoardError("FEN 找不到行棋方的將帥")
    attacks = attacked_squares(board, opponent)
    checking = attacks.get(king_square, [])
    moves = legal_moves(fen)
    in_check = bool(checking)
    return {
        "side_to_move": moving,
        "king_square": king_square,
        "is_check": in_check,
        "is_checkmate": in_check and not moves,
        "is_stalemate": not in_check and not moves,
        "legal_moves": moves,
        "checking_pieces": checking,
        "attacked_squares": attacks,
    }
