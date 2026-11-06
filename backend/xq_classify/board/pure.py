"""The pure-Python move generator.

Its output order is observable: evidence cites the first matching legal move,
so ``generate_legal_moves`` must keep listing moves by source square, then in
each piece's fixed direction order.  pyffish lists the same set in another order.

The geometry is deliberately the lab's, quirks included: ``attacked_squares``
does not confine advisors and generals to the palace or elephants to their side
of the river.  tests/test_board_reference.py compares every function here with
the original implementation on random boards.
"""

from collections.abc import Callable

from .fen import board_to_fen, has_both_generals, parse_fen, side_to_move
from .geometry import coords, inside_palace, is_red, square_at, squares_between

Board = dict[str, str]
Attacks = dict[str, list[dict[str, str]]]

ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ELEPHANT_STEPS = ((2, 2), (2, -2), (-2, 2), (-2, -2))
# (dx, dy, leg dx, leg dy): a horse move and the leg square that blocks it, both relative to the horse.
HORSE_STEPS = (
    (1, 2, 0, 1),
    (-1, 2, 0, 1),
    (1, -2, 0, -1),
    (-1, -2, 0, -1),
    (2, 1, 1, 0),
    (2, -1, 1, 0),
    (-2, 1, -1, 0),
    (-2, -1, -1, 0),
)


def _scan(board: Board, x: int, y: int, dx: int, dy: int, empties: list[str] | None) -> tuple[str, int, int] | None:
    """Walk from (x, y) in direction (dx, dy), appending each empty square to *empties* when given.

    Returns the first occupied square with its coordinates, or ``None`` at the edge of the board.
    """
    while (target := square_at(x, y)) is not None:
        if board.get(target) is not None:
            return target, x, y
        if empties is not None:
            empties.append(target)
        x, y = x + dx, y + dy
    return None


# --- Pseudo-legal moves ------------------------------------------------------


def _add_if_open(board: Board, targets: list[str], target: str | None, red: bool) -> None:
    if target is None:
        return
    occupant = board.get(target)
    if occupant is None or is_red(occupant) != red:
        targets.append(target)


def _chariot_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy in ORTHOGONAL:
        blocker = _scan(board, x + dx, y + dy, dx, dy, targets)
        if blocker is not None and is_red(board[blocker[0]]) != red:
            targets.append(blocker[0])


def _cannon_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy in ORTHOGONAL:
        screen = _scan(board, x + dx, y + dy, dx, dy, targets)
        if screen is None:
            continue
        _, sx, sy = screen
        victim = _scan(board, sx + dx, sy + dy, dx, dy, None)
        if victim is not None and is_red(board[victim[0]]) != red:
            targets.append(victim[0])


def _horse_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy, leg_x, leg_y in HORSE_STEPS:
        leg = square_at(x + leg_x, y + leg_y)
        if leg is not None and leg not in board:
            _add_if_open(board, targets, square_at(x + dx, y + dy), red)


def _elephant_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy in ELEPHANT_STEPS:
        eye = square_at(x + dx // 2, y + dy // 2)
        target = square_at(x + dx, y + dy)
        if target is None or eye is None or eye in board:
            continue
        target_rank = int(target[1])
        if (red and target_rank <= 4) or (not red and target_rank >= 5):
            _add_if_open(board, targets, target, red)


def _advisor_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy in DIAGONAL:
        target = square_at(x + dx, y + dy)
        if target is not None and inside_palace(x + dx, y + dy, red):
            _add_if_open(board, targets, target, red)


def _general_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    for dx, dy in ORTHOGONAL:
        target = square_at(x + dx, y + dy)
        if target is not None and inside_palace(x + dx, y + dy, red):
            _add_if_open(board, targets, target, red)
    for direction in (-1, 1):  # the generals face each other along an open file
        facing = _scan(board, x, y + direction, 0, direction, None)
        if facing is not None:
            occupant = board[facing[0]]
            if occupant.upper() == 'K' and is_red(occupant) != red:
                targets.append(facing[0])


def _pawn_targets(board: Board, x: int, y: int, red: bool, targets: list[str]) -> None:
    direction = 1 if red else -1
    _add_if_open(board, targets, square_at(x, y + direction), red)
    crossed_river = y >= 5 if red else y <= 4
    if crossed_river:
        _add_if_open(board, targets, square_at(x - 1, y), red)
        _add_if_open(board, targets, square_at(x + 1, y), red)


_TARGETS: dict[str, Callable[[Board, int, int, bool, list[str]], None]] = {
    'R': _chariot_targets,
    'C': _cannon_targets,
    'N': _horse_targets,
    'B': _elephant_targets,
    'A': _advisor_targets,
    'K': _general_targets,
    'P': _pawn_targets,
}


def pseudo_legal_targets(board: Board, source: str, piece: str) -> list[str]:
    """Generate Xiangqi moves before filtering moves that expose the general."""
    x, y = coords(source)
    targets: list[str] = []
    generate = _TARGETS.get(piece.upper())
    if generate is not None:
        generate(board, x, y, is_red(piece), targets)
    return targets


# --- Is one square attacked? (looks outward from the target) -----------------


def _attacker_on_target(board: Board, target: str, by_red: bool) -> bool:
    # A chariot or general of the attacking side standing on the target itself counts as attacking it.
    piece = board.get(target)
    return piece is not None and is_red(piece) == by_red and piece.upper() in {'R', 'K'}


def _nearest_piece_attacks(piece: str, by_red: bool, vertical: bool, distance: int) -> bool:
    """Whether the first piece along a line from the target attacks it: a chariot, or a facing or adjacent general."""
    if is_red(piece) != by_red:
        return False
    kind = piece.upper()
    return kind == 'R' or (kind == 'K' and (vertical or distance == 1))


def _line_attack(board: Board, tx: int, ty: int, by_red: bool) -> bool:
    cannon = 'C' if by_red else 'c'
    for dx, dy in ORTHOGONAL:
        nearest = _scan(board, tx + dx, ty + dy, dx, dy, None)
        if nearest is None:
            continue
        square, nx, ny = nearest
        if _nearest_piece_attacks(board[square], by_red, dx == 0, abs(nx - tx) + abs(ny - ty)):
            return True
        beyond = _scan(board, nx + dx, ny + dy, dx, dy, None)
        if beyond is not None and board[beyond[0]] == cannon:
            return True
    return False


def _horse_attack(board: Board, tx: int, ty: int, by_red: bool) -> bool:
    horse = 'N' if by_red else 'n'
    for dx, dy, leg_x, leg_y in HORSE_STEPS:  # a horse at target - (dx, dy) would land on the target
        sx, sy = tx - dx, ty - dy
        source = square_at(sx, sy)
        if source is None or board.get(source) != horse:
            continue
        leg = square_at(sx + leg_x, sy + leg_y)
        if leg is not None and leg not in board:
            return True
    return False


def _elephant_attack(board: Board, tx: int, ty: int, by_red: bool) -> bool:
    elephant = 'B' if by_red else 'b'
    for dx, dy in ELEPHANT_STEPS:
        sx, sy = tx - dx, ty - dy
        source = square_at(sx, sy)
        if source is None or board.get(source) != elephant:
            continue
        eye = square_at(sx + dx // 2, sy + dy // 2)
        if eye is not None and eye not in board:
            return True
    return False


def _advisor_attack(board: Board, tx: int, ty: int, by_red: bool) -> bool:
    advisor = 'A' if by_red else 'a'
    return any(board.get(square_at(tx - dx, ty - dy)) == advisor for dx, dy in DIAGONAL)


def _pawn_attack(board: Board, tx: int, ty: int, by_red: bool) -> bool:
    pawn = 'P' if by_red else 'p'
    direction = 1 if by_red else -1
    if board.get(square_at(tx, ty - direction)) == pawn:
        return True
    crossed_river = ty >= 5 if by_red else ty <= 4  # a sideways capture keeps the pawn on the target's rank
    return crossed_river and pawn in (board.get(square_at(tx - 1, ty)), board.get(square_at(tx + 1, ty)))


def is_square_attacked(board: Board, target: str, by_red: bool) -> bool:
    """Fast targeted attack test used by the legal-move filter."""
    tx, ty = coords(target)
    return (
        _attacker_on_target(board, target, by_red)
        or _line_attack(board, tx, ty, by_red)
        or _horse_attack(board, tx, ty, by_red)
        or _elephant_attack(board, tx, ty, by_red)
        or _advisor_attack(board, tx, ty, by_red)
        or _pawn_attack(board, tx, ty, by_red)
    )


# --- Attack map (every square each piece of one side attacks, with reasons) ---


def _add_attack(attacks: Attacks, target: str, source: str, reason: str) -> None:
    attacks.setdefault(target, []).append({'square': source, 'reason': reason})


def _chariot_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy in ORTHOGONAL:
        empties: list[str] = []
        blocker = _scan(board, x + dx, y + dy, dx, dy, empties)
        for target in empties:
            _add_attack(attacks, target, source, 'line_attack')
        if blocker is not None:
            _add_attack(attacks, blocker[0], source, 'line_attack')


def _cannon_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy in ORTHOGONAL:
        screen = _scan(board, x + dx, y + dy, dx, dy, None)
        if screen is None:
            continue
        _, sx, sy = screen
        victim = _scan(board, sx + dx, sy + dy, dx, dy, None)
        if victim is not None:
            _add_attack(attacks, victim[0], source, 'cannon_screen')


def _general_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy in ORTHOGONAL:
        target = square_at(x + dx, y + dy)
        if target:
            _add_attack(attacks, target, source, 'general_attack')
    # Flying-general attack is represented as a direct line attack.
    for target, other in board.items():
        if (
            other.upper() == 'K'
            and is_red(other) != red
            and source[0] == target[0]
            and not any(square in board for square in squares_between(source, target))
        ):
            _add_attack(attacks, target, source, 'flying_general')


def _horse_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy, leg_x, leg_y in HORSE_STEPS:
        leg = square_at(x + leg_x, y + leg_y)
        target = square_at(x + dx, y + dy)
        if target and not (leg and leg in board):
            _add_attack(attacks, target, source, 'horse_attack')


def _elephant_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy in ELEPHANT_STEPS:
        eye = square_at(x + dx // 2, y + dy // 2)
        target = square_at(x + dx, y + dy)
        if target and eye not in board:
            _add_attack(attacks, target, source, 'elephant_attack')


def _advisor_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    for dx, dy in DIAGONAL:
        target = square_at(x + dx, y + dy)
        if target:
            _add_attack(attacks, target, source, 'advisor_attack')


def _pawn_attacks(board: Board, source: str, x: int, y: int, red: bool, attacks: Attacks) -> None:
    direction = 1 if red else -1
    for dx, dy in ((0, direction), (-1, 0), (1, 0)):
        target = square_at(x + dx, y + dy)
        if target and (red and y >= 5 or not red and y <= 4 or dx == 0):
            _add_attack(attacks, target, source, 'pawn_attack')


_ATTACKS: dict[str, Callable[[Board, str, int, int, bool, Attacks], None]] = {
    'R': _chariot_attacks,
    'C': _cannon_attacks,
    'K': _general_attacks,
    'N': _horse_attacks,
    'B': _elephant_attacks,
    'A': _advisor_attacks,
    'P': _pawn_attacks,
}


def attacked_squares(board: Board, by_side: str) -> Attacks:
    """Return target squares attacked by *by_side* with deterministic reasons."""
    red = by_side == 'red'
    attacks: Attacks = {}
    for source, piece in board.items():
        if is_red(piece) != red:
            continue
        x, y = coords(source)
        collect = _ATTACKS.get(piece.upper())
        if collect is not None:
            collect(board, source, x, y, red, attacks)
    return attacks


# --- Legal moves ------------------------------------------------------------


def generate_legal_moves(fen: str) -> list[str]:
    """All legal UCCI moves for the side to move; ``[]`` unless both generals are on the board."""
    board = parse_fen(fen)
    if not has_both_generals(board):
        return []
    moving_red = side_to_move(fen) == 'red'
    king_piece = 'K' if moving_red else 'k'
    king_square = next(square for square, occupant in board.items() if occupant == king_piece)
    result: list[str] = []

    for source, piece in sorted(board.items()):
        if is_red(piece) != moving_red:
            continue
        for target in pseudo_legal_targets(board, source, piece):
            next_board = dict(board)
            next_board.pop(source)
            next_board[target] = piece
            next_king_square = target if source == king_square else king_square
            if not is_square_attacked(next_board, next_king_square, not moving_red):
                result.append(f'{source}{target}')

    return result


def apply_legal_move(fen: str, ucci: str) -> str:
    """The FEN after *ucci*, which the caller has already checked is legal.

    The halfmove clock only ever increments; pyffish resets it on a capture, so
    FEN strings differ between the two generators while positions do not.
    """
    parts = fen.strip().split()
    board = parse_fen(fen)
    piece = board.pop(ucci[:2])
    board[ucci[2:]] = piece
    next_side = 'b' if parts[1] == 'w' else 'w'
    halfmove = int(parts[4]) + 1 if len(parts) > 4 else 1
    fullmove = int(parts[5]) if len(parts) > 5 else 1
    if parts[1] == 'b':
        fullmove += 1
    return f'{board_to_fen(board)} {next_side} - - {halfmove} {fullmove}'


class PureMoveGenerator:
    """The default ``MoveGenerator``: standard library only."""

    name = 'pure'

    def legal_moves(self, fen: str) -> list[str]:
        return generate_legal_moves(fen)

    def apply_move(self, fen: str, ucci: str) -> str:
        return apply_legal_move(fen, ucci)


PURE_BACKEND = PureMoveGenerator()
