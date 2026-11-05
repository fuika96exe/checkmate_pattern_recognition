from __future__ import annotations

from functools import lru_cache

from .board import (
    _between,
    _board_to_fen,
    _pseudo_legal_targets,
    _xy,
    attacked_squares,
    apply_move,
    build_piece_identity,
    legal_moves,
    move_piece_identity,
    parse_fen,
    position_analysis,
)


PATTERN_ORDER = [
    "CROWNED_CHECKMATE",
    "CENTROID_CHECKMATE",
    "CANNONS_SANDWICHING_CHARIOT_CHECKMATE",
    "DOUBLE_CANNON_CHECKMATE",
    "SMOTHERED_CANNON_CHECKMATE",
    "HEAVEN_AND_EARTH_CANNON_CHECKMATE",
    "IRON_BOLT_CHECKMATE",
    "DRAWER_CHECKMATE",
    "THROAT_CUTTING_CHECKMATE",
    "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE",
    "TWO_DEVILS_KNOCKING_CHECKMATE",
    "DOUBLE_CHARIOTS_CHECKMATE",
    "DISCOVERED_HORSE_CHECKMATE",
    "TIGER_SILHOUETTE_CHECKMATE",
    "HORSE_CANNON_CHECKMATE",
    "ELBOW_HORSE_CHECKMATE",
    "PALCORNER_HORSE_CHECKMATE",
    "OCTAGON_HORSE_CHECKMATE",
    "ANGLER_HORSE_CHECKMATE",
    "SMOTHERED_CHECKMATE",
    "DOUBLE_CHECK_CHECKMATE",
    "WHITE_FACE_GENERAL",
    "STALEMATE",
]

CHECKMATE_RULES_VERSION = "checkmate-patterns-2026.11.05-v15"


@lru_cache(maxsize=2048)
def _apply_moves_cached(fen: str, moves: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    current_fen = fen
    for move in moves:
        current_fen = apply_move(current_fen, move)
    return current_fen, moves


def _apply_moves(fen: str, moves: list[str] | None) -> tuple[str, list[str]]:
    current_fen, applied = _apply_moves_cached(fen, tuple(moves or ()))
    return current_fen, list(applied)


@lru_cache(maxsize=1024)
def _move_trace_cached(fen: str, moves: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    current_fen = fen
    identities = build_piece_identity(fen)
    trace: list[dict[str, object]] = []
    for ply, move in enumerate(moves, start=1):
        board = parse_fen(current_fen)
        from_square = move[:2]
        to_square = move[2:]
        piece = board[from_square]
        piece_id = identities[from_square]
        next_fen = apply_move(current_fen, move)
        next_analysis = position_analysis(next_fen)
        trace.append(
            {
                "ply": ply,
                "move": move,
                "piece": piece,
                "piece_id": piece_id,
                "from_square": from_square,
                "to_square": to_square,
                "analysis": next_analysis,
            }
        )
        identities = move_piece_identity(identities, from_square, to_square)
        current_fen = next_fen
    return tuple(trace)


def _move_trace(fen: str, moves: list[str] | None) -> list[dict[str, object]]:
    return list(_move_trace_cached(fen, tuple(moves or ())))


def _attacker_and_defender_trace(
    fen: str, moves: list[str] | None, attacker: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    trace = _move_trace(fen, moves)
    initial_side = (fen.split()[1] if len(fen.split()) > 1 else "w")
    initial_attacker = "red" if initial_side == "w" else "black"
    attacker_offset = 0 if attacker == initial_attacker else 1
    return trace[attacker_offset::2], trace[1 - attacker_offset::2]


def _infer_sides(current_fen: str) -> tuple[dict[str, str], dict, str, str, str | None, str | None]:
    board = parse_fen(current_fen)
    analysis = position_analysis(current_fen)
    defender = analysis["side_to_move"]
    attacker = "red" if defender == "black" else "black"
    defender_piece = "k" if defender == "black" else "K"
    attacker_piece = "K" if attacker == "red" else "k"
    defender_king = next((s for s, p in board.items() if p == defender_piece), None)
    attacker_king = next((s for s, p in board.items() if p == attacker_piece), None)
    return board, analysis, attacker, defender, attacker_king, defender_king


def _palace_contains(square: str, side: str) -> bool:
    file_ok = square[0] in "def"
    rank = int(square[1])
    if side == "red":
        return file_ok and 0 <= rank <= 2
    return file_ok and 7 <= rank <= 9


def _orthogonal_palace_neighbors(square: str, side: str) -> list[str]:
    x = ord(square[0]) - ord("a")
    y = int(square[1])
    neighbors: list[str] = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = x + dx
        ny = y + dy
        if 0 <= nx < 9 and 0 <= ny <= 9:
            target = f"{chr(ord('a') + nx)}{ny}"
            if _palace_contains(target, side):
                neighbors.append(target)
    return neighbors


def _home_rank(side: str) -> str:
    return "0" if side == "red" else "9"


def _is_attacker_piece(piece: str, attacker: str) -> bool:
    return piece.isupper() if attacker == "red" else piece.islower()


def _flank_name(square: str) -> str | None:
    if square[0] in {"a", "b", "c"}:
        return "left"
    if square[0] in {"g", "h", "i"}:
        return "right"
    return None


def _horse_leg_square(horse_square: str, target_square: str) -> str | None:
    hx, hy = _xy(horse_square)
    tx, ty = _xy(target_square)
    dx = tx - hx
    dy = ty - hy
    if abs(dx) == 1 and abs(dy) == 2:
        return f"{horse_square[0]}{hy + (1 if dy > 0 else -1)}"
    if abs(dx) == 2 and abs(dy) == 1:
        return f"{chr(ord(horse_square[0]) + (1 if dx > 0 else -1))}{horse_square[1]}"
    return None


def recognize_centroid_chariot_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(current_fen)
    center = "e8" if defender == "black" else "e1"
    piece = board.get(center, "")
    checkers = analysis["checking_pieces"]
    present = bool(piece and _is_attacker_piece(piece, attacker) and piece.upper() in {"R", "P"})
    detected = bool(analysis["is_checkmate"] and present and checkers and all(x["square"] != center for x in checkers))
    return {"pattern_id": "CENTROID_CHECKMATE", "pattern_name_zh": "花心杀", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis,
            "features": {"attacker_side": attacker, "defender_side": defender, "centroid_square": center, "centroid_piece": piece or None, "centroid_is_checker": any(x["square"] == center for x in checkers)},
            "diagnostics": ["车或兵占据花心，由另一棋子将死，花心子不将军。"]}


def recognize_crowned_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    crown_front_square = "e8" if defender == "black" else "e1"
    front_piece = board.get(crown_front_square)
    supporting_front_piece = bool(
        front_piece
        and _is_attacker_piece(front_piece, attacker)
        and front_piece.upper() in {"R", "P"}
    )
    cannon_square = None
    clear_cannon_path = False
    for item in analysis["checking_pieces"]:
        if item["reason"] != "cannon_screen":
            continue
        source = item["square"]
        if board.get(source) != cannon_piece or not defender_king:
            continue
        between_king = _between(board, source, defender_king)
        occupied_between_king = [square for square in between_king if square in board]
        if occupied_between_king != [crown_front_square]:
            continue
        between_front = _between(board, source, crown_front_square)
        if any(square in board for square in between_front):
            continue
        cannon_square = source
        clear_cannon_path = True
        break

    checking_front_piece = any(
        item["square"] == crown_front_square and item["reason"] in {"line_attack", "pawn_attack"}
        for item in analysis["checking_pieces"]
    )
    auxiliary_crown_pieces = sorted(
        square
        for square, piece in board.items()
        if _is_attacker_piece(piece, attacker)
        and piece.upper() in {"R", "P"}
        and square[1] == crown_front_square[1]
        and square != crown_front_square
    )
    detected = bool(
        analysis["is_checkmate"]
        and supporting_front_piece
        and cannon_square
        and clear_cannon_path
        and checking_front_piece
        and len(analysis["checking_pieces"]) >= 2
    )
    return {
        "pattern_id": "CROWNED_CHECKMATE",
        "pattern_name_zh": "平顶冠",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "crown_front_square": crown_front_square,
            "front_piece": front_piece,
            "cannon_square": cannon_square,
            "clear_cannon_path": clear_cannon_path,
            "auxiliary_crown_pieces": auxiliary_crown_pieces,
            "checking_piece_count": len(analysis["checking_pieces"]),
        },
        "diagnostics": [
            "攻击方有车或兵顶在将帅正前方，形成冠顶的正面压迫。",
            "其后方另有一门中炮透过该前线棋子形成空心炮双将。",
            "终局无合法解杀，因此构成平顶冠。",
        ],
    }


def recognize_eunuchs_chasing_emperor_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    attacker_trace, defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    pawn_piece = "P" if attacker == "red" else "p"
    home_rank = _home_rank(defender)
    palace_ranks = {"7", "8", "9"} if defender == "black" else {"0", "1", "2"}

    pawn_moves = [item for item in attacker_trace if str(item["piece"]).upper() == "P"]
    pawn_move_count = len(pawn_moves)
    pawn_ids = [str(item["piece_id"]) for item in pawn_moves]
    repeated_pawn_ids = sorted(
        {
            piece_id
            for piece_id in pawn_ids
            if pawn_ids.count(piece_id) >= 2
        }
    )
    advanced_pawn_squares = sorted(
        square
        for square, piece in board.items()
        if piece == pawn_piece and square[1] in palace_ranks
    )
    pawn_check_count = sum(
        1
        for item in pawn_moves
        if any(
            entry["square"] == str(item["to_square"]) and entry["reason"] == "pawn_attack"
            for entry in item["analysis"]["checking_pieces"]
        )
    )
    final_checking_piece_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )
    support_piece_squares = sorted(
        square
        for square, piece in board.items()
        if _is_attacker_piece(piece, attacker)
        and piece.upper() in {"R", "C", "N"}
        and any(
            entry["square"] == square
            for target in (
                [defender_king] + _orthogonal_palace_neighbors(defender_king, defender)
                if defender_king
                else []
            )
            for entry in analysis["attacked_squares"].get(target, [])
        )
    )
    defender_king_replies = [
        item
        for item in defender_trace
        if str(item["piece"]).upper() == "K"
    ]
    king_reply_count = len(defender_king_replies)
    detected = bool(
        analysis["is_checkmate"]
        and pawn_move_count >= 2
        and repeated_pawn_ids
        and (pawn_check_count >= 1 or advanced_pawn_squares)
        and king_reply_count >= 2
        and support_piece_squares
    )
    return {
        "pattern_id": "EUNUCHS_CHASING_EMPEROR_CHECKMATE",
        "pattern_name_zh": "太监追皇帝",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "pawn_move_count": pawn_move_count,
            "repeated_pawn_ids": repeated_pawn_ids,
            "advanced_pawn_squares": advanced_pawn_squares,
            "pawn_check_count": pawn_check_count,
            "support_piece_squares": support_piece_squares,
            "king_reply_count": king_reply_count,
            "final_checking_piece_types": final_checking_piece_types,
        },
        "diagnostics": [
            "兵卒在整段追杀里持续推进，并由同一兵卒或同组兵卒承担主导攻击角色。",
            "车、炮或马负责封锁将帅及其逃位，迫使对方将帅一路退守九宫应对。",
            "虽然最后一击不必由兵卒完成，但整段追杀以兵卒为核心，因此属于太监追皇帝。",
        ],
    }


def recognize_centroid_pawn_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    return recognize_centroid_chariot_checkmate(fen, moves)


def recognize_discovered_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    horse_piece = "N" if attacker == "red" else "n"
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    final_attack = attacker_trace[-1] if attacker_trace else None
    previous_fen, _ = _apply_moves(fen, applied[:-1]) if applied else (fen, [])
    previous_board = parse_fen(previous_fen)

    discovered_horses: list[dict[str, object]] = []
    if final_attack and defender_king:
        vacated_square = str(final_attack["from_square"])
        for item in analysis["checking_pieces"]:
            horse_square = item["square"]
            if item["reason"] != "horse_attack" or board.get(horse_square) != horse_piece:
                continue
            leg_square = _horse_leg_square(horse_square, defender_king)
            if not leg_square or leg_square != vacated_square:
                continue
            if previous_board.get(horse_square) != horse_piece:
                continue
            blocker_piece = previous_board.get(leg_square)
            if not blocker_piece or not _is_attacker_piece(blocker_piece, attacker):
                continue
            discovered_horses.append(
                {
                    "horse_square": horse_square,
                    "leg_square": leg_square,
                    "unblocking_piece": str(final_attack["piece"]).upper(),
                    "destination_square": str(final_attack["to_square"]),
                }
            )

    detected = bool(
        analysis["is_checkmate"]
        and final_attack
        and str(final_attack["piece"]).upper() != "N"
        and discovered_horses
        and bool(final_attack["analysis"]["is_checkmate"])
    )
    return {
        "pattern_id": "DISCOVERED_HORSE_CHECKMATE",
        "pattern_name_zh": "拔簧马",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "discovered_horses": discovered_horses,
            "discovered_horse_count": len(discovered_horses),
            "final_unblocking_piece_type": (
                str(final_attack["piece"]).upper() if final_attack else None
            ),
            "final_unblocking_from": (
                str(final_attack["from_square"]) if final_attack else None
            ),
            "final_unblocking_to": (
                str(final_attack["to_square"]) if final_attack else None
            ),
        },
        "diagnostics": [
            "最后一着并非马跳将，而是另一枚己方棋子离开了马腿位置。",
            "该着法一旦把马腿拔开，原本静止的马立即形成马将并完成绝杀。",
            "因此该终局构成拔簧马。",
        ],
    }


def recognize_double_cannon_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    cannon_squares = sorted(
        square for square, piece in board.items() if piece == cannon_piece
    )
    checking_cannons = [
        item for item in analysis["checking_pieces"] if item["reason"] == "cannon_screen"
    ]
    same_file = False
    same_rank = False
    screen_cannon_square: str | None = None
    checking_cannon_square: str | None = None
    if len(cannon_squares) >= 2 and defender_king and checking_cannons:
        checking_cannon_square = checking_cannons[0]["square"]
        for other in cannon_squares:
            if other == checking_cannon_square:
                continue
            if other[0] == checking_cannon_square[0] == defender_king[0]:
                same_file = True
                between = {
                    square
                    for square in board
                    if square[0] == checking_cannon_square[0]
                    and min(int(square[1]), int(defender_king[1]))
                    < int(other[1])
                    < max(int(square[1]), int(defender_king[1]))
                }
                if other in between or (
                    min(int(checking_cannon_square[1]), int(defender_king[1]))
                    < int(other[1])
                    < max(int(checking_cannon_square[1]), int(defender_king[1]))
                ):
                    screen_cannon_square = other
                    break
            if other[1] == checking_cannon_square[1] == defender_king[1]:
                same_rank = True
                if min(ord(checking_cannon_square[0]), ord(defender_king[0])) < ord(other[0]) < max(ord(checking_cannon_square[0]), ord(defender_king[0])):
                    screen_cannon_square = other
                    break
    orientation = "file" if screen_cannon_square and screen_cannon_square[0] == checking_cannon_square[0] else "rank" if screen_cannon_square else None
    detected = bool(
        analysis["is_checkmate"]
        and len(cannon_squares) >= 2
        and checking_cannons
        and screen_cannon_square
        and (same_file or same_rank)
    )
    return {
        "pattern_id": "DOUBLE_CANNON_CHECKMATE",
        "pattern_name_zh": "重炮杀",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "cannon_squares": cannon_squares,
            "checking_cannon_square": checking_cannon_square,
            "screen_cannon_square": screen_cannon_square,
            "orientation": orientation,
        },
        "diagnostics": [
            "攻击方两个炮在同一列或同一行形成重炮结构。",
            "其中一炮借另一炮作炮架实施将军。",
            "防守方没有任何合法防守，因此构成重炮杀。",
        ],
    }


def recognize_cannons_sandwiching_chariot_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    cannon_piece = "C" if attacker == "red" else "c"
    attacking_ranks = {"7", "8", "9"} if defender == "black" else {"0", "1", "2"}
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece and square[1] in attacking_ranks)
    cannon_squares = sorted(
        square for square, piece in board.items() if piece == cannon_piece and square[1] in attacking_ranks
    )
    flank_groups: list[dict[str, object]] = []
    for flank in ("left", "right"):
        flank_rooks = [square for square in rook_squares if _flank_name(square) == flank]
        flank_cannons = [
            square for square in cannon_squares if _flank_name(square) == flank
        ]
        if flank_rooks and len(flank_cannons) >= 2:
            flank_groups.append(
                {
                    "flank": flank,
                    "rook_squares": flank_rooks,
                    "cannon_squares": flank_cannons,
                }
            )

    final_checker_squares = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() in {"R", "C"}
    ]
    final_checker_types = sorted(
        {board.get(square, "").upper() for square in final_checker_squares}
    )
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    checking_attackers = [
        item
        for item in attacker_trace
        if str(item["piece"]).upper() in {"R", "C"} and bool(item["analysis"]["is_check"])
    ]
    attack_sequence_types = [str(item["piece"]).upper() for item in checking_attackers[-5:]]
    distinct_attacker_ids = sorted(
        {str(item["piece_id"]) for item in checking_attackers[-5:]}
    )

    detected = bool(
        analysis["is_checkmate"]
        and flank_groups
        and any(square in group["rook_squares"] or square in group["cannon_squares"] for group in flank_groups for square in final_checker_squares)
        and (
            not applied
            or len(checking_attackers) >= 1
        )
    )
    return {
        "pattern_id": "CANNONS_SANDWICHING_CHARIOT_CHECKMATE",
        "pattern_name_zh": "夹车炮",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "flank_groups": flank_groups,
            "attacking_ranks": sorted(attacking_ranks),
            "final_checker_squares": final_checker_squares,
            "final_checker_types": final_checker_types,
            "checking_attack_count": len(checking_attackers),
            "attack_sequence_types": attack_sequence_types,
            "distinct_attacker_ids": distinct_attacker_ids,
        },
        "diagnostics": [
            "攻击方在同一侧集结的车和双炮均须位于敌方底部三路。",
            "终局由该侧的车或炮完成将军，并形成绝杀。",
            "若过程中出现车炮轮番压将，也一并归入夹车炮。",
        ],
    }


def recognize_smothered_cannon_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = _infer_sides(current_fen)
    advisor = "a" if defender == "black" else "A"
    checkers = analysis["checking_pieces"]
    types = {board.get(x["square"], "").upper() for x in checkers}
    matches = []
    for checker in checkers:
        square = checker["square"]
        if not king or board.get(square, "").upper() != "C":
            continue
        between = [x for x in _between(board, square, king) if x in board]
        perpendicular = [x for x in _orthogonal_palace_neighbors(king, defender) if (x[0] == king[0] if square[1] == king[1] else x[1] == king[1])]
        if len(between) == 1 and board[between[0]].upper() == "A" and perpendicular and all(board.get(x) == advisor for x in perpendicular):
            matches.append({"cannon": square, "screen": between[0], "blocked_squares": perpendicular})
    detected = bool(analysis["is_checkmate"] and types == {"C"} and matches)
    return {"pattern_id": "SMOTHERED_CANNON_CHECKMATE", "pattern_name_zh": "闷宫杀", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"matching_cannons": matches, "checking_piece_types": sorted(types)}, "diagnostics": ["只由炮将军，以士为炮架，垂直炮线的宫内去路全部被己方士堵住。"]}


def recognize_double_chariots_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece)
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    recent_attackers = attacker_trace[-3:] if len(attacker_trace) >= 3 else []
    alternating_rooks = False
    checking_sequence = False
    if len(recent_attackers) == 3:
        ids = [str(item["piece_id"]) for item in recent_attackers]
        pieces = [str(item["piece"]) for item in recent_attackers]
        checks = [bool(item["analysis"]["is_check"]) for item in recent_attackers]
        alternating_rooks = (
            all(piece.upper() == "R" for piece in pieces)
            and ids[0] == ids[2]
            and ids[0] != ids[1]
        )
        checking_sequence = all(checks)
    checking_rooks = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() == "R"
    ]
    supporting_rooks = [square for square in rook_squares if square not in checking_rooks]
    supporting_rook_escape_squares = []
    if defender_king:
        for target in _orthogonal_palace_neighbors(defender_king, defender):
            if board.get(target):
                continue
            attacks = analysis["attacked_squares"].get(target, [])
            supported_by_other_rook = any(entry["square"] in supporting_rooks for entry in attacks)
            checked_by_finishing_rook = any(
                entry["square"] in checking_rooks for entry in attacks
            ) or any(
                rook[0] == defender_king[0] == target[0]
                or rook[1] == defender_king[1] == target[1]
                for rook in checking_rooks
            )
            if supported_by_other_rook and not checked_by_finishing_rook:
                supporting_rook_escape_squares.append(target)
    immediate_rook_finish = bool(
        attacker_trace
        and str(attacker_trace[-1]["piece"]).upper() == "R"
        and attacker_trace[-1]["analysis"]["is_checkmate"]
        and checking_rooks
        and (len(checking_rooks) >= 2 or supporting_rook_escape_squares)
    )
    different_files = len({square[0] for square in rook_squares}) >= 2
    different_ranks = len({square[1] for square in rook_squares}) >= 2
    detected = bool(
        analysis["is_checkmate"]
        and len(rook_squares) >= 2
        and (alternating_rooks and checking_sequence or immediate_rook_finish)
        and (different_files or different_ranks)
    )
    return {
        "pattern_id": "DOUBLE_CHARIOTS_CHECKMATE",
        "pattern_name_zh": "双车错",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "rook_squares": rook_squares,
            "different_files": different_files,
            "different_ranks": different_ranks,
            "alternating_rooks": alternating_rooks,
            "checking_sequence": checking_sequence,
            "immediate_rook_finish": immediate_rook_finish,
            "checking_rook_squares": checking_rooks,
            "supporting_rook_squares": supporting_rooks,
            "supporting_rook_escape_squares": supporting_rook_escape_squares,
        },
        "diagnostics": [
            "攻击方两辆车分处不同列或不同行。",
            "最后一段攻击序列可以是双车交替将军，或由一辆车将军、另一辆车封锁将军车未控制的空逃路。",
            "终局没有合法防守，因此构成双车错绝杀。",
        ],
    }


def _cannon_pinned_defenders(
    board: dict[str, str], cannon: str, king: str, attacker: str, defender: str
) -> list[str]:
    """Find defenders pinned to their general by this cannon, independently of other checks."""
    if cannon[0] != king[0] and cannon[1] != king[1]:
        return []
    defender_pieces = {"a", "b"} if defender == "black" else {"A", "B"}
    candidates = [square for square in _between(board, cannon, king) if board.get(square) in defender_pieces]
    if not candidates:
        return []
    probe = dict(board)
    for checker in attacked_squares(board, attacker).get(king, []):
        source = checker["square"]
        if source != cannon and probe.get(source, "").upper() != "K":
            probe.pop(source, None)
    probe_fen = f"{_board_to_fen(probe)} {'w' if defender == 'red' else 'b'} - - 0 1"
    moves = legal_moves(probe_fen)
    pinned = []
    for square in candidates:
        piece = probe.get(square)
        if piece not in defender_pieces or any(move.startswith(square) for move in moves):
            continue
        for target in _pseudo_legal_targets(probe, square, piece):
            moved = dict(probe)
            moved[target] = moved.pop(square)
            if any(entry["square"] == cannon for entry in attacked_squares(moved, attacker).get(king, [])):
                pinned.append(square)
                break
    return pinned


def recognize_heaven_and_earth_cannon_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    home_rank = _home_rank(defender)
    cannons = sorted(
        square for square, piece in board.items() if piece == cannon_piece
    )
    heaven_cannons = [square for square in cannons if square[1] == home_rank]
    earth_cannons = [square for square in cannons if square[0] == "e" and square[1] != home_rank]

    pre_final_board = None
    final_piece = None
    final_destination = None
    captured_piece = None
    if applied:
        pre_final_fen, _ = _apply_moves(fen, applied[:-1])
        pre_final_board = parse_fen(pre_final_fen)
        final_piece = pre_final_board.get(applied[-1][:2])
        final_destination = applied[-1][2:]
        captured_piece = pre_final_board.get(final_destination)

    pre_pins: dict[str, list[str]] = {}
    final_pins: dict[str, list[str]] = {}
    scenarios: list[str] = []
    supporting_rooks: list[str] = []
    protecting_cannons: list[str] = []
    if analysis["is_checkmate"] and defender_king and defender_king == "e" + home_rank and heaven_cannons and earth_cannons:
        for cannon in heaven_cannons + earth_cannons:
            final_pins[cannon] = _cannon_pinned_defenders(board, cannon, defender_king, attacker, defender)
        if pre_final_board:
            pre_king = next((square for square, piece in pre_final_board.items() if piece == ("k" if defender == "black" else "K")), None)
            if pre_king:
                for cannon in heaven_cannons + earth_cannons:
                    if pre_final_board.get(cannon) == cannon_piece:
                        pre_pins[cannon] = _cannon_pinned_defenders(pre_final_board, cannon, pre_king, attacker, defender)

        checking_squares = {item["square"] for item in analysis["checking_pieces"]}
        if final_destination:
            protecting_cannons = sorted(
                entry["square"]
                for entry in analysis["attacked_squares"].get(final_destination, [])
                if entry["square"] in heaven_cannons + earth_cannons
                and entry["reason"] == "cannon_screen"
            )
        if (
            final_piece and final_piece.upper() in {"R", "P"}
            and final_destination and _palace_contains(final_destination, defender)
            and any(pre_pins.get(cannon) for cannon in heaven_cannons)
            and any(pre_pins.get(cannon) for cannon in earth_cannons)
            and final_destination in checking_squares
            and protecting_cannons
        ):
            scenarios.append("cannon_protected_finish")

        if (
            any(final_pins.get(cannon) for cannon in earth_cannons)
            and any(cannon in checking_squares for cannon in heaven_cannons)
        ):
            scenarios.append("center_pin_bottom_cannon_check")

        empty_center = any(
            not any(square in board for square in _between(board, cannon, defender_king))
            for cannon in earth_cannons
        )
        bottom_advisor_check = any(
            cannon in checking_squares
            and len(screens := [square for square in _between(board, cannon, defender_king) if square in board]) == 1
            and board[screens[0]] == ("a" if defender == "black" else "A")
            for cannon in heaven_cannons
        )
        second_rank = "8" if defender == "black" else "1"
        rook_piece = "R" if attacker == "red" else "r"
        supporting_rooks = sorted(square for square, piece in board.items() if piece == rook_piece and square[1] == second_rank)
        if empty_center and bottom_advisor_check and supporting_rooks:
            scenarios.append("empty_center_bottom_advisor_screen")

    detected = bool(scenarios)
    return {
        "pattern_id": "HEAVEN_AND_EARTH_CANNON_CHECKMATE",
        "pattern_name_zh": "天地炮",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "heaven_cannon_squares": heaven_cannons,
            "earth_cannon_squares": earth_cannons,
            "pre_final_pins": pre_pins,
            "final_pins": final_pins,
            "scenarios": scenarios,
            "supporting_rook_squares": supporting_rooks,
            "protecting_cannon_squares": protecting_cannons,
            "final_piece_type": final_piece.upper() if final_piece else None,
            "final_destination": final_destination,
            "captured_piece": captured_piece,
        },
        "diagnostics": [
            "攻击方同时具备一门对方底线炮与一门中路炮。",
            "双炮各自牵制士象，由受炮保护的车兵入宫将死；或中炮牵制士象、底炮将军；或中炮空头、底炮以底士为架将军且有车在下二路。",
        ],
    }


def recognize_throat_cutting_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = _infer_sides(current_fen)
    advisor = "a" if defender == "black" else "A"
    center = "e8" if defender == "black" else "e1"
    qualifying = []
    for item in _move_trace(fen, moves):
        if not _is_attacker_piece(str(item["piece"]), attacker) or str(item["piece"]).upper() not in {"R", "P"} or item["to_square"] != center:
            continue
        before, _ = _apply_moves(fen, applied[:int(item["ply"]) - 1])
        previous = parse_fen(before)
        if previous.get(center) != advisor:
            continue
        other_advisors = [sq for sq, piece in previous.items() if piece == advisor and sq != center]
        after_capture, _ = _apply_moves(fen, applied[:int(item["ply"])])
        defenders = sorted(move[:2] for move in legal_moves(after_capture) if move[2:] == center)
        if other_advisors or defenders:
            qualifying.append({"ply": item["ply"], "other_advisors": other_advisors, "protectors": defenders})
    detected = bool(analysis["is_checkmate"] and qualifying)
    return {"pattern_id": "THROAT_CUTTING_CHECKMATE", "pattern_name_zh": "大胆穿心", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"center_square": center, "qualifying_captures": qualifying}, "diagnostics": ["车或兵吃花心士，且当时另有士或被吃的士受保护。"]}


def recognize_drawer_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    cannon_piece = "C" if attacker == "red" else "c"
    home_rank = _home_rank(defender)
    # 2026.11.05-v15 (expert review): the drawer works on either rib file.
    cave_files = {"d", "f"}
    cave_ranks = {"8", "9"} if defender == "black" else {"0", "1"}
    king_tunnel_squares = {"e8", "e9"} if defender == "black" else {"e0", "e1"}
    attacker_trace, defender_trace = _attacker_and_defender_trace(fen, moves, attacker)

    home_cannons = sorted(
        square
        for square, piece in board.items()
        if piece == cannon_piece and square[1] == home_rank
    )

    rook_cycles: list[dict[str, object]] = []
    for start in range(len(attacker_trace)):
        candidate = attacker_trace[start:]
        if len(candidate) < 2:
            continue
        same_rook = all(
            str(item["piece"]).upper() == "R"
            and str(item["piece_id"]) == str(candidate[0]["piece_id"])
            for item in candidate
        )
        if not same_rook:
            continue
        squares = [str(item["to_square"]) for item in candidate]
        if any(square[0] not in cave_files or square[1] not in cave_ranks for square in squares):
            continue
        if len(set(squares)) != 2:
            continue
        ordered = list(dict.fromkeys(squares))
        if len(ordered) != 2:
            continue
        first_square, second_square = ordered
        if first_square[0] != second_square[0] or abs(int(first_square[1]) - int(second_square[1])) != 1:
            continue
        replies = [next((reply for reply in defender_trace if int(reply["ply"]) == int(move["ply"]) + 1), None) for move in candidate[:-1]]
        if not all(
            reply is not None and
            str(reply["piece"]).upper() == "K" and str(reply["to_square"]) in king_tunnel_squares
            for reply in replies
        ):
            continue
        rook_cycles.append(
            {
                "rook_id": str(candidate[0]["piece_id"]),
                "rook_squares": squares,
                "cycle_start_ply": int(candidate[0]["ply"]),
                "reply_squares": [str(reply["to_square"]) for reply in replies if reply is not None],
            }
        )

    penetration_started = any(
        str(item["piece"]).upper() in {"R", "P"}
        and str(item["to_square"]) == ("e8" if defender == "black" else "e1")
        for item in attacker_trace
    )
    final_piece_type = str(attacker_trace[-1]["piece"]).upper() if attacker_trace else None
    detected = bool(
        analysis["is_checkmate"]
        and home_cannons
        and rook_cycles
        and final_piece_type == "R"
    )
    return {
        "pattern_id": "DRAWER_CHECKMATE",
        "pattern_name_zh": "进洞出洞",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "home_cannon_squares": home_cannons,
            "rook_cycles": rook_cycles,
            "penetration_started": penetration_started,
            "final_piece_type": final_piece_type,
            "cave_files": sorted(cave_files),
            "king_tunnel_squares": sorted(king_tunnel_squares),
        },
        "diagnostics": [
            "攻击方先以底线炮牵制宫内守势，再由同一辆肋道车在宫边相邻两格进出往返。",
            "防守方将帅被逼在 e 线相邻两格之间应将，形成典型的进洞出洞循环。",
            "最终红车收束成绝杀，因此该局面属于进洞出洞。",
        ],
    }


def recognize_elbow_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    elbow_targets = {"c8", "g8"} if defender == "black" else {"c1", "g1"}
    attacker_horse_piece = "N" if attacker == "red" else "n"
    defender_king_piece = "k" if defender == "black" else "K"
    attacker_trace, defender_trace = _attacker_and_defender_trace(fen, moves, attacker)

    elbow_index: int | None = None
    elbow_move: dict[str, object] | None = None
    for index, item in enumerate(attacker_trace):
        if (
            str(item["piece"]) == attacker_horse_piece
            and str(item["to_square"]) in elbow_targets
            and bool(item["analysis"]["is_check"])
        ):
            elbow_index = index
            elbow_move = item
            break

    forced_king_reply = False
    immediate_finish = False
    if elbow_move is not None and elbow_index is not None:
        immediate_finish = bool(elbow_move["analysis"]["is_checkmate"])
        if not immediate_finish and elbow_index < len(defender_trace):
            reply = defender_trace[elbow_index]
            reply_piece = str(reply["piece"])
            forced_king_reply = (
                reply_piece == defender_king_piece
                and str(reply["from_square"]) == str(elbow_move["analysis"]["king_square"])
            )

    elbow_square = str(elbow_move["to_square"]) if elbow_move else None
    elbow_horse_present = bool(
        elbow_square and board.get(elbow_square) == attacker_horse_piece
    )
    static_elbow_horses = sorted(
        square
        for square, piece in board.items()
        if piece == attacker_horse_piece and square in elbow_targets
    )
    king_and_escape_squares = (
        [defender_king, *_orthogonal_palace_neighbors(defender_king, defender)]
        if defender_king else []
    )
    elbow_horse_control = {
        square: [target for target in king_and_escape_squares if any(
            attack["square"] == square and attack["reason"] == "horse_attack"
            for attack in analysis["attacked_squares"].get(target, [])
        )]
        for square in static_elbow_horses
    }
    active_elbow_horses = [square for square, targets in elbow_horse_control.items() if targets]

    final_piece_type = None
    if attacker_trace:
        final_piece_type = str(attacker_trace[-1]["piece"]).upper()
    final_checker_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )

    final_support = bool(
        analysis["is_checkmate"]
        and static_elbow_horses
        and (any(piece_type in {"R", "C", "P"} for piece_type in final_checker_types)
             or any(item["square"] in static_elbow_horses and item["reason"] == "horse_attack" for item in analysis["checking_pieces"]))
    )
    detected = bool(
        analysis["is_checkmate"]
        and active_elbow_horses
        and (
            final_support
            or (
                elbow_move
                and elbow_horse_present
                and (
                    immediate_finish
                    or (
                        forced_king_reply
                        and any(piece_type in {"R", "C", "P"} for piece_type in final_checker_types)
                    )
                )
            )
        )
    )
    return {
        "pattern_id": "ELBOW_HORSE_CHECKMATE",
        "pattern_name_zh": "卧槽马",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "elbow_square": elbow_square,
            "elbow_horse_present": elbow_horse_present,
            "static_elbow_horse_squares": static_elbow_horses,
            "elbow_horse_control": elbow_horse_control,
            "active_elbow_horses": active_elbow_horses,
            "elbow_move_ply": int(elbow_move["ply"]) if elbow_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
        },
        "diagnostics": [
            "绝杀黑方时检查攻击方马是否位于 c8/g8；绝杀红方时检查攻击方马是否位于 c1/g1。",
            "终局卧槽马须实际攻击将帅或控制宫内相邻逃路，蹩马腿时不算控制。",
            "随后再由车、炮或兵完成绝杀，因此构成卧槽马。",
        ],
    }


def recognize_palcorner_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    # Both corner ranks can occur in the opponent's palace.  The distinction
    # from Octagon Horse is made by the number of palace squares controlled,
    # not by the corner coordinate alone.
    palcorner_targets = (
        {"d7", "d9", "f7", "f9"}
        if defender == "black"
        else {"d0", "d2", "f0", "f2"}
    )
    defender_king_piece = "k" if defender == "black" else "K"
    attacker_trace, defender_trace = _attacker_and_defender_trace(fen, moves, attacker)

    palcorner_index: int | None = None
    palcorner_move: dict[str, object] | None = None
    for index, item in enumerate(attacker_trace):
        if (
            str(item["piece"]).upper() == "N"
            and str(item["to_square"]) in palcorner_targets
            and bool(item["analysis"]["is_check"])
        ):
            palcorner_index = index
            palcorner_move = item
            break

    forced_king_reply = False
    immediate_finish = False
    if palcorner_move is not None and palcorner_index is not None:
        immediate_finish = bool(palcorner_move["analysis"]["is_checkmate"])
        if not immediate_finish:
            reply = next((item for item in defender_trace if int(item["ply"]) == int(palcorner_move["ply"]) + 1), None)
            forced_king_reply = reply is not None and (
                str(reply["piece"]) == defender_king_piece
                and str(reply["from_square"])
                == str(palcorner_move["analysis"]["king_square"])
            )

    palcorner_square = str(palcorner_move["to_square"]) if palcorner_move else None
    palcorner_horse_present = bool(
        palcorner_square and board.get(palcorner_square, "").upper() == "N"
    )
    defender_neighbors = (
        _orthogonal_palace_neighbors(defender_king, defender) if defender_king else []
    )
    palace_control_squares = (
        [defender_king, *defender_neighbors] if defender_king else defender_neighbors
    )
    palcorner_restricted_escape_squares = sorted(
        square
        for square in palace_control_squares
        if any(
            attack["square"] == palcorner_square
            and attack["reason"] == "horse_attack"
            for attack in analysis["attacked_squares"].get(square, [])
        )
    )
    final_piece_type = str(attacker_trace[-1]["piece"]).upper() if attacker_trace else None
    final_checker_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )

    horse_piece = "N" if attacker == "red" else "n"
    stationary_candidates = []
    for square in sorted(palcorner_targets):
        if board.get(square) != horse_piece:
            continue
        controlled = [target for target in palace_control_squares if any(
            attack["square"] == square and attack["reason"] == "horse_attack"
            for attack in analysis["attacked_squares"].get(target, [])
        )]
        if len(controlled) == 1 and any(item["square"] != square for item in analysis["checking_pieces"]):
            stationary_candidates.append({"square": square, "controlled_squares": controlled})

    detected = bool(
        analysis["is_checkmate"]
        and (stationary_candidates or (palcorner_move
        and palcorner_horse_present
        and len(palcorner_restricted_escape_squares) == 1
        and (
            immediate_finish
            or (
                forced_king_reply
                and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
            )
        )))
    )
    if stationary_candidates and not palcorner_move:
        palcorner_square = stationary_candidates[0]["square"]
        palcorner_horse_present = True
        palcorner_restricted_escape_squares = stationary_candidates[0]["controlled_squares"]
    return {
        "pattern_id": "PALCORNER_HORSE_CHECKMATE",
        "pattern_name_zh": "挂角马",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "palcorner_square": palcorner_square,
            "palcorner_horse_present": palcorner_horse_present,
            "palcorner_restricted_escape_squares": palcorner_restricted_escape_squares,
            "palcorner_move_ply": int(palcorner_move["ply"]) if palcorner_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
            "stationary_horse_candidates": stationary_candidates,
        },
        "diagnostics": [
            "挂角马可以先行占位并控制一个将帅或宫内去路，再由其他棋子将死。",
            "马也可以跳入挂角位将军，随后逼出将帅应将或直接绝杀。",
        ],
    }


def recognize_angler_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    angler_targets = {"c7", "g7"} if defender == "black" else {"c2", "g2"}
    attacker_horse_piece = "N" if attacker == "red" else "n"
    defender_king_piece = "k" if defender == "black" else "K"
    attacker_trace, defender_trace = _attacker_and_defender_trace(fen, moves, attacker)

    angler_horses = sorted(
        square
        for square, piece in board.items()
        if piece == attacker_horse_piece and square in angler_targets
    )
    empty_escape_squares = {
        square for square in (
            _orthogonal_palace_neighbors(defender_king, defender)
            if defender_king else []
        ) if square not in board
    }
    angler_horse_contributions = {
        square: sorted(
            target
            for target, reasons in analysis["attacked_squares"].items()
            if (target == defender_king or target in empty_escape_squares)
            and any(
                reason["reason"] == "horse_attack"
                and reason["square"] == square
                for reason in reasons
            )
            and not any(
                reason["reason"] != "horse_attack"
                and _is_attacker_piece(board.get(reason["square"], ""), attacker)
                for reason in reasons
            )
        )
        for square in angler_horses
    }
    angler_horse_contributions = {
        square: targets
        for square, targets in angler_horse_contributions.items()
        if targets
    }

    angler_index: int | None = None
    angler_move: dict[str, object] | None = None
    for index, item in enumerate(attacker_trace):
        if (
            str(item["piece"]) == attacker_horse_piece
            and str(item["to_square"]) in angler_targets
            and bool(item["analysis"]["is_check"])
        ):
            angler_index = index
            angler_move = item
            break

    forced_king_reply = False
    immediate_finish = False
    if angler_move is not None and angler_index is not None:
        immediate_finish = bool(angler_move["analysis"]["is_checkmate"])
        if not immediate_finish and angler_index < len(defender_trace):
            reply = defender_trace[angler_index]
            forced_king_reply = (
                str(reply["piece"]) == defender_king_piece
                and str(reply["from_square"]) == str(angler_move["analysis"]["king_square"])
            )

    final_piece_type = str(attacker_trace[-1]["piece"]).upper() if attacker_trace else None
    final_checker_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )

    static_angler_support = bool(
        analysis["is_checkmate"]
        and angler_horse_contributions
        and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
    )
    dynamic_angler_support = bool(
        analysis["is_checkmate"]
        and angler_move
        and angler_horse_contributions
        and (
            immediate_finish
            or (
                forced_king_reply
                and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
            )
        )
    )
    detected = bool(static_angler_support or dynamic_angler_support)
    return {
        "pattern_id": "ANGLER_HORSE_CHECKMATE",
        "pattern_name_zh": "钓鱼马",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "angler_horse_squares": angler_horses,
            "angler_horse_contributions": angler_horse_contributions,
            "empty_escape_squares": sorted(empty_escape_squares),
            "angler_move_square": str(angler_move["to_square"]) if angler_move else None,
            "angler_move_ply": int(angler_move["ply"]) if angler_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
            "static_angler_support": static_angler_support,
        },
        "diagnostics": [
            "绝杀黑方时只检查红马是否稳占 c7/g7；绝杀红方时只检查黑马是否稳占 c2/g2。",
            "该马可以先手跳入钓鱼位将军，也可以作为既有钓鱼位支撑最后一击。",
            "随后再由车、马、炮或兵完成绝杀，因此构成钓鱼马。",
        ],
    }


def recognize_double_horses_drinking_spring_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    horse_piece = "N" if attacker == "red" else "n"
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    final_attack = attacker_trace[-1] if attacker_trace else None
    horse_squares = sorted(
        square for square, piece in board.items() if piece == horse_piece
    )
    palace_targets: set[str] = set()
    if defender_king:
        palace_targets.add(defender_king)
        palace_targets.update(_orthogonal_palace_neighbors(defender_king, defender))
    attacker_attacks = attacked_squares(board, attacker)
    horse_contributions: list[dict[str, object]] = []
    for square in horse_squares:
        attacked_targets = sorted(
            target
            for target in palace_targets
            if any(
                entry["square"] == square and entry["reason"] == "horse_attack"
                for entry in attacker_attacks.get(target, [])
            )
        )
        if attacked_targets:
            horse_contributions.append(
                {
                    "horse_square": square,
                    "attacked_targets": attacked_targets,
                }
            )
    defender_half_ready = bool(horse_squares) and all(
        int(square[1]) >= 5 if defender == "black" else int(square[1]) <= 4
        for square in horse_squares
    )
    final_checking_horses = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"]) == horse_piece and item["reason"] == "horse_attack"
    ]
    checking_moves = [item for item in attacker_trace if item["analysis"]["is_check"]]
    all_checks_by_horses = all(
        all(entry["reason"] == "horse_attack" for entry in item["analysis"]["checking_pieces"])
        for item in checking_moves
    ) and all(entry["reason"] == "horse_attack" for entry in analysis["checking_pieces"])
    detected = bool(
        analysis["is_checkmate"]
        and final_attack
        and str(final_attack["piece"]).upper() == "N"
        and len(horse_squares) >= 2
        and len(horse_contributions) >= 2
        and final_checking_horses
        and defender_half_ready
        and all_checks_by_horses
    )
    return {
        "pattern_id": "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE",
        "pattern_name_zh": "双马饮泉",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "horse_squares": horse_squares,
            "horse_contributions": horse_contributions,
            "final_checking_horse_squares": final_checking_horses,
            "final_piece_type": str(final_attack["piece"]).upper() if final_attack else None,
            "defender_half_ready": defender_half_ready,
            "all_checks_by_horses": all_checks_by_horses,
        },
        "diagnostics": [
            "攻击方终局至少保有两匹马，并且最后一着由马完成绝杀。",
            "两匹马都直接参与限制将帅；整条题目中攻击方每次将军都只能由马将军。",
            "因此该终局属于双马饮泉。",
        ],
    }


def recognize_tiger_silhouette_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    # The tiger horse must occupy a flank square in the defender's camp:
    # c6/g6 for Red's attack and c3/g3 for Black's attack.
    tiger_horse_targets = {"c6", "g6"} if attacker == "red" else {"c3", "g3"}
    horse_piece = "N" if attacker == "red" else "n"
    tiger_horses = sorted(
        square
        for square, piece in board.items()
        if piece == horse_piece and square in tiger_horse_targets
    )
    checking_support_pieces = [
        item
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() != "N"
    ]
    defender_escape_squares = set(_orthogonal_palace_neighbors(defender_king, defender)) if defender_king else set()
    tiger_horse_contributions = {
        square: sorted(
            target
            for target, reasons in analysis["attacked_squares"].items()
            if (target == defender_king or target in defender_escape_squares)
            and any(
                reason["reason"] == "horse_attack"
                and reason["square"] == square
                for reason in reasons
            )
        )
        for square in tiger_horses
    }
    tiger_horse_contributions = {
        square: targets
        for square, targets in tiger_horse_contributions.items()
        if targets
    }
    king_control_plies = []
    for ply in range(len(applied) + 1):
        position, _ = _apply_moves(fen, applied[:ply])
        historical_board = parse_fen(position)
        historical_king = next((sq for sq, piece in historical_board.items() if piece == ("k" if defender == "black" else "K")), None)
        if historical_king and any(
            entry["reason"] == "horse_attack" and entry["square"] in tiger_horse_targets
            for entry in attacked_squares(historical_board, attacker).get(historical_king, [])
        ):
            king_control_plies.append(ply)
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    tiger_horse_move_ply = next(
        (
            int(item["ply"])
            for item in attacker_trace
            if str(item["piece"]).upper() == "N"
            and str(item["to_square"]) in tiger_horse_targets
        ),
        None,
    )
    support_check_count = sum(
        1
        for item in attacker_trace
        if str(item["piece"]).upper() != "N" and bool(item["analysis"]["is_check"])
    )
    detected = bool(
        analysis["is_checkmate"]
        and defender_king
        and defender_king[0] in {"d", "f"}
        and king_control_plies
        and checking_support_pieces
    )
    return {
        "pattern_id": "TIGER_SILHOUETTE_CHECKMATE",
        "pattern_name_zh": "侧面虎",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "tiger_horse_squares": tiger_horses,
            "checking_support_squares": [item["square"] for item in checking_support_pieces],
            "tiger_horse_contributions": tiger_horse_contributions,
            "king_control_plies": king_control_plies,
            "tiger_horse_move_ply": tiger_horse_move_ply,
            "support_check_count": support_check_count,
        },
        "diagnostics": [
            "防守方将帅位于 d 路或 f 路肋道。",
            "攻击方的马必须进入对方阵营的 c6/c3/g6/g3 侧面虎马位。",
            "该马必须实际控制将帅周边的宫内活动位置，并由其他棋子参与最终攻击。",
        ],
    }


def recognize_horse_cannon_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    horse_piece = "N" if attacker == "red" else "n"
    defender_neighbors = (
        _orthogonal_palace_neighbors(defender_king, defender) if defender_king else []
    )
    cannon_horse_pairs: list[dict[str, object]] = []

    for item in analysis["checking_pieces"]:
        cannon_square = item["square"]
        if (
            item["reason"] != "cannon_screen"
            or board.get(cannon_square) != cannon_piece
            or not defender_king
        ):
            continue
        between_squares = _between(board, cannon_square, defender_king)
        occupied_between = [square for square in between_squares if square in board]
        if len(occupied_between) != 1:
            continue
        horse_square = occupied_between[0]
        if board.get(horse_square) != horse_piece:
            continue
        restricted_escape_squares = sorted(
            square
            for square in defender_neighbors
            if square == horse_square
            or any(
                attack["square"] == horse_square and attack["reason"] == "horse_attack"
                for attack in analysis["attacked_squares"].get(square, [])
            )
        )
        cannon_horse_pairs.append(
            {
                "cannon_square": cannon_square,
                "horse_square": horse_square,
                "axis": "file" if cannon_square[0] == defender_king[0] else "rank",
                "restricted_escape_squares": restricted_escape_squares,
            }
        )

    # The horse does not have to attack a palace neighbor directly. In a
    # classic horse-cannon mate it can serve as the cannon screen while the
    # other attacking pieces close the remaining escape squares.
    qualified_pairs = cannon_horse_pairs
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    final_attack = attacker_trace[-1] if attacker_trace else None
    final_cannon_finish = bool(
        final_attack
        and bool(final_attack["analysis"]["is_checkmate"])
        and str(final_attack["piece"]).upper() in {"C", "N"}
        and qualified_pairs
    )
    horse_move_ply = next(
        (
            int(item["ply"])
            for item in attacker_trace
            if str(item["piece"]).upper() == "N"
        ),
        None,
    )
    cannon_finish_ply = int(final_attack["ply"]) if final_cannon_finish else None
    detected = bool(
        analysis["is_checkmate"]
        and qualified_pairs
        and (not applied or final_cannon_finish)
    )
    return {
        "pattern_id": "HORSE_CANNON_CHECKMATE",
        "pattern_name_zh": "马后炮",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "cannon_horse_pairs": qualified_pairs,
            "pair_count": len(qualified_pairs),
            "final_cannon_finish": final_cannon_finish,
            "horse_move_ply": horse_move_ply,
            "cannon_finish_ply": cannon_finish_ply,
        },
        "diagnostics": [
            "最终形成将军的是一门炮，而且炮与将帅之间唯一的炮架正好是己方马。",
            "马可以直接控制宫内逃位，也可以作为炮架，由其他攻击子力共同封锁其余逃路。",
            "最后一步可以是炮移动，也可以是马走入炮架位置后完成绝杀。",
        ],
    }


def recognize_double_check_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)
    final_attack = attacker_trace[-1] if attacker_trace else None
    checking_piece_squares = [item["square"] for item in analysis["checking_pieces"]]
    checking_piece_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )
    checking_reasons = sorted({item["reason"] for item in analysis["checking_pieces"]})
    final_move_created_mate = bool(
        final_attack and bool(final_attack["analysis"]["is_checkmate"])
    )
    detected = bool(
        analysis["is_checkmate"]
        and len(checking_piece_squares) >= 2
        and (not applied or final_move_created_mate)
    )
    return {
        "pattern_id": "DOUBLE_CHECK_CHECKMATE",
        "pattern_name_zh": "双将",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "checking_piece_count": len(checking_piece_squares),
            "checking_piece_squares": checking_piece_squares,
            "checking_piece_types": checking_piece_types,
            "checking_reasons": checking_reasons,
            "final_move_piece_type": (
                str(final_attack["piece"]).upper() if final_attack else None
            ),
            "final_move_created_mate": final_move_created_mate,
        },
        "diagnostics": [
            "终局同时有两枚或以上攻击方棋子直接对将帅形成将军。",
            "防守方在双重将军下没有任何合法着法，因此属于双将绝杀。",
            "该标签可以与更具体的杀法名称并存，不会排斥其他阵型判断。",
        ],
    }


def recognize_octagon_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    octagon_targets = (
        {"d7", "d9", "f7", "f9"}
        if defender == "black"
        else {"d0", "d2", "f0", "f2"}
    )
    horse_piece = "N" if attacker == "red" else "n"
    attacker_trace, _defender_trace = _attacker_and_defender_trace(fen, moves, attacker)

    octagon_move = next(
        (
            item
            for item in attacker_trace
            if str(item["piece"]).upper() == "N"
            and str(item["to_square"]) in octagon_targets
        ),
        None,
    )
    static_octagon_horses = sorted(
        square
        for square, piece in board.items()
        if piece == horse_piece and square in octagon_targets
    )
    octagon_square = (
        str(octagon_move["to_square"])
        if octagon_move and str(octagon_move["to_square"]) in static_octagon_horses
        else (static_octagon_horses[0] if static_octagon_horses else None)
    )
    octagon_horse_present = bool(octagon_square)
    opposite_corner = {
        "d7": "f9",
        "f9": "d7",
        "f7": "d9",
        "d9": "f7",
        "d2": "f0",
        "f0": "d2",
        "f2": "d0",
        "d0": "f2",
    }.get(octagon_square)
    diagonal_corner_alignment = bool(
        octagon_square and defender_king == opposite_corner
    )
    defender_neighbors = (
        _orthogonal_palace_neighbors(defender_king, defender) if defender_king else []
    )
    palace_control_squares = (
        [defender_king, *defender_neighbors] if defender_king else defender_neighbors
    )
    restricted_escape_squares = sorted(
        square
        for square in palace_control_squares
        if any(
            attack["square"] == octagon_square and attack["reason"] == "horse_attack"
            for attack in analysis["attacked_squares"].get(square, [])
        )
    )
    final_attack = attacker_trace[-1] if attacker_trace else None
    final_checker_types = sorted(
        {
            board.get(item["square"], "").upper()
            for item in analysis["checking_pieces"]
        }
    )
    final_move_created_mate = bool(
        final_attack and bool(final_attack["analysis"]["is_checkmate"])
    )
    octagon_direct_checkmate = bool(
        octagon_square
        and any(item["square"] == octagon_square for item in analysis["checking_pieces"])
        and final_move_created_mate
    )
    detected = bool(
        analysis["is_checkmate"]
        and static_octagon_horses
        and octagon_horse_present
        and diagonal_corner_alignment
        and len(restricted_escape_squares) >= 2
        and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
        and (not applied or final_move_created_mate)
    )
    return {
        "pattern_id": "OCTAGON_HORSE_CHECKMATE",
        "pattern_name_zh": "八角马",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "octagon_square": octagon_square,
            "octagon_horse_squares": static_octagon_horses,
            "octagon_horse_present": octagon_horse_present,
            "opposite_corner": opposite_corner,
            "diagonal_corner_alignment": diagonal_corner_alignment,
            "restricted_escape_squares": restricted_escape_squares,
            "final_checker_types": final_checker_types,
            "octagon_move_ply": int(octagon_move["ply"]) if octagon_move else None,
            "final_move_created_mate": final_move_created_mate,
            "octagon_direct_checkmate": octagon_direct_checkmate,
        },
        "diagnostics": [
            "攻击方马位于对方九宫角位，并与对方将帅处于九宫对角位置。",
            "控制范围达到两个或以上才是八角马；只控制一个位置由挂角马负责。",
            "随后可以由另一匹马、车、炮或兵完成绝杀；只要八角马实际参与控制逃路即可。",
        ],
    }


def recognize_three_chariots_attacking_advisor_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    starting_board = parse_fen(fen)
    defender_advisor = "a" if defender == "black" else "A"
    starting_main_pieces = sorted(
        square
        for square, piece in starting_board.items()
        if _is_attacker_piece(piece, attacker) and piece.upper() in {"R", "P"}
    )
    starting_rooks = [
        square for square in starting_main_pieces if starting_board[square].upper() == "R"
    ]
    starting_pawns = [
        square for square in starting_main_pieces if starting_board[square].upper() == "P"
    ]
    final_checker_squares = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() in {"R", "P"}
    ]
    trace = _move_trace(fen, applied) if applied else []
    final_move_piece = trace[-1]["piece"].upper() if trace else None
    advisor_squares = sorted(
        square for square, piece in starting_board.items() if piece == defender_advisor
    )
    identities = build_piece_identity(fen)
    main_ids = {identities[square]: square for square in starting_main_pieces}
    participation: dict[str, list[str]] = {piece_id: [] for piece_id in main_ids}
    position = fen
    if position_analysis(fen)["side_to_move"] == defender:
        for checker in position_analysis(fen)["checking_pieces"]:
            piece_id = identities.get(checker["square"])
            if piece_id in participation:
                participation[piece_id].append("check")
    for item in trace:
        move = str(item["move"])
        piece_id = str(item["piece_id"])
        before = parse_fen(position)
        if piece_id in participation:
            if before.get(move[2:]) == defender_advisor:
                participation[piece_id].append("capture_advisor")
        identities = move_piece_identity(identities, move[:2], move[2:])
        for checker in item["analysis"]["checking_pieces"]:
            checker_id = identities.get(checker["square"])
            if checker_id in participation and "check" not in participation[checker_id]:
                participation[checker_id].append("check")
        position = apply_move(position, move)
    if defender_king:
        escape_squares = [square for square in _orthogonal_palace_neighbors(defender_king, defender) if not board.get(square)]
        for square, piece_id in identities.items():
            if piece_id in participation and any(
                any(attack["square"] == square for attack in analysis["attacked_squares"].get(target, []))
                for target in escape_squares
            ):
                participation[piece_id].append("control_escape")
    participating_squares = sorted(
        square for piece_id, square in main_ids.items() if participation[piece_id]
    )
    detected = bool(
        analysis["is_checkmate"]
        and not analysis["is_stalemate"]
        and len(participating_squares) >= 3
        and any(starting_board[square].upper() == "R" for square in participating_squares)
        and any(starting_board[square].upper() == "P" for square in participating_squares)
        and advisor_squares
        and final_checker_squares
        and final_move_piece in {"R", "P"}
    )
    return {
        "pattern_id": "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE",
        "pattern_name_zh": "三车闹士",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "starting_main_piece_squares": starting_main_pieces,
            "starting_rook_squares": starting_rooks,
            "starting_pawn_squares": starting_pawns,
            "defender_advisor_squares": advisor_squares,
            "final_checker_squares": final_checker_squares,
            "final_move_piece_type": final_move_piece,
            "participating_starting_squares": participating_squares,
            "participation": [
                {"starting_square": square, "piece_id": piece_id, "reasons": participation[piece_id]}
                for piece_id, square in main_ids.items()
            ],
        },
        "diagnostics": [
            "至少三枚车兵参与杀局，其中至少有一车和一兵。",
            "参与包括吃士、直接将军，或在终局控制将帅相邻的空逃格。",
        ],
    }


def recognize_two_devils_knocking_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = _infer_sides(current_fen)
    rank = "8" if defender == "black" else "1"
    eyes = ["d" + rank, "f" + rank]
    occurrences = []
    for ply in range(len(applied) + 1):
        position, _ = _apply_moves(fen, applied[:ply])
        state = parse_fen(position)
        if all((piece := state.get(sq, "")) and _is_attacker_piece(piece, attacker) and piece.upper() == "P" for sq in eyes):
            occurrences.append(ply)
    detected = bool(analysis["is_checkmate"] and occurrences)
    return {"pattern_id": "TWO_DEVILS_KNOCKING_CHECKMATE", "pattern_name_zh": "双鬼拍门", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"elephant_eye_squares": eyes, "occurrence_plies": occurrences}, "diagnostics": ["过程中两枚己方兵同时占据敌方象眼。"]}


def recognize_iron_bolt_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    # Only the advisor creates the iron-bolt gate.  An elephant alone is
    # not a sufficient lock because it can still participate in defense.
    lock_piece_set = {"a"} if defender == "black" else {"A"}
    attacker_line_pieces = {"C", "R"} if attacker == "red" else {"c", "r"}
    home_rank = _home_rank(defender)
    central_lock_candidates = sorted(
        square
        for square, piece in board.items()
        if piece in attacker_line_pieces and square[0] == "e"
    )
    if attacker_king and attacker_king[0] == "e":
        central_lock_candidates.append(attacker_king)
    central_lock_square = None
    central_lock_piece = None
    locked_midline_pieces: list[str] = []
    flank_checkers = [
        item
        for item in analysis["checking_pieces"]
        if item["square"][1] == home_rank
        and board.get(item["square"], "").upper() in {"R", "P"}
    ]
    if analysis["is_checkmate"] and flank_checkers and defender_king and defender_king[0] == "e":
        for lock_square in central_lock_candidates:
            between = _between(board, lock_square, defender_king)
            if not any(board.get(square) in lock_piece_set for square in between):
                continue
            # In a checkmate every defender has zero legal moves. Remove the
            # other checking pieces to test the advisor's independent pin.
            probe = dict(board)
            for checker in analysis["checking_pieces"]:
                source = checker["square"]
                if source != lock_square and probe.get(source, "").upper() != "K":
                    probe.pop(source, None)
            probe_fen = f"{_board_to_fen(probe)} {'w' if defender == 'red' else 'b'} - - 0 1"
            probe_moves = legal_moves(probe_fen)
            locked = []
            for square in between:
                if probe.get(square) not in lock_piece_set:
                    continue
                if any(move.startswith(square) for move in probe_moves):
                    continue
                # The lock itself must expose the general when the advisor
                # moves; immobility caused solely by another piece is not a pin.
                for target in _pseudo_legal_targets(probe, square, probe[square]):
                    moved = dict(probe)
                    moved[target] = moved.pop(square)
                    if any(
                        attack["square"] == lock_square
                        for attack in attacked_squares(moved, attacker).get(defender_king, [])
                    ):
                        locked.append(square)
                        break
            if locked:
                central_lock_square = lock_square
                central_lock_piece = board[lock_square]
                locked_midline_pieces = locked
                break
    detected = bool(
        analysis["is_checkmate"]
        and defender_king
        and defender_king[0] == "e"
        and defender_king[1] == home_rank
        and central_lock_square
        and locked_midline_pieces
        and flank_checkers
    )
    return {
        "pattern_id": "IRON_BOLT_CHECKMATE",
        "pattern_name_zh": "铁门栓",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "central_cannon_square": central_lock_square,
            "central_lock_square": central_lock_square,
            "central_lock_piece": central_lock_piece,
            "locked_midline_pieces": locked_midline_pieces,
            "flank_checker_squares": [item["square"] for item in flank_checkers],
            "flank_checker_types": sorted(
                {board.get(item["square"], "").upper() for item in flank_checkers}
            ),
        },
        "diagnostics": [
            "移除其他将军子后，中路士仍无合法走法，且走开会暴露中路车、炮或帅的将军。",
            "最终由底线车或兵实施将军，底线不限定为 d/f 肋道。",
            "防守方没有任何合法解杀，因此构成铁门栓。",
        ],
    }


def recognize_smothered_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = _infer_sides(current_fen)
    checkers = analysis["checking_pieces"]
    types = {board.get(x["square"], "").upper() for x in checkers}
    neighbors = _orthogonal_palace_neighbors(king, defender) if king else []
    outside = []
    for target in neighbors:
        # Test the checking pieces against the hypothetical king position; this
        # accounts for vacating the king square, screens and captures.
        hypothetical = board.copy()
        king_piece = hypothetical.pop(king)
        hypothetical[target] = king_piece
        attacks = attacked_squares(hypothetical, attacker).get(target, [])
        if not any(a["square"] == c["square"] for a in attacks for c in checkers):
            outside.append(target)
    blocked = [sq for sq in outside if (piece := board.get(sq, "")) and not _is_attacker_piece(piece, attacker) and piece.upper() != "A"]
    perpendicular_groups = []
    for checker in checkers:
        square = checker["square"]
        if not king or checker["reason"] not in {"line_attack", "cannon_screen"}:
            continue
        if square[0] == king[0]:
            targets = [target for target in neighbors if target[1] == king[1]]
        elif square[1] == king[1]:
            targets = [target for target in neighbors if target[0] == king[0]]
        else:
            continue
        blockers = [target for target in targets if (piece := board.get(target, "")) and not _is_attacker_piece(piece, attacker) and piece.upper() != "A"]
        perpendicular_groups.append({"checker": square, "targets": targets, "blockers": blockers})
    double_cannon = recognize_double_cannon_checkmate(fen, moves)["detected"]
    line_blocked = any(group["targets"] and len(group["targets"]) == len(group["blockers"]) for group in perpendicular_groups)
    non_line_blocked = not perpendicular_groups and bool(outside) and len(blocked) == len(outside)
    detected = bool(analysis["is_checkmate"] and checkers and "N" not in types and (line_blocked or non_line_blocked) and not double_cannon)
    return {"pattern_id": "SMOTHERED_CHECKMATE", "pattern_name_zh": "闷杀", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"checking_piece_types": sorted(types), "outside_checker_attack": outside, "defender_blockers": blocked, "perpendicular_groups": perpendicular_groups, "double_cannon": double_cannon}, "diagnostics": ["直线将军时，垂直于将军方向的宫内去路全部被己方非士棋子堵住；马将杀和重炮杀除外。"]}


def recognize_white_face_general(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    checking_pieces = [
        x["square"]
        for x in analysis["checking_pieces"]
    ]
    central_escape_square = f"e{defender_king[1]}" if defender_king else None
    central_file_open = bool(
        attacker_king
        and attacker_king[0] == "e"
        and central_escape_square
        and board.get(central_escape_square) is None
        and not any(
            square in board
            for square in _between(board, attacker_king, central_escape_square)
        )
    )
    geometry = bool(
        attacker_king
        and defender_king
        and attacker_king[0] == "e"
        and defender_king[0] in {"d", "f"}
        and central_file_open
        and checking_pieces
    )
    forced_block_capture = False
    if geometry and not analysis["is_checkmate"]:
        block_responses = [
            move for move in analysis["legal_moves"] if move[2] == defender_king[0]
        ]
        if block_responses:
            forced_block_capture = True
        for defensive_move in block_responses:
            blocked_fen = apply_move(current_fen, defensive_move)
            destination = defensive_move[2:]
            survives_capture = True
            for follow_up in legal_moves(blocked_fen):
                if follow_up[:2] in checking_pieces and follow_up[2:] == destination:
                    survives_capture = not position_analysis(
                        apply_move(blocked_fen, follow_up)
                    )["is_checkmate"]
                    break
            if survives_capture:
                forced_block_capture = False
                break
    detected = bool(geometry and (analysis["is_checkmate"] or forced_block_capture))
    return {
        "pattern_id": "WHITE_FACE_GENERAL",
        "pattern_name_zh": "白脸将",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "central_file": "e",
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "central_escape_square": central_escape_square,
            "attacker_general_on_central_file": bool(
                attacker_king and attacker_king[0] == "e"
            ),
            "central_file_open": central_file_open,
            "defender_general_on_adjacent_file": bool(
                defender_king and defender_king[0] in {"d", "f"}
            ),
            "line_piece_gives_file_check": bool(
                any(square[0] == defender_king[0] for square in checking_pieces)
                and defender_king
            ),
            "checking_piece_types": sorted(
                {board.get(square, "").upper() for square in checking_pieces}
            ),
            "is_checkmate": analysis["is_checkmate"],
        },
        "diagnostics": [
            "攻击方将帅在 e 路。",
            "防守方将帅在 d 路或 f 路。",
            "中路必须打通形成白脸；最后一步可由车、炮、马、兵等其他子力完成绝杀。",
        ],
    }


def recognize_stalemate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    _board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    detected = bool((not analysis["is_check"]) and (not analysis["legal_moves"]))
    return {
        "pattern_id": "STALEMATE",
        "pattern_name_zh": "困毙",
        "detected": detected,
        "causal": detected,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "features": {
            "attacker_side": attacker,
            "defender_side": defender,
            "attacker_general_square": attacker_king,
            "defender_general_square": defender_king,
            "legal_move_count": len(analysis["legal_moves"]),
            "is_check": analysis["is_check"],
            "is_stalemate": detected,
        },
        "diagnostics": [
            "防守方当前没有任何合法着法。",
            "防守方当前并未被将军。",
            "因此该局面属于困毙。",
        ],
    }


def recognize_pattern(
    pattern_id: str, fen: str, moves: list[str] | None = None
) -> dict:
    normalized = pattern_id.strip().upper()
    if normalized == "CROWNED_CHECKMATE":
        return recognize_crowned_checkmate(fen, moves)
    if normalized in {"CENTROID_CHECKMATE", "CENTROID_PAWN_CHECKMATE", "CENTROID_CHARIOT_CHECKMATE"}:
        return recognize_centroid_chariot_checkmate(fen, moves)
    if normalized == "CANNONS_SANDWICHING_CHARIOT_CHECKMATE":
        return recognize_cannons_sandwiching_chariot_checkmate(fen, moves)
    if normalized == "DOUBLE_CANNON_CHECKMATE":
        return recognize_double_cannon_checkmate(fen, moves)
    if normalized == "DISCOVERED_HORSE_CHECKMATE":
        return recognize_discovered_horse_checkmate(fen, moves)
    if normalized == "SMOTHERED_CANNON_CHECKMATE":
        return recognize_smothered_cannon_checkmate(fen, moves)
    if normalized == "HEAVEN_AND_EARTH_CANNON_CHECKMATE":
        return recognize_heaven_and_earth_cannon_checkmate(fen, moves)
    if normalized == "DRAWER_CHECKMATE":
        return recognize_drawer_checkmate(fen, moves)
    if normalized == "THROAT_CUTTING_CHECKMATE":
        return recognize_throat_cutting_checkmate(fen, moves)
    if normalized == "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE":
        return recognize_three_chariots_attacking_advisor_checkmate(fen, moves)
    if normalized == "TIGER_SILHOUETTE_CHECKMATE":
        return recognize_tiger_silhouette_checkmate(fen, moves)
    if normalized == "HORSE_CANNON_CHECKMATE":
        return recognize_horse_cannon_checkmate(fen, moves)
    if normalized == "OCTAGON_HORSE_CHECKMATE":
        return recognize_octagon_horse_checkmate(fen, moves)
    if normalized == "DOUBLE_CHECK_CHECKMATE":
        return recognize_double_check_checkmate(fen, moves)
    if normalized == "TWO_DEVILS_KNOCKING_CHECKMATE":
        return recognize_two_devils_knocking_checkmate(fen, moves)
    if normalized == "ELBOW_HORSE_CHECKMATE":
        return recognize_elbow_horse_checkmate(fen, moves)
    if normalized == "PALCORNER_HORSE_CHECKMATE":
        return recognize_palcorner_horse_checkmate(fen, moves)
    if normalized == "ANGLER_HORSE_CHECKMATE":
        return recognize_angler_horse_checkmate(fen, moves)
    if normalized == "IRON_BOLT_CHECKMATE":
        return recognize_iron_bolt_checkmate(fen, moves)
    if normalized == "DOUBLE_CHARIOTS_CHECKMATE":
        return recognize_double_chariots_checkmate(fen, moves)
    if normalized == "CENTROID_CHARIOT_CHECKMATE":
        return recognize_centroid_chariot_checkmate(fen, moves)
    if normalized == "SMOTHERED_CHECKMATE":
        return recognize_smothered_checkmate(fen, moves)
    if normalized == "WHITE_FACE_GENERAL":
        return recognize_white_face_general(fen, moves)
    if normalized == "STALEMATE":
        return recognize_stalemate(fen, moves)
    raise ValueError(f"不支援的 pattern_id：{pattern_id}")


def classify_mating_material(fen: str, analysis: dict) -> dict | None:
    """Classify actual checking pieces and pieces controlling king escape squares."""
    if not analysis["is_checkmate"]:
        return None
    board = parse_fen(fen)
    defender = analysis["side_to_move"]
    attacker = "black" if defender == "red" else "red"
    king = analysis["king_square"]
    king_piece = board[king]
    names = {"R": "车", "N": "马", "C": "炮", "P": "兵"}
    checkers = [{"square": item["square"], "piece": board[item["square"]].upper()}
                for item in analysis["checking_pieces"] if board[item["square"]].upper() in names]
    controls: dict[str, dict] = {}
    for target in _orthogonal_palace_neighbors(king, defender):
        occupant = board.get(target)
        if occupant and not _is_attacker_piece(occupant, attacker):
            continue
        hypothetical = board.copy()
        hypothetical.pop(king)
        hypothetical[target] = king_piece
        for attack in attacked_squares(hypothetical, attacker).get(target, []):
            square = attack["square"]
            piece = hypothetical[square].upper()
            if piece not in names:
                continue
            entry = controls.setdefault(square, {"square": square, "piece": piece, "targets": []})
            entry["targets"].append(target)
    types = {item["piece"] for item in checkers} | {item["piece"] for item in controls.values()}
    code = "".join(piece for piece in "RNCP" if piece in types)
    allowed = {"R", "N", "C", "P", "RN", "RC", "RP", "RNC", "RNP", "RCP", "NC", "NCP", "NP", "CP"}
    if code not in allowed:
        return None
    return {"id": code, "label_zh": "".join(names[piece] for piece in code) + ("杀" if len(code) == 1 else ""),
            "checking_pieces": checkers, "controlling_pieces": sorted(controls.values(), key=lambda item: item["square"])}


def analyze_patterns(fen: str, moves: list[str] | None = None, pattern_id: str | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    analysis = position_analysis(current_fen)
    if pattern_id:
        candidate_ids = [pattern_id.strip().upper()]
    else:
        candidate_ids = PATTERN_ORDER
    matches = [
        recognize_pattern(candidate_id, fen, moves)
        for candidate_id in candidate_ids
    ]
    detected = [match for match in matches if match["detected"]]
    excluded_by = {
        "DOUBLE_CHARIOTS_CHECKMATE": {"CENTROID_CHECKMATE", "TWO_DEVILS_KNOCKING_CHECKMATE", "CROWNED_CHECKMATE"},
        "DISCOVERED_HORSE_CHECKMATE": {"ELBOW_HORSE_CHECKMATE"},
        "PALCORNER_HORSE_CHECKMATE": {"HORSE_CANNON_CHECKMATE"},
        # 2026.11.05-v15 (expert review): 闷宫杀 already names this finish.
        "HEAVEN_AND_EARTH_CANNON_CHECKMATE": {"SMOTHERED_CANNON_CHECKMATE"},
    }
    present = {match["pattern_id"] for match in detected}
    if pattern_id and detected and detected[0]["pattern_id"] in excluded_by:
        present.update(
            candidate for candidate in excluded_by[detected[0]["pattern_id"]]
            if recognize_pattern(candidate, fen, moves)["detected"]
        )
    detected = [match for match in detected if not (excluded_by.get(match["pattern_id"], set()) & present)]
    checker_types = {parse_fen(current_fen).get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    if "C" in checker_types and checker_types.intersection({"R", "P"}) and any(match["pattern_id"] == "DOUBLE_CHECK_CHECKMATE" for match in detected):
        has_other = any(match["pattern_id"] != "DOUBLE_CHECK_CHECKMATE" for match in detected)
        if pattern_id and not has_other:
            has_other = any(recognize_pattern(candidate, fen, moves)["detected"] for candidate in PATTERN_ORDER if candidate != "DOUBLE_CHECK_CHECKMATE")
        if has_other:
            detected = [match for match in detected if match["pattern_id"] != "DOUBLE_CHECK_CHECKMATE"]
    best_match = detected[0] if detected else None
    return {
        "requested_pattern_id": pattern_id.strip().upper() if pattern_id else None,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "best_match": best_match,
        "matches": detected,
        "material_fallback": classify_mating_material(current_fen, analysis) if not pattern_id and not detected else None,
    }
