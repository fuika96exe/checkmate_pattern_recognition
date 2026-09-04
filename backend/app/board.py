from __future__ import annotations

import re
from functools import lru_cache

try:  # Native locally; unavailable in Cloudflare's WebAssembly Python runtime.
    import pyffish
except ImportError:  # pragma: no cover - exercised by the Cloudflare deployment
    pyffish = None

VARIANT = "xiangqi"
START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
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


@lru_cache(maxsize=1024)
def _parse_fen_cached(fen: str) -> dict[str, str]:
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


def parse_fen(fen: str) -> dict[str, str]:
    """Parse a FEN into a fresh board while caching its validated shape."""
    return dict(_parse_fen_cached(fen))


def side_to_move(fen: str) -> str:
    return "red" if fen.split()[1] == "w" else "black"


@lru_cache(maxsize=512)
def legal_moves(fen: str) -> list[str]:
    if pyffish is not None:
        try:
            return [
                engine_to_ucci(move)
                for move in pyffish.legal_moves(VARIANT, fen, [])
            ]
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"局面不能產生合法着法：{exc}") from exc

    board = parse_fen(fen)
    moving_red = side_to_move(fen) == "red"
    king_piece = "K" if moving_red else "k"
    king_square = next(
        (square for square, occupant in board.items() if occupant == king_piece),
        None,
    )
    if king_square is None:
        return []
    result: list[str] = []

    for source, piece in sorted(board.items()):
        if _is_red(piece) != moving_red:
            continue
        for target in _pseudo_legal_targets(board, source, piece):
            next_board = dict(board)
            next_board.pop(source)
            next_board[target] = piece
            next_king_square = target if source == king_square else king_square
            if not _is_square_attacked(next_board, next_king_square, not moving_red):
                result.append(f"{source}{target}")

    return result


@lru_cache(maxsize=8192)
def apply_move(fen: str, ucci: str) -> str:
    engine_move = ucci_to_engine(ucci)
    if ucci not in legal_moves(fen):
        raise BoardError(f"非法着法：{ucci}")

    if pyffish is not None:
        try:
            return pyffish.get_fen(VARIANT, fen, [engine_move])
        except Exception as exc:  # pragma: no cover - engine text varies
            raise BoardError(f"無法套用着法：{exc}") from exc

    parts = fen.strip().split()
    board = parse_fen(fen)
    piece = board.pop(ucci[:2])
    board[ucci[2:]] = piece
    next_side = "b" if parts[1] == "w" else "w"
    halfmove = int(parts[4]) + 1 if len(parts) > 4 else 1
    fullmove = int(parts[5]) if len(parts) > 5 else 1
    if parts[1] == "b":
        fullmove += 1
    return f"{_board_to_fen(board)} {next_side} - - {halfmove} {fullmove}"


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
# The compact move generator below keeps the recognition lab deployable on
# runtimes that cannot load native CPython extensions.
FILES = "abcdefghi"


def _xy(square: str) -> tuple[int, int]:
    return FILES.index(square[0]), int(square[1])


def _square(x: int, y: int) -> str | None:
    if 0 <= x < 9 and 0 <= y <= 9:
        return f"{FILES[x]}{y}"
    return None


def _is_red(piece: str) -> bool:
    return piece.isupper()


def _board_to_fen(board: dict[str, str]) -> str:
    encoded_ranks: list[str] = []
    for rank in range(9, -1, -1):
        empty = 0
        encoded = ""
        for file_name in FILES:
            piece = board.get(f"{file_name}{rank}")
            if piece is None:
                empty += 1
                continue
            if empty:
                encoded += str(empty)
                empty = 0
            encoded += piece
        if empty:
            encoded += str(empty)
        encoded_ranks.append(encoded)
    return "/".join(encoded_ranks)


def _inside_palace(x: int, y: int, red: bool) -> bool:
    return 3 <= x <= 5 and ((0 <= y <= 2) if red else (7 <= y <= 9))


def _pseudo_legal_targets(
    board: dict[str, str], source: str, piece: str
) -> list[str]:
    """Generate Xiangqi moves before filtering moves that expose the general."""
    x, y = _xy(source)
    red = _is_red(piece)
    kind = piece.upper()
    targets: list[str] = []

    def add_if_open(target: str | None) -> None:
        if target is None:
            return
        occupant = board.get(target)
        if occupant is None or _is_red(occupant) != red:
            targets.append(target)

    if kind in {"R", "C"}:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cx, cy = x + dx, y + dy
            screen_seen = False
            while (target := _square(cx, cy)) is not None:
                occupant = board.get(target)
                if kind == "R":
                    if occupant is None:
                        targets.append(target)
                    else:
                        if _is_red(occupant) != red:
                            targets.append(target)
                        break
                elif not screen_seen:
                    if occupant is None:
                        targets.append(target)
                    else:
                        screen_seen = True
                elif occupant is not None:
                    if _is_red(occupant) != red:
                        targets.append(target)
                    break
                cx, cy = cx + dx, cy + dy
        return targets

    if kind == "N":
        horse_steps = (
            (1, 2, 0, 1),
            (-1, 2, 0, 1),
            (1, -2, 0, -1),
            (-1, -2, 0, -1),
            (2, 1, 1, 0),
            (2, -1, 1, 0),
            (-2, 1, -1, 0),
            (-2, -1, -1, 0),
        )
        for dx, dy, leg_x, leg_y in horse_steps:
            leg = _square(x + leg_x, y + leg_y)
            if leg is not None and leg not in board:
                add_if_open(_square(x + dx, y + dy))
        return targets

    if kind == "B":
        for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            eye = _square(x + dx // 2, y + dy // 2)
            target = _square(x + dx, y + dy)
            if target is None or eye is None or eye in board:
                continue
            target_rank = int(target[1])
            if (red and target_rank <= 4) or (not red and target_rank >= 5):
                add_if_open(target)
        return targets

    if kind == "A":
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            target = _square(x + dx, y + dy)
            if target is not None and _inside_palace(x + dx, y + dy, red):
                add_if_open(target)
        return targets

    if kind == "K":
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            target = _square(x + dx, y + dy)
            if target is not None and _inside_palace(x + dx, y + dy, red):
                add_if_open(target)

        for direction in (-1, 1):
            cy = y + direction
            while (target := _square(x, cy)) is not None:
                occupant = board.get(target)
                if occupant is not None:
                    if occupant.upper() == "K" and _is_red(occupant) != red:
                        targets.append(target)
                    break
                cy += direction
        return targets

    if kind == "P":
        direction = 1 if red else -1
        add_if_open(_square(x, y + direction))
        crossed_river = y >= 5 if red else y <= 4
        if crossed_river:
            add_if_open(_square(x - 1, y))
            add_if_open(_square(x + 1, y))
        return targets

    return targets


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


def _is_square_attacked(
    board: dict[str, str], target: str, by_red: bool
) -> bool:
    """Fast targeted attack test used by the legal-move filter."""
    tx, ty = _xy(target)
    for source, piece in board.items():
        if _is_red(piece) != by_red:
            continue

        sx, sy = _xy(source)
        dx, dy = tx - sx, ty - sy
        abs_dx, abs_dy = abs(dx), abs(dy)
        kind = piece.upper()

        if kind == "R":
            if (dx == 0 or dy == 0) and not any(
                square in board for square in _between(board, source, target)
            ):
                return True
        elif kind == "C":
            if (dx == 0 or dy == 0) and sum(
                square in board for square in _between(board, source, target)
            ) == 1:
                return True
        elif kind == "K":
            if abs_dx + abs_dy == 1:
                return True
            if dx == 0 and not any(
                square in board for square in _between(board, source, target)
            ):
                return True
        elif kind == "N" and sorted((abs_dx, abs_dy)) == [1, 2]:
            if abs_dx == 2:
                leg = _square(sx + (1 if dx > 0 else -1), sy)
            else:
                leg = _square(sx, sy + (1 if dy > 0 else -1))
            if leg is not None and leg not in board:
                return True
        elif kind == "B" and abs_dx == 2 and abs_dy == 2:
            eye = _square(sx + dx // 2, sy + dy // 2)
            if eye is not None and eye not in board:
                return True
        elif kind == "A" and abs_dx == 1 and abs_dy == 1:
            return True
        elif kind == "P":
            direction = 1 if by_red else -1
            if dx == 0 and dy == direction:
                return True
            crossed_river = sy >= 5 if by_red else sy <= 4
            if crossed_river and dy == 0 and abs_dx == 1:
                return True

    return False


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
                    and not any(
                        square in board for square in _between(board, source, target)
                    )
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


@lru_cache(maxsize=256)
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
