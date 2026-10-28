"""Pure long-check / long-chase cycle evaluator.

This module deliberately has no dependency on application state, services, or
recognition code.  Call :func:`evaluate_cycle` with a FEN and UCCI moves when
the caller wants an isolated rule decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from .board import (
    BoardError,
    apply_move,
    attacked_squares,
    build_piece_identity,
    legal_moves,
    move_piece_identity,
    parse_fen,
    position_analysis,
    side_to_move,
)


PIECE_VALUE = {"R": 9, "N": 4, "C": 4, "B": 2, "A": 2, "P": 1, "K": 99}
SCORE = {"idle": 0, "chase": 1, "pinned_rook_chase": 2, "check": 3}


@dataclass(frozen=True)
class CycleMove:
    ply: int
    side: str
    ucci: str
    kind: str
    chase_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CycleRuleResult:
    verdict: str  # red_must_change | black_must_change | draw | warning | watch | none
    red_kind: str
    black_kind: str
    repeated: bool
    reason: str
    moves: tuple[CycleMove, ...]


def _red(piece: str) -> bool:
    return piece.isupper()


def _crossed(square: str, piece: str) -> bool:
    return int(square[1]) >= 5 if _red(piece) else int(square[1]) <= 4


def _allowed_attacker(piece: str, square: str) -> bool:
    return piece.upper() == "K" or (piece.upper() == "P" and _crossed(square, piece))


def _ignored_target(piece: str, square: str) -> bool:
    return piece.upper() == "P" and not _crossed(square, piece)


def _position_key(fen: str) -> str:
    parts = fen.split()
    return f"{parts[0]} {parts[1]}"


def _fen_for_side(fen: str, side: str) -> str:
    parts = fen.split()
    parts[1] = "w" if side == "red" else "b"
    return " ".join(parts)


def _profitable_capture(fen: str, source: str, target: str, attacker: str, victim: str) -> bool:
    """True only when the immediate legal exchange leaves the attacker ahead."""
    if PIECE_VALUE[attacker.upper()] == PIECE_VALUE[victim.upper()]:
        if any(move[2:] == source for move in legal_moves(fen)):
            return False  # equal-value offer / exchange
    parts = fen.split()
    parts[1] = "w" if _red(attacker) else "b"
    try:
        after_capture = apply_move(" ".join(parts), f"{source}{target}")
    except BoardError:
        return False
    recaptured = any(move[2:] == target for move in legal_moves(after_capture))
    return not recaptured or PIECE_VALUE[victim.upper()] > PIECE_VALUE[attacker.upper()]


def _pairs(fen: str, identities: dict[str, str], side: str) -> set[tuple[str, str]]:
    board = parse_fen(fen)
    result: set[tuple[str, str]] = set()
    for target, sources in attacked_squares(board, side).items():
        victim = board.get(target)
        victim_id = identities.get(target)
        if not victim or not victim_id or _red(victim) == (side == "red"):
            continue
        if victim.upper() == "K" or _ignored_target(victim, target):
            continue
        for info in sources:
            source = info["square"]
            attacker = board.get(source)
            attacker_id = identities.get(source)
            if not attacker or not attacker_id or _allowed_attacker(attacker, source):
                continue
            if _profitable_capture(fen, source, target, attacker, victim):
                result.add((attacker_id, victim_id))
    return result


def _lower_value_pair(fen: str, identities: dict[str, str], pair: tuple[str, str]) -> bool:
    board = parse_fen(fen)
    pieces = {identity: board[square] for square, identity in identities.items() if square in board}
    attacker, victim = pieces.get(pair[0]), pieces.get(pair[1])
    return bool(attacker and victim and PIECE_VALUE[attacker.upper()] < PIECE_VALUE[victim.upper()])


def _pinned_rooks(fen: str, identities: dict[str, str], side: str) -> dict[str, str]:
    """Find a C8/G8 or C1/G1 horse that leaves an enemy rook only its capture."""
    board = parse_fen(fen)
    layouts = (("c8", "d8", "e9"), ("g8", "f8", "e9")) if side == "red" else (("c1", "d1", "e0"), ("g1", "f1", "e0"))
    horse, rook, general = ("N", "r", "k") if side == "red" else ("n", "R", "K")
    defender_moves = legal_moves(fen)
    result: dict[str, str] = {}
    for horse_square, leg_square, king_square in layouts:
        if board.get(horse_square) != horse or board.get(leg_square) != rook or board.get(king_square) != general:
            continue
        rook_moves = [move for move in defender_moves if move[:2] == leg_square]
        if rook_moves and all(move[2:] == horse_square for move in rook_moves):
            result[identities[leg_square]] = identities[horse_square]
    return result


def _classify(actions: list[dict], start: int, end: int, side: str) -> str:
    own = [action for action in actions if start < action["ply"] <= end and action["side"] == side]
    if not own:
        return "idle"
    if all(action["is_check"] for action in own):
        return "check"
    if any(action["is_check"] for action in own):
        return "idle"
    for field, kind in (("pinned", "pinned_rook_chase"), ("targets", "chase")):
        common = set.intersection(*(set(action[field]) for action in own))
        if common:
            return kind
    return "idle"


def evaluate_cycle(initial_fen: str, moves: list[str], *, assume_cycle: bool = False) -> CycleRuleResult:
    """Evaluate a sequence without changing application state.

    With ``assume_cycle=False`` (default), the function requires a real
    repeated position and uses normal third/fourth-occurrence thresholds.
    With ``assume_cycle=True``, it treats the supplied sequence as the proven
    cycle.  This is useful for abbreviated book fixtures such as WXR d025.
    """
    fen = initial_fen
    identities = build_piece_identity(fen)
    latches = _pairs(fen, identities, "red") | _pairs(fen, identities, "black")
    positions = [{"ply": 0, "key": _position_key(fen)}]
    actions: list[dict] = []
    rendered: list[CycleMove] = []

    for ply, move in enumerate(moves, 1):
        side = side_to_move(fen)
        moved_id = identities.get(move[:2])
        before_fen, before_ids = fen, identities
        fen = apply_move(fen, move)
        identities = move_piece_identity(identities, move[:2], move[2:])
        before, after = _pairs(before_fen, before_ids, side), _pairs(fen, identities, side)
        all_after = _pairs(fen, identities, "red") | _pairs(fen, identities, "black")
        prior = set(latches)
        latches = prior & all_after
        events = {
            pair for pair in after
            if pair not in before and pair not in latches
            and ((pair[1], pair[0]) not in prior or pair[0] == moved_id or _lower_value_pair(fen, identities, pair))
        }
        latches.update(events)
        pins = _pinned_rooks(fen, identities, side)
        pinned = {victim for attacker, victim in events if victim in pins and attacker != pins[victim]}
        is_check = position_analysis(fen)["is_check"]
        targets = {victim for _, victim in events}
        kind = "check" if is_check else "pinned_rook_chase" if pinned else "chase" if targets else "idle"
        rendered.append(CycleMove(ply, side, move, kind, tuple(sorted(events))))
        actions.append({"ply": ply, "side": side, "is_check": is_check, "targets": targets, "pinned": pinned})
        positions.append({"ply": ply, "key": _position_key(fen)})

    matching = [i for i, position in enumerate(positions) if position["key"] == positions[-1]["key"]]
    repeated = len(matching) > 1
    if assume_cycle:
        start, occurrences = 0, 3
    elif repeated:
        start, occurrences = matching[-2], len(matching)
    else:
        return CycleRuleResult("none", "idle", "idle", False, "没有重复局面；如这是缩略题例，可用 assume_cycle=True 评估棋例性质。", tuple(rendered))

    red, black = _classify(actions, positions[start]["ply"], positions[-1]["ply"], "red"), _classify(actions, positions[start]["ply"], positions[-1]["ply"], "black")
    # A real game has a two-stage experience.  The first repeated position is
    # only observed; the third occurrence warns both players.  On the fourth
    # occurrence an equal cycle is a draw, while the higher-ranked side must
    # change its move.  ``assume_cycle`` remains decisive for short book
    # fixtures, whose input is explicitly declared to be a completed cycle.
    if occurrences < 3 and not assume_cycle:
        verdict = "watch"
    elif SCORE[red] != SCORE[black]:
        if assume_cycle or occurrences >= 4:
            verdict = "red_must_change" if SCORE[red] > SCORE[black] else "black_must_change"
        else:
            verdict = "warning"
    elif assume_cycle or occurrences >= 4:
        verdict = "draw"
    else:
        verdict = "warning"
    reason = f"循环分类：红方 {red}，黑方 {black}。"
    return CycleRuleResult(verdict, red, black, repeated, reason, tuple(rendered))
