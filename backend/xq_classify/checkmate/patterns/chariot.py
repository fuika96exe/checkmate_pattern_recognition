"""Chariot-led checkmate patterns: 双车错, 三车闹士, 铁门栓, 进洞出洞, 双鬼拍门 and 大胆穿心."""

from typing import NamedTuple

from ...board import (
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
from ..geometry import (
    apply_moves,
    attacker_and_defender_trace,
    home_rank_of,
    infer_sides,
    is_attacker_piece,
    move_trace,
    orthogonal_palace_neighbors,
)


class _Sides(NamedTuple):
    """The result of ``infer_sides``, by name."""

    board: dict[str, str]
    analysis: dict
    attacker: str
    defender: str
    attacker_king: str | None
    defender_king: str | None


class _DrawerZone(NamedTuple):
    """Where the drawer's rook and the defending general may shuttle."""

    cave_files: set[str]
    cave_ranks: set[str]
    king_tunnel_squares: set[str]


class _Pin(NamedTuple):
    """A central piece looking at the defending general through the midline."""

    lock_square: str
    between: list[str]
    lock_pieces: set[str]


# 双车错


def _alternating_rook_checks(attacker_trace: list[dict]) -> tuple[bool, bool]:
    """``(alternating_rooks, checking_sequence)`` for the attacker's last three plies."""
    if len(attacker_trace) < 3:
        return False, False
    recent_attackers = attacker_trace[-3:]
    ids = [str(item['piece_id']) for item in recent_attackers]
    pieces = [str(item['piece']) for item in recent_attackers]
    checks = [bool(item['analysis']['is_check']) for item in recent_attackers]
    alternating_rooks = all(piece.upper() == 'R' for piece in pieces) and ids[0] == ids[2] and ids[0] != ids[1]
    return alternating_rooks, all(checks)


def _on_line_through_general(rook: str, defender_king: str, target: str) -> bool:
    return rook[0] == defender_king[0] == target[0] or rook[1] == defender_king[1] == target[1]


def _supporting_rook_escape_squares(sides: _Sides, checking_rooks: list[str], supporting_rooks: list[str]) -> list[str]:
    """Empty palace neighbours of the general that only the non-checking rook holds."""
    board, analysis, _attacker, defender, _attacker_king, defender_king = sides
    if not defender_king:
        return []
    escape_squares = []
    for target in orthogonal_palace_neighbors(defender_king, defender):
        if board.get(target):
            continue
        attacks = analysis['attacked_squares'].get(target, [])
        supported_by_other_rook = any(entry['square'] in supporting_rooks for entry in attacks)
        checked_by_finishing_rook = any(entry['square'] in checking_rooks for entry in attacks) or any(
            _on_line_through_general(rook, defender_king, target) for rook in checking_rooks
        )
        if supported_by_other_rook and not checked_by_finishing_rook:
            escape_squares.append(target)
    return escape_squares


def _immediate_rook_finish(attacker_trace: list[dict], checking_rooks: list[str], escape_squares: list[str]) -> bool:
    return bool(
        attacker_trace
        and str(attacker_trace[-1]['piece']).upper() == 'R'
        and attacker_trace[-1]['analysis']['is_checkmate']
        and checking_rooks
        and (len(checking_rooks) >= 2 or escape_squares)
    )


def recognize_double_chariots_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    sides = _Sides(*infer_sides(current_fen))
    board, analysis, attacker, defender, attacker_king, defender_king = sides
    rook_piece = 'R' if attacker == 'red' else 'r'
    rook_squares = sorted(square for square, piece in board.items() if piece == rook_piece)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    alternating_rooks, checking_sequence = _alternating_rook_checks(attacker_trace)
    checking_rooks = [
        item['square'] for item in analysis['checking_pieces'] if board.get(item['square'], '').upper() == 'R'
    ]
    supporting_rooks = [square for square in rook_squares if square not in checking_rooks]
    supporting_rook_escape_squares = _supporting_rook_escape_squares(sides, checking_rooks, supporting_rooks)
    immediate_rook_finish = _immediate_rook_finish(attacker_trace, checking_rooks, supporting_rook_escape_squares)
    different_files = len({square[0] for square in rook_squares}) >= 2
    different_ranks = len({square[1] for square in rook_squares}) >= 2
    detected = bool(
        analysis['is_checkmate']
        and len(rook_squares) >= 2
        and (alternating_rooks and checking_sequence or immediate_rook_finish)
        and (different_files or different_ranks)
    )
    return {
        'pattern_id': 'DOUBLE_CHARIOTS_CHECKMATE',
        'pattern_name_zh': '双车错',
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
            'rook_squares': rook_squares,
            'different_files': different_files,
            'different_ranks': different_ranks,
            'alternating_rooks': alternating_rooks,
            'checking_sequence': checking_sequence,
            'immediate_rook_finish': immediate_rook_finish,
            'checking_rook_squares': checking_rooks,
            'supporting_rook_squares': supporting_rooks,
            'supporting_rook_escape_squares': supporting_rook_escape_squares,
        },
        'diagnostics': [
            '攻击方两辆车分处不同列或不同行。',
            '最后一段攻击序列可以是双车交替将军，或由一辆车将军、另一辆车封锁将军车未控制的空逃路。',
            '终局没有合法防守，因此构成双车错绝杀。',
        ],
    }


# 三车闹士


def _starting_main_pieces(starting_board: dict[str, str], attacker: str) -> list[str]:
    """The squares of the attacker's chariots and pawns at the start of the line."""
    return sorted(
        square
        for square, piece in starting_board.items()
        if is_attacker_piece(piece, attacker) and piece.upper() in {'R', 'P'}
    )


def _squares_of_type(starting_board: dict[str, str], squares: list[str], piece_type: str) -> list[str]:
    return [square for square in squares if starting_board[square].upper() == piece_type]


def _note_opening_checks(
    fen: str, defender: str, identities: dict[str, str], participation: dict[str, list[str]]
) -> None:
    """A main piece already giving check when the line starts takes part."""
    opening = position_analysis(fen)
    if opening['side_to_move'] != defender:
        return
    for checker in opening['checking_pieces']:
        piece_id = identities.get(checker['square'])
        if piece_id in participation:
            participation[piece_id].append('check')


def _note_later_checks(item: dict, identities: dict[str, str], participation: dict[str, list[str]]) -> None:
    for checker in item['analysis']['checking_pieces']:
        checker_id = identities.get(checker['square'])
        if checker_id in participation and 'check' not in participation[checker_id]:
            participation[checker_id].append('check')


def _note_line_participation(
    line: tuple[str, list[dict]],
    identities: dict[str, str],
    participation: dict[str, list[str]],
    defender_advisor: str,
) -> dict[str, str]:
    """Record advisor captures and checks along the line; returns the final piece identities."""
    position, trace = line
    for item in trace:
        move = str(item['move'])
        piece_id = str(item['piece_id'])
        before = parse_fen(position)
        if piece_id in participation and before.get(move[2:]) == defender_advisor:
            participation[piece_id].append('capture_advisor')
        identities = move_piece_identity(identities, move[:2], move[2:])
        _note_later_checks(item, identities, participation)
        position = apply_move(position, move)
    return identities


def _attacks_any(analysis: dict, square: str, targets: list[str]) -> bool:
    return any(
        any(attack['square'] == square for attack in analysis['attacked_squares'].get(target, []))
        for target in targets
    )


def _note_escape_control(sides: _Sides, identities: dict[str, str], participation: dict[str, list[str]]) -> None:
    """A main piece covering an empty palace neighbour of the mated general takes part."""
    board, analysis, _attacker, defender, _attacker_king, defender_king = sides
    if not defender_king:
        return
    escape_squares = [
        square for square in orthogonal_palace_neighbors(defender_king, defender) if not board.get(square)
    ]
    for square, piece_id in identities.items():
        if piece_id in participation and _attacks_any(analysis, square, escape_squares):
            participation[piece_id].append('control_escape')


def _has_piece_type(starting_board: dict[str, str], squares: list[str], piece_type: str) -> bool:
    return any(starting_board[square].upper() == piece_type for square in squares)


def recognize_three_chariots_attacking_advisor_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    sides = _Sides(*infer_sides(current_fen))
    board, analysis, attacker, defender, attacker_king, defender_king = sides
    starting_board = parse_fen(fen)
    defender_advisor = 'a' if defender == 'black' else 'A'
    starting_main_pieces = _starting_main_pieces(starting_board, attacker)
    starting_rooks = _squares_of_type(starting_board, starting_main_pieces, 'R')
    starting_pawns = _squares_of_type(starting_board, starting_main_pieces, 'P')
    final_checker_squares = [
        item['square'] for item in analysis['checking_pieces'] if board.get(item['square'], '').upper() in {'R', 'P'}
    ]
    trace = move_trace(fen, applied) if applied else []
    final_move_piece = trace[-1]['piece'].upper() if trace else None
    advisor_squares = sorted(square for square, piece in starting_board.items() if piece == defender_advisor)
    identities = build_piece_identity(fen)
    main_ids = {identities[square]: square for square in starting_main_pieces}
    participation: dict[str, list[str]] = {piece_id: [] for piece_id in main_ids}
    _note_opening_checks(fen, defender, identities, participation)
    identities = _note_line_participation((fen, trace), identities, participation, defender_advisor)
    _note_escape_control(sides, identities, participation)
    participating_squares = sorted(square for piece_id, square in main_ids.items() if participation[piece_id])
    detected = bool(
        analysis['is_checkmate']
        and not analysis['is_stalemate']
        and len(participating_squares) >= 3
        and _has_piece_type(starting_board, participating_squares, 'R')
        and _has_piece_type(starting_board, participating_squares, 'P')
        and advisor_squares
        and final_checker_squares
        and final_move_piece in {'R', 'P'}
    )
    return {
        'pattern_id': 'THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE',
        'pattern_name_zh': '三车闹士',
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
            'starting_main_piece_squares': starting_main_pieces,
            'starting_rook_squares': starting_rooks,
            'starting_pawn_squares': starting_pawns,
            'defender_advisor_squares': advisor_squares,
            'final_checker_squares': final_checker_squares,
            'final_move_piece_type': final_move_piece,
            'participating_starting_squares': participating_squares,
            'participation': [
                {'starting_square': square, 'piece_id': piece_id, 'reasons': participation[piece_id]}
                for piece_id, square in main_ids.items()
            ],
        },
        'diagnostics': [
            '至少三枚车兵参与杀局，其中至少有一车和一兵。',
            '参与包括吃士、直接将军，或在终局控制将帅相邻的空逃格。',
        ],
    }


# 铁门栓


def _central_lock_candidates(sides: _Sides) -> list[str]:
    """The attacker's chariots and cannons on the e-file, then the attacking general if it stands there."""
    board, _analysis, attacker, _defender, attacker_king, _defender_king = sides
    attacker_line_pieces = {'C', 'R'} if attacker == 'red' else {'c', 'r'}
    candidates = sorted(square for square, piece in board.items() if piece in attacker_line_pieces and square[0] == 'e')
    if attacker_king and attacker_king[0] == 'e':
        candidates.append(attacker_king)
    return candidates


def _probe_without_other_checkers(sides: _Sides, lock_square: str) -> dict[str, str]:
    # In a checkmate every defender has zero legal moves. Remove the
    # other checking pieces to test the advisor's independent pin.
    probe = dict(sides.board)
    for checker in sides.analysis['checking_pieces']:
        source = checker['square']
        if source != lock_square and probe.get(source, '').upper() != 'K':
            probe.pop(source, None)
    return probe


def _move_exposes_general(probe: dict[str, str], square: str, sides: _Sides, lock_square: str) -> bool:
    # The lock itself must expose the general when the advisor
    # moves; immobility caused solely by another piece is not a pin.
    for target in pseudo_legal_targets(probe, square, probe[square]):
        moved = dict(probe)
        moved[target] = moved.pop(square)
        if any(
            attack['square'] == lock_square
            for attack in attacked_squares(moved, sides.attacker).get(sides.defender_king, [])
        ):
            return True
    return False


def _pinned_advisors(sides: _Sides, pin: _Pin) -> list[str]:
    """The midline advisors that only the piece on ``pin.lock_square`` holds in place."""
    probe = _probe_without_other_checkers(sides, pin.lock_square)
    side_letter = 'w' if sides.defender == 'red' else 'b'
    probe_fen = f'{board_to_fen(probe)} {side_letter} - - 0 1'
    probe_moves = legal_moves(probe_fen)
    locked = []
    for square in pin.between:
        if probe.get(square) not in pin.lock_pieces:
            continue
        if any(move.startswith(square) for move in probe_moves):
            continue
        if _move_exposes_general(probe, square, sides, pin.lock_square):
            locked.append(square)
    return locked


def _find_central_lock(sides: _Sides, lock_pieces: set[str]) -> tuple[str | None, str | None, list[str]]:
    """``(lock_square, lock_piece, locked_midline_pieces)`` of the first candidate that pins an advisor."""
    board = sides.board
    for lock_square in _central_lock_candidates(sides):
        between = squares_between(lock_square, sides.defender_king)
        if not any(board.get(square) in lock_pieces for square in between):
            continue
        locked = _pinned_advisors(sides, _Pin(lock_square, between, lock_pieces))
        if locked:
            return lock_square, board[lock_square], locked
    return None, None, []


def recognize_iron_bolt_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    sides = _Sides(*infer_sides(current_fen))
    board, analysis, attacker, defender, attacker_king, defender_king = sides
    # Only the advisor creates the iron-bolt gate.  An elephant alone is
    # not a sufficient lock because it can still participate in defense.
    lock_piece_set = {'a'} if defender == 'black' else {'A'}
    home_rank = home_rank_of(defender)
    central_lock_square = None
    central_lock_piece = None
    locked_midline_pieces: list[str] = []
    flank_checkers = [
        item
        for item in analysis['checking_pieces']
        if item['square'][1] == home_rank and board.get(item['square'], '').upper() in {'R', 'P'}
    ]
    if analysis['is_checkmate'] and flank_checkers and defender_king and defender_king[0] == 'e':
        central_lock_square, central_lock_piece, locked_midline_pieces = _find_central_lock(sides, lock_piece_set)
    detected = bool(
        analysis['is_checkmate']
        and defender_king
        and defender_king[0] == 'e'
        and defender_king[1] == home_rank
        and central_lock_square
        and locked_midline_pieces
        and flank_checkers
    )
    return {
        'pattern_id': 'IRON_BOLT_CHECKMATE',
        'pattern_name_zh': '铁门栓',
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
            'central_cannon_square': central_lock_square,
            'central_lock_square': central_lock_square,
            'central_lock_piece': central_lock_piece,
            'locked_midline_pieces': locked_midline_pieces,
            'flank_checker_squares': [item['square'] for item in flank_checkers],
            'flank_checker_types': sorted({board.get(item['square'], '').upper() for item in flank_checkers}),
        },
        'diagnostics': [
            '移除其他将军子后，中路士仍无合法走法，且走开会暴露中路车、炮或帅的将军。',
            '最终由底线车或兵实施将军，底线不限定为 d/f 肋道。',
            '防守方没有任何合法解杀，因此构成铁门栓。',
        ],
    }


# 进洞出洞


def _drawer_zone(defender: str) -> _DrawerZone:
    # 2026.11.05-v15 (expert review): the drawer works on either rib file.
    if defender == 'black':
        return _DrawerZone({'d', 'f'}, {'8', '9'}, {'e8', 'e9'})
    return _DrawerZone({'d', 'f'}, {'0', '1'}, {'e0', 'e1'})


def _is_single_rook(candidate: list[dict]) -> bool:
    return all(
        str(item['piece']).upper() == 'R' and str(item['piece_id']) == str(candidate[0]['piece_id'])
        for item in candidate
    )


def _shuttles_in_cave(squares: list[str], zone: _DrawerZone) -> bool:
    """Every square lies in the cave, and the rook uses exactly two adjacent squares of one file."""
    if any(square[0] not in zone.cave_files or square[1] not in zone.cave_ranks for square in squares):
        return False
    ordered = list(dict.fromkeys(squares))
    if len(ordered) != 2:
        return False
    first_square, second_square = ordered
    return first_square[0] == second_square[0] and abs(int(first_square[1]) - int(second_square[1])) == 1


def _reply_to(move: dict, defender_trace: list[dict]) -> dict | None:
    return next((reply for reply in defender_trace if int(reply['ply']) == int(move['ply']) + 1), None)


def _general_tunnel_replies(replies: list[dict | None], zone: _DrawerZone) -> bool:
    return all(
        reply is not None
        and str(reply['piece']).upper() == 'K'
        and str(reply['to_square']) in zone.king_tunnel_squares
        for reply in replies
    )


def _rook_cycle(candidate: list[dict], defender_trace: list[dict], zone: _DrawerZone) -> dict[str, object] | None:
    """The cycle formed by this suffix of the attacker's moves, if it is one."""
    if len(candidate) < 2 or not _is_single_rook(candidate):
        return None
    squares = [str(item['to_square']) for item in candidate]
    if not _shuttles_in_cave(squares, zone):
        return None
    replies = [_reply_to(move, defender_trace) for move in candidate[:-1]]
    if not _general_tunnel_replies(replies, zone):
        return None
    return {
        'rook_id': str(candidate[0]['piece_id']),
        'rook_squares': squares,
        'cycle_start_ply': int(candidate[0]['ply']),
        'reply_squares': [str(reply['to_square']) for reply in replies if reply is not None],
    }


def _rook_cycles(attacker_trace: list[dict], defender_trace: list[dict], zone: _DrawerZone) -> list[dict[str, object]]:
    cycles = []
    for start in range(len(attacker_trace)):
        cycle = _rook_cycle(attacker_trace[start:], defender_trace, zone)
        if cycle is not None:
            cycles.append(cycle)
    return cycles


def recognize_drawer_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    cannon_piece = 'C' if attacker == 'red' else 'c'
    home_rank = home_rank_of(defender)
    zone = _drawer_zone(defender)
    attacker_trace, defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    home_cannons = sorted(
        square for square, piece in board.items() if piece == cannon_piece and square[1] == home_rank
    )
    rook_cycles = _rook_cycles(attacker_trace, defender_trace, zone)
    center = 'e8' if defender == 'black' else 'e1'
    penetration_started = any(
        str(item['piece']).upper() in {'R', 'P'} and str(item['to_square']) == center for item in attacker_trace
    )
    final_piece_type = str(attacker_trace[-1]['piece']).upper() if attacker_trace else None
    detected = bool(analysis['is_checkmate'] and home_cannons and rook_cycles and final_piece_type == 'R')
    return {
        'pattern_id': 'DRAWER_CHECKMATE',
        'pattern_name_zh': '进洞出洞',
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
            'home_cannon_squares': home_cannons,
            'rook_cycles': rook_cycles,
            'penetration_started': penetration_started,
            'final_piece_type': final_piece_type,
            'cave_files': sorted(zone.cave_files),
            'king_tunnel_squares': sorted(zone.king_tunnel_squares),
        },
        'diagnostics': [
            '攻击方先以底线炮牵制宫内守势，再由同一辆肋道车在宫边相邻两格进出往返。',
            '防守方将帅被逼在 e 线相邻两格之间应将，形成典型的进洞出洞循环。',
            '最终红车收束成绝杀，因此该局面属于进洞出洞。',
        ],
    }


# 双鬼拍门


def _attacker_pawn_on(state: dict[str, str], square: str, attacker: str) -> bool:
    piece = state.get(square, '')
    return bool(piece) and is_attacker_piece(piece, attacker) and piece.upper() == 'P'


def recognize_two_devils_knocking_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    _, analysis, attacker, defender, *_ = infer_sides(current_fen)
    rank = '8' if defender == 'black' else '1'
    eyes = ['d' + rank, 'f' + rank]
    occurrences = []
    for ply in range(len(applied) + 1):
        position, _ = apply_moves(fen, applied[:ply])
        state = parse_fen(position)
        if all(_attacker_pawn_on(state, square, attacker) for square in eyes):
            occurrences.append(ply)
    detected = bool(analysis['is_checkmate'] and occurrences)
    return {
        'pattern_id': 'TWO_DEVILS_KNOCKING_CHECKMATE',
        'pattern_name_zh': '双鬼拍门',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {'elephant_eye_squares': eyes, 'occurrence_plies': occurrences},
        'diagnostics': ['过程中两枚己方兵同时占据敌方象眼。'],
    }


# 大胆穿心


def _is_main_piece_entering(item: dict, attacker: str, center: str) -> bool:
    piece = str(item['piece'])
    return is_attacker_piece(piece, attacker) and piece.upper() in {'R', 'P'} and item['to_square'] == center


def _qualifying_capture(line: tuple[str, list[str]], item: dict, advisor: str, center: str) -> dict | None:
    """The capture of the centre advisor at this ply, when another advisor remained or the victim was protected."""
    fen, applied = line
    before, _ = apply_moves(fen, applied[:int(item['ply']) - 1])
    previous = parse_fen(before)
    if previous.get(center) != advisor:
        return None
    other_advisors = [square for square, piece in previous.items() if piece == advisor and square != center]
    after_capture, _ = apply_moves(fen, applied[:int(item['ply'])])
    defenders = sorted(move[:2] for move in legal_moves(after_capture) if move[2:] == center)
    if other_advisors or defenders:
        return {'ply': item['ply'], 'other_advisors': other_advisors, 'protectors': defenders}
    return None


def recognize_throat_cutting_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    _, analysis, attacker, defender, *_ = infer_sides(current_fen)
    advisor = 'a' if defender == 'black' else 'A'
    center = 'e8' if defender == 'black' else 'e1'
    qualifying = []
    for item in move_trace(fen, moves):
        if not _is_main_piece_entering(item, attacker, center):
            continue
        capture = _qualifying_capture((fen, applied), item, advisor, center)
        if capture is not None:
            qualifying.append(capture)
    detected = bool(analysis['is_checkmate'] and qualifying)
    return {
        'pattern_id': 'THROAT_CUTTING_CHECKMATE',
        'pattern_name_zh': '大胆穿心',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {'center_square': center, 'qualifying_captures': qualifying},
        'diagnostics': ['车或兵吃花心士，且当时另有士或被吃的士受保护。'],
    }
