# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""Cannon-led checkmate patterns: 重炮杀, 夹车炮, 闷宫杀, 天地炮 and 马后炮."""

from typing import NamedTuple

from ...board import attacked_squares, board_to_fen, legal_moves, parse_fen, pseudo_legal_targets, squares_between
from ..geometry import (
    apply_moves,
    attacker_and_defender_trace,
    home_rank_of,
    infer_sides,
    orthogonal_palace_neighbors,
    palace_contains,
)

# --- 重炮杀 (double cannon) ---------------------------------------------------


def _is_file_screen(other: str, checker: str, king: str) -> bool:
    """Whether ``other``, on the file of the checking cannon and the general, stands between the two."""
    return min(int(checker[1]), int(king[1])) < int(other[1]) < max(int(checker[1]), int(king[1]))


def _is_rank_screen(other: str, checker: str, king: str) -> bool:
    """Whether ``other``, on the rank of the checking cannon and the general, stands between the two."""
    return min(ord(checker[0]), ord(king[0])) < ord(other[0]) < max(ord(checker[0]), ord(king[0]))


def _find_screen_cannon(cannon_squares: list[str], checker: str, king: str) -> tuple[bool, bool, str | None]:
    """``(same_file, same_rank, screen_cannon_square)``; the scan stops at the first screening cannon."""
    same_file = False
    same_rank = False
    for other in cannon_squares:
        if other == checker:
            continue
        if other[0] == checker[0] == king[0]:
            same_file = True
            if _is_file_screen(other, checker, king):
                return same_file, same_rank, other
        if other[1] == checker[1] == king[1]:
            same_rank = True
            if _is_rank_screen(other, checker, king):
                return same_file, same_rank, other
    return same_file, same_rank, None


def _screen_orientation(screen_cannon_square: str | None, checking_cannon_square: str | None) -> str | None:
    if not screen_cannon_square:
        return None
    return 'file' if screen_cannon_square[0] == checking_cannon_square[0] else 'rank'


def recognize_double_cannon_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    cannon_piece = 'C' if attacker == 'red' else 'c'
    cannon_squares = sorted(square for square, piece in board.items() if piece == cannon_piece)
    checking_cannons = [item for item in analysis['checking_pieces'] if item['reason'] == 'cannon_screen']
    same_file = False
    same_rank = False
    screen_cannon_square: str | None = None
    checking_cannon_square: str | None = None
    if len(cannon_squares) >= 2 and defender_king and checking_cannons:
        checking_cannon_square = checking_cannons[0]['square']
        same_file, same_rank, screen_cannon_square = _find_screen_cannon(
            cannon_squares, checking_cannon_square, defender_king
        )
    orientation = _screen_orientation(screen_cannon_square, checking_cannon_square)
    detected = bool(
        analysis['is_checkmate']
        and len(cannon_squares) >= 2
        and checking_cannons
        and screen_cannon_square
        and (same_file or same_rank)
    )
    return {
        'pattern_id': 'DOUBLE_CANNON_CHECKMATE',
        'pattern_name_zh': '重炮杀',
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
            'cannon_squares': cannon_squares,
            'checking_cannon_square': checking_cannon_square,
            'screen_cannon_square': screen_cannon_square,
            'orientation': orientation,
        },
        'diagnostics': [
            '攻击方两个炮在同一列或同一行形成重炮结构。',
            '其中一炮借另一炮作炮架实施将军。',
            '防守方没有任何合法防守，因此构成重炮杀。',
        ],
    }


# --- 夹车炮 (cannons sandwiching a chariot) -----------------------------------


def _flank_name(square: str) -> str | None:
    if square[0] in {'a', 'b', 'c'}:
        return 'left'
    if square[0] in {'g', 'h', 'i'}:
        return 'right'
    return None


def _flank_groups(rook_squares: list[str], cannon_squares: list[str]) -> list[dict[str, object]]:
    """Each flank that holds a chariot and at least two cannons on the attacking ranks."""
    flank_groups: list[dict[str, object]] = []
    for flank in ('left', 'right'):
        flank_rooks = [square for square in rook_squares if _flank_name(square) == flank]
        flank_cannons = [square for square in cannon_squares if _flank_name(square) == flank]
        if flank_rooks and len(flank_cannons) >= 2:
            flank_groups.append({'flank': flank, 'rook_squares': flank_rooks, 'cannon_squares': flank_cannons})
    return flank_groups


def _pieces_on_ranks(board: dict[str, str], wanted: str, ranks: set[str]) -> list[str]:
    return sorted(square for square, piece in board.items() if piece == wanted and square[1] in ranks)


def _flank_gives_final_check(flank_groups: list[dict[str, object]], final_checker_squares: list[str]) -> bool:
    return any(
        square in group['rook_squares'] or square in group['cannon_squares']
        for group in flank_groups
        for square in final_checker_squares
    )


def _rook_or_cannon_checks(attacker_trace: list[dict[str, object]]) -> list[dict[str, object]]:
    """The attacker's chariot and cannon moves that gave check."""
    return [
        item
        for item in attacker_trace
        if str(item['piece']).upper() in {'R', 'C'} and bool(item['analysis']['is_check'])
    ]


def recognize_cannons_sandwiching_chariot_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    rook_piece = 'R' if attacker == 'red' else 'r'
    cannon_piece = 'C' if attacker == 'red' else 'c'
    attacking_ranks = {'7', '8', '9'} if defender == 'black' else {'0', '1', '2'}
    flank_groups = _flank_groups(
        _pieces_on_ranks(board, rook_piece, attacking_ranks),
        _pieces_on_ranks(board, cannon_piece, attacking_ranks),
    )

    final_checker_squares = [
        item['square'] for item in analysis['checking_pieces'] if board.get(item['square'], '').upper() in {'R', 'C'}
    ]
    final_checker_types = sorted({board.get(square, '').upper() for square in final_checker_squares})
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    checking_attackers = _rook_or_cannon_checks(attacker_trace)
    attack_sequence_types = [str(item['piece']).upper() for item in checking_attackers[-5:]]
    distinct_attacker_ids = sorted({str(item['piece_id']) for item in checking_attackers[-5:]})

    detected = bool(
        analysis['is_checkmate']
        and flank_groups
        and _flank_gives_final_check(flank_groups, final_checker_squares)
        and (not applied or len(checking_attackers) >= 1)
    )
    return {
        'pattern_id': 'CANNONS_SANDWICHING_CHARIOT_CHECKMATE',
        'pattern_name_zh': '夹车炮',
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
            'flank_groups': flank_groups,
            'attacking_ranks': sorted(attacking_ranks),
            'final_checker_squares': final_checker_squares,
            'final_checker_types': final_checker_types,
            'checking_attack_count': len(checking_attackers),
            'attack_sequence_types': attack_sequence_types,
            'distinct_attacker_ids': distinct_attacker_ids,
        },
        'diagnostics': [
            '攻击方在同一侧集结的车和双炮均须位于敌方底部三路。',
            '终局由该侧的车或炮完成将军，并形成绝杀。',
            '若过程中出现车炮轮番压将，也一并归入夹车炮。',
        ],
    }


# --- 闷宫杀 (smothered cannon) ------------------------------------------------


def _smothered_cannon_match(board: dict[str, str], square: str, king: str, defender: str) -> dict[str, object] | None:
    """The match for one checking cannon: an advisor is its only screen and advisors block the perpendicular exits."""
    advisor = 'a' if defender == 'black' else 'A'
    between = [x for x in squares_between(square, king) if x in board]
    perpendicular = [
        x
        for x in orthogonal_palace_neighbors(king, defender)
        if (x[0] == king[0] if square[1] == king[1] else x[1] == king[1])
    ]
    if (
        len(between) == 1
        and board[between[0]].upper() == 'A'
        and perpendicular
        and all(board.get(x) == advisor for x in perpendicular)
    ):
        return {'cannon': square, 'screen': between[0], 'blocked_squares': perpendicular}
    return None


def _smothered_cannon_matches(
    board: dict[str, str], checkers: list[dict], king: str | None, defender: str
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for checker in checkers:
        square = checker['square']
        if not king or board.get(square, '').upper() != 'C':
            continue
        match = _smothered_cannon_match(board, square, king, defender)
        if match:
            matches.append(match)
    return matches


def recognize_smothered_cannon_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, _attacker, defender, _attacker_king, king = infer_sides(current_fen)
    checkers = analysis['checking_pieces']
    types = {board.get(x['square'], '').upper() for x in checkers}
    matches = _smothered_cannon_matches(board, checkers, king, defender)
    detected = bool(analysis['is_checkmate'] and types == {'C'} and matches)
    return {
        'pattern_id': 'SMOTHERED_CANNON_CHECKMATE',
        'pattern_name_zh': '闷宫杀',
        'detected': detected,
        'causal': detected,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'features': {'matching_cannons': matches, 'checking_piece_types': sorted(types)},
        'diagnostics': ['只由炮将军，以士为炮架，垂直炮线的宫内去路全部被己方士堵住。'],
    }


# --- 天地炮 (heaven and earth cannon) -----------------------------------------


class _LineFinish(NamedTuple):
    """The line's last move, read off the position before it; every field is ``None`` when no move was played."""

    pre_board: dict[str, str] | None
    piece: str | None
    destination: str | None
    captured: str | None


class _HeavenEarth(NamedTuple):
    """The final position as the scenarios read it, once the gate has passed."""

    board: dict[str, str]
    analysis: dict
    attacker: str
    defender: str
    king: str
    cannon_piece: str
    heaven: list[str]
    earth: list[str]


class _HeavenEarthFindings(NamedTuple):
    pre_pins: dict[str, list[str]]
    final_pins: dict[str, list[str]]
    scenarios: list[str]
    supporting_rooks: list[str]
    protecting_cannons: list[str]


def _board_without_other_checkers(board: dict[str, str], cannon: str, king: str, attacker: str) -> dict[str, str]:
    probe = dict(board)
    for checker in attacked_squares(board, attacker).get(king, []):
        source = checker['square']
        if source != cannon and probe.get(source, '').upper() != 'K':
            probe.pop(source, None)
    return probe


def _some_move_leaves_cannon_attack(probe: dict[str, str], square: str, piece: str, line: tuple[str, str, str]) -> bool:
    """Whether a pseudo-legal move of this piece leaves the cannon attacking; ``line`` is (cannon, king, attacker)."""
    cannon, king, attacker = line
    for target in pseudo_legal_targets(probe, square, piece):
        moved = dict(probe)
        moved[target] = moved.pop(square)
        if any(entry['square'] == cannon for entry in attacked_squares(moved, attacker).get(king, [])):
            return True
    return False


def _cannon_pinned_defenders(board: dict[str, str], cannon: str, king: str, attacker: str, defender: str) -> list[str]:
    """Find defenders pinned to their general by this cannon, independently of other checks."""
    if cannon[0] != king[0] and cannon[1] != king[1]:
        return []
    defender_pieces = {'a', 'b'} if defender == 'black' else {'A', 'B'}
    candidates = [square for square in squares_between(cannon, king) if board.get(square) in defender_pieces]
    if not candidates:
        return []
    probe = _board_without_other_checkers(board, cannon, king, attacker)
    side_to_move = 'w' if defender == 'red' else 'b'
    probe_moves = legal_moves(f'{board_to_fen(probe)} {side_to_move} - - 0 1')
    pinned = []
    for square in candidates:
        piece = probe.get(square)
        if piece not in defender_pieces or any(move.startswith(square) for move in probe_moves):
            continue
        if _some_move_leaves_cannon_attack(probe, square, piece, (cannon, king, attacker)):
            pinned.append(square)
    return pinned


def _line_finish(fen: str, applied: list[str]) -> _LineFinish:
    if not applied:
        return _LineFinish(None, None, None, None)
    pre_final_fen, _ = apply_moves(fen, applied[:-1])
    pre_board = parse_fen(pre_final_fen)
    piece = pre_board.get(applied[-1][:2])
    destination = applied[-1][2:]
    return _LineFinish(pre_board, piece, destination, pre_board.get(destination))


def _final_pins(setup: _HeavenEarth) -> dict[str, list[str]]:
    pins: dict[str, list[str]] = {}
    for cannon in setup.heaven + setup.earth:
        pins[cannon] = _cannon_pinned_defenders(setup.board, cannon, setup.king, setup.attacker, setup.defender)
    return pins


def _pre_final_pins(setup: _HeavenEarth, pre_board: dict[str, str] | None) -> dict[str, list[str]]:
    pins: dict[str, list[str]] = {}
    if not pre_board:
        return pins
    general = 'k' if setup.defender == 'black' else 'K'
    pre_king = next((square for square, piece in pre_board.items() if piece == general), None)
    if not pre_king:
        return pins
    for cannon in setup.heaven + setup.earth:
        if pre_board.get(cannon) == setup.cannon_piece:
            pins[cannon] = _cannon_pinned_defenders(pre_board, cannon, pre_king, setup.attacker, setup.defender)
    return pins


def _protecting_cannons(setup: _HeavenEarth, destination: str | None) -> list[str]:
    if not destination:
        return []
    return sorted(
        entry['square']
        for entry in setup.analysis['attacked_squares'].get(destination, [])
        if entry['square'] in setup.heaven + setup.earth and entry['reason'] == 'cannon_screen'
    )


def _is_cannon_protected_finish(
    setup: _HeavenEarth,
    finish: _LineFinish,
    pre_pins: dict[str, list[str]],
    protecting: list[str],
    checking_squares: set[str],
) -> bool:
    """Both cannons pinned before the last move, and a cannon-protected chariot or pawn mates in the palace."""
    return bool(
        finish.piece
        and finish.piece.upper() in {'R', 'P'}
        and finish.destination
        and palace_contains(finish.destination, setup.defender)
        and any(pre_pins.get(cannon) for cannon in setup.heaven)
        and any(pre_pins.get(cannon) for cannon in setup.earth)
        and finish.destination in checking_squares
        and protecting
    )


def _is_center_pin_bottom_check(
    setup: _HeavenEarth, final_pins: dict[str, list[str]], checking_squares: set[str]
) -> bool:
    return any(final_pins.get(cannon) for cannon in setup.earth) and any(
        cannon in checking_squares for cannon in setup.heaven
    )


def _has_empty_center(setup: _HeavenEarth) -> bool:
    return any(
        not any(square in setup.board for square in squares_between(cannon, setup.king)) for cannon in setup.earth
    )


def _has_bottom_advisor_check(setup: _HeavenEarth, checking_squares: set[str]) -> bool:
    advisor = 'a' if setup.defender == 'black' else 'A'
    return any(
        cannon in checking_squares
        and len(screens := [square for square in squares_between(cannon, setup.king) if square in setup.board]) == 1
        and setup.board[screens[0]] == advisor
        for cannon in setup.heaven
    )


def _second_rank_rooks(setup: _HeavenEarth) -> list[str]:
    second_rank = '8' if setup.defender == 'black' else '1'
    rook_piece = 'R' if setup.attacker == 'red' else 'r'
    return sorted(square for square, piece in setup.board.items() if piece == rook_piece and square[1] == second_rank)


def _heaven_earth_findings(setup: _HeavenEarth, finish: _LineFinish) -> _HeavenEarthFindings:
    final_pins = _final_pins(setup)
    pre_pins = _pre_final_pins(setup, finish.pre_board)
    checking_squares = {item['square'] for item in setup.analysis['checking_pieces']}
    protecting_cannons = _protecting_cannons(setup, finish.destination)
    scenarios: list[str] = []
    if _is_cannon_protected_finish(setup, finish, pre_pins, protecting_cannons, checking_squares):
        scenarios.append('cannon_protected_finish')
    if _is_center_pin_bottom_check(setup, final_pins, checking_squares):
        scenarios.append('center_pin_bottom_cannon_check')
    empty_center = _has_empty_center(setup)
    bottom_advisor_check = _has_bottom_advisor_check(setup, checking_squares)
    supporting_rooks = _second_rank_rooks(setup)
    if empty_center and bottom_advisor_check and supporting_rooks:
        scenarios.append('empty_center_bottom_advisor_screen')
    return _HeavenEarthFindings(pre_pins, final_pins, scenarios, supporting_rooks, protecting_cannons)


def recognize_heaven_and_earth_cannon_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    cannon_piece = 'C' if attacker == 'red' else 'c'
    home_rank = home_rank_of(defender)
    cannons = sorted(square for square, piece in board.items() if piece == cannon_piece)
    heaven_cannons = [square for square in cannons if square[1] == home_rank]
    earth_cannons = [square for square in cannons if square[0] == 'e' and square[1] != home_rank]
    finish = _line_finish(fen, applied)

    findings = _HeavenEarthFindings({}, {}, [], [], [])
    if (
        analysis['is_checkmate']
        and defender_king
        and defender_king == 'e' + home_rank
        and heaven_cannons
        and earth_cannons
    ):
        setup = _HeavenEarth(
            board, analysis, attacker, defender, defender_king, cannon_piece, heaven_cannons, earth_cannons
        )
        findings = _heaven_earth_findings(setup, finish)

    detected = bool(findings.scenarios)
    return {
        'pattern_id': 'HEAVEN_AND_EARTH_CANNON_CHECKMATE',
        'pattern_name_zh': '天地炮',
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
            'heaven_cannon_squares': heaven_cannons,
            'earth_cannon_squares': earth_cannons,
            'pre_final_pins': findings.pre_pins,
            'final_pins': findings.final_pins,
            'scenarios': findings.scenarios,
            'supporting_rook_squares': findings.supporting_rooks,
            'protecting_cannon_squares': findings.protecting_cannons,
            'final_piece_type': finish.piece.upper() if finish.piece else None,
            'final_destination': finish.destination,
            'captured_piece': finish.captured,
        },
        'diagnostics': [
            '攻击方同时具备一门对方底线炮与一门中路炮。',
            '双炮各自牵制士象，由受炮保护的车兵入宫将死；或中炮牵制士象、底炮将军；或中炮空头、底炮以底士为架将军且有车在下二路。',
        ],
    }


# --- 马后炮 (horse-cannon) ----------------------------------------------------


class _HorseCannonSetup(NamedTuple):
    board: dict[str, str]
    analysis: dict
    cannon_piece: str
    horse_piece: str
    king: str | None
    neighbors: list[str]


def _horse_screen(setup: _HorseCannonSetup, item: dict) -> str | None:
    """The square of the attacker's horse when it is the only screen of this checking cannon."""
    cannon_square = item['square']
    if item['reason'] != 'cannon_screen' or setup.board.get(cannon_square) != setup.cannon_piece or not setup.king:
        return None
    between_squares = squares_between(cannon_square, setup.king)
    occupied_between = [square for square in between_squares if square in setup.board]
    if len(occupied_between) != 1:
        return None
    horse_square = occupied_between[0]
    return horse_square if setup.board.get(horse_square) == setup.horse_piece else None


def _restricted_escape_squares(setup: _HorseCannonSetup, horse_square: str) -> list[str]:
    return sorted(
        square
        for square in setup.neighbors
        if square == horse_square
        or any(
            attack['square'] == horse_square and attack['reason'] == 'horse_attack'
            for attack in setup.analysis['attacked_squares'].get(square, [])
        )
    )


def _cannon_horse_pairs(setup: _HorseCannonSetup) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for item in setup.analysis['checking_pieces']:
        horse_square = _horse_screen(setup, item)
        if horse_square is None:
            continue
        cannon_square = item['square']
        pairs.append(
            {
                'cannon_square': cannon_square,
                'horse_square': horse_square,
                'axis': 'file' if cannon_square[0] == setup.king[0] else 'rank',
                'restricted_escape_squares': _restricted_escape_squares(setup, horse_square),
            }
        )
    return pairs


def _horse_cannon_finish(
    attacker_trace: list[dict[str, object]], qualified_pairs: list[dict[str, object]]
) -> tuple[bool, int | None, int | None]:
    """``(final_cannon_finish, horse_move_ply, cannon_finish_ply)`` from the attacker's plies."""
    final_attack = attacker_trace[-1] if attacker_trace else None
    final_cannon_finish = bool(
        final_attack
        and bool(final_attack['analysis']['is_checkmate'])
        and str(final_attack['piece']).upper() in {'C', 'N'}
        and qualified_pairs
    )
    horse_move_ply = next((int(item['ply']) for item in attacker_trace if str(item['piece']).upper() == 'N'), None)
    cannon_finish_ply = int(final_attack['ply']) if final_cannon_finish else None
    return final_cannon_finish, horse_move_ply, cannon_finish_ply


def recognize_horse_cannon_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    cannon_piece = 'C' if attacker == 'red' else 'c'
    horse_piece = 'N' if attacker == 'red' else 'n'
    defender_neighbors = orthogonal_palace_neighbors(defender_king, defender) if defender_king else []
    setup = _HorseCannonSetup(board, analysis, cannon_piece, horse_piece, defender_king, defender_neighbors)

    # The horse does not have to attack a palace neighbor directly. In a
    # classic horse-cannon mate it can serve as the cannon screen while the
    # other attacking pieces close the remaining escape squares.
    qualified_pairs = _cannon_horse_pairs(setup)
    attacker_trace, _defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    final_cannon_finish, horse_move_ply, cannon_finish_ply = _horse_cannon_finish(attacker_trace, qualified_pairs)
    detected = bool(analysis['is_checkmate'] and qualified_pairs and (not applied or final_cannon_finish))
    return {
        'pattern_id': 'HORSE_CANNON_CHECKMATE',
        'pattern_name_zh': '马后炮',
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
            'cannon_horse_pairs': qualified_pairs,
            'pair_count': len(qualified_pairs),
            'final_cannon_finish': final_cannon_finish,
            'horse_move_ply': horse_move_ply,
            'cannon_finish_ply': cannon_finish_ply,
        },
        'diagnostics': [
            '最终形成将军的是一门炮，而且炮与将帅之间唯一的炮架正好是己方马。',
            '马可以直接控制宫内逃位，也可以作为炮架，由其他攻击子力共同封锁其余逃路。',
            '最后一步可以是炮移动，也可以是马走入炮架位置后完成绝杀。',
        ],
    }
