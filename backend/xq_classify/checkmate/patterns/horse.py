# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""Horse checkmate patterns: discovered (拔簧马), elbow (卧槽马), palace corner (挂角马), angler (钓鱼马), octagon (八角马)."""

from collections.abc import Callable
from typing import NamedTuple

from ...board import coords, parse_fen
from ..geometry import (
    apply_moves,
    attacker_and_defender_trace,
    infer_sides,
    is_attacker_piece,
    orthogonal_palace_neighbors,
)

_Ply = dict[str, object]


class _Pattern(NamedTuple):
    pattern_id: str
    name_zh: str
    diagnostics: tuple[str, ...]


class _Line(NamedTuple):
    """The final position of the line, who attacks whom, and each side's plies."""

    fen: str
    applied: list[str]
    board: dict[str, str]
    analysis: dict
    attacker: str
    defender: str
    attacker_king: str | None
    defender_king: str | None
    attacker_trace: list[_Ply]
    defender_trace: list[_Ply]


class _HorseEntry(NamedTuple):
    """The first horse jump that gave check on a target square, and what followed it."""

    move: _Ply | None
    immediate_finish: bool
    forced_king_reply: bool


class _Corner(NamedTuple):
    """Where the palace-corner horse stands and the palace squares it restricts."""

    square: str | None
    horse_present: bool
    restricted: list[str]


_ReplyFinder = Callable[[_Line, int, _Ply], _Ply | None]

_DISCOVERED = _Pattern(
    'DISCOVERED_HORSE_CHECKMATE',
    '拔簧马',
    (
        '最后一着并非马跳将，而是另一枚己方棋子离开了马腿位置。',
        '该着法一旦把马腿拔开，原本静止的马立即形成马将并完成绝杀。',
        '因此该终局构成拔簧马。',
    ),
)
_ELBOW = _Pattern(
    'ELBOW_HORSE_CHECKMATE',
    '卧槽马',
    (
        '绝杀黑方时检查攻击方马是否位于 c8/g8；绝杀红方时检查攻击方马是否位于 c1/g1。',
        '终局卧槽马须实际攻击将帅或控制宫内相邻逃路，蹩马腿时不算控制。',
        '随后再由车、炮或兵完成绝杀，因此构成卧槽马。',
    ),
)
_PALCORNER = _Pattern(
    'PALCORNER_HORSE_CHECKMATE',
    '挂角马',
    (
        '挂角马可以先行占位并控制一个将帅或宫内去路，再由其他棋子将死。',
        '马也可以跳入挂角位将军，随后逼出将帅应将或直接绝杀。',
    ),
)
_ANGLER = _Pattern(
    'ANGLER_HORSE_CHECKMATE',
    '钓鱼马',
    (
        '绝杀黑方时只检查红马是否稳占 c7/g7；绝杀红方时只检查黑马是否稳占 c2/g2。',
        '该马可以先手跳入钓鱼位将军，也可以作为既有钓鱼位支撑最后一击。',
        '随后再由车、马、炮或兵完成绝杀，因此构成钓鱼马。',
    ),
)
_OCTAGON = _Pattern(
    'OCTAGON_HORSE_CHECKMATE',
    '八角马',
    (
        '攻击方马位于对方九宫角位，并与对方将帅处于九宫对角位置。',
        '控制范围达到两个或以上才是八角马；只控制一个位置由挂角马负责。',
        '随后可以由另一匹马、车、炮或兵完成绝杀；只要八角马实际参与控制逃路即可。',
    ),
)

_ELBOW_VS_BLACK = frozenset({'c8', 'g8'})
_ELBOW_VS_RED = frozenset({'c1', 'g1'})
_ANGLER_VS_BLACK = frozenset({'c7', 'g7'})
_ANGLER_VS_RED = frozenset({'c2', 'g2'})
_CORNERS_VS_BLACK = frozenset({'d7', 'd9', 'f7', 'f9'})
_CORNERS_VS_RED = frozenset({'d0', 'd2', 'f0', 'f2'})
_OPPOSITE_CORNER = {
    'd7': 'f9',
    'f9': 'd7',
    'f7': 'd9',
    'd9': 'f7',
    'd2': 'f0',
    'f0': 'd2',
    'f2': 'd0',
    'd0': 'f2',
}
_ANY_HORSE = frozenset({'N', 'n'})
_ALL_FINISHERS = frozenset({'R', 'N', 'C', 'P'})
_NON_HORSE_FINISHERS = frozenset({'R', 'C', 'P'})


def _horse_leg_square(horse_square: str, target_square: str) -> str | None:
    hx, hy = coords(horse_square)
    tx, ty = coords(target_square)
    dx = tx - hx
    dy = ty - hy
    if abs(dx) == 1 and abs(dy) == 2:
        return f'{horse_square[0]}{hy + (1 if dy > 0 else -1)}'
    if abs(dx) == 2 and abs(dy) == 1:
        return f'{chr(ord(horse_square[0]) + (1 if dx > 0 else -1))}{horse_square[1]}'
    return None


def _read_line(fen: str, moves: list[str] | None) -> _Line:
    current_fen, applied = apply_moves(fen, moves)
    board, analysis, attacker, defender, attacker_king, defender_king = infer_sides(current_fen)
    attacker_trace, defender_trace = attacker_and_defender_trace(fen, moves, attacker)
    return _Line(
        current_fen,
        applied,
        board,
        analysis,
        attacker,
        defender,
        attacker_king,
        defender_king,
        attacker_trace,
        defender_trace,
    )


def _report(line: _Line, pattern: _Pattern, detected: bool, features: dict[str, object]) -> dict:
    return {
        'pattern_id': pattern.pattern_id,
        'pattern_name_zh': pattern.name_zh,
        'detected': detected,
        'causal': detected,
        'fen': line.fen,
        'moves': line.applied,
        'analysis': line.analysis,
        'features': {
            'attacker_side': line.attacker,
            'defender_side': line.defender,
            'attacker_general_square': line.attacker_king,
            'defender_general_square': line.defender_king,
            **features,
        },
        'diagnostics': list(pattern.diagnostics),
    }


def _horse_of(side: str) -> str:
    return 'N' if side == 'red' else 'n'


def _general_of(defender: str) -> str:
    return 'k' if defender == 'black' else 'K'


def _horses_on(board: dict[str, str], horse: str, squares: frozenset[str]) -> list[str]:
    return sorted(square for square, piece in board.items() if piece == horse and square in squares)


def _palace_neighbors(line: _Line) -> list[str]:
    return orthogonal_palace_neighbors(line.defender_king, line.defender) if line.defender_king else []


def _king_and_palace_neighbors(line: _Line) -> list[str]:
    return [line.defender_king, *_palace_neighbors(line)] if line.defender_king else []


def _horse_controlled(analysis: dict, horse_square: str | None, squares: list[str]) -> list[str]:
    """Those of ``squares`` the horse on ``horse_square`` really attacks, in the order given."""
    return [
        square
        for square in squares
        if any(
            attack['square'] == horse_square and attack['reason'] == 'horse_attack'
            for attack in analysis['attacked_squares'].get(square, [])
        )
    ]


def _final_attack(line: _Line) -> _Ply | None:
    return line.attacker_trace[-1] if line.attacker_trace else None


def _final_piece_type(line: _Line) -> str | None:
    return str(line.attacker_trace[-1]['piece']).upper() if line.attacker_trace else None


def _final_checker_types(line: _Line) -> list[str]:
    return sorted({line.board.get(item['square'], '').upper() for item in line.analysis['checking_pieces']})


def _has_finisher(checker_types: list[str], finishers: frozenset[str]) -> bool:
    return any(piece_type in finishers for piece_type in checker_types)


def _move_square(move: _Ply | None) -> str | None:
    return str(move['to_square']) if move else None


def _move_ply(move: _Ply | None) -> int | None:
    return int(move['ply']) if move else None


def _first_horse_check(trace: list[_Ply], targets: frozenset[str], horses: frozenset[str]) -> tuple[int, _Ply] | None:
    """The first ply, with its trace index, where one of ``horses`` lands on a target and gives check."""
    for index, item in enumerate(trace):
        if str(item['piece']) in horses and str(item['to_square']) in targets and bool(item['analysis']['is_check']):
            return index, item
    return None


# The two reply lookups below are not interchangeable: when the attacker moves second in the line, the
# defender ply at the same trace index is the one before the attacker's move, not the one after it.
def _reply_at_same_index(line: _Line, index: int, _move: _Ply) -> _Ply | None:
    return line.defender_trace[index] if index < len(line.defender_trace) else None


def _reply_on_next_ply(line: _Line, _index: int, move: _Ply) -> _Ply | None:
    return next((item for item in line.defender_trace if int(item['ply']) == int(move['ply']) + 1), None)


def _horse_entry(line: _Line, landing: tuple[int, _Ply] | None, find_reply: _ReplyFinder) -> _HorseEntry:
    if landing is None:
        return _HorseEntry(None, False, False)
    index, move = landing
    if bool(move['analysis']['is_checkmate']):
        return _HorseEntry(move, True, False)
    reply = find_reply(line, index, move)
    forced_king_reply = reply is not None and (
        str(reply['piece']) == _general_of(line.defender)
        and str(reply['from_square']) == str(move['analysis']['king_square'])
    )
    return _HorseEntry(move, False, forced_king_reply)


def _own_horse_entry(line: _Line, targets: frozenset[str]) -> _HorseEntry:
    """Elbow and angler: only the attacker's own horse counts, and the reply is read at the same trace index."""
    own_horse = frozenset({_horse_of(line.attacker)})
    return _horse_entry(line, _first_horse_check(line.attacker_trace, targets, own_horse), _reply_at_same_index)


def _entry_finishes(entry: _HorseEntry, checker_types: list[str], finishers: frozenset[str]) -> bool:
    return entry.immediate_finish or (entry.forced_king_reply and _has_finisher(checker_types, finishers))


def _finish_features(line: _Line, entry: _HorseEntry, checker_types: list[str]) -> dict[str, object]:
    return {
        'immediate_finish': entry.immediate_finish,
        'forced_king_reply': entry.forced_king_reply,
        'final_piece_type': _final_piece_type(line),
        'final_checker_types': checker_types,
    }


def _unblocked_leg(line: _Line, item: dict, vacated_square: str, previous_board: dict[str, str]) -> str | None:
    """The horse-leg square the last move cleared of the attacker's own piece, if ``item`` is such a horse check."""
    horse_piece = _horse_of(line.attacker)
    horse_square = item['square']
    if item['reason'] != 'horse_attack' or line.board.get(horse_square) != horse_piece:
        return None
    leg_square = _horse_leg_square(horse_square, line.defender_king)
    if not leg_square or leg_square != vacated_square:
        return None
    if previous_board.get(horse_square) != horse_piece:
        return None
    blocker_piece = previous_board.get(leg_square)
    if not blocker_piece or not is_attacker_piece(blocker_piece, line.attacker):
        return None
    return leg_square


def _discovered_horses(
    line: _Line, final_attack: _Ply | None, previous_board: dict[str, str]
) -> list[dict[str, object]]:
    if not (final_attack and line.defender_king):
        return []
    vacated_square = str(final_attack['from_square'])
    found: list[dict[str, object]] = []
    for item in line.analysis['checking_pieces']:
        leg_square = _unblocked_leg(line, item, vacated_square, previous_board)
        if leg_square is None:
            continue
        found.append(
            {
                'horse_square': item['square'],
                'leg_square': leg_square,
                'unblocking_piece': str(final_attack['piece']).upper(),
                'destination_square': str(final_attack['to_square']),
            }
        )
    return found


def recognize_discovered_horse_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    line = _read_line(fen, moves)
    final_attack = _final_attack(line)
    previous_fen, _ = apply_moves(fen, line.applied[:-1]) if line.applied else (fen, [])
    discovered = _discovered_horses(line, final_attack, parse_fen(previous_fen))
    detected = bool(
        line.analysis['is_checkmate']
        and final_attack
        and str(final_attack['piece']).upper() != 'N'
        and discovered
        and bool(final_attack['analysis']['is_checkmate'])
    )
    return _report(
        line,
        _DISCOVERED,
        detected,
        {
            'discovered_horses': discovered,
            'discovered_horse_count': len(discovered),
            'final_unblocking_piece_type': _final_piece_type(line),
            'final_unblocking_from': str(final_attack['from_square']) if final_attack else None,
            'final_unblocking_to': _move_square(final_attack),
        },
    )


def _elbow_final_support(line: _Line, static_horses: list[str], checker_types: list[str]) -> bool:
    return bool(
        line.analysis['is_checkmate']
        and static_horses
        and (
            _has_finisher(checker_types, _NON_HORSE_FINISHERS)
            or any(
                item['square'] in static_horses and item['reason'] == 'horse_attack'
                for item in line.analysis['checking_pieces']
            )
        )
    )


def recognize_elbow_horse_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    line = _read_line(fen, moves)
    targets = _ELBOW_VS_BLACK if line.defender == 'black' else _ELBOW_VS_RED
    horse = _horse_of(line.attacker)
    entry = _own_horse_entry(line, targets)
    elbow_square = _move_square(entry.move)
    elbow_horse_present = bool(elbow_square and line.board.get(elbow_square) == horse)
    static_horses = _horses_on(line.board, horse, targets)
    control_squares = _king_and_palace_neighbors(line)
    horse_control = {square: _horse_controlled(line.analysis, square, control_squares) for square in static_horses}
    active_horses = [square for square, controlled in horse_control.items() if controlled]
    checker_types = _final_checker_types(line)
    final_support = _elbow_final_support(line, static_horses, checker_types)
    detected = bool(
        line.analysis['is_checkmate']
        and active_horses
        and (
            final_support
            or (entry.move and elbow_horse_present and _entry_finishes(entry, checker_types, _NON_HORSE_FINISHERS))
        )
    )
    return _report(
        line,
        _ELBOW,
        detected,
        {
            'elbow_square': elbow_square,
            'elbow_horse_present': elbow_horse_present,
            'static_elbow_horse_squares': static_horses,
            'elbow_horse_control': horse_control,
            'active_elbow_horses': active_horses,
            'elbow_move_ply': _move_ply(entry.move),
            **_finish_features(line, entry, checker_types),
        },
    )


def _palcorner_from_entry(line: _Line, entry: _HorseEntry, control_squares: list[str]) -> _Corner:
    square = _move_square(entry.move)
    horse_present = bool(square and line.board.get(square, '').upper() == 'N')
    return _Corner(square, horse_present, sorted(_horse_controlled(line.analysis, square, control_squares)))


def _stationary_palcorner_horses(line: _Line, targets: frozenset[str], control_squares: list[str]) -> list[dict]:
    candidates: list[dict] = []
    for square in _horses_on(line.board, _horse_of(line.attacker), targets):
        controlled = _horse_controlled(line.analysis, square, control_squares)
        if len(controlled) == 1 and any(item['square'] != square for item in line.analysis['checking_pieces']):
            candidates.append({'square': square, 'controlled_squares': controlled})
    return candidates


def _palcorner_entry_mates(entry: _HorseEntry, corner: _Corner, checker_types: list[str]) -> bool:
    return bool(
        entry.move
        and corner.horse_present
        and len(corner.restricted) == 1
        and _entry_finishes(entry, checker_types, _ALL_FINISHERS)
    )


def recognize_palcorner_horse_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    line = _read_line(fen, moves)
    # Both corner ranks can occur in the opponent's palace.  The distinction
    # from Octagon Horse is made by the number of palace squares controlled,
    # not by the corner coordinate alone.
    targets = _CORNERS_VS_BLACK if line.defender == 'black' else _CORNERS_VS_RED
    entry = _horse_entry(line, _first_horse_check(line.attacker_trace, targets, _ANY_HORSE), _reply_on_next_ply)
    control_squares = _king_and_palace_neighbors(line)
    corner = _palcorner_from_entry(line, entry, control_squares)
    checker_types = _final_checker_types(line)
    stationary = _stationary_palcorner_horses(line, targets, control_squares)
    detected = bool(
        line.analysis['is_checkmate'] and (stationary or _palcorner_entry_mates(entry, corner, checker_types))
    )
    if stationary and not entry.move:
        corner = _Corner(stationary[0]['square'], True, stationary[0]['controlled_squares'])
    return _report(
        line,
        _PALCORNER,
        detected,
        {
            'palcorner_square': corner.square,
            'palcorner_horse_present': corner.horse_present,
            'palcorner_restricted_escape_squares': corner.restricted,
            'palcorner_move_ply': _move_ply(entry.move),
            **_finish_features(line, entry, checker_types),
            'stationary_horse_candidates': stationary,
        },
    )


def _empty_escape_squares(line: _Line) -> set[str]:
    return {square for square in _palace_neighbors(line) if square not in line.board}


def _only_horse_reaches(line: _Line, horse_square: str, reasons: list[dict]) -> bool:
    """True when this horse attacks the square and no other attacking piece type does."""
    return any(
        reason['reason'] == 'horse_attack' and reason['square'] == horse_square for reason in reasons
    ) and not any(
        reason['reason'] != 'horse_attack' and is_attacker_piece(line.board.get(reason['square'], ''), line.attacker)
        for reason in reasons
    )


def _angler_contributions(line: _Line, angler_horses: list[str], escape_squares: set[str]) -> dict[str, list[str]]:
    """For each angler horse that contributes, the king and empty escape squares only it covers."""
    contributions = {
        square: sorted(
            target
            for target, reasons in line.analysis['attacked_squares'].items()
            if (target == line.defender_king or target in escape_squares) and _only_horse_reaches(line, square, reasons)
        )
        for square in angler_horses
    }
    return {square: targets for square, targets in contributions.items() if targets}


def recognize_angler_horse_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    line = _read_line(fen, moves)
    targets = _ANGLER_VS_BLACK if line.defender == 'black' else _ANGLER_VS_RED
    angler_horses = _horses_on(line.board, _horse_of(line.attacker), targets)
    escape_squares = _empty_escape_squares(line)
    contributions = _angler_contributions(line, angler_horses, escape_squares)
    entry = _own_horse_entry(line, targets)
    checker_types = _final_checker_types(line)
    static_support = bool(
        line.analysis['is_checkmate'] and contributions and _has_finisher(checker_types, _ALL_FINISHERS)
    )
    dynamic_support = bool(
        line.analysis['is_checkmate']
        and entry.move
        and contributions
        and _entry_finishes(entry, checker_types, _ALL_FINISHERS)
    )
    detected = bool(static_support or dynamic_support)
    return _report(
        line,
        _ANGLER,
        detected,
        {
            'angler_horse_squares': angler_horses,
            'angler_horse_contributions': contributions,
            'empty_escape_squares': sorted(escape_squares),
            'angler_move_square': _move_square(entry.move),
            'angler_move_ply': _move_ply(entry.move),
            **_finish_features(line, entry, checker_types),
            'static_angler_support': static_support,
        },
    )


def _first_octagon_move(trace: list[_Ply], targets: frozenset[str]) -> _Ply | None:
    return next(
        (item for item in trace if str(item['piece']).upper() == 'N' and str(item['to_square']) in targets),
        None,
    )


def _octagon_square(octagon_move: _Ply | None, static_horses: list[str]) -> str | None:
    if octagon_move and str(octagon_move['to_square']) in static_horses:
        return str(octagon_move['to_square'])
    return static_horses[0] if static_horses else None


def _final_move_created_mate(line: _Line) -> bool:
    final_attack = _final_attack(line)
    return bool(final_attack and bool(final_attack['analysis']['is_checkmate']))


def recognize_octagon_horse_checkmate(fen: str, moves: list[str] | None = None) -> dict:
    line = _read_line(fen, moves)
    targets = _CORNERS_VS_BLACK if line.defender == 'black' else _CORNERS_VS_RED
    octagon_move = _first_octagon_move(line.attacker_trace, targets)
    static_horses = _horses_on(line.board, _horse_of(line.attacker), targets)
    octagon_square = _octagon_square(octagon_move, static_horses)
    octagon_horse_present = bool(octagon_square)
    opposite_corner = _OPPOSITE_CORNER.get(octagon_square)
    diagonal_corner_alignment = bool(octagon_square and line.defender_king == opposite_corner)
    restricted = sorted(_horse_controlled(line.analysis, octagon_square, _king_and_palace_neighbors(line)))
    checker_types = _final_checker_types(line)
    created_mate = _final_move_created_mate(line)
    octagon_direct_checkmate = bool(
        octagon_square
        and any(item['square'] == octagon_square for item in line.analysis['checking_pieces'])
        and created_mate
    )
    detected = bool(
        line.analysis['is_checkmate']
        and static_horses
        and octagon_horse_present
        and diagonal_corner_alignment
        and len(restricted) >= 2
        and _has_finisher(checker_types, _ALL_FINISHERS)
        and (not line.applied or created_mate)
    )
    return _report(
        line,
        _OCTAGON,
        detected,
        {
            'octagon_square': octagon_square,
            'octagon_horse_squares': static_horses,
            'octagon_horse_present': octagon_horse_present,
            'opposite_corner': opposite_corner,
            'diagonal_corner_alignment': diagonal_corner_alignment,
            'restricted_escape_squares': restricted,
            'final_checker_types': checker_types,
            'octagon_move_ply': _move_ply(octagon_move),
            'final_move_created_mate': created_mate,
            'octagon_direct_checkmate': octagon_direct_checkmate,
        },
    )
