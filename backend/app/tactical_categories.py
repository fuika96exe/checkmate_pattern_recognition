"""Auditable, short-horizon recognizer for the nine user-facing tactics.

The rules intentionally favour evidence over guesses.  Every occurrence names
the squares that caused it, so a player can challenge and refine a rule in the
lab instead of treating the label as an engine evaluation.
"""
from __future__ import annotations

from .board import apply_move, attacked_squares, legal_moves, parse_fen, side_to_move
from .tactics import (
    _fen, _is_side, _other, _piece_label,
    _pins_created_by, _pin_relationships, _piece_value, _trapped_pieces,
    _unsafe_captures,
)

CATEGORY_RULES_VERSION = "nine-tactics-draft-0.1"
LABELS = {
    "exchange": "交换", "fork": "捉双", "skewer": "串打",
    "discovered_attack": "闪击", "remove_defender": "消除保护",
    "trap": "围困", "pin": "牵制", "cannon_pawn_breakthrough": "炮兵突破",
}


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


def _defense_relations(board: dict[str, str], side: str) -> set[tuple[str, str]]:
    """Return each concrete ``defender -> protected piece`` relationship.

    A relationship exists only if, after an enemy capture of the protected
    piece, this exact defender has a *legal* immediate recapture.  This is
    deliberately stronger than sharing a rank/file or geometrically attacking
    a square: pinned pieces and invalid cannon mounts do not protect.
    """
    relations: set[tuple[str, str]] = set()
    for defender, piece in board.items():
        if not _is_side(piece, side):
            continue
        for victim, protected_piece in board.items():
            if defender == victim or not _is_side(protected_piece, side) or protected_piece.upper() == "K":
                continue
            # Turn only the protected friendly piece into an enemy on its own
            # square, then ask the legal-move generator whether this exact
            # defender could take it.  This validates cannon mounts, horse
            # legs and pins even when the target is not attacked *yet*.
            trial = dict(board)
            trial[victim] = protected_piece.lower() if side == "red" else protected_piece.upper()
            if f"{defender}{victim}" in legal_moves(_fen(trial, side)):
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
    protected_now = {victim for _, victim in _defense_relations(board, enemy)}
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
            protected_after_front_leaves = {victim for _, victim in _defense_relations(without_front, enemy)}
            x, y = files.index(front[0]) + dx, int(front[1]) + dy
            while 0 <= x < 9 and 0 <= y <= 9:
                rear = f"{files[x]}{y}"
                if _is_side(without_front.get(rear), enemy) and f"{source}{rear}" in legal_moves(virtual_position):
                    kind = "pin" if front in protected_now else "skewer"
                    if kind == "pin" or rear not in protected_after_front_leaves:
                        result.append((kind, source, front, rear))
                    # The closest legal rear attack is the tactical follow-up;
                    # do not jump over it to manufacture a second relation.
                    break
                x += dx; y += dy
    return result


def analyze_tactical_categories(fen: str, moves: list[str]) -> list[dict[str, object]]:
    annotations: list[dict[str, object]] = []
    current = fen
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

        # 交换：价值接近的吃子，且对方可立即合法回吃落点。明显得利或
        # 吃亏的换子由得子／失子类规则描述，不作为独立的等值交换。
        if captured_piece and captured_piece.upper() != "K":
            replies = [reply for reply in _captures(after_fen) if reply[2:] == target]
            own_value = _piece_value(moving_piece, source, side)
            taken_value = _piece_value(captured_piece, target, enemy)
            if replies and abs(own_value - taken_value) <= 2:
                add("exchange", [source, target, replies[0][:2]], f"{_piece_label(before, source)} 吃掉 {_piece_label(before, target)}；对方可用 {replies[0]} 合法回吃，构成可验证的交换。")

        # 捉双：走后同一枚刚移动的棋子同时有两项“可安全吃到”的
        # 非将目标，并且本手至少新增其中一项攻击。另一个目标可以在
        # 走前已受攻击；例如车横移后保留左炮攻击、并新增右炮攻击，
        # 仍然是本手形成的捉双。受保护、吃后立即会被合法回吃的棋子
        # 不算一个“捉”目标。
        before_position = _fen(before, side)
        before_safe_targets = {
            item[2:] for item in _captures(before_position)
            if item[:2] == source and _is_safe_capture(before_position, item, side)
        }
        after_by_mover = [item for item in _captures(after_fen, side) if item[:2] == target and after[item[2:]].upper() != "K"]
        fork_targets = sorted({item[2:] for item in after_by_mover if _is_safe_capture(after_fen, item, side)})
        if len(fork_targets) >= 2 and set(fork_targets) - before_safe_targets:
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

        # 闪击：移动一子后，另一枚己子的“几何攻击线”被实际打开。
        # 不能只因己方将帅脱离将军、使一条原本已有的攻击恢复合法，就
        # 误称闪击；该情形没有移动任何遮挡攻击线的棋子。
        before_geometric_attacks = attacked_squares(before, side)
        after_geometric_attacks = attacked_squares(after, side)
        newly_opened = [
            candidate for candidate in _new_captures(before, after_fen, side)
            if candidate[:2] != target
            and any(entry["square"] == candidate[:2] for entry in after_geometric_attacks.get(candidate[2:], []))
            and not any(entry["square"] == candidate[:2] for entry in before_geometric_attacks.get(candidate[2:], []))
        ]
        if newly_opened:
            opened = newly_opened[0]
            add("discovered_attack", [source, target, opened[:2], opened[2:]], f"{source} 移开至 {target} 后，{_piece_label(after, opened[:2])} 新获得 {opened} 的合法攻击线。")

        # 消除保护：只认“本手直接吃掉指定守子”这一种手段。闪击将军、
        # 牵制或线路变化即使让某条保护关系暂时失效，也不在此标签中
        # 另算消除保护；被保护目标本身被吃则属于交换／得子。
        before_defenses = _defense_relations(before, enemy)
        after_defenses = _defense_relations(after, enemy)
        removed_defenses = sorted(
            (defender, victim)
            for defender, victim in before_defenses - after_defenses
            # The protected target must still be an enemy piece.  A new
            # attacker occupying its square means it was simply captured.
            if _is_side(after.get(victim), enemy)
            # The defender itself must be the piece captured by this move.
            # No capture means no 消除保护 label.
            and defender == target and not _is_side(after.get(defender), enemy)
        )
        for defender, victim in removed_defenses:
            add("remove_defender", [defender, victim, source, target], f"本手吃掉守子 {_piece_label(before, defender)}；它原本保护 {_piece_label(before, victim)} 的这条防守关系已被消除。")

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
                add("trap", [victim, hunter[:2]], f"{_piece_label(after, victim)} 的每个合法去处都会被安全吃掉，且 {hunter[:2]} 正直接捉住它；满足“围”与“困”两个条件。")

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

        # 炮兵突破：兵的本手造成一门己炮新增合法吃子，或改变炮架后打开攻击。
        if moving_piece.upper() == "P":
            cannon_captures = [candidate for candidate in _new_captures(before, after_fen, side) if after.get(candidate[:2], "").upper() == "C"]
            if cannon_captures:
                cannon = cannon_captures[0]
                add("cannon_pawn_breakthrough", [source, target, cannon[:2], cannon[2:]], f"兵从 {source} 到 {target} 改变炮线／炮架，使 {cannon[:2]} 新取得 {cannon} 的合法攻击；炮兵协同形成突破。")

        annotations.append({"ply": ply, "side": side, "ucci": move, "occurrences": occurrences})
        current = after_fen
    return annotations
