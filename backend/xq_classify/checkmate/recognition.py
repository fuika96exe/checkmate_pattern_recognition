"""Checkmate pattern recognition: the dispatcher and ``analyze_patterns``.

Each pattern's recogniser moves to ``checkmate/patterns/`` in phase 0 step 7.
"""
from __future__ import annotations

from ..board import (
    apply_move,
    attacked_squares,
    board_to_fen,
    build_piece_identity,
    legal_moves,
    move_piece_identity,
    parse_fen,
    position_analysis,
    pseudo_legal_targets,
    squares_between,
)
from ..version import CHECKMATE_RULES_VERSION  # noqa: F401 - re-exported
from .geometry import (
    apply_moves,
    attacker_and_defender_trace,
    home_rank_of,
    infer_sides,
    is_attacker_piece,
    move_trace,
    orthogonal_palace_neighbors,
)
from .material import classify_mating_material
from .patterns.cannon import (
    recognize_cannons_sandwiching_chariot_checkmate,
    recognize_double_cannon_checkmate,
    recognize_heaven_and_earth_cannon_checkmate,
    recognize_horse_cannon_checkmate,
    recognize_smothered_cannon_checkmate,
)
from .patterns.horse import (
    recognize_angler_horse_checkmate,
    recognize_discovered_horse_checkmate,
    recognize_elbow_horse_checkmate,
    recognize_octagon_horse_checkmate,
    recognize_palcorner_horse_checkmate,
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



def recognize_centroid_chariot_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    center = "e8" if defender == "black" else "e1"
    piece = board.get(center, "")
    checkers = analysis["checking_pieces"]
    present = bool(piece and is_attacker_piece(piece, attacker) and piece.upper() in {"R", "P"})
    detected = bool(analysis["is_checkmate"] and present and checkers and all(x["square"] != center for x in checkers))
    return {"pattern_id": "CENTROID_CHECKMATE", "pattern_name_zh": "花心杀", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis,
            "features": {"attacker_side": attacker, "defender_side": defender, "centroid_square": center, "centroid_piece": piece or None, "centroid_is_checker": any(x["square"] == center for x in checkers)},
            "diagnostics": ["车或兵占据花心，由另一棋子将死，花心子不将军。"]}


def recognize_crowned_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    cannon_piece = "C" if attacker == "red" else "c"
    crown_front_square = "e8" if defender == "black" else "e1"
    front_piece = board.get(crown_front_square)
    supporting_front_piece = bool(
        front_piece
        and is_attacker_piece(front_piece, attacker)
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
        between_king = squares_between(source, defender_king)
        occupied_between_king = [square for square in between_king if square in board]
        if occupied_between_king != [crown_front_square]:
            continue
        between_front = squares_between(source, crown_front_square)
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
        if is_attacker_piece(piece, attacker)
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


def recognize_double_chariots_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
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
        for target in orthogonal_palace_neighbors(defender_king, defender):
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


def recognize_throat_cutting_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = infer_sides(current_fen)
    advisor = "a" if defender == "black" else "A"
    center = "e8" if defender == "black" else "e1"
    qualifying = []
    for item in move_trace(fen, moves):
        if not is_attacker_piece(str(item["piece"]), attacker) or str(item["piece"]).upper() not in {"R", "P"} or item["to_square"] != center:
            continue
        before, _ = apply_moves(fen, applied[:int(item["ply"]) - 1])
        previous = parse_fen(before)
        if previous.get(center) != advisor:
            continue
        other_advisors = [sq for sq, piece in previous.items() if piece == advisor and sq != center]
        after_capture, _ = apply_moves(fen, applied[:int(item["ply"])])
        defenders = sorted(move[:2] for move in legal_moves(after_capture) if move[2:] == center)
        if other_advisors or defenders:
            qualifying.append({"ply": item["ply"], "other_advisors": other_advisors, "protectors": defenders})
    detected = bool(analysis["is_checkmate"] and qualifying)
    return {"pattern_id": "THROAT_CUTTING_CHECKMATE", "pattern_name_zh": "大胆穿心", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"center_square": center, "qualifying_captures": qualifying}, "diagnostics": ["车或兵吃花心士，且当时另有士或被吃的士受保护。"]}


def recognize_drawer_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    rook_piece = "R" if attacker == "red" else "r"
    cannon_piece = "C" if attacker == "red" else "c"
    home_rank = home_rank_of(defender)
    # 2026.11.05-v15 (expert review): the drawer works on either rib file.
    cave_files = {"d", "f"}
    cave_ranks = {"8", "9"} if defender == "black" else {"0", "1"}
    king_tunnel_squares = {"e8", "e9"} if defender == "black" else {"e0", "e1"}
    attacker_trace, defender_trace = attacker_and_defender_trace(fen, moves, attacker)

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


def recognize_tiger_silhouette_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
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
    defender_escape_squares = set(orthogonal_palace_neighbors(defender_king, defender)) if defender_king else set()
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
        position, _ = apply_moves(fen, applied[:ply])
        historical_board = parse_fen(position)
        historical_king = next((sq for sq, piece in historical_board.items() if piece == ("k" if defender == "black" else "K")), None)
        if historical_king and any(
            entry["reason"] == "horse_attack" and entry["square"] in tiger_horse_targets
            for entry in attacked_squares(historical_board, attacker).get(historical_king, [])
        ):
            king_control_plies.append(ply)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
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


def recognize_double_check_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
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
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    starting_board = parse_fen(fen)
    defender_advisor = "a" if defender == "black" else "A"
    starting_main_pieces = sorted(
        square
        for square, piece in starting_board.items()
        if is_attacker_piece(piece, attacker) and piece.upper() in {"R", "P"}
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
    trace = move_trace(fen, applied) if applied else []
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
        escape_squares = [square for square in orthogonal_palace_neighbors(defender_king, defender) if not board.get(square)]
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
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = infer_sides(current_fen)
    rank = "8" if defender == "black" else "1"
    eyes = ["d" + rank, "f" + rank]
    occurrences = []
    for ply in range(len(applied) + 1):
        position, _ = apply_moves(fen, applied[:ply])
        state = parse_fen(position)
        if all((piece := state.get(sq, "")) and is_attacker_piece(piece, attacker) and piece.upper() == "P" for sq in eyes):
            occurrences.append(ply)
    detected = bool(analysis["is_checkmate"] and occurrences)
    return {"pattern_id": "TWO_DEVILS_KNOCKING_CHECKMATE", "pattern_name_zh": "双鬼拍门", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"elephant_eye_squares": eyes, "occurrence_plies": occurrences}, "diagnostics": ["过程中两枚己方兵同时占据敌方象眼。"]}


def recognize_iron_bolt_checkmate(
    fen: str, moves: list[str] | None = None
) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
        current_fen
    )
    # Only the advisor creates the iron-bolt gate.  An elephant alone is
    # not a sufficient lock because it can still participate in defense.
    lock_piece_set = {"a"} if defender == "black" else {"A"}
    attacker_line_pieces = {"C", "R"} if attacker == "red" else {"c", "r"}
    home_rank = home_rank_of(defender)
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
            between = squares_between(lock_square, defender_king)
            if not any(board.get(square) in lock_piece_set for square in between):
                continue
            # In a checkmate every defender has zero legal moves. Remove the
            # other checking pieces to test the advisor's independent pin.
            probe = dict(board)
            for checker in analysis["checking_pieces"]:
                source = checker["square"]
                if source != lock_square and probe.get(source, "").upper() != "K":
                    probe.pop(source, None)
            probe_fen = f"{board_to_fen(probe)} {'w' if defender == 'red' else 'b'} - - 0 1"
            probe_moves = legal_moves(probe_fen)
            locked = []
            for square in between:
                if probe.get(square) not in lock_piece_set:
                    continue
                if any(move.startswith(square) for move in probe_moves):
                    continue
                # The lock itself must expose the general when the advisor
                # moves; immobility caused solely by another piece is not a pin.
                for target in pseudo_legal_targets(probe, square, probe[square]):
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
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, king = infer_sides(current_fen)
    checkers = analysis["checking_pieces"]
    types = {board.get(x["square"], "").upper() for x in checkers}
    neighbors = orthogonal_palace_neighbors(king, defender) if king else []
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
    blocked = [sq for sq in outside if (piece := board.get(sq, "")) and not is_attacker_piece(piece, attacker) and piece.upper() != "A"]
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
        blockers = [target for target in targets if (piece := board.get(target, "")) and not is_attacker_piece(piece, attacker) and piece.upper() != "A"]
        perpendicular_groups.append({"checker": square, "targets": targets, "blockers": blockers})
    double_cannon = recognize_double_cannon_checkmate(fen, moves)["detected"]
    line_blocked = any(group["targets"] and len(group["targets"]) == len(group["blockers"]) for group in perpendicular_groups)
    non_line_blocked = not perpendicular_groups and bool(outside) and len(blocked) == len(outside)
    detected = bool(analysis["is_checkmate"] and checkers and "N" not in types and (line_blocked or non_line_blocked) and not double_cannon)
    return {"pattern_id": "SMOTHERED_CHECKMATE", "pattern_name_zh": "闷杀", "detected": detected, "causal": detected, "fen": current_fen, "moves": applied, "analysis": analysis, "features": {"checking_piece_types": sorted(types), "outside_checker_attack": outside, "defender_blockers": blocked, "perpendicular_groups": perpendicular_groups, "double_cannon": double_cannon}, "diagnostics": ["直线将军时，垂直于将军方向的宫内去路全部被己方非士棋子堵住；马将杀和重炮杀除外。"]}


def recognize_white_face_general(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
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
            for square in squares_between(attacker_king, central_escape_square)
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
    current_fen, applied = apply_moves(fen, moves)
    _board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(
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




_RECOGNIZERS = {
    'CROWNED_CHECKMATE': recognize_crowned_checkmate,
    'CENTROID_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CENTROID_PAWN_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CENTROID_CHARIOT_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CANNONS_SANDWICHING_CHARIOT_CHECKMATE': recognize_cannons_sandwiching_chariot_checkmate,
    'DOUBLE_CANNON_CHECKMATE': recognize_double_cannon_checkmate,
    'DISCOVERED_HORSE_CHECKMATE': recognize_discovered_horse_checkmate,
    'SMOTHERED_CANNON_CHECKMATE': recognize_smothered_cannon_checkmate,
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE': recognize_heaven_and_earth_cannon_checkmate,
    'DRAWER_CHECKMATE': recognize_drawer_checkmate,
    'THROAT_CUTTING_CHECKMATE': recognize_throat_cutting_checkmate,
    'THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE': recognize_three_chariots_attacking_advisor_checkmate,
    'TIGER_SILHOUETTE_CHECKMATE': recognize_tiger_silhouette_checkmate,
    'HORSE_CANNON_CHECKMATE': recognize_horse_cannon_checkmate,
    'OCTAGON_HORSE_CHECKMATE': recognize_octagon_horse_checkmate,
    'DOUBLE_CHECK_CHECKMATE': recognize_double_check_checkmate,
    'TWO_DEVILS_KNOCKING_CHECKMATE': recognize_two_devils_knocking_checkmate,
    'ELBOW_HORSE_CHECKMATE': recognize_elbow_horse_checkmate,
    'PALCORNER_HORSE_CHECKMATE': recognize_palcorner_horse_checkmate,
    'ANGLER_HORSE_CHECKMATE': recognize_angler_horse_checkmate,
    'IRON_BOLT_CHECKMATE': recognize_iron_bolt_checkmate,
    'DOUBLE_CHARIOTS_CHECKMATE': recognize_double_chariots_checkmate,
    'SMOTHERED_CHECKMATE': recognize_smothered_checkmate,
    'WHITE_FACE_GENERAL': recognize_white_face_general,
    'STALEMATE': recognize_stalemate,
}

# A pattern is dropped when one of the patterns listed for it is also present.
_EXCLUDED_BY = {
    'DOUBLE_CHARIOTS_CHECKMATE': {'CENTROID_CHECKMATE', 'TWO_DEVILS_KNOCKING_CHECKMATE', 'CROWNED_CHECKMATE'},
    'DISCOVERED_HORSE_CHECKMATE': {'ELBOW_HORSE_CHECKMATE'},
    'PALCORNER_HORSE_CHECKMATE': {'HORSE_CANNON_CHECKMATE'},
    # 2026.11.05-v15 (expert review): 闷宫杀 already names this finish.
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE': {'SMOTHERED_CANNON_CHECKMATE'},
}
_DOUBLE_CHECK = 'DOUBLE_CHECK_CHECKMATE'


def recognize_pattern(pattern_id: str, fen: str, moves: list[str] | None = None) -> dict:
    recognizer = _RECOGNIZERS.get(pattern_id.strip().upper())
    if recognizer is None:
        raise ValueError(f'不支援的 pattern_id：{pattern_id}')
    return recognizer(fen, moves)


def _apply_exclusions(detected: list[dict], request: tuple[str | None, str, list[str] | None]) -> list[dict]:
    pattern_id, fen, moves = request
    present = {match['pattern_id'] for match in detected}
    if pattern_id and detected and detected[0]['pattern_id'] in _EXCLUDED_BY:
        present.update(
            candidate for candidate in _EXCLUDED_BY[detected[0]['pattern_id']]
            if recognize_pattern(candidate, fen, moves)['detected']
        )
    return [match for match in detected if not (_EXCLUDED_BY.get(match['pattern_id'], set()) & present)]


def _drop_redundant_double_check(
    detected: list[dict], position: tuple[str, dict], request: tuple[str | None, str, list[str] | None],
) -> list[dict]:
    """A cannon check alongside a chariot or pawn check is named by the other pattern, when there is one."""
    pattern_id, fen, moves = request
    current_fen, analysis = position
    checker_types = {parse_fen(current_fen).get(item['square'], '').upper() for item in analysis['checking_pieces']}
    if not ('C' in checker_types and checker_types.intersection({'R', 'P'})
            and any(match['pattern_id'] == _DOUBLE_CHECK for match in detected)):
        return detected
    has_other = any(match['pattern_id'] != _DOUBLE_CHECK for match in detected)
    if pattern_id and not has_other:
        has_other = any(recognize_pattern(candidate, fen, moves)['detected']
                        for candidate in PATTERN_ORDER if candidate != _DOUBLE_CHECK)
    return [match for match in detected if match['pattern_id'] != _DOUBLE_CHECK] if has_other else detected


def analyze_patterns(fen: str, moves: list[str] | None = None, pattern_id: str | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    analysis = position_analysis(current_fen)
    candidate_ids = [pattern_id.strip().upper()] if pattern_id else PATTERN_ORDER
    matches = [recognize_pattern(candidate_id, fen, moves) for candidate_id in candidate_ids]
    request = (pattern_id, fen, moves)
    detected = _apply_exclusions([match for match in matches if match['detected']], request)
    detected = _drop_redundant_double_check(detected, (current_fen, analysis), request)
    return {
        'requested_pattern_id': pattern_id.strip().upper() if pattern_id else None,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'best_match': detected[0] if detected else None,
        'matches': detected,
        'material_fallback': classify_mating_material(current_fen, analysis) if not pattern_id and not detected else None,
    }
