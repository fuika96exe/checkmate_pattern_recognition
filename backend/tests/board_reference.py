"""Pre-split reference for the board's attack and move geometry (differential-test oracle).

A verbatim copy of ``pseudo_legal_targets``, ``is_square_attacked`` and
``attacked_squares`` as they were moved from the lab into ``xq_classify.board.pure``
(phase 0 step 2a), before they were split to cognitive complexity
<= 15. ``test_board_reference.py`` checks that the split versions return exactly
the same results, in the same order, on random boards. Do not edit these
functions; if the board's behaviour is meant to change, change the test instead.
"""

from xq_classify.board.geometry import coords, inside_palace, is_red, square_at, squares_between

def pseudo_legal_targets(board: dict[str, str], source: str, piece: str) -> list[str]:
    """Generate Xiangqi moves before filtering moves that expose the general."""
    x, y = coords(source)
    red = is_red(piece)
    kind = piece.upper()
    targets: list[str] = []

    def add_if_open(target: str | None) -> None:
        if target is None:
            return
        occupant = board.get(target)
        if occupant is None or is_red(occupant) != red:
            targets.append(target)

    if kind in {'R', 'C'}:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cx, cy = x + dx, y + dy
            screen_seen = False
            while (target := square_at(cx, cy)) is not None:
                occupant = board.get(target)
                if kind == 'R':
                    if occupant is None:
                        targets.append(target)
                    else:
                        if is_red(occupant) != red:
                            targets.append(target)
                        break
                elif not screen_seen:
                    if occupant is None:
                        targets.append(target)
                    else:
                        screen_seen = True
                elif occupant is not None:
                    if is_red(occupant) != red:
                        targets.append(target)
                    break
                cx, cy = cx + dx, cy + dy
        return targets

    if kind == 'N':
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
            leg = square_at(x + leg_x, y + leg_y)
            if leg is not None and leg not in board:
                add_if_open(square_at(x + dx, y + dy))
        return targets

    if kind == 'B':
        for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            eye = square_at(x + dx // 2, y + dy // 2)
            target = square_at(x + dx, y + dy)
            if target is None or eye is None or eye in board:
                continue
            target_rank = int(target[1])
            if (red and target_rank <= 4) or (not red and target_rank >= 5):
                add_if_open(target)
        return targets

    if kind == 'A':
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            target = square_at(x + dx, y + dy)
            if target is not None and inside_palace(x + dx, y + dy, red):
                add_if_open(target)
        return targets

    if kind == 'K':
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            target = square_at(x + dx, y + dy)
            if target is not None and inside_palace(x + dx, y + dy, red):
                add_if_open(target)

        for direction in (-1, 1):
            cy = y + direction
            while (target := square_at(x, cy)) is not None:
                occupant = board.get(target)
                if occupant is not None:
                    if occupant.upper() == 'K' and is_red(occupant) != red:
                        targets.append(target)
                    break
                cy += direction
        return targets

    if kind == 'P':
        direction = 1 if red else -1
        add_if_open(square_at(x, y + direction))
        crossed_river = y >= 5 if red else y <= 4
        if crossed_river:
            add_if_open(square_at(x - 1, y))
            add_if_open(square_at(x + 1, y))
        return targets

    return targets


def is_square_attacked(board: dict[str, str], target: str, by_red: bool) -> bool:
    """Fast targeted attack test used by the legal-move filter."""
    tx, ty = coords(target)
    for source, piece in board.items():
        if is_red(piece) != by_red:
            continue

        sx, sy = coords(source)
        dx, dy = tx - sx, ty - sy
        abs_dx, abs_dy = abs(dx), abs(dy)
        kind = piece.upper()

        if kind == 'R':
            if (dx == 0 or dy == 0) and not any(square in board for square in squares_between(source, target)):
                return True
        elif kind == 'C':
            if (dx == 0 or dy == 0) and sum(square in board for square in squares_between(source, target)) == 1:
                return True
        elif kind == 'K':
            if abs_dx + abs_dy == 1:
                return True
            if dx == 0 and not any(square in board for square in squares_between(source, target)):
                return True
        elif kind == 'N' and sorted((abs_dx, abs_dy)) == [1, 2]:
            if abs_dx == 2:
                leg = square_at(sx + (1 if dx > 0 else -1), sy)
            else:
                leg = square_at(sx, sy + (1 if dy > 0 else -1))
            if leg is not None and leg not in board:
                return True
        elif kind == 'B' and abs_dx == 2 and abs_dy == 2:
            eye = square_at(sx + dx // 2, sy + dy // 2)
            if eye is not None and eye not in board:
                return True
        elif kind == 'A' and abs_dx == 1 and abs_dy == 1:
            return True
        elif kind == 'P':
            direction = 1 if by_red else -1
            if dx == 0 and dy == direction:
                return True
            crossed_river = sy >= 5 if by_red else sy <= 4
            if crossed_river and dy == 0 and abs_dx == 1:
                return True

    return False


def attacked_squares(board: dict[str, str], by_side: str) -> dict[str, list[dict[str, str]]]:
    """Return target squares attacked by *by_side* with deterministic reasons."""
    red = by_side == 'red'
    attacks: dict[str, list[dict[str, str]]] = {}

    def add(target: str, source: str, reason: str) -> None:
        attacks.setdefault(target, []).append({'square': source, 'reason': reason})

    for source, piece in board.items():
        if is_red(piece) != red:
            continue
        x, y = coords(source)
        kind = piece.upper()
        if kind in {'R', 'C'}:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cx, cy = x + dx, y + dy
                screens = 0
                while (target := square_at(cx, cy)) is not None:
                    occupant = board.get(target)
                    if kind == 'C':
                        if screens == 1 and occupant is not None:
                            add(target, source, 'cannon_screen')
                            break
                        if occupant is not None:
                            screens += 1
                    else:
                        if screens == 0:
                            add(target, source, 'line_attack')
                        if occupant is not None:
                            break
                    cx, cy = cx + dx, cy + dy
        if kind == 'K':
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                target = square_at(x + dx, y + dy)
                if target:
                    add(target, source, 'general_attack')
            # Flying-general attack is represented as a direct line attack.
            for target, other in board.items():
                if (
                    other.upper() == 'K'
                    and is_red(other) != red
                    and source[0] == target[0]
                    and not any(square in board for square in squares_between(source, target))
                ):
                    add(target, source, 'flying_general')
        elif kind == 'N':
            for dx, dy, lx, ly in (
                (1, 2, 0, 1), (-1, 2, 0, 1), (1, -2, 0, -1), (-1, -2, 0, -1),
                (2, 1, 1, 0), (2, -1, 1, 0), (-2, 1, -1, 0), (-2, -1, -1, 0),
            ):
                leg = square_at(x + lx, y + ly)
                target = square_at(x + dx, y + dy)
                if target and not (leg and leg in board):
                    add(target, source, 'horse_attack')
        elif kind == 'B':
            for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
                eye = square_at(x + dx // 2, y + dy // 2)
                target = square_at(x + dx, y + dy)
                if target and eye not in board:
                    add(target, source, 'elephant_attack')
        elif kind == 'A':
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                target = square_at(x + dx, y + dy)
                if target:
                    add(target, source, 'advisor_attack')
        elif kind == 'P':
            direction = 1 if red else -1
            for dx, dy in ((0, direction), (-1, 0), (1, 0)):
                target = square_at(x + dx, y + dy)
                if target and (red and y >= 5 or not red and y <= 4 or dx == 0):
                    add(target, source, 'pawn_attack')
    return attacks
