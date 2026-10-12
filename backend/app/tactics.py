"""Move-by-move tactical motif annotations.

These rules intentionally describe immediate board facts only.  In particular,
they do not ask an engine to score a move, so "妙手" is deliberately absent.
"""
from __future__ import annotations

from .board import FILES, apply_move, attacked_squares, legal_moves, parse_fen, side_to_move

TACTIC_RULES_VERSION = "tactics-draft-0.1"
LABELS = {
    "escape": "逃", "protect": "保", "sacrifice": "弃", "block": "挡",
    "seal": "封锁", "trap": "困", "pin": "牵",
}
PIECE_NAMES = {"R": "车", "C": "炮", "N": "马", "B": "相", "A": "仕", "K": "帅", "P": "兵"}
MATERIAL_VALUES = {"R": 9, "N": 4, "C": 4, "B": 2, "A": 2, "P": 1}
PIN_PIECES = {"R", "N", "C"}


def _other(side: str) -> str:
    return "black" if side == "red" else "red"


def _is_in_check(board: dict[str, str], side: str) -> bool:
    general = next(
        (square for square, piece in board.items()
         if _is_side(piece, side) and piece.upper() == "K"),
        None,
    )
    return bool(general and attacked_squares(board, _other(side)).get(general))


def _is_side(piece: str | None, side: str) -> bool:
    return bool(piece) and (piece.isupper() if side == "red" else piece.islower())


def _is_pin_piece(piece: str | None) -> bool:
    """牵制 is intentionally limited to rook, horse, and cannon material."""
    return bool(piece) and piece.upper() in PIN_PIECES


def _piece_label(board: dict[str, str], square: str) -> str:
    piece = board.get(square, "")
    side = "红" if piece.isupper() else "黑"
    return f"{side}{PIECE_NAMES.get(piece.upper(), '子')} {square}"


def _has_crossed_river(piece: str, square: str, side: str) -> bool:
    if piece.upper() != "P":
        return True
    rank = int(square[1])
    return rank >= 5 if side == "red" else rank <= 4


def _meaningful_attackers(board: dict[str, str], square: str, by_side: str) -> list[dict[str, str]]:
    """Un-crossed pawns do not create an escape annotation."""
    return [
        entry for entry in attacked_squares(board, by_side).get(square, [])
        if _has_crossed_river(board.get(entry["square"], ""), entry["square"], by_side)
    ]


def _sacrifice_eligible(piece: str, square: str, side: str) -> bool:
    """Ordinary sacrifices are limited to rook, horse and cannon."""
    return piece.upper() in {"R", "N", "C"}


def _sacrifice_attackers(board: dict[str, str], square: str, by_side: str) -> list[dict[str, str]]:
    """Attackers relevant to a sacrifice; advisors and elephants are excluded."""
    return [
        entry for entry in attacked_squares(board, by_side).get(square, [])
        if board.get(entry["square"], "").upper() in {"R", "N", "C", "P"}
    ]


def _sacrifice_material_loss(board: dict[str, str], square: str, owner: str) -> int:
    return max(
        (_capture_material_loss(board, square, owner, entry["square"])
         for entry in _sacrifice_attackers(board, square, _other(owner))),
        default=0,
    )


def _minor_for_two_guards_sacrifice(
    before: dict[str, str], after_fen: str, source: str, target: str, side: str,
) -> list[str]:
    """Return guard recaptures in a horse/cannon-for-two-guards sacrifice.

    A horse or cannon taking one advisor/elephant, being taken by the other,
    and then allowing a friendly recapture is strategically a sacrifice.  It
    must not be flattened into an ordinary equal-value exchange merely because
    the last guard can be recaptured.
    """
    if (
        before.get(source, "").upper() not in {"N", "C"}
        or before.get(target, "").upper() not in {"A", "B"}
    ):
        return []
    after = parse_fen(after_fen)
    guard_replies: list[str] = []
    for reply in legal_moves(after_fen):
        if reply[2:] != target or after.get(reply[:2], "").upper() not in {"A", "B"}:
            continue
        after_reply = apply_move(after_fen, reply)
        if any(recapture[2:] == target for recapture in legal_moves(after_reply)):
            guard_replies.append(reply)
    return guard_replies


def _is_crossing_pawn_move(before: dict[str, str], after: dict[str, str], source: str, target: str, side: str) -> bool:
    return (
        before.get(source, "").upper() == "P"
        and after.get(target, "").upper() == "P"
        and not _has_crossed_river(before[source], source, side)
        and _has_crossed_river(after[target], target, side)
    )


def _has_uncrossed_pawn_attacker(board: dict[str, str], square: str, by_side: str) -> bool:
    return any(
        board.get(entry["square"], "").upper() == "P"
        and not _has_crossed_river(board.get(entry["square"], ""), entry["square"], by_side)
        for entry in attacked_squares(board, by_side).get(square, [])
    )


def _direct_escape_attackers(board: dict[str, str], square: str, by_side: str) -> list[dict[str, str]]:
    """Forcing attacks relevant to the tactical "escape" label."""
    result: list[dict[str, str]] = []
    for entry in attacked_squares(board, by_side).get(square, []):
        attacker = entry["square"]
        piece = board.get(attacker, "")
        # Advisor/general pressure is legal, but is not treated as the direct
        # tactical threat required for an escape annotation.  A legal elephant
        # attack does count: its eye has already been checked by attack-map.
        if piece.upper() not in {"R", "C", "N", "B", "P"}:
            continue
        if piece.upper() == "P" and not _has_crossed_river(piece, attacker, by_side):
            continue
        result.append(entry)
    return result


def _piece_value(piece: str, square: str, side: str) -> int:
    if piece.upper() == "P":
        return 2 if _has_crossed_river(piece, square, side) else 1
    return MATERIAL_VALUES.get(piece.upper(), 0)


def _capture_material_loss(board: dict[str, str], victim: str, owner: str, attacker: str) -> int:
    """Owner's net material loss if attacker takes victim and best reply follows."""
    enemy_fen = _fen(board, _other(owner))
    capture = f"{attacker}{victim}"
    if capture not in legal_moves(enemy_fen):
        return 0
    victim_value = _piece_value(board.get(victim, ""), victim, owner)
    after_capture = apply_move(enemy_fen, capture)
    # Any legal immediate recapture wins the attacker back.  The attacker is
    # on victim's square after its capture, so its value is fixed here.
    if any(reply[2:] == victim for reply in legal_moves(after_capture)):
        return victim_value - _piece_value(board.get(attacker, ""), attacker, _other(owner))
    return victim_value


def _escape_material_loss(board: dict[str, str], square: str, owner: str) -> int:
    """Worst net loss among direct attacking exchanges on this piece."""
    return max(
        (_capture_material_loss(board, square, owner, entry["square"])
         for entry in _direct_escape_attackers(board, square, _other(owner))
         if not _is_reciprocal_trade(board, square, entry["square"], owner)),
        default=0,
    )


def _fen(board: dict[str, str], side: str) -> str:
    ranks: list[str] = []
    for rank in range(9, -1, -1):
        empty = 0
        encoded = ""
        for file_name in FILES:
            piece = board.get(f"{file_name}{rank}")
            if piece:
                if empty:
                    encoded += str(empty); empty = 0
                encoded += piece
            else:
                empty += 1
        if empty:
            encoded += str(empty)
        ranks.append(encoded)
    return f"{'/'.join(ranks)} {'w' if side == 'red' else 'b'} - - 0 1"


def _is_reciprocal_trade(board: dict[str, str], victim: str, attacker: str, owner: str) -> bool:
    """Whether the allegedly chased piece can immediately capture its attacker.

    A mutual rook/cannon contact is a兑子 relation, not a one-sided 捉.  This
    is checked before material-loss calculation because the defender can elect
    to take first instead of passively allowing the proposed capture.
    """
    return f"{victim}{attacker}" in legal_moves(_fen(board, owner))


def _ray(board: dict[str, str], source: str, dx: int, dy: int) -> list[str]:
    x, y = FILES.index(source[0]) + dx, int(source[1]) + dy
    squares: list[str] = []
    while 0 <= x < 9 and 0 <= y <= 9:
        square = f"{FILES[x]}{y}"
        squares.append(square)
        if square in board:
            break
        x += dx; y += dy
    return squares


def _rook_blocks(board: dict[str, str], side: str) -> dict[str, tuple[str, int]]:
    """First blocker of each enemy rook ray, keyed by blocker square."""
    result: dict[str, tuple[str, int]] = {}
    rook = "R" if side == "red" else "r"
    for square, piece in board.items():
        if piece != rook:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ray = _ray(board, square, dx, dy)
            if ray and ray[-1] in board:
                result[ray[-1]] = (square, len(ray))
    return result


def _line_piece_blocks(board: dict[str, str], side: str) -> dict[str, tuple[str, int]]:
    """First blocker for each rook/cannon ray, keyed by the blocker square."""
    result: dict[str, tuple[str, int]] = {}
    allowed = {"R", "C"} if side == "red" else {"r", "c"}
    for square, piece in board.items():
        if piece not in allowed:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ray = _ray(board, square, dx, dy)
            if ray and ray[-1] in board:
                result[ray[-1]] = (square, len(ray))
    return result


def _rook_reachable(board: dict[str, str], rook_side: str) -> dict[str, set[str]]:
    """Squares an opponent rook may reach or capture on its four rays."""
    rook = "R" if rook_side == "red" else "r"
    reachable: dict[str, set[str]] = {}
    for source, piece in board.items():
        if piece != rook:
            continue
        targets: set[str] = set()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = FILES.index(source[0]) + dx, int(source[1]) + dy
            while 0 <= x < 9 and 0 <= y <= 9:
                square = f"{FILES[x]}{y}"
                occupant = board.get(square)
                if occupant is None:
                    targets.add(square)
                else:
                    if _is_side(occupant, _other(rook_side)):
                        targets.add(square)
                    break
                x += dx; y += dy
        reachable[source] = targets
    return reachable


def _blocks_rook_route(rook: str, blocker: str, lost: str) -> bool:
    if rook[0] == lost[0] == blocker[0]:
        return min(int(rook[1]), int(lost[1])) < int(blocker[1]) < max(int(rook[1]), int(lost[1]))
    if rook[1] == lost[1] == blocker[1]:
        return min(FILES.index(rook[0]), FILES.index(lost[0])) < FILES.index(blocker[0]) < max(FILES.index(rook[0]), FILES.index(lost[0]))
    return False


def _unsafe_captures(board: dict[str, str], victim: str, owner: str) -> list[str]:
    """Enemy sources that can take victim without an immediate legal recapture."""
    enemy = _other(owner)
    unsafe: list[str] = []
    enemy_fen = _fen(board, enemy)
    for capture in legal_moves(enemy_fen):
        if capture[2:] != victim:
            continue
        after_capture = apply_move(enemy_fen, capture)
        if not any(recapture[2:] == victim for recapture in legal_moves(after_capture)):
            unsafe.append(capture[:2])
    return sorted(unsafe)


def _is_protected(board: dict[str, str], victim: str, owner: str) -> bool:
    """Whether any legal enemy capture of victim can be immediately recaptured."""
    enemy = _other(owner)
    enemy_fen = _fen(board, enemy)
    for capture in legal_moves(enemy_fen):
        if capture[2:] != victim:
            continue
        if any(recapture[2:] == victim for recapture in legal_moves(apply_move(enemy_fen, capture))):
            return True
    return False


def _has_effective_defender(board: dict[str, str], victim: str, owner: str) -> bool:
    """Whether a named friendly piece can legally defend ``victim``.

    Unlike ``_is_protected``, this does not require an enemy attack to exist
    *right now*.  That matters for a rear pin target: the front pinned piece
    can still be blocking the attack line, while another friendly piece is
    already capable of defending the rear target.
    """
    piece = board.get(victim)
    if not _is_side(piece, owner):
        return False
    trial = dict(board)
    trial[victim] = piece.lower() if owner == "red" else piece.upper()
    return any(move[2:] == victim for move in legal_moves(_fen(trial, owner)))


def _has_geometric_defender(board: dict[str, str], victim: str, owner: str) -> bool:
    """A defender remains relevant to a line pin even while its side is checked."""
    return bool(board.get(victim)) and any(
        entry["square"] != victim
        for entry in attacked_squares(board, owner).get(victim, [])
    )


def _piece_protects(board: dict[str, str], protector: str, side: str) -> set[str]:
    """Friendly pieces that this exact piece can legally defend.

    Each friendly candidate is temporarily made an enemy target.  This asks
    whether ``protector`` could take it while preserving its own general.  It
    deliberately does *not* require an enemy attacker to exist already:
    protection is a relationship on the current board, not a label that first
    appears only when an opponent begins a chase.  A lower-value defender does
    not count as a tactical protector for a higher-value target: exchanging it
    still leaves the attacking side ahead.
    """
    result: set[str] = set()
    if not _is_side(board.get(protector), side):
        return result
    for victim, piece in board.items():
        if victim == protector or not _is_side(piece, side) or piece.upper() == "K":
            continue
        if _piece_value(board[protector], protector, side) < _piece_value(piece, victim, side):
            continue
        trial = dict(board)
        trial[victim] = piece.lower() if side == "red" else piece.upper()
        if f"{protector}{victim}" in legal_moves(_fen(trial, side)):
            result.add(victim)
    return result


def _trapped_pieces(board: dict[str, str], side: str) -> set[str]:
    """Pieces of side that have legal moves, but every move loses them at once.

    ``attacked_squares`` is deliberately only a *geometric* screen here: it
    can include a pinned attacker, but it cannot miss a legal capture.  A
    square absent from that map is therefore safe immediately; squares present
    in it still go through ``_unsafe_captures`` for the exact legal
    capture/recapture test.  This keeps tactical classification strict without
    running full legal-move generation for every evidently safe destination.
    """
    positions = _fen(board, side)
    enemy = _other(side)
    enemy_attacks_before = attacked_squares(board, enemy)
    grouped: dict[str, list[str]] = {}
    for move in legal_moves(positions):
        grouped.setdefault(move[:2], []).append(move)
    trapped: set[str] = set()
    for source, moves in grouped.items():
        piece = board.get(source, "")
        # A pawn/soldier before crossing the river is not treated as "困".
        # Its restricted forward movement is part of its normal opening role,
        # rather than a tactical confinement.
        if not _has_crossed_river(piece, source, side):
            continue
        # No geometric enemy attack means no legal enemy capture can protect
        # this piece, so avoid the comparatively costly exact query.
        if source in enemy_attacks_before and _is_protected(board, source, side):
            continue
        unsafe = True
        for move in moves:
            after = apply_move(positions, move)
            after_board = parse_fen(after)
            destination = move[2:]
            # This map is computed once for this candidate position.  It is a
            # conservative pre-filter only; pinned/illegal attackers are
            # rejected by _unsafe_captures below.
            if destination not in attacked_squares(after_board, enemy):
                unsafe = False
                break
            # A capture that can itself be immediately recaptured does not
            # make the destination unsafe: the moved piece remains protected.
            if not _unsafe_captures(after_board, destination, side):
                unsafe = False
                break
        if unsafe:
            trapped.add(source)
    return trapped


def _trap_detail(board: dict[str, str], victim: str, side: str) -> str:
    """Human-readable proof of why every legal move of victim loses it."""
    positions = _fen(board, side)
    options = [move for move in legal_moves(positions) if move[:2] == victim]
    proofs: list[str] = []
    enemy = _other(side)
    for option in options:
        after = apply_move(positions, option)
        after_board = parse_fen(after)
        destination = option[2:]
        # Match the recognizer's two-stage test so the displayed proof cannot
        # claim a capture on a geometrically safe square.
        unsafe_sources = (
            _unsafe_captures(after_board, destination, side)
            if destination in attacked_squares(after_board, enemy)
            else []
        )
        if unsafe_sources:
            source = unsafe_sources[0]
            reply = f"{source}{option[2:]}"
            proofs.append(f"{option} 后 {_piece_label(after_board, source)} 可走 {reply} 吃掉它，且无法被立即回吃")
    return f"{_piece_label(board, victim)} 的合法走法只有 {', '.join(options)}；" + "；".join(proofs) + "。"


def _pins(board: dict[str, str], rook_side: str) -> set[tuple[str, str, str]]:
    """Relative 牵制: a same-line R/N/C rear target must be undefended."""
    rook = "R" if rook_side == "red" else "r"
    enemy = _other(rook_side)
    found: set[tuple[str, str, str]] = set()
    for rook_square, piece in board.items():
        if piece != rook:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = FILES.index(rook_square[0]) + dx, int(rook_square[1]) + dy
            occupied: list[str] = []
            while 0 <= x < 9 and 0 <= y <= 9:
                square = f"{FILES[x]}{y}"
                if square in board:
                    occupied.append(square)
                x += dx; y += dy
            if len(occupied) < 2:
                continue
            first, second = occupied[:2]
            if (
                _is_side(board[first], enemy)
                and _is_side(board[second], enemy)
                and _is_pin_piece(board[rook_square])
                and _is_pin_piece(board[first])
                and _is_pin_piece(board[second])
                and not _has_geometric_defender(board, second, enemy)
            ):
                found.add((rook_square, first, second))
    return found


def _absolute_pins(board: dict[str, str], attacker_side: str) -> set[tuple[str, str, str]]:
    """Find absolute pins whose removal would immediately expose the general.

    Unlike ordinary material pins, the constrained piece may be any enemy
    piece. A rook creates ``rook -> blocker -> general``; a cannon creates
    ``cannon -> screen -> blocker -> general`` so removing the blocker leaves
    exactly one cannon screen. The move is illegal because it exposes check.
    """
    enemy = _other(attacker_side)
    found: set[tuple[str, str, str]] = set()
    for attacker, piece in board.items():
        if not _is_side(piece, attacker_side) or piece.upper() not in {"R", "C"}:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = FILES.index(attacker[0]) + dx, int(attacker[1]) + dy
            occupied: list[str] = []
            while 0 <= x < 9 and 0 <= y <= 9:
                square = f"{FILES[x]}{y}"
                if square in board:
                    occupied.append(square)
                x += dx
                y += dy
            if piece.upper() == "R" and len(occupied) >= 2:
                blocker, general = occupied[:2]
                if (
                    _is_side(board[blocker], enemy)
                    and board[blocker].upper() != "K"
                    and _is_side(board[general], enemy)
                    and board[general].upper() == "K"
                ):
                    found.add((attacker, blocker, general))
            elif piece.upper() == "C" and len(occupied) >= 3:
                _, blocker, general = occupied[:3]
                if (
                    _is_side(board[blocker], enemy)
                    and board[blocker].upper() != "K"
                    and _is_side(board[general], enemy)
                    and board[general].upper() == "K"
                ):
                    found.add((attacker, blocker, general))
    return found


def _protection_pins(board: dict[str, str], side: str) -> set[tuple[str, str, str]]:
    """Rook/cannon protectors constrained by a legal recapture duty."""
    enemy_fen = _fen(board, _other(side))
    found: set[tuple[str, str, str]] = set()
    for capture in legal_moves(enemy_fen):
        victim = capture[2:]
        if not _is_side(board.get(victim), side):
            continue
        after_capture = apply_move(enemy_fen, capture)
        for recapture in legal_moves(after_capture):
            protector = recapture[:2]
            if recapture[2:] != victim or protector == victim:
                continue
            if (
                board.get(protector, "").upper() in {"R", "C"}
                and _is_pin_piece(board.get(victim))
                and _is_pin_piece(board.get(capture[:2]))
            ):
                found.add((protector, victim, capture[:2]))
    return found


def _same_straight_line(*squares: str) -> bool:
    return len({square[0] for square in squares}) == 1 or len({square[1] for square in squares}) == 1


def _pins_created_by(board: dict[str, str], mover_side: str) -> tuple[set[tuple[str, str, str]], set[tuple[str, str, str]]]:
    """Only constraints the mover creates for the opposing side are relevant."""
    # General-facing absolute pins are distinct from ordinary material pins:
    # the blocker may be a pawn, advisor, elephant, etc., because leaving the
    # line exposes an illegal check on the general.
    line_pins = _pins(board, mover_side) | _absolute_pins(board, mover_side)
    # A cross-line protection relationship is not a 牵制.  It is a normal
    # defence relation, even if losing it would cost material.
    return line_pins, set()


def _pin_relationships(line_pins: set[tuple[str, str, str]], protection_pins: set[tuple[str, str, str]]) -> set[tuple[str, str]]:
    """Stable identity of a 牵 relation, independent of pinner movement."""
    return (
        {tuple(sorted((first, second))) for _, first, second in line_pins}
        | {(protector, victim) for protector, victim, _ in protection_pins}
    )


def analyze_tactics(fen: str, moves: list[str]) -> list[dict[str, object]]:
    annotations: list[dict[str, object]] = []
    current = fen
    previous_new_attacks: set[str] = set()
    for ply, move in enumerate(moves, start=1):
        side = side_to_move(current)
        enemy = _other(side)
        before = parse_fen(current)
        was_in_check = _is_in_check(before, side)
        before_enemy_attacks = attacked_squares(before, enemy)
        before_enemy_rook_blocks = _rook_blocks(before, enemy)
        before_enemy_line_blocks = _line_piece_blocks(before, enemy)
        before_traps = _trapped_pieces(before, enemy)
        before_line_pins, before_protection_pins = _pins_created_by(before, side)
        before_pin_relationships = _pin_relationships(before_line_pins, before_protection_pins)
        after_fen = apply_move(current, move)
        after = parse_fen(after_fen)
        moved_to = move[2:]
        occurrences: list[dict[str, object]] = []

        def add(identifier: str, squares: list[str], detail: str) -> None:
            occurrences.append({"id": identifier, "label_zh": LABELS[identifier], "squares": squares, "detail": detail})

        direct_attackers = _direct_escape_attackers(before, move[:2], enemy)
        prior_attacker_squares = {entry["square"] for entry in direct_attackers}
        before_escape_loss = _escape_material_loss(before, move[:2], side)
        after_escape_loss = _escape_material_loss(after, moved_to, side)
        # Imported FENs do not include the preceding move.  Therefore an
        # escape is recognised from the current effective chase itself; the
        # material calculation excludes mutual trades, so merely facing an
        # exchange still cannot manufacture an “escape” label.
        if (direct_attackers
                and before_escape_loss > after_escape_loss
                # Capturing the attacker resolves the threat tactically, but
                # it is not an "escape" move under this feature's definition.
                and moved_to not in prior_attacker_squares):
            add("escape", [move[:2], moved_to], f"{_piece_label(before, move[:2])} 走到 {moved_to}，走前受直接攻击；按最佳立即回吃计算，原交换净亏 {before_escape_loss} 分，走后降为 {after_escape_loss} 分。")

        protected_before = _piece_protects(before, move[:2], side)
        protected_after = _piece_protects(after, moved_to, side)
        # “保” means that the target itself newly gains its first defender.
        # Adding a second defender to a piece that was already protected does
        # not create another protect label.
        already_defended = {
            victim
            for protector, piece in before.items()
            if _is_side(piece, side)
            for victim in _piece_protects(before, protector, side)
        }
        protected = sorted(
            victim for victim in (protected_after - protected_before) - already_defended
            # The target must already be in a materially losing chase before
            # this move.  Opening an unrelated new attack and discovering an
            # old defender is not a “保” move.
            if _escape_material_loss(before, victim, side) > 0
        )
        if protected and not was_in_check:
            add("protect", [moved_to, *protected], f"{_piece_label(after, moved_to)} 走后可在对方吃掉 {', '.join(protected)} 时合法回吃。")

        # A move may uncover another friendly piece's protection, such as
        # moving a cannon away from a horse leg.  This is a new protection
        # relation even though the newly active protector did not move.
        uncovered_protection: list[tuple[str, list[str]]] = []
        for victim, piece in after.items():
            if not _is_side(piece, side) or victim == moved_to:
                continue
            if _escape_material_loss(before, victim, side) <= 0:
                continue
            before_protectors = {
                square for square, candidate in before.items()
                if _is_side(candidate, side) and victim in _piece_protects(before, square, side)
            }
            if before_protectors:
                continue
            newly_available_protectors = sorted(
                square for square, candidate in after.items()
                if _is_side(candidate, side)
                and square != moved_to
                and victim in _piece_protects(after, square, side)
                and square not in before_protectors
            )
            if newly_available_protectors:
                uncovered_protection.append((victim, newly_available_protectors))
        if not was_in_check:
            for victim, protectors in uncovered_protection:
                add("protect", [moved_to, victim, *protectors], f"本手让开后，{', '.join(protectors)} 才能在对方吃掉 {victim} 时合法回吃；{victim} 因此新获得保护。")

        unsafe_capturers = _unsafe_captures(after, moved_to, side)
        sacrifice_capturers = [entry["square"] for entry in _sacrifice_attackers(after, moved_to, enemy)]
        sacrifice_loss = _sacrifice_material_loss(after, moved_to, side)
        guard_recaptures = _minor_for_two_guards_sacrifice(before, after_fen, move[:2], moved_to, side)
        crossing_pawn = _is_crossing_pawn_move(before, after, move[:2], moved_to, side)
        if guard_recaptures:
            add("sacrifice", [move[:2], moved_to, *[reply[:2] for reply in guard_recaptures]], f"{_piece_label(before, move[:2])} 吃掉 {_piece_label(before, moved_to)} 后，另一枚士／象可用 {', '.join(guard_recaptures)} 回吃；即使己方随后还能回吃，马／炮换双士／双象仍按弃子处理。")
        elif crossing_pawn and sacrifice_capturers:
            add("sacrifice", [moved_to, *sacrifice_capturers], f"兵／卒本手越过河界后立即受到 {', '.join(sacrifice_capturers)} 攻击，构成弃兵。")
        elif sacrifice_loss > 0 and _sacrifice_eligible(after.get(moved_to, ""), moved_to, side):
            add("sacrifice", [moved_to, *sacrifice_capturers], f"本手走到 {moved_to} 后，对方 {', '.join(sacrifice_capturers)} 可吃掉该子；按立即回吃计算，己方净亏 {sacrifice_loss} 分。")

        # A forced check response can consciously leave another major/minor
        # piece to be taken.  It is not ordinary “protect” or “block”: the
        # move's primary purpose is saving the general, and the abandoned
        # piece is the resulting sacrifice.
        if was_in_check:
            forced_abandoned = [
                (square, capturers)
                for square, piece in after.items()
                if square != moved_to and _is_side(piece, side)
                and _sacrifice_eligible(piece, square, side)
                and (capturers := _unsafe_captures(after, square, side))
            ]
            for square, capturers in forced_abandoned:
                add("sacrifice", [square, *capturers], f"本手为保护将／帅而应将，留下 {_piece_label(after, square)} 可被 {', '.join(capturers)} 安全吃掉，构成弃子。")

        # A move can also abandon a *different* friendly piece by opening a
        # new, safe enemy capture on it.  This is distinct from the moved
        # piece's active sacrifice and gets its own concrete explanation.
        newly_exposed = []
        for square, piece in after.items():
            if square == moved_to or not _is_side(piece, side):
                continue
            capturers = _unsafe_captures(after, square, side)
            previous_capturers = _unsafe_captures(before, square, side) if square in before else []
            new_capturers = sorted(set(capturers) - set(previous_capturers))
            if new_capturers and _sacrifice_eligible(piece, square, side):
                newly_exposed.append((square, new_capturers))
        for square, capturers in newly_exposed:
            add("sacrifice", [square, *capturers], f"本手 {move} 新打开了对 {square} 的攻击；对方 {', '.join(capturers)} 可安全吃掉 {_piece_label(after, square)}，己方无法立即回吃。")

        # The previous opponent move is the only event that may create a newly
        # abandoned target, which naturally prevents repeated labels.
        abandoned = sorted(
            square for square in previous_new_attacks
            if square in after and square != move[:2]
            and square not in protected_after
            and _sacrifice_eligible(after[square], square, side)
            and _escape_material_loss(after, square, side) > 0
        )
        if abandoned:
            losses = {square: _escape_material_loss(after, square, side) for square in abandoned}
            # The defender gets one reply only.  Several pieces may be under
            # attack, but the immediate outcome is the single largest loss,
            # never the sum of every simultaneously threatened piece.
            most_valuable = min(square for square, loss in losses.items() if loss == max(losses.values()))
            attackers = sorted(entry["square"] for entry in _direct_escape_attackers(after, most_valuable, enemy))
            add("sacrifice", [most_valuable, *attackers], f"上一手后 {most_valuable} 刚受到 {', '.join(attackers)} 攻击；本手 {move} 未化解。双方本回合只能应对一子，预期最大净亏 {losses[most_valuable]} 分。")

        before_rook_routes = _rook_reachable(before, enemy)
        after_rook_routes = _rook_reachable(after, enemy)
        for rook, before_targets in before_rook_routes.items():
            if was_in_check:
                continue
            # A blocker that can be safely captured is a sacrifice, not a
            # durable route block.
            if unsafe_capturers:
                continue
            # The existing first blocker moving closer is a seal, not a new
            # block.  A block must be a different piece entering the route.
            if before_enemy_rook_blocks.get(move[:2], (None, 0))[0] == rook:
                continue
            lost_targets = before_targets - after_rook_routes.get(rook, set())
            blocked_targets = sorted(target for target in lost_targets if _blocks_rook_route(rook, moved_to, target))
            if blocked_targets:
                add("block", [rook, moved_to, *blocked_targets], f"{_piece_label(after, moved_to)} 落在 {rook} 的线路上，使该车无法再到达 {', '.join(blocked_targets)}。")
                break

        for rook_square, ray_distance in _rook_blocks(after, enemy).items():
            if was_in_check:
                continue
            # Keep the legacy "first obstruction" branch consistent with the
            # route-difference branch above: a piece the rook can safely take
            # is a sacrifice, rather than a lasting block.
            if unsafe_capturers:
                break
            if any(item["id"] == "block" for item in occurrences):
                break
            if rook_square != moved_to:
                continue
            rook = ray_distance[0]
            before_ray = _ray(
                before, rook,
                (FILES.index(moved_to[0]) > FILES.index(rook[0])) - (FILES.index(moved_to[0]) < FILES.index(rook[0])),
                (int(moved_to[1]) > int(rook[1])) - (int(moved_to[1]) < int(rook[1])),
            )
            dx = (FILES.index(moved_to[0]) > FILES.index(rook[0])) - (FILES.index(moved_to[0]) < FILES.index(rook[0]))
            dy = (int(moved_to[1]) > int(rook[1])) - (int(moved_to[1]) < int(rook[1]))
            # A capturable piece on the final edge still leaves the rook's
            # whole ray available.  Moving it inward is the first block.
            source_is_edge = not _ray(before, move[:2], dx, dy)
            if before_ray and before_ray[-1] == move[:2] and source_is_edge:
                add("block", [ray_distance[0], moved_to], "将原本全线通行的车路首次截断。")

        after_enemy_line_blocks = _line_piece_blocks(after, enemy)
        if move[:2] in before_enemy_line_blocks and moved_to in after_enemy_line_blocks:
            line_piece, old_distance = before_enemy_line_blocks[move[:2]]
            new_line_piece, new_distance = after_enemy_line_blocks[moved_to]
            if line_piece == new_line_piece and new_distance < old_distance:
                add("seal", [line_piece, move[:2], moved_to], f"在已受限的 {_piece_label(after, line_piece)} 线路上向其逼近，使其活动范围继续缩小。")

        newly_trapped = sorted(_trapped_pieces(after, enemy) - before_traps)
        if newly_trapped:
            add("trap", newly_trapped, " ".join(_trap_detail(after, square, enemy) for square in newly_trapped))

        line_pins, protection_pins = _pins_created_by(after, side)
        for rook, first, second in sorted(line_pins | protection_pins):
            relation = _pin_relationships(
                {(rook, first, second)} if (rook, first, second) in line_pins else set(),
                {(rook, first, second)} if (rook, first, second) in protection_pins else set(),
            )
            if relation & before_pin_relationships:
                continue
            if after.get(second, "").upper() == "K":
                add("pin", [rook, first, second], f"绝对牵制：{_piece_label(after, first)} 一旦离开 {rook} 与将／帅 {second} 的线路，就会直接暴露将军；因此该离线走法不合法。")
            elif (rook, first, second) in line_pins:
                add("pin", [rook, first, second], f"{_piece_label(after, rook)} 与 {_piece_label(after, first)}、{_piece_label(after, second)} 同线；两枚后方敌子任一离线，另一枚会被车直接吃到。")
            else:
                add("pin", [rook, first, second], f"{_piece_label(after, rook)} 是 {_piece_label(after, first)} 的回吃保护；若 {_piece_label(after, second)} 吃掉 {first}，它可回吃，因此 {rook} 受这条线约束。")

        annotations.append({"ply": ply, "side": side, "ucci": move, "occurrences": occurrences})

        # New attacks formed by this move are only eligible for the opposing
        # player's immediately following move.
        next_side = _other(side)
        previous_new_attacks = {
            square for square, piece in after.items()
            if _is_side(piece, next_side)
            and _sacrifice_eligible(piece, square, next_side)
            and _escape_material_loss(after, square, next_side) > 0
            and _escape_material_loss(before, square, next_side) <= 0
        }
        current = after_fen
    return annotations
