from __future__ import annotations

from .board import (
    _between,
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
    "EUNUCHS_CHASING_EMPEROR_CHECKMATE",
    "CENTROID_PAWN_CHECKMATE",
    "CANNONS_SANDWICHING_CHARIOT_CHECKMATE",
    "DOUBLE_CANNON_CHECKMATE",
    "DOUBLE_TOAST_CHECKMATE",
    "SMOTHERED_CANNON_CHECKMATE",
    "HEAVEN_AND_EARTH_CANNON_CHECKMATE",
    "IRON_BOLT_CHECKMATE",
    "DRAWER_CHECKMATE",
    "THROAT_CUTTING_CHECKMATE",
    "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE",
    "TWO_DEVILS_KNOCKING_CHECKMATE",
    "DOUBLE_CHARIOTS_CHECKMATE",
    "DISCOVERED_HORSE_CHECKMATE",
    "CENTROID_CHARIOT_CHECKMATE",
    "TIGER_SILHOUETTE_CHECKMATE",
    "HORSE_CANNON_CHECKMATE",
    "ELBOW_HORSE_CHECKMATE",
    "PALCORNER_HORSE_CHECKMATE",
    "ANGLER_HORSE_CHECKMATE",
    "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE",
    "SMOTHERED_CHECKMATE",
    "DOUBLE_CHECK_CHECKMATE",
    "WHITE_FACE_GENERAL",
    "STALEMATE",
]


def _apply_moves(fen: str, moves: list[str] | None) -> tuple[str, list[str]]:
    current_fen = fen
    applied: list[str] = []
    for move in moves or []:
        current_fen = apply_move(current_fen, move)
        applied.append(move)
    return current_fen, applied


def _move_trace(fen: str, moves: list[str] | None) -> list[dict[str, object]]:
    current_fen = fen
    identities = build_piece_identity(fen)
    trace: list[dict[str, object]] = []
    for ply, move in enumerate(moves or [], start=1):
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
    return trace


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


def recognize_centroid_chariot_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    centroid_square = "e8" if defender == "black" else "e1"
    centroid_rook = "R" if attacker == "red" else "r"
    centroid_present = board.get(centroid_square) == centroid_rook
    external_checkers = [
        item for item in analysis["checking_pieces"] if item["square"] != centroid_square
    ]
    detected = bool(centroid_present and analysis["is_checkmate"] and external_checkers)
    return {
        "pattern_id": "CENTROID_CHARIOT_CHECKMATE",
        "pattern_name_zh": "花心车",
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
            "centroid_square": centroid_square,
            "centroid_rook_present": centroid_present,
            "external_checker_count": len(external_checkers),
            "external_checker_squares": [item["square"] for item in external_checkers],
        },
        "diagnostics": [
            "攻击方有一辆车占据对方九宫中心 e8/e1。",
            "真正实施将军的是另一枚攻击方棋子，而不是这辆花心车本身。",
            "终局没有任何合法防守，因此构成花心车绝杀。",
        ],
    }


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
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]
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


def recognize_centroid_pawn_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    centroid_square = "e8" if defender == "black" else "e1"
    centroid_pawn = "P" if attacker == "red" else "p"
    centroid_present = board.get(centroid_square) == centroid_pawn
    pawn_checker = any(
        item["square"] == centroid_square and item["reason"] == "pawn_attack"
        for item in analysis["checking_pieces"]
    )
    controlled_neighbors = sorted(
        target
        for target in _orthogonal_palace_neighbors(centroid_square, defender)
        if any(
            entry["square"] == centroid_square
            for entry in analysis["attacked_squares"].get(target, [])
        )
    )
    detected = bool(
        analysis["is_checkmate"]
        and centroid_present
        and (pawn_checker or bool(controlled_neighbors))
    )
    return {
        "pattern_id": "CENTROID_PAWN_CHECKMATE",
        "pattern_name_zh": "èŠ±å¿ƒå…µ",
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
            "centroid_square": centroid_square,
            "centroid_pawn_present": centroid_present,
            "centroid_is_checker": pawn_checker,
            "controlled_neighbors": controlled_neighbors,
        },
        "diagnostics": [
            "æ”»å‡»æ–¹å…µå’è¿›å…¥äº†å¯¹æ–¹ä¹å®«ä¸­å¿ƒ e8/e1ï¼Œä¹Ÿå°±æ˜¯èŠ±å¿ƒä½ç½®ã€‚",
            "è¯¥å…µå’æœ¬èº«å‚ä¸Žäº†å¯¹ä¹å®«é€ƒä½çš„æŽ§åˆ¶ï¼Œæˆ–ç›´æŽ¥å½¢æˆå…µå°†ã€‚",
            "ç»ˆå±€å·²ç»æž„æˆç»æ€ï¼Œå› æ­¤å¯ä»¥é¢å¤–æ ‡è®°ä¸ºèŠ±å¿ƒå…µã€‚",
        ],
    }


def recognize_discovered_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    horse_piece = "N" if attacker == "red" else "n"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
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
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece)
    cannon_squares = sorted(
        square for square, piece in board.items() if piece == cannon_piece
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
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
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
        and final_checker_squares
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
            "final_checker_squares": final_checker_squares,
            "final_checker_types": final_checker_types,
            "checking_attack_count": len(checking_attackers),
            "attack_sequence_types": attack_sequence_types,
            "distinct_attacker_ids": distinct_attacker_ids,
        },
        "diagnostics": [
            "攻击方在同一侧边线同时集结一车双炮。",
            "终局由该侧的车或炮完成将军，并形成绝杀。",
            "若过程中出现车炮轮番压将，也一并归入夹车炮。",
        ],
    }


def recognize_double_toast_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    elephant_piece = "b" if defender == "black" else "B"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]

    sacrifice_move: dict[str, object] | None = None
    capture_reply: dict[str, object] | None = None
    reload_move: dict[str, object] | None = None
    for index in range(len(attacker_trace) - 1):
        first = attacker_trace[index]
        if str(first["piece"]).upper() != "C":
            continue
        if index >= len(defender_trace):
            continue
        reply = defender_trace[index]
        if (
            str(reply["piece"]) != elephant_piece
            or str(reply["to_square"]) != str(first["to_square"])
        ):
            continue
        second = attacker_trace[index + 1]
        if (
            str(second["piece"]).upper() == "C"
            and str(second["to_square"]) == str(first["to_square"])
        ):
            sacrifice_move = first
            capture_reply = reply
            reload_move = second
            break

    final_screen_square = None
    final_screen_piece = None
    checking_cannons = [
        item
        for item in analysis["checking_pieces"]
        if item["reason"] == "cannon_screen"
        and board.get(item["square"], "").upper() == "C"
    ]
    if defender_king and checking_cannons:
        between_squares = _between(board, checking_cannons[0]["square"], defender_king)
        occupied = [square for square in between_squares if square in board]
        if len(occupied) == 1:
            final_screen_square = occupied[0]
            final_screen_piece = board[final_screen_square]

    detected = bool(
        analysis["is_checkmate"]
        and sacrifice_move
        and capture_reply
        and reload_move
        and final_screen_piece == ("a" if defender == "black" else "A")
    )
    return {
        "pattern_id": "DOUBLE_TOAST_CHECKMATE",
        "pattern_name_zh": "双杯献酒",
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
            "sacrifice_square": str(sacrifice_move["to_square"]) if sacrifice_move else None,
            "capturing_elephant_from": str(capture_reply["from_square"]) if capture_reply else None,
            "reload_square": str(reload_move["to_square"]) if reload_move else None,
            "final_screen_square": final_screen_square,
            "final_screen_piece": final_screen_piece,
        },
        "diagnostics": [
            "攻击方先献出一门炮，让防守方的象吃到同一落点。",
            "随后第二门炮回到该点，复现闷宫型炮杀结构。",
            "防守方无合法解杀，因此构成双杯献酒。",
        ],
    }


def recognize_smothered_cannon_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    advisor_piece = "a" if defender == "black" else "A"
    checking_cannons = [
        item
        for item in analysis["checking_pieces"]
        if item["reason"] == "cannon_screen"
        and board.get(item["square"], "").upper() == "C"
    ]
    checking_piece_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )
    screen_square: str | None = None
    screen_piece: str | None = None
    if defender_king and checking_cannons:
        between_squares = _between(board, checking_cannons[0]["square"], defender_king)
        occupied = [square for square in between_squares if square in board]
        if len(occupied) == 1:
            screen_square = occupied[0]
            screen_piece = board[screen_square]
    detected = bool(
        analysis["is_checkmate"]
        and checking_cannons
        and checking_piece_types == ["C"]
        and screen_square
        and screen_piece == advisor_piece
    )
    return {
        "pattern_id": "SMOTHERED_CANNON_CHECKMATE",
        "pattern_name_zh": "闷宫杀",
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
            "checking_cannon_square": checking_cannons[0]["square"] if checking_cannons else None,
            "checking_piece_types": checking_piece_types,
            "screen_square": screen_square,
            "screen_piece": screen_piece,
            "screen_is_defender_advisor": screen_piece == advisor_piece,
        },
        "diagnostics": [
            "攻击方当前只能由单炮隔子将军，不能同时有其他棋子一起将军。",
            "炮架是防守方自己的士，形成闷宫结构。",
            "防守方没有任何合法解杀，因此构成闷宫杀。",
        ],
    }


def recognize_double_chariots_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece)
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
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
    immediate_rook_finish = bool(
        attacker_trace
        and str(attacker_trace[-1]["piece"]).upper() == "R"
        and attacker_trace[-1]["analysis"]["is_checkmate"]
        and checking_rooks
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
        },
        "diagnostics": [
            "攻击方两辆车分处不同列或不同行。",
            "最后一段攻击序列可以是双车交替将军，或由一辆车一步完成双车错绝杀。",
            "终局没有合法防守，因此构成双车错绝杀。",
        ],
    }


def recognize_heaven_and_earth_cannon_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    home_rank = _home_rank(defender)
    lock_piece_set = {"a", "b"} if defender == "black" else {"A", "B"}
    cannons = sorted(
        square for square, piece in board.items() if piece == cannon_piece
    )
    heaven_cannons = [square for square in cannons if square[1] == home_rank]
    earth_cannons = [square for square in cannons if square[0] == "e" and square[1] != home_rank]

    pre_final_fen = None
    pre_final_board = None
    final_move = None
    final_piece = None
    final_destination = None
    captured_piece = None
    if applied:
        pre_final_fen, _ = _apply_moves(fen, applied[:-1])
        pre_final_board = parse_fen(pre_final_fen)
        final_move = applied[-1]
        final_piece = pre_final_board.get(final_move[:2])
        final_destination = final_move[2:]
        captured_piece = pre_final_board.get(final_destination)

    controlled_targets: dict[str, list[str]] = {}
    if pre_final_board:
        pre_attacks = attacked_squares(pre_final_board, attacker)
        for target, entries in pre_attacks.items():
            if pre_final_board.get(target) not in lock_piece_set:
                continue
            cannon_sources = [
                entry["square"]
                for entry in entries
                if pre_final_board.get(entry["square"]) == cannon_piece
                and entry["square"] in heaven_cannons + earth_cannons
                and entry["reason"] == "cannon_screen"
            ]
            if cannon_sources:
                controlled_targets[target] = sorted(set(cannon_sources))

    distinct_control = False
    if controlled_targets:
        heaven_controls = {
            target
            for target, sources in controlled_targets.items()
            if any(source in heaven_cannons for source in sources)
        }
        earth_controls = {
            target
            for target, sources in controlled_targets.items()
            if any(source in earth_cannons for source in sources)
        }
        distinct_control = bool(
            heaven_controls
            and earth_controls
            and len(heaven_controls | earth_controls) >= 2
        )

    detected = bool(
        analysis["is_checkmate"]
        and defender_king
        and defender_king[0] == "e"
        and defender_king[1] == home_rank
        and heaven_cannons
        and earth_cannons
        and pre_final_board
        and final_piece
        and final_piece.upper() in {"R", "N", "P"}
        and final_destination
        and _palace_contains(final_destination, defender)
        and captured_piece in lock_piece_set
        and final_destination in controlled_targets
        and distinct_control
    )
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
            "controlled_targets": controlled_targets,
            "final_piece_type": final_piece.upper() if final_piece else None,
            "final_destination": final_destination,
            "captured_piece": captured_piece,
        },
        "diagnostics": [
            "攻击方同时具备一门对方底线炮与一门中路炮。",
            "双炮分别联控黑方宫内士象等关键守子。",
            "最后由车、马或兵吃入其中一个受控守子并完成将死，因此构成天地炮。",
        ],
    }


def recognize_throat_cutting_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    advisor_piece = "a" if defender == "black" else "A"
    cannon_piece = "C" if attacker == "red" else "c"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]
    center_square = "e8" if defender == "black" else "e1"

    penetration_index: int | None = None
    penetration_move: dict[str, object] | None = None
    recapture_reply: dict[str, object] | None = None
    pre_penetration_board: dict[str, str] | None = None

    current_before = fen
    for index, item in enumerate(attacker_trace):
        board_before = parse_fen(current_before)
        from_square = str(item["from_square"])
        to_square = str(item["to_square"])
        moving_piece = board_before.get(from_square)
        captured_piece = board_before.get(to_square)
        if (
            moving_piece
            and moving_piece.upper() in {"R", "P"}
            and to_square == center_square
            and captured_piece == advisor_piece
        ):
            penetration_index = index
            penetration_move = item
            pre_penetration_board = board_before
            if index < len(defender_trace):
                reply = defender_trace[index]
                if str(reply["to_square"]) == center_square:
                    recapture_reply = reply
            break
        current_before = apply_move(current_before, str(item["move"]))
        if index < len(defender_trace):
            current_before = apply_move(current_before, str(defender_trace[index]["move"]))

    lock_cannon_squares: list[str] = []
    controlled_guard_squares: list[str] = []
    reply_piece_type = None
    final_piece_type = str(attacker_trace[-1]["piece"]).upper() if attacker_trace else None
    if pre_penetration_board:
        pre_attacks = attacked_squares(pre_penetration_board, attacker)
        for square, piece in pre_penetration_board.items():
            if piece != cannon_piece:
                continue
            if any(
                attacked_piece["reason"] == "cannon_screen"
                for target, entries in pre_attacks.items()
                for attacked_piece in entries
                if attacked_piece["square"] == square
                and pre_penetration_board.get(target, "").lower() in {"a", "b"}
            ):
                lock_cannon_squares.append(square)
        controlled_guard_squares = sorted(
            square
            for square, piece in pre_penetration_board.items()
            if piece.lower() in {"a", "b"}
            and any(
                attack["square"] in lock_cannon_squares
                and attack["reason"] == "cannon_screen"
                for attack in pre_attacks.get(square, [])
            )
        )
    if recapture_reply:
        reply_piece_type = str(recapture_reply["piece"]).upper()

    detected = bool(
        analysis["is_checkmate"]
        and penetration_move
        and pre_penetration_board
        and lock_cannon_squares
        and controlled_guard_squares
        and final_piece_type in {"R", "P"}
    )
    return {
        "pattern_id": "THROAT_CUTTING_CHECKMATE",
        "pattern_name_zh": "大胆穿心",
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
            "center_square": center_square,
            "penetration_move_ply": int(penetration_move["ply"]) if penetration_move else None,
            "penetration_piece_type": (
                str(penetration_move["piece"]).upper() if penetration_move else None
            ),
            "lock_cannon_squares": lock_cannon_squares,
            "controlled_guard_squares": controlled_guard_squares,
            "reply_piece_type": reply_piece_type,
            "reply_to_center": bool(recapture_reply),
            "final_piece_type": final_piece_type,
        },
        "diagnostics": [
            "攻击方先以车或兵吃入对方中士，形成穿心的第一步。",
            "在该时刻，己方炮已经对宫内士象形成牵制，使中路防线出现缺口。",
            "后续再由车或兵完成绝杀，因此归入大胆穿心。",
        ],
    }


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
    cave_file = "f" if defender == "black" else "d"
    cave_ranks = {"8", "9"} if defender == "black" else {"0", "1"}
    king_tunnel_squares = {"e8", "e9"} if defender == "black" else {"e0", "e1"}
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]

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
        if any(square[0] != cave_file or square[1] not in cave_ranks for square in squares):
            continue
        if len(set(squares)) != 2:
            continue
        ordered = list(dict.fromkeys(squares))
        if len(ordered) != 2:
            continue
        first_square, second_square = ordered
        if first_square[0] != second_square[0] or abs(int(first_square[1]) - int(second_square[1])) != 1:
            continue
        replies = defender_trace[start : start + len(candidate) - 1]
        if replies and not all(
            str(reply["piece"]).upper() == "K" and str(reply["to_square"]) in king_tunnel_squares
            for reply in replies
        ):
            continue
        rook_cycles.append(
            {
                "rook_id": str(candidate[0]["piece_id"]),
                "rook_squares": squares,
                "cycle_start_ply": int(candidate[0]["ply"]),
                "reply_squares": [str(reply["to_square"]) for reply in replies],
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
            "cave_file": cave_file,
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
    elbow_targets = {"c8", "c2", "g8", "g2"}
    defender_king_piece = "k" if defender == "black" else "K"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]

    elbow_index: int | None = None
    elbow_move: dict[str, object] | None = None
    for index, item in enumerate(attacker_trace):
        if (
            str(item["piece"]).upper() == "N"
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
        elbow_square and board.get(elbow_square, "").upper() == "N"
    )

    final_piece_type = None
    if attacker_trace:
        final_piece_type = str(attacker_trace[-1]["piece"]).upper()
    final_checker_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )

    detected = bool(
        analysis["is_checkmate"]
        and elbow_move
        and elbow_horse_present
        and (
            immediate_finish
            or (
                forced_king_reply
                and any(piece_type in {"R", "C", "P"} for piece_type in final_checker_types)
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
            "elbow_move_ply": int(elbow_move["ply"]) if elbow_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
        },
        "diagnostics": [
            "攻击方有一着马跳入 c8/c2/g8/g2 的卧槽位并形成将军。",
            "若未当场绝杀，则先逼出对方将帅应将一步。",
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
    palcorner_targets = {"d2", "d7", "f2", "f7"}
    defender_king_piece = "k" if defender == "black" else "K"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]

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
        if not immediate_finish and palcorner_index < len(defender_trace):
            reply = defender_trace[palcorner_index]
            forced_king_reply = (
                str(reply["piece"]) == defender_king_piece
                and str(reply["from_square"])
                == str(palcorner_move["analysis"]["king_square"])
            )

    palcorner_square = str(palcorner_move["to_square"]) if palcorner_move else None
    palcorner_horse_present = bool(
        palcorner_square and board.get(palcorner_square, "").upper() == "N"
    )
    final_piece_type = str(attacker_trace[-1]["piece"]).upper() if attacker_trace else None
    final_checker_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )

    detected = bool(
        analysis["is_checkmate"]
        and palcorner_move
        and palcorner_horse_present
        and (
            immediate_finish
            or (
                forced_king_reply
                and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
            )
        )
    )
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
            "palcorner_move_ply": int(palcorner_move["ply"]) if palcorner_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
        },
        "diagnostics": [
            "攻击方有一着马跳入 d2/d7/f2/f7 的挂角位并形成将军。",
            "若未当场绝杀，则先逼出对方将帅应将一步。",
            "随后再由车、马、炮或兵完成绝杀，因此构成挂角马。",
        ],
    }


def recognize_angler_horse_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    angler_targets = {"c7", "g7", "c2", "g2"}
    defender_king_piece = "k" if defender == "black" else "K"
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    defender_trace = trace[1::2]

    angler_horses = sorted(
        square
        for square, piece in board.items()
        if piece.upper() == "N" and square in angler_targets
    )

    angler_index: int | None = None
    angler_move: dict[str, object] | None = None
    for index, item in enumerate(attacker_trace):
        if (
            str(item["piece"]).upper() == "N"
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
        and angler_horses
        and any(piece_type in {"R", "N", "C", "P"} for piece_type in final_checker_types)
    )
    dynamic_angler_support = bool(
        analysis["is_checkmate"]
        and angler_move
        and angler_horses
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
            "angler_move_square": str(angler_move["to_square"]) if angler_move else None,
            "angler_move_ply": int(angler_move["ply"]) if angler_move else None,
            "immediate_finish": immediate_finish,
            "forced_king_reply": forced_king_reply,
            "final_piece_type": final_piece_type,
            "final_checker_types": final_checker_types,
            "static_angler_support": static_angler_support,
        },
        "diagnostics": [
            "攻击方有马稳占 c7/g7/c2/g2 的钓鱼位，限制对方将帅活动。",
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
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
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
    detected = bool(
        analysis["is_checkmate"]
        and final_attack
        and str(final_attack["piece"]).upper() == "N"
        and len(horse_squares) >= 2
        and len(horse_contributions) >= 2
        and final_checking_horses
        and defender_half_ready
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
        },
        "diagnostics": [
            "攻击方终局至少保有两匹马，并且最后一着由马完成绝杀。",
            "两匹马都直接参与限制对方将帅及其宫内逃位，形成双马协同压迫。",
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
    tiger_horse_targets = {"c6", "c3", "g6", "g3"}
    horse_piece = "N" if attacker == "red" else "n"
    tiger_horses = sorted(
        square
        for square, piece in board.items()
        if piece == horse_piece and square in tiger_horse_targets
    )
    checking_rooks = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() == "R"
    ]
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    tiger_horse_move_ply = next(
        (
            int(item["ply"])
            for item in attacker_trace
            if str(item["piece"]).upper() == "N"
            and str(item["to_square"]) in tiger_horse_targets
        ),
        None,
    )
    rook_check_count = sum(
        1
        for item in attacker_trace
        if str(item["piece"]).upper() == "R" and bool(item["analysis"]["is_check"])
    )
    detected = bool(
        analysis["is_checkmate"]
        and defender_king
        and defender_king[0] in {"d", "f"}
        and tiger_horses
        and checking_rooks
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
            "checking_rook_squares": checking_rooks,
            "tiger_horse_move_ply": tiger_horse_move_ply,
            "rook_check_count": rook_check_count,
        },
        "diagnostics": [
            "防守方将帅位于 d 路或 f 路肋道。",
            "攻击方有一匹马稳占 c6/c3/g6/g3 的侧面虎马位。",
            "最终由车在侧翼连续压将并完成绝杀，因此构成侧面虎。",
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
            if any(
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

    qualified_pairs = [
        pair for pair in cannon_horse_pairs if pair["restricted_escape_squares"]
    ]
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
    final_attack = attacker_trace[-1] if attacker_trace else None
    final_cannon_finish = bool(
        final_attack
        and str(final_attack["piece"]).upper() == "C"
        and bool(final_attack["analysis"]["is_checkmate"])
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
            "最后形成将军的是一门炮，而且炮与将帅之间唯一的炮架正好是己方马。",
            "这匹马同时限制了对方将帅至少一个宫内逃位，属于马控位、炮发力的结构。",
            "终局无任何合法解将手段，因此构成马后炮。",
        ],
    }


def recognize_double_check_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    trace = _move_trace(fen, moves)
    attacker_trace = trace[::2]
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
    home_rank = _home_rank(defender)
    attacking_zone = sorted(
        square
        for square in starting_main_pieces
        if (
            square[1] == home_rank
            or _palace_contains(square, defender)
            or square[1] in (("7", "8") if defender == "black" else ("1", "2"))
            or square[1] == ("6" if defender == "black" else "3")
        )
    )
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
    detected = bool(
        analysis["is_checkmate"]
        and not analysis["is_stalemate"]
        and len(starting_main_pieces) == 3
        and len(starting_rooks) >= 1
        and len(starting_pawns) >= 1
        and len(attacking_zone) == 3
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
        },
        "diagnostics": [
            "起始局面有三枚车形主攻子力，组合可以是两车一兵或一车两兵。",
            "三枚主攻子力集中在对方九宫、宫门或下二路关键区域。",
            "它们围绕对方士的防守结构进行攻击、牵制、驱赶或消灭，并形成将死。",
        ],
    }


def recognize_two_devils_knocking_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    starting_board = parse_fen(fen)
    home_rank = _home_rank(defender)
    starting_ghost_squares = sorted(
        square
        for square, piece in starting_board.items()
        if _is_attacker_piece(piece, attacker)
        and piece.upper() in {"R", "P"}
    )
    # The two devils are the only two attacking rooks/pawns in the initial
    # position. Other pieces may assist, but a third rook/pawn makes this a
    # different pattern (for example Three Chariots Attacking the Advisor).
    attacking_ghost_squares = sorted(
        square
        for square in starting_ghost_squares
        if (
            square[1] == home_rank
            or _palace_contains(square, defender)
            or square[1] in (("7", "8") if defender == "black" else ("1", "2"))
            or square[1] == ("6" if defender == "black" else "3")
        )
    )
    final_checker_squares = [
        item["square"]
        for item in analysis["checking_pieces"]
        if board.get(item["square"], "").upper() in {"R", "P"}
    ]
    trace = _move_trace(fen, applied) if applied else []
    final_move_piece = trace[-1]["piece"].upper() if trace else None
    cannon_restraint_squares = sorted(
        square
        for square, piece in board.items()
        if _is_attacker_piece(piece, attacker)
        and piece.upper() == "C"
        and square[1] == home_rank
    )
    detected = bool(
        analysis["is_checkmate"]
        and not analysis["is_stalemate"]
        and len(starting_ghost_squares) == 2
        and len(attacking_ghost_squares) == 2
        and final_checker_squares
        and final_move_piece in {"R", "P"}
    )
    return {
        "pattern_id": "TWO_DEVILS_KNOCKING_CHECKMATE",
        "pattern_name_zh": "双鬼拍门",
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
            "ghost_piece_squares": attacking_ghost_squares,
            "ghost_piece_count": len(starting_ghost_squares),
            "starting_ghost_squares": starting_ghost_squares,
            "final_checker_squares": final_checker_squares,
            "final_move_piece_type": final_move_piece,
            "cannon_restraint_squares": cannon_restraint_squares,
        },
        "diagnostics": [
            "起始局面恰有两枚攻击方的车或兵作为双鬼，位置可在九宫、宫口或下二路关键线。",
            "最终杀棋必须由这两枚车或兵中的一枚直接完成，不能由第三枚车或兵替代。",
            "炮、马、象、士或帅可以辅助保护、牵制和封锁，但不改变双鬼的主体数量。",
        ],
    }


def recognize_iron_bolt_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    lock_piece_set = {"a", "b"} if defender == "black" else {"A", "B"}
    home_rank = _home_rank(defender)
    central_cannons = sorted(
        square
        for square, piece in board.items()
        if piece == cannon_piece and square[0] == "e"
    )
    central_cannon_square = None
    locked_midline_pieces: list[str] = []
    if defender_king and defender_king[0] == "e":
        for cannon_square in central_cannons:
            between = _between(board, cannon_square, defender_king)
            locked = [
                square
                for square in between
                if board.get(square) in lock_piece_set and square[0] == "e"
            ]
            if locked:
                central_cannon_square = cannon_square
                locked_midline_pieces = locked
                break
    flank_checkers = [
        item
        for item in analysis["checking_pieces"]
        if item["square"][0] in {"d", "f"}
        and item["square"][1] == home_rank
        and board.get(item["square"], "").upper() in {"R", "P"}
    ]
    detected = bool(
        analysis["is_checkmate"]
        and defender_king
        and defender_king[0] == "e"
        and defender_king[1] == home_rank
        and central_cannon_square
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
            "central_cannon_square": central_cannon_square,
            "locked_midline_pieces": locked_midline_pieces,
            "flank_checker_squares": [item["square"] for item in flank_checkers],
            "flank_checker_types": sorted(
                {board.get(item["square"], "").upper() for item in flank_checkers}
            ),
        },
        "diagnostics": [
            "攻击方以中炮控制 e 路士象，形成中路封锁。",
            "最终由 d 路或 f 路的底线攻击子实施将军。",
            "防守方没有任何合法解杀，因此构成铁门栓。",
        ],
    }


def recognize_smothered_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    checking_piece_types = sorted(
        {board.get(item["square"], "").upper() for item in analysis["checking_pieces"]}
    )
    allowed_checkers = {"R", "N", "P"}
    orthogonal_neighbors = (
        _orthogonal_palace_neighbors(defender_king, defender) if defender_king else []
    )
    defender_blockers = [
        square
        for square in orthogonal_neighbors
        if board.get(square, "").isalpha()
        and (
            board[square].islower() if defender == "black" else board[square].isupper()
        )
    ]
    occupied_neighbors = [square for square in orthogonal_neighbors if square in board]
    detected = bool(
        analysis["is_checkmate"]
        and checking_piece_types
        and set(checking_piece_types).issubset(allowed_checkers)
        and defender_blockers
        and len(occupied_neighbors) == len(orthogonal_neighbors)
    )
    return {
        "pattern_id": "SMOTHERED_CHECKMATE",
        "pattern_name_zh": "闷杀",
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
            "checking_piece_types": checking_piece_types,
            "orthogonal_neighbors": orthogonal_neighbors,
            "occupied_neighbors": occupied_neighbors,
            "defender_blockers": defender_blockers,
        },
        "diagnostics": [
            "防守方将帅在九宫内的上下左右去路都已被堵死。",
            "实施将军的是车、马或兵，而不是炮。",
            "防守方没有任何合法解杀，因此构成闷杀。",
        ],
    }


def recognize_white_face_general(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = _apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = _infer_sides(
        current_fen
    )
    checking_files = {"R", "C"}
    checking_pieces = [
        x["square"]
        for x in analysis["checking_pieces"]
        if board.get(x["square"], "").upper() in checking_files
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
        and any(square[0] == defender_king[0] for square in checking_pieces)
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
            "中路必须打通形成白脸，并由车或炮沿防守方将帅所在直线将军。",
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
    if normalized == "EUNUCHS_CHASING_EMPEROR_CHECKMATE":
        return recognize_eunuchs_chasing_emperor_checkmate(fen, moves)
    if normalized == "CENTROID_PAWN_CHECKMATE":
        return recognize_centroid_pawn_checkmate(fen, moves)
    if normalized == "CANNONS_SANDWICHING_CHARIOT_CHECKMATE":
        return recognize_cannons_sandwiching_chariot_checkmate(fen, moves)
    if normalized == "DOUBLE_CANNON_CHECKMATE":
        return recognize_double_cannon_checkmate(fen, moves)
    if normalized == "DOUBLE_TOAST_CHECKMATE":
        return recognize_double_toast_checkmate(fen, moves)
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
    if normalized == "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE":
        return recognize_double_horses_drinking_spring_checkmate(fen, moves)
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
    best_match = detected[0] if detected else None
    return {
        "requested_pattern_id": pattern_id.strip().upper() if pattern_id else None,
        "fen": current_fen,
        "moves": applied,
        "analysis": analysis,
        "best_match": best_match,
        "matches": detected,
    }
