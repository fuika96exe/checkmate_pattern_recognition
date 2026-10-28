from __future__ import annotations

from dataclasses import dataclass

from .board import legal_moves, parse_fen, position_analysis


SEVERITY = {"idle": 0, "chase": 1, "pinned_rook_chase": 2, "check": 3}


def position_key(fen: str) -> str:
    """The rules repeat a position, not a move sequence or FEN clocks."""
    parts = fen.split()
    return f"{parts[0]} {parts[1]}"


def _is_red(piece: str) -> bool:
    return piece.isupper()


def _crossed_river(square: str, piece: str) -> bool:
    """Whether a pawn has crossed its own river."""
    rank = int(square[1])
    return rank >= 5 if _is_red(piece) else rank <= 4


def _allowed_chaser(piece: str, square: str) -> bool:
    """Generals and crossed pawns may perpetually chase by product rule."""
    return piece.upper() == "K" or (piece.upper() == "P" and _crossed_river(square, piece))


def _ignored_target(piece: str, square: str) -> bool:
    """An uncrossed pawn is not a target that can create a chase offence."""
    return piece.upper() == "P" and not _crossed_river(square, piece)


def forced_rook_pins(
    fen: str, identities: dict[str, str], pinning_side: str
) -> dict[str, str]:
    """Return constrained enemy-rook ID -> pinning-horse ID relationships.

    A red horse on c8/g8 (or a black horse on c1/g1) has the classic
    ``卧槽马`` geometry against the opposing general. The adjacent rook on
    the horse-leg square is truly constrained only when every legal rook move
    is the capture of that horse. The pin alone is legal; callers use this
    only to elevate a *different* friendly piece's effective chase of that
    rook.
    """
    board = parse_fen(fen)
    layouts = (
        (("c8", "d8", "e9"), ("g8", "f8", "e9"))
        if pinning_side == "red"
        else (("c1", "d1", "e0"), ("g1", "f1", "e0"))
    )
    horse_piece = "N" if pinning_side == "red" else "n"
    rook_piece = "r" if pinning_side == "red" else "R"
    general_piece = "k" if pinning_side == "red" else "K"
    defender_moves = legal_moves(fen)
    result: dict[str, str] = {}

    for horse_square, leg_square, general_square in layouts:
        if (
            board.get(horse_square) != horse_piece
            or board.get(leg_square) != rook_piece
            or board.get(general_square) != general_piece
        ):
            continue
        rook_id = identities.get(leg_square)
        horse_id = identities.get(horse_square)
        if rook_id is None or horse_id is None:
            continue
        rook_moves = [move for move in defender_moves if move[:2] == leg_square]
        if rook_moves and all(move[2:] == horse_square for move in rook_moves):
            result[rook_id] = horse_id
    return result


def _fen_for_side(fen: str, side: str) -> str:
    """Use the same board with *side* to move, without exploring a variation."""
    parts = fen.split()
    parts[1] = "w" if side == "red" else "b"
    return " ".join(parts)


@dataclass(frozen=True)
class MoveRuleAssessment:
    """The self-contained rule facts produced by one completed move.

    The evaluator intentionally considers only the resulting board and the
    immediately available legal capture. It never plays that capture, scores
    material, or follows a recapture line. Repetition adjudication consumes
    these facts later, after it has assembled a cycle of positions.
    """

    is_check: bool
    chase_pairs: tuple[tuple[str, str], ...]
    pinned_rook_chase_target_ids: tuple[str, ...]

    @property
    def chase_target_ids(self) -> tuple[str, ...]:
        return tuple(sorted({victim_id for _, victim_id in self.chase_pairs}))

    def as_action(self, ply: int, side: str) -> dict[str, object]:
        return {
            "ply": ply,
            "side": side,
            "is_check": self.is_check,
            "chase_pairs": [list(pair) for pair in self.chase_pairs],
            "chase_target_ids": list(self.chase_target_ids),
            "pinned_rook_chase_target_ids": list(self.pinned_rook_chase_target_ids),
        }


def assess_move(after_fen: str, identities: dict[str, str], side: str) -> MoveRuleAssessment:
    """Classify the just-completed move with a one-ply, non-mutating rule.

    ``after_fen`` is the position after ``side`` moved. The only hypothetical
    position is the same board with ``side`` to move, which asks whether that
    side has an *immediate legal capture* of an opposing piece. No capture is
    applied and no reply, exchange valuation, or deeper line is calculated.
    """
    board = parse_fen(after_fen)
    capture_moves = legal_moves(_fen_for_side(after_fen, side))
    pairs: set[tuple[str, str]] = set()
    for move in capture_moves:
        source, target = move[:2], move[2:]
        attacker = board.get(source)
        victim = board.get(target)
        if attacker is None or victim is None or _is_red(attacker) != (side == "red"):
            continue
        if _is_red(victim) == (side == "red") or victim.upper() == "K" or _ignored_target(victim, target):
            continue
        if _allowed_chaser(attacker, source):
            continue
        attacker_id = identities.get(source)
        victim_id = identities.get(target)
        if attacker_id is not None and victim_id is not None:
            pairs.add((attacker_id, victim_id))

    pins = forced_rook_pins(after_fen, identities, side)
    pinned_rook_targets = {
        victim_id
        for attacker_id, victim_id in pairs
        if victim_id in pins and attacker_id != pins[victim_id]
    }
    return MoveRuleAssessment(
        is_check=position_analysis(after_fen)["is_check"],
        chase_pairs=tuple(sorted(pairs)),
        pinned_rook_chase_target_ids=tuple(sorted(pinned_rook_targets)),
    )


@dataclass(frozen=True)
class CycleClassification:
    red: str
    black: str


def classify_cycle(actions: list[dict], start_ply: int, end_ply: int) -> CycleClassification:
    """Classify each side over a repeated-position interval.

    A check wins over a simultaneous chase on the same move.  A chase needs
    every relevant move to attack exactly the same piece identity; everything
    else (including check/chase mixtures) is idle.
    """
    result: dict[str, str] = {}
    for side in ("red", "black"):
        moves = [
            action for action in actions
            if start_ply < action["ply"] <= end_ply and action["side"] == side
        ]
        if not moves:
            result[side] = "idle"
        elif all(action["is_check"] for action in moves):
            result[side] = "check"
        elif any(action["is_check"] for action in moves):
            result[side] = "idle"
        else:
            pinned_target_sets = [set(action.get("pinned_rook_chase_target_ids", [])) for action in moves]
            pinned_common = set.intersection(*pinned_target_sets) if pinned_target_sets else set()
            if pinned_common:
                result[side] = "pinned_rook_chase"
                continue
            target_sets = [set(action["chase_target_ids"]) for action in moves]
            common = set.intersection(*target_sets) if target_sets else set()
            # A move may threaten more than one piece.  It is still a
            # perpetual chase when one *physical* victim is common to every
            # relevant move; requiring exactly one target would incorrectly
            # discard that case.
            result[side] = "chase" if common else "idle"
    return CycleClassification(red=result["red"], black=result["black"])


def adjudicate(positions: list[dict], actions: list[dict]) -> dict:
    """Return the non-mutating adjudication for the latest position.

    Position occurrences include the original position.  At the third
    occurrence, only an unambiguously more-severe offender must vary.  Equal
    severity warns at the third occurrence and becomes a draw at the fourth.
    """
    current = positions[-1]
    matching = [index for index, item in enumerate(positions) if item["key"] == current["key"]]
    occurrence_count = len(matching)
    repeat_count = max(0, occurrence_count - 1)
    if occurrence_count == 1:
        return _decision("none", repeat_count, occurrence_count=occurrence_count)

    start_index = matching[-2]
    cycle = classify_cycle(actions, positions[start_index]["ply"], current["ply"])
    red_score = SEVERITY[cycle.red]
    black_score = SEVERITY[cycle.black]
    if occurrence_count < 3:
        return _decision(
            "watch", repeat_count, occurrence_count=occurrence_count,
            cycle=cycle, start_ply=positions[start_index]["ply"],
        )

    if red_score != black_score and occurrence_count >= 4:
        side = "red" if red_score > black_score else "black"
        return _decision(
            "must_change",
            repeat_count,
            occurrence_count=occurrence_count,
            cycle=cycle,
            start_ply=positions[start_index]["ply"],
            restricted_side=side,
            restricted_position_keys=sorted({item["key"] for item in positions[start_index:]}),
        )
    if occurrence_count >= 4:
        return _decision(
            "draw", repeat_count, occurrence_count=occurrence_count,
            cycle=cycle, start_ply=positions[start_index]["ply"],
        )
    return _decision(
        "warning", repeat_count, occurrence_count=occurrence_count,
        cycle=cycle, start_ply=positions[start_index]["ply"],
    )


def _decision(status: str, repeat_count: int, *, occurrence_count: int | None = None,
              cycle: CycleClassification | None = None,
              start_ply: int | None = None, restricted_side: str | None = None,
              restricted_position_keys: list[str] | None = None) -> dict:
    return {
        "status": status,
        "repeat_count": repeat_count,
        "occurrence_count": occurrence_count or (repeat_count + 1),
        "cycle_start_ply": start_ply,
        "red_classification": cycle.red if cycle else "idle",
        "black_classification": cycle.black if cycle else "idle",
        "restricted_side": restricted_side,
        "restricted_position_keys": restricted_position_keys or [],
    }
