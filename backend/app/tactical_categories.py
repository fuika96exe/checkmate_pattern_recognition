"""Auditable, short-horizon recognizer for the nine user-facing tactics.

The rules intentionally favour evidence over guesses.  Every occurrence names
the squares that caused it, so a player can challenge and refine a rule in the
lab instead of treating the label as an engine evaluation.
"""
from __future__ import annotations

from .board import FILES, apply_move, attacked_squares, legal_moves, parse_fen, side_to_move

CATEGORY_RULES_VERSION = "nine-tactics-draft-0.9"
LABELS = {
    "exchange": "交换", "fork": "捉双", "skewer": "串打",
    "discovered_attack": "闪击", "remove_defender": "消除保护",
    "trap": "围困", "pin": "牵制", "cannon_pawn_breakthrough": "炮兵突破",
}
PIECE_NAMES = {"R": "车", "C": "炮", "N": "马", "B": "相", "A": "仕", "K": "帅", "P": "兵"}
MATERIAL_VALUES = {"R": 9, "N": 4, "C": 4, "B": 2, "A": 2, "P": 1}
PIN_PIECES = {"R", "N", "C"}


# These are deliberately local rule primitives.  The categories tab and the
# move-purpose tab share only objective board operations (legal moves, attack
# maps and FEN parsing); changing either tab's tactical policy must not silently
# change the other one.
def _other(side: str) -> str:
    return "black" if side == "red" else "red"


def _is_side(piece: str | None, side: str) -> bool:
    return bool(piece) and (piece.isupper() if side == "red" else piece.islower())


def _fen(board: dict[str, str], side: str) -> str:
    ranks: list[str] = []
    for rank in range(9, -1, -1):
        empty = 0
        encoded = ""
        for file_name in FILES:
            piece = board.get(f"{file_name}{rank}")
            if piece:
                if empty:
                    encoded += str(empty)
                    empty = 0
                encoded += piece
            else:
                empty += 1
        if empty:
            encoded += str(empty)
        ranks.append(encoded)
    return f"{'/'.join(ranks)} {'w' if side == 'red' else 'b'} - - 0 1"


def _piece_label(board: dict[str, str], square: str) -> str:
    piece = board.get(square, "")
    side = "红" if piece.isupper() else "黑"
    return f"{side}{PIECE_NAMES.get(piece.upper(), '子')} {square}"


def _has_crossed_river(piece: str, square: str, side: str) -> bool:
    if piece.upper() != "P":
        return True
    rank = int(square[1])
    return rank >= 5 if side == "red" else rank <= 4


def _piece_value(piece: str, square: str, side: str) -> int:
    if piece.upper() == "P":
        return 2 if _has_crossed_river(piece, square, side) else 1
    return MATERIAL_VALUES.get(piece.upper(), 0)


def _is_chase_target(board: dict[str, str], square: str, owner: str) -> bool:
    """Uncrossed pawns/soldiers are not tactical chase targets."""
    piece = board.get(square, "")
    return piece.upper() != "P" or _has_crossed_river(piece, square, owner)


def _unsafe_captures(board: dict[str, str], victim: str, owner: str) -> list[str]:
    """Enemy sources that can take victim without an immediate legal recapture."""
    enemy_fen = _fen(board, _other(owner))
    unsafe: list[str] = []
    for capture in legal_moves(enemy_fen):
        if capture[2:] != victim:
            continue
        after_capture = apply_move(enemy_fen, capture)
        if not any(reply[2:] == victim for reply in legal_moves(after_capture)):
            unsafe.append(capture[:2])
    return sorted(unsafe)


def _forcing_trap_capture(board: dict[str, str], victim: str, owner: str) -> bool:
    """Whether an enemy capture makes this destination tactically losing.

    A protected rook is still chased by a horse or cannon: even after the
    recapture, exchanging a 4-point minor for a 9-point rook wins material.
    Other targets retain the stricter immediate-recapture rule.
    """
    target = board.get(victim, "")
    enemy_fen = _fen(board, _other(owner))
    unsafe_sources = set(_unsafe_captures(board, victim, owner))
    for capture in legal_moves(enemy_fen):
        if capture[2:] != victim:
            continue
        attacker = board.get(capture[:2], "").upper()
        if capture[:2] in unsafe_sources or (target.upper() == "R" and attacker in {"N", "C"}):
            return True
    return False


def _is_minor_for_two_guards_sacrifice(
    before: dict[str, str], after_fen: str, source: str, target: str,
) -> bool:
    """Horse/cannon for both advisors or elephants is a sacrifice, not 交换."""
    if (
        before.get(source, "").upper() not in {"N", "C"}
        or before.get(target, "").upper() not in {"A", "B"}
    ):
        return False
    after = parse_fen(after_fen)
    for reply in legal_moves(after_fen):
        if reply[2:] != target or after.get(reply[:2], "").upper() not in {"A", "B"}:
            continue
        after_reply = apply_move(after_fen, reply)
        if any(recapture[2:] == target for recapture in legal_moves(after_reply)):
            return True
    return False


def _is_protected(board: dict[str, str], victim: str, owner: str) -> bool:
    enemy_fen = _fen(board, _other(owner))
    for capture in legal_moves(enemy_fen):
        if capture[2:] == victim and any(reply[2:] == victim for reply in legal_moves(apply_move(enemy_fen, capture))):
            return True
    return False


def _has_effective_defender(board: dict[str, str], victim: str, owner: str) -> bool:
    """Category-local defence check, including targets blocked by the pin."""
    piece = board.get(victim)
    if not _is_side(piece, owner):
        return False
    trial = dict(board)
    trial[victim] = piece.lower() if owner == "red" else piece.upper()
    return any(move[2:] == victim for move in legal_moves(_fen(trial, owner)))


def _has_geometric_defender(board: dict[str, str], victim: str, owner: str) -> bool:
    """Whether a friendly piece geometrically covers ``victim``.

    A line relation is described from the defender's point of view, even if
    the side is currently in check and therefore cannot play that defensive
    move *this turn*.  Requiring a legal reply in that situation would erase a
    real defender and manufacture a false pin or skewer.
    """
    return bool(board.get(victim)) and any(
        entry["square"] != victim
        for entry in attacked_squares(board, owner).get(victim, [])
    )


def _trapped_pieces(board: dict[str, str], side: str) -> set[str]:
    """Category-local definition of 困: every legal exit loses immediately.

    A side in check has a temporary whole-board restriction: it must answer
    the check, so most otherwise available piece moves disappear from the
    legal-move list.  That is not a local 围困 of any individual piece.
    """
    position = _fen(board, side)
    enemy = _other(side)
    if _gives_check(board, enemy):
        return set()
    enemy_attacks = attacked_squares(board, enemy)
    grouped: dict[str, list[str]] = {}
    for move in legal_moves(position):
        grouped.setdefault(move[:2], []).append(move)
    trapped: set[str] = set()
    for source, moves in grouped.items():
        if not _has_crossed_river(board.get(source, ""), source, side):
            continue
        if source in enemy_attacks and _is_protected(board, source, side) and not _forcing_trap_capture(board, source, side):
            continue
        for move in moves:
            after = apply_move(position, move)
            after_board = parse_fen(after)
            destination = move[2:]
            if destination not in attacked_squares(after_board, enemy) or not _forcing_trap_capture(after_board, destination, side):
                break
        else:
            trapped.add(source)
    return trapped


def _is_pin_piece(piece: str | None) -> bool:
    return bool(piece) and piece.upper() in PIN_PIECES


def _pins(board: dict[str, str], attacker_side: str) -> set[tuple[str, str, str]]:
    """Relative pins: same-line R/N/C relations with an undefended rear."""
    rook = "R" if attacker_side == "red" else "r"
    enemy = _other(attacker_side)
    found: set[tuple[str, str, str]] = set()
    for attacker, piece in board.items():
        if piece != rook:
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
            if len(occupied) >= 2:
                first, second = occupied[:2]
                if (_is_side(board[first], enemy) and _is_side(board[second], enemy)
                    and _is_pin_piece(board[attacker]) and _is_pin_piece(board[first]) and _is_pin_piece(board[second])
                    and not _has_geometric_defender(board, second, enemy)):
                    found.add((attacker, first, second))
    return found


def _absolute_pins(board: dict[str, str], attacker_side: str) -> set[tuple[str, str, str]]:
    """Absolute pins to the general; the blocker may be any piece type."""
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
            required = 2 if piece.upper() == "R" else 3
            if len(occupied) < required:
                continue
            blocker, general = (occupied[0], occupied[1]) if piece.upper() == "R" else (occupied[1], occupied[2])
            # A rook on the opponent's back rank facing an advisor/elephant
            # before the general is ordinary baseline pressure, not the
            # tactical 牵制 label used by players.
            baseline_rook_vs_guard = (
                piece.upper() == "R"
                and attacker[1] == general[1]
                and attacker[1] in {"0", "9"}
                and board[blocker].upper() in {"A", "B"}
            )
            if (_is_side(board[blocker], enemy) and board[blocker].upper() in PIN_PIECES
                and _is_side(board[general], enemy) and board[general].upper() == "K"):
                if not baseline_rook_vs_guard:
                    found.add((attacker, blocker, general))
    return found


def _protection_pins(board: dict[str, str], side: str) -> set[tuple[str, str, str]]:
    enemy_fen = _fen(board, _other(side))
    found: set[tuple[str, str, str]] = set()
    for capture in legal_moves(enemy_fen):
        victim = capture[2:]
        if not _is_side(board.get(victim), side):
            continue
        after_capture = apply_move(enemy_fen, capture)
        for recapture in legal_moves(after_capture):
            protector = recapture[:2]
            if recapture[2:] == victim and protector != victim and board.get(protector, "").upper() in {"R", "C"} and _is_pin_piece(board.get(victim)) and _is_pin_piece(board.get(capture[:2])):
                found.add((protector, victim, capture[:2]))
    return found


def _same_straight_line(*squares: str) -> bool:
    return len({square[0] for square in squares}) == 1 or len({square[1] for square in squares}) == 1


def _pins_created_by(board: dict[str, str], mover_side: str) -> tuple[set[tuple[str, str, str]], set[tuple[str, str, str]]]:
    line_pins = _pins(board, mover_side) | _absolute_pins(board, mover_side)
    # Cross-line protection is defence, not a pin relation.
    return line_pins, set()


def _pin_relationships(line_pins: set[tuple[str, str, str]], protection_pins: set[tuple[str, str, str]]) -> set[tuple[str, str]]:
    return {tuple(sorted((first, second))) for _, first, second in line_pins} | {(protector, victim) for protector, victim, _ in protection_pins}


def _captures(fen: str, side: str | None = None) -> list[str]:
    """Legal captures for ``side`` (or the FEN's current side)."""
    board = parse_fen(fen)
    if side is not None and side != side_to_move(fen):
        fen = _fen(board, side)
        board = parse_fen(fen)
    return [move for move in legal_moves(fen) if move[2:] in board and not _is_side(board[move[2:]], side_to_move(fen))]


def _new_captures(before: dict[str, str], after_fen: str, side: str) -> list[str]:
    before_moves = set(_captures(_fen(before, side)))
    return sorted(set(_captures(after_fen, side)) - before_moves)


def _is_safe_capture(fen: str, capture: str, side: str) -> bool:
    """Whether this exact capture cannot be immediately legally recaptured."""
    position = _fen(parse_fen(fen), side)
    if capture not in legal_moves(position):
        return False
    after_capture = apply_move(position, capture)
    return not any(reply[2:] == capture[2:] for reply in legal_moves(after_capture))


def _is_unanswerable_flash_capture(board: dict[str, str], capture: str, side: str) -> bool:
    """Whether a newly opened capture is a concrete gain rather than a trade.

    A flash attack must survive the opponent's immediate answer.  Keep the
    legal-recapture check, then conservatively reject a target square still
    covered by an enemy line or piece after the virtual capture.  This avoids
    promoting mutually protected rook/cannon contact into a 闪击 label.
    """
    position = _fen(board, side)
    if not _is_safe_capture(position, capture, side):
        return False
    # If the newly attacked piece can immediately take the newly active
    # attacker, the contact is a mutual exchange.  It is not a forcing flash
    # attack even though the attacker would have a capture on the next turn.
    enemy_position = _fen(board, _other(side))
    if f"{capture[2:]}{capture[:2]}" in legal_moves(enemy_position):
        return False
    after_capture = parse_fen(apply_move(position, capture))
    return not bool(attacked_squares(after_capture, _other(side)).get(capture[2:]))


def _general_square(board: dict[str, str], side: str) -> str | None:
    return next(
        (square for square, piece in board.items() if _is_side(piece, side) and piece.upper() == "K"),
        None,
    )


def _new_check_by_piece(
    before: dict[str, str], after: dict[str, str], side: str, piece_kind: str,
) -> str | None:
    """Return a newly checking friendly piece of the requested kind."""
    general = _general_square(after, _other(side))
    if not general:
        return None
    after_attackers = [
        entry["square"]
        for entry in attacked_squares(after, side).get(general, [])
        if after.get(entry["square"], "").upper() == piece_kind
    ]
    before_attackers = {
        entry["square"]
        for entry in attacked_squares(before, side).get(general, [])
        if before.get(entry["square"], "").upper() == piece_kind
    }
    return next((square for square in after_attackers if square not in before_attackers), None)


def _horse_leg(horse: str, destination: str) -> str | None:
    """Return the horse-leg square for a legal horse-shaped attack."""
    file_delta = ord(destination[0]) - ord(horse[0])
    rank_delta = int(destination[1]) - int(horse[1])
    if (abs(file_delta), abs(rank_delta)) not in {(1, 2), (2, 1)}:
        return None
    if abs(file_delta) == 2:
        return f"{chr(ord(horse[0]) + (1 if file_delta > 0 else -1))}{horse[1]}"
    return f"{horse[0]}{int(horse[1]) + (1 if rank_delta > 0 else -1)}"


def _is_unprotected_major_target(board: dict[str, str], square: str, owner: str) -> bool:
    """A flash target is an enemy rook, horse, or cannon without cover."""
    return (
        board.get(square, "").upper() in {"R", "N", "C"}
        and not _has_geometric_defender(board, square, owner)
    )


def _same_kind_can_capture_attacker(
    board: dict[str, str], attacker: str, victim: str, owner: str,
) -> bool:
    """Whether an attacked equal major piece can immediately take its attacker."""
    attacker_piece = board.get(attacker, "").upper()
    victim_piece = board.get(victim, "").upper()
    return (
        attacker_piece in {"R", "N", "C"}
        and attacker_piece == victim_piece
        and f"{victim}{attacker}" in legal_moves(_fen(board, _other(owner)))
    )


def _can_directly_capture(board: dict[str, str], square: str, owner: str) -> bool:
    """Whether the opponent has a legal immediate capture of this square."""
    return any(move[2:] == square for move in legal_moves(_fen(board, _other(owner))))


def _gives_check(board: dict[str, str], side: str) -> bool:
    enemy_general = next(
        (square for square, piece in board.items()
         if _is_side(piece, _other(side)) and piece.upper() == "K"),
        None,
    )
    return bool(enemy_general and attacked_squares(board, side).get(enemy_general))


def _breakthrough_gain(position: str, cannon_capture: str, side: str) -> bool:
    """A breakthrough wins an undefended piece, or trades a cannon for a rook."""
    board = parse_fen(position)
    target = board.get(cannon_capture[2:], "")
    if target.upper() == "K" or not _is_side(target, _other(side)):
        return False
    return target.upper() == "R" or _is_safe_capture(position, cannon_capture, side)


def _pawn_sacrifice_breakthrough(board: dict[str, str], pawn_move: str, side: str, cannon_square: str | None = None) -> tuple[str, str] | None:
    """Find the cannon gain after an enemy capture of an uncrossed pawn."""
    pawn_source, pawn_target = pawn_move[:2], pawn_move[2:]
    if board.get(pawn_source, "").upper() != "P" or _has_crossed_river(board[pawn_source], pawn_source, side):
        return None
    pawn_position = _fen(board, side)
    if pawn_move not in legal_moves(pawn_position):
        return None
    after_pawn = apply_move(pawn_position, pawn_move)
    pawn_replies = [
        reply for reply in legal_moves(after_pawn)
        if reply[2:] == pawn_target and parse_fen(after_pawn).get(reply[:2], "").upper() == "P"
    ]
    # 炮兵突破以兵卒相见、对方只能以兵卒吃兵为前提；若车、马、炮等
    # 也能吃该兵，便不是这种特定的弃兵破屏障手段。
    if not pawn_replies or any(
        reply[2:] == pawn_target and parse_fen(after_pawn).get(reply[:2], "").upper() != "P"
        for reply in legal_moves(after_pawn)
    ):
        return None
    for reply in pawn_replies:
        after_reply = apply_move(after_pawn, reply)
        reply_board = parse_fen(after_reply)
        for cannon_capture in legal_moves(after_reply):
            cannon = cannon_capture[:2]
            if (cannon_square is not None and cannon != cannon_square) or reply_board.get(cannon, "").upper() != "C":
                continue
            if _breakthrough_gain(after_reply, cannon_capture, side):
                return reply, cannon_capture
    return None


def _pawn_breakthrough_check(board: dict[str, str], pawn_target: str, side: str) -> str | None:
    """A pawn screen is a breakthrough when its capture would expose check."""
    enemy = _other(side)
    pseudo_pawn_capturers = [
        entry["square"] for entry in attacked_squares(board, enemy).get(pawn_target, [])
        if board.get(entry["square"], "").upper() == "P"
    ]
    if not pseudo_pawn_capturers or any(move[2:] == pawn_target for move in legal_moves(_fen(board, enemy))):
        return None
    enemy_general = next((square for square, piece in board.items() if _is_side(piece, enemy) and piece.upper() == "K"), None)
    if not enemy_general:
        return None
    for capturer in pseudo_pawn_capturers:
        # Build the geometrically possible pawn capture without requiring it
        # to be legal; legality is exactly what this rule is explaining.
        virtual = dict(board)
        pawn = virtual.pop(capturer)
        virtual[pawn_target] = pawn
        cannon_attackers = [
            entry["square"] for entry in attacked_squares(virtual, side).get(enemy_general, [])
            if virtual.get(entry["square"], "").upper() == "C"
        ]
        if cannon_attackers:
            return cannon_attackers[0]
    return None


def _defense_relations(board: dict[str, str], side: str) -> set[tuple[str, str]]:
    """Return each concrete ``defender -> protected piece`` relationship.

    This relation is deliberately scoped to 消除保护: only a rook, horse, or
    cannon is a qualifying defender.  Pawn, advisor, elephant and general
    protection remains relevant to other tactical rules, but does not create
    a 消除保护 opportunity.

    A relationship exists only if, after an enemy capture of the protected
    piece, this exact defender has a *legal* immediate recapture.  This is
    deliberately stronger than sharing a rank/file or geometrically attacking
    a square: pinned pieces and invalid cannon mounts do not protect.
    """
    relations: set[tuple[str, str]] = set()
    enemy = _other(side)
    enemy_position = _fen(board, enemy)
    for defender, piece in board.items():
        if not _is_side(piece, side) or piece.upper() not in {"R", "N", "C"}:
            continue
        for victim, protected_piece in board.items():
            if (
                defender == victim
                or not _is_side(protected_piece, side)
                or protected_piece.upper() not in {"R", "N", "C"}
            ):
                continue
            # Turn only the protected friendly piece into an enemy on its own
            # square, then ask the legal-move generator whether this exact
            # defender could take it.  This validates cannon mounts, horse
            # legs and pins even when the target is not attacked *yet*.
            trial = dict(board)
            trial[victim] = protected_piece.lower() if side == "red" else protected_piece.upper()
            if f"{defender}{victim}" not in legal_moves(_fen(trial, side)):
                continue

            # A nominal defender does not make a target effectively guarded
            # when the opponent can already sacrifice a cheaper piece for it.
            # For example, N x R remains a five-point gain even if the horse
            # is immediately recaptured.  Such a relation must not later
            # manufacture a 消除保护 label when the defender is taken away.
            victim_value = _piece_value(protected_piece, victim, side)
            profitable_enemy_capture = any(
                _piece_value(board.get(capture[:2], ""), capture[:2], enemy) < victim_value
                for capture in legal_moves(enemy_position)
                if capture[2:] == victim
            )
            if not profitable_enemy_capture:
                relations.add((defender, victim))
    return relations


def _line_follow_ups(board: dict[str, str], side: str) -> list[tuple[str, str, str, str]]:
    """Find newly useful front-target -> rear-target line relationships.

    ``skewer`` means the front target is presently unprotected and, after it
    leaves the line, the rear target is both attackable and unprotected.
    ``pin`` means the same line exists but the front target is protected now.
    A cannon's existing screen is retained during the virtual removal, so this
    includes cannon 串打 without mistaking the screen for either target.
    """
    result: list[tuple[str, str, str, str]] = []
    enemy = _other(side)
    # This is a positional line relation, so count geometric guards too.  A
    # checked side may have no legal move other than answering check, while
    # its horse/cannon still protects the rear target for pin/skewer purposes.
    protected_now = {
        victim for victim, piece in board.items()
        if _is_side(piece, enemy) and _has_geometric_defender(board, victim, enemy)
    }
    position = _fen(board, side)
    files = "abcdefghi"

    for source, piece in board.items():
        if not _is_side(piece, side) or piece.upper() not in {"R", "C"}:
            continue
        legal_fronts = [
            move for move in _captures(position)
            if move[:2] == source and board.get(move[2:], "").upper() != "K"
        ]
        for front_move in legal_fronts:
            front = front_move[2:]
            dx = (files.index(front[0]) > files.index(source[0])) - (files.index(front[0]) < files.index(source[0]))
            dy = (int(front[1]) > int(source[1])) - (int(front[1]) < int(source[1]))
            if not (dx or dy):
                continue
            without_front = dict(board)
            without_front.pop(front)
            virtual_position = _fen(without_front, side)
            protected_after_front_leaves = {
                victim for victim, candidate in without_front.items()
                if _is_side(candidate, enemy) and _has_geometric_defender(without_front, victim, enemy)
            }
            x, y = files.index(front[0]) + dx, int(front[1]) + dy
            while 0 <= x < 9 and 0 <= y <= 9:
                rear = f"{files[x]}{y}"
                if _is_side(without_front.get(rear), enemy) and f"{source}{rear}" in legal_moves(virtual_position):
                    kind = "pin" if front in protected_now else "skewer"
                    # The front and rear of a line tactic are tactical
                    # targets.  An uncrossed pawn/soldier is deliberately
                    # excluded from both roles: its opening restriction is
                    # ordinary movement, not a 串打 or 牵制 opportunity.
                    valid_line_targets = (
                        _is_chase_target(board, front, enemy)
                        and _is_chase_target(board, rear, enemy)
                    )
                    # A material pin is deliberately limited to rook, horse
                    # and cannon.  Pawns (including uncrossed pawns),
                    # elephants and advisors may sit on the line, but do not
                    # turn that geometry into a 牵制 relation.
                    pin_material = all(
                        _is_pin_piece(board.get(square))
                        for square in (source, front, rear)
                    )
                    # 炮打车、车后又有炮时，直接炮换车已是得子，不能
                    # 说前车因顾忌后炮而受到牵制。
                    cannon_rook_cannon = (
                        piece.upper() == "C"
                        and board.get(front, "").upper() == "R"
                        and board.get(rear, "").upper() == "C"
                    )
                    if (
                        valid_line_targets
                        and not _same_kind_can_capture_attacker(board, source, front, side)
                        and (
                            (kind == "pin" and pin_material and not cannon_rook_cannon and rear not in protected_now)
                            # 串打只指炮隔子攻击一串无保护目标；车的同线
                            # 关系不会标为串打。
                            or (kind == "skewer" and piece.upper() == "C" and rear not in protected_after_front_leaves)
                        )
                    ):
                        result.append((kind, source, front, rear))
                    # The closest legal rear attack is the tactical follow-up;
                    # do not jump over it to manufacture a second relation.
                    break
                x += dx; y += dy
    return result


def analyze_tactical_categories(fen: str, moves: list[str]) -> list[dict[str, object]]:
    annotations: list[dict[str, object]] = []
    current = fen
    # A concrete recapture can be delayed by up to three plies.  Keep the
    # original capture intact when intervening moves also happen to capture.
    recent_captures: list[tuple[int, dict[str, str], str, str, str, str, str]] = []
    for ply, move in enumerate(moves, start=1):
        side = side_to_move(current)
        enemy = _other(side)
        before = parse_fen(current)
        after_fen = apply_move(current, move)
        after = parse_fen(after_fen)
        source, target = move[:2], move[2:]
        moving_piece = before[source]
        captured_piece = before.get(target)
        occurrences: list[dict[str, object]] = []

        def add(identifier: str, squares: list[str], detail: str) -> None:
            occurrences.append({"id": identifier, "label_zh": LABELS[identifier], "squares": squares, "detail": detail})

        # 交换必须是对原落点上吃子者的实际反吃，而非仅有潜在反吃。
        # 允许该反吃在原吃子后的三个 ply 内发生；中间的走子（包括
        # 其他吃子）不会抹掉原本的交换关系。
        if captured_piece and captured_piece.upper() != "K":
            for (
                prior_ply,
                prior_board,
                prior_after,
                prior_source,
                prior_target,
                prior_mover,
                prior_victim,
            ) in recent_captures:
                prior_side = _other(side)
                prior_value = _piece_value(prior_mover, prior_source, prior_side)
                prior_taken_value = _piece_value(prior_victim, prior_target, side)
                if (
                    1 <= ply - prior_ply <= 3
                    and target == prior_target
                    and captured_piece == prior_mover
                    and prior_value == prior_taken_value
                    and not _is_minor_for_two_guards_sacrifice(
                        prior_board, prior_after, prior_source, prior_target
                    )
                ):
                    add(
                        "exchange",
                        [prior_source, prior_target, source],
                        f"{_piece_label(prior_board, prior_source)} 先吃 {prior_target}，"
                        f"本手 {source}{target} 于三个 ply 内明确反吃落点，交换实际完成。",
                    )
                    break

        # 捉双：本手新形成两项“可安全吃到”的车、马、炮目标即可。
        # 两项攻击可以来自同一枚子，也可以是一子走动后同时让另一枚
        # 己子获得攻击线；但不能把走前就存在的无关攻击拼成捉双。将军
        # 同时捉住另一枚车、马或炮时，将帅作为第一目标，也属于捉双。
        # 兵、士、象不构成第二目标。
        before_position = _fen(before, side)
        def is_fork_capture(position: str, board: dict[str, str], capture: str) -> bool:
            """A fork target must be genuinely chased, not merely contacted."""
            attacker = board.get(capture[:2], "").upper()
            victim = board.get(capture[2:], "").upper()
            if _same_kind_can_capture_attacker(board, capture[:2], capture[2:], side):
                return False
            # A horse/cannon attacking a rook is still a chase even if the
            # rook is guarded: exchanging a 4-point minor for a rook gains.
            if victim == "R" and attacker in {"N", "C"}:
                return True
            return not _has_geometric_defender(board, capture[2:], enemy)

        before_safe_captures = {
            (item[:2], item[2:]) for item in _captures(before_position)
            if before[item[2:]].upper() in {"R", "N", "C"}
            and _is_chase_target(before, item[2:], enemy)
            and is_fork_capture(before_position, before, item)
        }
        after_safe_captures = {
            (item[:2], item[2:]) for item in _captures(after_fen, side)
            if after[item[2:]].upper() in {"R", "N", "C"}
            and _is_chase_target(after, item[2:], enemy)
            and is_fork_capture(after_fen, after, item)
        }
        fork_targets = sorted({victim for _, victim in after_safe_captures - before_safe_captures})
        gives_check = _gives_check(after, side)
        normal_fork = len(fork_targets) >= 2
        checking_fork = gives_check and bool(fork_targets)
        if normal_fork or checking_fork:
            if checking_fork:
                add("fork", [target, *fork_targets], f"{_piece_label(after, target)} 将军的同时攻击 {', '.join(fork_targets)}；将帅与该车、马或炮构成捉双，吃子可安全完成。")
            else:
                add("fork", [target, *fork_targets], f"{_piece_label(after, target)} 本手后新增同时攻击 {', '.join(fork_targets)} 两个目标；两项吃子均可安全完成，无法被立即合法回吃。")

        # 串打／牵制：攻击前子后，若其离开线路会让后子受攻击。
        # 前子当前无保护且后子在前子离线后无保护，是串打；前子当前
        # 已有有效保护，则同一线路关系归为牵制。
        before_follow_ups = {(source, front, rear) for _, source, front, rear in _line_follow_ups(before, side)}
        for kind, attacker, front, rear in _line_follow_ups(after, side):
            if (attacker, front, rear) in before_follow_ups:
                continue
            if kind == "skewer":
                add("skewer", [attacker, front, rear], f"{_piece_label(after, attacker)} 正攻击未受保护的 {front}；若 {front} 离开线路，后方未受保护的 {rear} 会立即受到攻击，构成串打。")
            else:
                add("pin", [attacker, front, rear], f"{_piece_label(after, attacker)} 攻击 {front}；{front} 当前有有效保护，但它离开线路会使后方 {rear} 受攻击，构成牵制。")

        # 闪击只认三种明确结构：移开马腿、移开车线，以及以非炮子
        # 移开炮线形成将军并同时攻击有效目标。不能只因将帅脱离将军、
        # 使已有攻击恢复合法而误触发。
        newly_opened = _new_captures(before, after_fen, side)
        horse_flash = next(
            (
                candidate
                for candidate in newly_opened
                if after.get(candidate[:2], "").upper() == "N"
                and _horse_leg(candidate[:2], candidate[2:]) == source
            ),
            None,
        )
        rook_check = (
            _new_check_by_piece(before, after, side, "R")
            if moving_piece.upper() != "R"
            else None
        )
        rook_flash = next(
            (
                candidate
                for candidate in newly_opened
                if moving_piece.upper() != "R"
                and after.get(candidate[:2], "").upper() == "R"
                and _is_unprotected_major_target(after, candidate[2:], enemy)
                and not _can_directly_capture(after, candidate[:2], side)
            ),
            None,
        )
        cannon_check = (
            _new_check_by_piece(before, after, side, "C")
            if moving_piece.upper() != "C"
            else None
        )
        cannon_partner_flash = next(
            (
                candidate
                for candidate in newly_opened
                if cannon_check
                and candidate[:2] == target
                and (
                    _is_unprotected_major_target(after, candidate[2:], enemy)
                    or (
                        after.get(candidate[2:], "").upper() == "P"
                        and _has_crossed_river(after[candidate[2:]], candidate[2:], enemy)
                    )
                )
            ),
            None,
        )
        if horse_flash:
            add("discovered_attack", [source, target, horse_flash[:2], horse_flash[2:]], f"{source} 移开马腿至 {target} 后，{_piece_label(after, horse_flash[:2])} 新获得对 {horse_flash[2:]} 的攻击。")
        elif rook_check:
            add("discovered_attack", [source, target, rook_check], f"{source} 移开至 {target} 后，{_piece_label(after, rook_check)} 形成将军；对方必须应将，构成车的闪击。")
        elif rook_flash:
            add("discovered_attack", [source, target, rook_flash[:2], rook_flash[2:]], f"{source} 移开至 {target} 后，{_piece_label(after, rook_flash[:2])} 新攻击未受保护的 {rook_flash[2:]}，且该车不能被直接吃掉。")
        elif cannon_partner_flash:
            add("discovered_attack", [source, target, cannon_check, cannon_partner_flash[2:]], f"{source} 移开至 {target} 后，{_piece_label(after, cannon_check)} 形成将军，同时 {target} 新攻击 {cannon_partner_flash[2:]}，构成炮的配合闪击。")

        # 消除保护：只认“本手直接吃掉指定守子”这一种手段。闪击将军、
        # 牵制或线路变化即使让某条保护关系暂时失效，也不在此标签中
        # 另算消除保护；被保护目标本身被吃则属于交换／得子。
        before_defenses = _defense_relations(before, enemy)
        after_defenses = _defense_relations(after, enemy)
        defended_after = {victim for _, victim in after_defenses}
        attacked_after = {capture[2:] for capture in _captures(after_fen, side)}

        def is_only_same_piece_trade(victim: str) -> bool:
            """Whether every newly available capture is a legal equal-piece trade.

            A defender may disappear while an enemy rook/horse/cannon is
            attacked, yet that target can simply take the attacking piece in
            return.  Players describe this as mutual contact / an exchange,
            not 消除保护.  A reciprocal capture that is illegal (for example it
            exposes its own general) is deliberately *not* filtered out.
            """
            captures = [capture for capture in _captures(after_fen, side) if capture[2:] == victim]
            if not captures:
                return False
            victim_piece = after.get(victim, "").upper()
            enemy_position = _fen(after, enemy)
            return all(
                after.get(capture[:2], "").upper() == victim_piece
                and f"{victim}{capture[:2]}" in legal_moves(enemy_position)
                for capture in captures
            )

        removed_defenses = sorted(
            (defender, victim)
            for defender, victim in before_defenses - after_defenses
            # The protected target must still be an enemy piece.  A new
            # attacker occupying its square means it was simply captured.
            if _is_side(after.get(victim), enemy)
            # The defender itself must be the piece captured by this move.
            # No capture means no 消除保护 label.
            and defender == target and not _is_side(after.get(defender), enemy)
            # The target must lose every defender and become actively
            # attackable.  Merely taking one of several guards is not
            # 消除保护.
            and victim not in defended_after
            and victim in attacked_after
            # 同类子力彼此可合法吃回只是互捉／潜在交换；除非反吃因将帅
            # 安全而非法，否则不标为消除保护。
            and not is_only_same_piece_trade(victim)
        )
        for defender, victim in removed_defenses:
            add("remove_defender", [defender, victim, source, target], f"本手吃掉守子 {_piece_label(before, defender)}；{victim} 已无其他有效保护，并转为我方可直接攻击的目标。")

        # 围困：目标的每一条合法走法都会立即安全失子，并且当前有己子直接捉它。
        # “困”可以早于“围”形成；本手若给一个早已被困的子新增直接捉子，
        # 两项条件也在此刻首次同时成立，应当输出标签。
        before_traps = _trapped_pieces(before, enemy)
        after_traps = _trapped_pieces(after, enemy)
        before_position = _fen(before, side)
        for victim in sorted(after_traps):
            before_hunters = {capture[:2] for capture in _captures(before_position) if capture[2:] == victim}
            hunters = [capture for capture in _captures(after_fen, side) if capture[2:] == victim]
            new_hunters = [capture for capture in hunters if capture[:2] not in before_hunters]
            if hunters and (victim not in before_traps or new_hunters):
                hunter = new_hunters[0] if new_hunters else hunters[0]
                add("trap", [victim, hunter[:2]], f"{_piece_label(after, victim)} 的每个合法去处都会遭受得子攻击，且 {hunter[:2]} 正直接捉住它；满足“围”与“困”两个条件。")

        # 牵制：沿用旧页面的“同线约束 + 合法回吃约束”，但只报告新关系。
        before_lines, before_protections = _pins_created_by(before, side)
        after_lines, after_protections = _pins_created_by(after, side)
        previous_relations = _pin_relationships(before_lines, before_protections)
        for rook, first, second in sorted(after_lines | after_protections):
            relation = _pin_relationships({(rook, first, second)} if (rook, first, second) in after_lines else set(), {(rook, first, second)} if (rook, first, second) in after_protections else set())
            if relation & previous_relations:
                continue
            if after.get(second, "").upper() == "K":
                detail = f"绝对牵制：{first} 一旦离开 {rook} 与将／帅 {second} 的线路，就会直接暴露将军，故该离线走法不合法。"
            elif (rook, first, second) in after_lines:
                detail = f"{rook} 与敌方 {first}、{second} 同线；任一离线都会让另一枚棋子被直接吃到。"
            else:
                detail = f"{rook} 是 {first} 的合法回吃保护；敌方 {second} 若吃 {first}，会被 {rook} 合法回吃。"
            add("pin", [rook, first, second], detail)

        # 炮兵突破：炮以未过河兵／卒作诱饵。若对方吃兵，吃兵的子会
        # 成为炮架或移走原屏障，令炮能吃到无保护子；受保护的车也算，
        # 因为炮换车仍是得子。炮先就位、下一步才挺兵同样算作该手法。
        breakthrough: tuple[str, str, str] | None = None
        if moving_piece.upper() == "P":
            plan = _pawn_sacrifice_breakthrough(before, move, side)
            if plan:
                reply, cannon_capture = plan
                breakthrough = (move, reply, cannon_capture)
            else:
                checking_cannon = _pawn_breakthrough_check(after, target, side)
                if checking_cannon:
                    add("cannon_pawn_breakthrough", [source, target, checking_cannon], f"兵／卒从 {source} 挺至 {target} 成为炮架，形成将军；对方兵／卒虽可几何攻击该兵，却不能合法吃掉它。")
        elif moving_piece.upper() == "C":
            for pawn_move in legal_moves(_fen(after, side)):
                pawn_source, pawn_target = pawn_move[:2], pawn_move[2:]
                if pawn_target[0] != target[0]:
                    continue
                plan = _pawn_sacrifice_breakthrough(after, pawn_move, side, target)
                if plan:
                    reply, cannon_capture = plan
                    breakthrough = (pawn_move, reply, cannon_capture)
                    break
        if breakthrough:
            pawn_move, reply, cannon_capture = breakthrough
            add("cannon_pawn_breakthrough", [pawn_move[:2], pawn_move[2:], reply[:2], cannon_capture[:2], cannon_capture[2:]], f"预备 {pawn_move} 弃兵／卒；若对方 {reply} 吃兵，{cannon_capture[:2]} 即可走 {cannon_capture} 吃掉目标，构成炮兵突破。")

        annotations.append({"ply": ply, "side": side, "ucci": move, "occurrences": occurrences})
        recent_captures = [
            capture for capture in recent_captures if ply - capture[0] < 3
        ]
        if captured_piece and captured_piece.upper() != "K":
            recent_captures.append(
                (ply, before, after_fen, source, target, moving_piece, captured_piece)
            )
        current = after_fen
    return annotations
