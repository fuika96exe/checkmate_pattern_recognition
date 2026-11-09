"""Checkmate pattern recognition: the dispatcher and ``analyze_patterns``.

Each pattern's recogniser moves to ``checkmate/patterns/`` in phase 0 step 7.
"""
from __future__ import annotations

from ..board import (
    apply_move,
    attacked_squares,
    legal_moves,
    parse_fen,
    position_analysis,
    squares_between,
)
from ..version import CHECKMATE_RULES_VERSION  # noqa: F401 - re-exported
from .geometry import (
    apply_moves,
    attacker_and_defender_trace,
    infer_sides,
    is_attacker_piece,
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
from .patterns.chariot import (
    recognize_double_chariots_checkmate,
    recognize_drawer_checkmate,
    recognize_iron_bolt_checkmate,
    recognize_three_chariots_attacking_advisor_checkmate,
    recognize_throat_cutting_checkmate,
    recognize_two_devils_knocking_checkmate,
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
