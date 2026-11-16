# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""Checkmates read from the general's own surroundings and from the way it is checked.

Patterns: centroid (花心杀), crowned (平顶冠), tiger silhouette (侧面虎), double check (双将),
smothered (闷杀), white face general (白脸将) and stalemate (困毙).
"""

from ...board import apply_move, attacked_squares, legal_moves, parse_fen, position_analysis, squares_between
from ..geometry import (
    apply_moves,
    attacker_and_defender_trace,
    infer_sides,
    is_attacker_piece,
    orthogonal_palace_neighbors,
)
from .cannon import recognize_double_cannon_checkmate


def recognize_centroid_chariot_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, _attacker_king, _defender_king = infer_sides(current_fen)
    center = 'e8' if defender == 'black' else 'e1'
    piece = board.get(center, '')
    checkers = analysis['checking_pieces']
    present = bool(piece and is_attacker_piece(piece, attacker) and piece.upper() in {'R', 'P'})
    detected = bool(analysis['is_checkmate'] and present and checkers and all(x['square'] != center for x in checkers))
    return {
        'pattern_id': 'CENTROID_CHECKMATE',
        'pattern_name_zh': '花心杀',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'attacker_side': attacker,
            'defender_side': defender,
            'centroid_square': center,
            'centroid_piece': piece or None,
            'centroid_is_checker': any(x['square'] == center for x in checkers),
        },
        'diagnostics': ['车或兵占据花心，由另一棋子将死，花心子不将军。'],
    }


def _crown_cannon_square(
    board: dict[str, str],
    checking_pieces: list[dict],
    cannon_piece: str,
    crown_front_square: str,
    defender_king: str | None,
) -> str | None:
    """The first checking cannon that screens through the crown piece alone, or ``None``."""
    for item in checking_pieces:
        if item['reason'] != 'cannon_screen':
            continue
        source = item['square']
        if board.get(source) != cannon_piece or not defender_king:
            continue
        between_king = squares_between(source, defender_king)
        occupied_between_king = [square for square in between_king if square in board]
        if occupied_between_king != [crown_front_square]:
            continue
        between_front = squares_between(source, crown_front_square)
        if any(square in board for square in between_front):
            continue
        return source
    return None


def _auxiliary_crown_pieces(board: dict[str, str], attacker: str, crown_front_square: str) -> list[str]:
    """The attacker's other chariots and pawns on the crown piece's rank."""
    return sorted(
        square
        for square, piece in board.items()
        if is_attacker_piece(piece, attacker)
        and piece.upper() in {'R', 'P'}
        and square[1] == crown_front_square[1]
        and square != crown_front_square
    )


def recognize_crowned_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    cannon_piece = 'C' if attacker == 'red' else 'c'
    crown_front_square = 'e8' if defender == 'black' else 'e1'
    front_piece = board.get(crown_front_square)
    supporting_front_piece = bool(
        front_piece and is_attacker_piece(front_piece, attacker) and front_piece.upper() in {'R', 'P'}
    )
    cannon_square = _crown_cannon_square(
        board, analysis['checking_pieces'], cannon_piece, crown_front_square, defender_king
    )
    clear_cannon_path = cannon_square is not None
    checking_front_piece = any(
        item['square'] == crown_front_square and item['reason'] in {'line_attack', 'pawn_attack'}
        for item in analysis['checking_pieces']
    )
    auxiliary_crown_pieces = _auxiliary_crown_pieces(board, attacker, crown_front_square)
    detected = bool(
        analysis['is_checkmate']
        and supporting_front_piece
        and cannon_square
        and clear_cannon_path
        and checking_front_piece
        and len(analysis['checking_pieces']) >= 2
    )
    return {
        'pattern_id': 'CROWNED_CHECKMATE',
        'pattern_name_zh': '平顶冠',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'attacker_side': attacker,
            'defender_side': defender,
            'attacker_general_square': attacker_king,
            'defender_general_square': defender_king,
            'crown_front_square': crown_front_square,
            'front_piece': front_piece,
            'cannon_square': cannon_square,
            'clear_cannon_path': clear_cannon_path,
            'auxiliary_crown_pieces': auxiliary_crown_pieces,
            'checking_piece_count': len(analysis['checking_pieces']),
        },
        'diagnostics': [
            '攻击方有车或兵顶在将帅正前方，形成冠顶的正面压迫。',
            '其后方另有一门中炮透过该前线棋子形成空心炮双将。',
            '终局无合法解杀，因此构成平顶冠。',
        ],
    }


def _tiger_horse_contributions(
    analysis: dict, tiger_horses: list[str], defender_king: str | None, escape_squares: set[str]
) -> dict[str, list[str]]:
    """For each tiger horse that has any, the general's square and palace exits it attacks."""
    contributions = {
        square: sorted(
            target
            for target, reasons in analysis['attacked_squares'].items()
            if (target == defender_king or target in escape_squares)
            and any(reason['reason'] == 'horse_attack' and reason['square'] == square for reason in reasons)
        )
        for square in tiger_horses
    }
    return {square: targets for square, targets in contributions.items() if targets}


def _king_control_plies(
    fen: str, applied: list[str], attacker: str, defender: str, tiger_horse_targets: set[str]
) -> list[int]:
    """The plies of the line, 0 being the start, at which a horse on a tiger square attacks the general."""
    king_piece = 'k' if defender == 'black' else 'K'
    plies = []
    for ply in range(len(applied) + 1):
        position, _ = apply_moves(fen, applied[:ply])
        historical_board = parse_fen(position)
        historical_king = next((sq for sq, piece in historical_board.items() if piece == king_piece), None)
        if historical_king and any(
            entry['reason'] == 'horse_attack' and entry['square'] in tiger_horse_targets
            for entry in attacked_squares(historical_board, attacker).get(historical_king, [])
        ):
            plies.append(ply)
    return plies


def _tiger_horse_move_ply(attacker_trace: list[dict], tiger_horse_targets: set[str]) -> int | None:
    """The first ply on which one of the attacker's horses lands on a tiger square, or ``None``."""
    return next(
        (
            int(item['ply'])
            for item in attacker_trace
            if str(item['piece']).upper() == 'N' and str(item['to_square']) in tiger_horse_targets
        ),
        None,
    )


def recognize_tiger_silhouette_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    # The tiger horse must occupy a flank square in the defender's camp:
    # c6/g6 for Red's attack and c3/g3 for Black's attack.
    tiger_horse_targets = {'c6', 'g6'} if attacker == 'red' else {'c3', 'g3'}
    horse_piece = 'N' if attacker == 'red' else 'n'
    tiger_horses = sorted(
        square for square, piece in board.items() if piece == horse_piece and square in tiger_horse_targets
    )
    checking_support_pieces = [
        item for item in analysis['checking_pieces'] if board.get(item['square'], '').upper() != 'N'
    ]
    defender_escape_squares = set(orthogonal_palace_neighbors(defender_king, defender)) if defender_king else set()
    tiger_horse_contributions = _tiger_horse_contributions(
        analysis, tiger_horses, defender_king, defender_escape_squares
    )
    king_control_plies = _king_control_plies(fen, applied, attacker, defender, tiger_horse_targets)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    tiger_horse_move_ply = _tiger_horse_move_ply(attacker_trace, tiger_horse_targets)
    support_check_count = sum(
        1 for item in attacker_trace if str(item['piece']).upper() != 'N' and bool(item['analysis']['is_check'])
    )
    detected = bool(
        analysis['is_checkmate']
        and defender_king
        and defender_king[0] in {'d', 'f'}
        and king_control_plies
        and checking_support_pieces
    )
    return {
        'pattern_id': 'TIGER_SILHOUETTE_CHECKMATE',
        'pattern_name_zh': '侧面虎',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'attacker_side': attacker,
            'defender_side': defender,
            'attacker_general_square': attacker_king,
            'defender_general_square': defender_king,
            'tiger_horse_squares': tiger_horses,
            'checking_support_squares': [item['square'] for item in checking_support_pieces],
            'tiger_horse_contributions': tiger_horse_contributions,
            'king_control_plies': king_control_plies,
            'tiger_horse_move_ply': tiger_horse_move_ply,
            'support_check_count': support_check_count,
        },
        'diagnostics': [
            '防守方将帅位于 d 路或 f 路肋道。',
            '攻击方的马必须进入对方阵营的 c6/c3/g6/g3 侧面虎马位。',
            '该马必须实际控制将帅周边的宫内活动位置，并由其他棋子参与最终攻击。',
        ],
    }


def recognize_double_check_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    final_attack = attacker_trace[-1] if attacker_trace else None
    checking_piece_squares = [item['square'] for item in analysis['checking_pieces']]
    checking_piece_types = sorted({board.get(item['square'], '').upper() for item in analysis['checking_pieces']})
    checking_reasons = sorted({item['reason'] for item in analysis['checking_pieces']})
    final_move_created_mate = bool(final_attack and bool(final_attack['analysis']['is_checkmate']))
    detected = bool(
        analysis['is_checkmate'] and len(checking_piece_squares) >= 2 and (not applied or final_move_created_mate)
    )
    return {
        'pattern_id': 'DOUBLE_CHECK_CHECKMATE',
        'pattern_name_zh': '双将',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'attacker_side': attacker,
            'defender_side': defender,
            'attacker_general_square': attacker_king,
            'defender_general_square': defender_king,
            'checking_piece_count': len(checking_piece_squares),
            'checking_piece_squares': checking_piece_squares,
            'checking_piece_types': checking_piece_types,
            'checking_reasons': checking_reasons,
            'final_move_piece_type': str(final_attack['piece']).upper() if final_attack else None,
            'final_move_created_mate': final_move_created_mate,
        },
        'diagnostics': [
            '终局同时有两枚或以上攻击方棋子直接对将帅形成将军。',
            '防守方在双重将军下没有任何合法着法，因此属于双将绝杀。',
            '该标签可以与更具体的杀法名称并存，不会排斥其他阵型判断。',
        ],
    }


def _squares_outside_checker_attack(
    board: dict[str, str], king: str | None, neighbors: list[str], attacker: str, checkers: list[dict]
) -> list[str]:
    """The palace neighbours where the general would not be attacked by any piece now checking it."""
    outside = []
    for target in neighbors:
        # Test the checking pieces against the hypothetical king position; this
        # accounts for vacating the king square, screens and captures.
        hypothetical = board.copy()
        king_piece = hypothetical.pop(king)
        hypothetical[target] = king_piece
        attacks = attacked_squares(hypothetical, attacker).get(target, [])
        if not any(a['square'] == c['square'] for a in attacks for c in checkers):
            outside.append(target)
    return outside


def _is_defender_blocker(board: dict[str, str], square: str, attacker: str) -> bool:
    """Whether the square holds one of the defender's own pieces other than an advisor."""
    piece = board.get(square, '')
    return bool(piece and not is_attacker_piece(piece, attacker) and piece.upper() != 'A')


def _perpendicular_targets(checker_square: str, king: str, neighbors: list[str]) -> list[str] | None:
    """The palace neighbours across the line of check, or ``None`` when the checker shares no line with the general."""
    if checker_square[0] == king[0]:
        return [target for target in neighbors if target[1] == king[1]]
    if checker_square[1] == king[1]:
        return [target for target in neighbors if target[0] == king[0]]
    return None


def _perpendicular_groups(
    board: dict[str, str], checkers: list[dict], king: str | None, neighbors: list[str], attacker: str
) -> list[dict]:
    """One entry per line check: the checker, the squares across its line and which of them are blocked."""
    groups = []
    for checker in checkers:
        square = checker['square']
        if not king or checker['reason'] not in {'line_attack', 'cannon_screen'}:
            continue
        targets = _perpendicular_targets(square, king, neighbors)
        if targets is None:
            continue
        blockers = [target for target in targets if _is_defender_blocker(board, target, attacker)]
        groups.append({'checker': square, 'targets': targets, 'blockers': blockers})
    return groups


def recognize_smothered_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, _attacker_king, king = infer_sides(current_fen)
    checkers = analysis['checking_pieces']
    types = {board.get(x['square'], '').upper() for x in checkers}
    neighbors = orthogonal_palace_neighbors(king, defender) if king else []
    outside = _squares_outside_checker_attack(board, king, neighbors, attacker, checkers)
    blocked = [sq for sq in outside if _is_defender_blocker(board, sq, attacker)]
    perpendicular_groups = _perpendicular_groups(board, checkers, king, neighbors, attacker)
    double_cannon = recognize_double_cannon_checkmate(fen, moves)['detected']
    line_blocked = any(
        group['targets'] and len(group['targets']) == len(group['blockers']) for group in perpendicular_groups
    )
    non_line_blocked = not perpendicular_groups and bool(outside) and len(blocked) == len(outside)
    detected = bool(
        analysis['is_checkmate']
        and checkers
        and 'N' not in types
        and (line_blocked or non_line_blocked)
        and not double_cannon
    )
    return {
        'pattern_id': 'SMOTHERED_CHECKMATE',
        'pattern_name_zh': '闷杀',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'checking_piece_types': sorted(types),
            'outside_checker_attack': outside,
            'defender_blockers': blocked,
            'perpendicular_groups': perpendicular_groups,
            'double_cannon': double_cannon,
        },
        'diagnostics': ['直线将军时，垂直于将军方向的宫内去路全部被己方非士棋子堵住；马将杀和重炮杀除外。'],
    }


def _central_file_open(board: dict[str, str], attacker_king: str | None, central_escape_square: str | None) -> bool:
    """Whether the central file is empty from the attacking general up to the escape square."""
    return bool(
        attacker_king
        and attacker_king[0] == 'e'
        and central_escape_square
        and board.get(central_escape_square) is None
        and not any(square in board for square in squares_between(attacker_king, central_escape_square))
    )


def _block_survives_capture(current_fen: str, defensive_move: str, checking_pieces: list[str]) -> bool:
    """False only when the first capture of the blocker by a checking piece is checkmate."""
    blocked_fen = apply_move(current_fen, defensive_move)
    destination = defensive_move[2:]
    for follow_up in legal_moves(blocked_fen):
        if follow_up[:2] in checking_pieces and follow_up[2:] == destination:
            return not position_analysis(apply_move(blocked_fen, follow_up))['is_checkmate']
    return True


def _is_forced_block_capture(current_fen: str, analysis: dict, defender_king: str, checking_pieces: list[str]) -> bool:
    """Whether the defender has moves onto the general's file and every one is captured with mate."""
    block_responses = [move for move in analysis['legal_moves'] if move[2] == defender_king[0]]
    return bool(block_responses) and not any(
        _block_survives_capture(current_fen, move, checking_pieces) for move in block_responses
    )


def recognize_white_face_general(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    checking_pieces = [x['square'] for x in analysis['checking_pieces']]
    central_escape_square = f'e{defender_king[1]}' if defender_king else None
    central_file_open = _central_file_open(board, attacker_king, central_escape_square)
    geometry = bool(
        attacker_king
        and defender_king
        and attacker_king[0] == 'e'
        and defender_king[0] in {'d', 'f'}
        and central_file_open
        and checking_pieces
    )
    forced_block_capture = (
        geometry
        and not analysis['is_checkmate']
        and _is_forced_block_capture(current_fen, analysis, defender_king, checking_pieces)
    )
    detected = bool(geometry and (analysis['is_checkmate'] or forced_block_capture))
    return {
        'pattern_id': 'WHITE_FACE_GENERAL',
        'pattern_name_zh': '白脸将',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'central_file': 'e',
            'attacker_side': attacker,
            'defender_side': defender,
            'attacker_general_square': attacker_king,
            'defender_general_square': defender_king,
            'central_escape_square': central_escape_square,
            'attacker_general_on_central_file': bool(attacker_king and attacker_king[0] == 'e'),
            'central_file_open': central_file_open,
            'defender_general_on_adjacent_file': bool(defender_king and defender_king[0] in {'d', 'f'}),
            'line_piece_gives_file_check': bool(
                any(square[0] == defender_king[0] for square in checking_pieces) and defender_king
            ),
            'checking_piece_types': sorted({board.get(square, '').upper() for square in checking_pieces}),
            'is_checkmate': analysis['is_checkmate'],
        },
        'diagnostics': [
            '攻击方将帅在 e 路。',
            '防守方将帅在 d 路或 f 路。',
            '中路必须打通形成白脸；最后一步可由车、炮、马、兵等其他子力完成绝杀。',
        ],
    }


def recognize_stalemate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    _board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    detected = bool((not analysis['is_check']) and (not analysis['legal_moves']))
    return {
        'pattern_id': 'STALEMATE',
        'pattern_name_zh': '困毙',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {
            'attacker_side': attacker,
            'defender_side': defender,
            'attacker_general_square': attacker_king,
            'defender_general_square': defender_king,
            'legal_move_count': len(analysis['legal_moves']),
            'is_check': analysis['is_check'],
            'is_stalemate': detected,
        },
        'diagnostics': [
            '防守方当前没有任何合法着法。',
            '防守方当前并未被将军。',
            '因此该局面属于困毙。',
        ],
    }
