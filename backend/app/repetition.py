from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .board import BoardError, apply_move, attacked_squares, legal_moves, parse_fen, side_to_move


SEVERITY = {"idle": 0, "chase": 1, "pinned_rook_chase": 2, "check": 3}


def position_key(fen: str) -> str:
    """The rules repeat a position, not a move sequence or FEN clocks."""
    parts = fen.split()
    return f"{parts[0]} {parts[1]}"


PIECE_VALUE = {"R": 9, "N": 4, "C": 4, "B": 2, "A": 2, "P": 1, "K": 99}


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


def _capture_is_profitable(
    fen: str, source: str, target: str, attacker: str, victim: str
) -> bool:
    """Use the immediate material exchange to filter ordinary protected pieces.

    This deliberately stops at the first recapture, but the recapture must be
    a *legal* move.  A geometrically attacking protector that is pinned to its
    general is a fake protector and cannot make an exchange unprofitable.
    """
    # For equally valued pieces, first give the defender its immediate legal
    # response.  If it can simply take the attacking piece now, the move is a
    # sacrifice/offer, not a chase.  A reply that exposes the defender's
    # general is absent from legal_moves(), so fake responses are excluded.
    if PIECE_VALUE[victim.upper()] == PIECE_VALUE[attacker.upper()]:
        if any(move[2:] == source for move in legal_moves(fen)):
            return False

    parts = fen.split()
    # `fen` is the position after the candidate move, so its side-to-move is
    # the defender.  Reconstruct the same board with the attacking side to
    # move in order to test the hypothetical capture legally.
    parts[1] = "w" if _is_red(attacker) else "b"
    capture_fen = " ".join(parts)
    try:
        after_capture = apply_move(capture_fen, f"{source}{target}")
    except BoardError:
        # A pinned attacker or a pseudo-attack cannot create a real chase.
        return False
    recaptured = any(move[2:] == target for move in legal_moves(after_capture))
    if not recaptured:
        return True
    return PIECE_VALUE[victim.upper()] > PIECE_VALUE[attacker.upper()]


def qualifying_chase_pairs(
    fen: str, identities: dict[str, str], side: str
) -> set[tuple[str, str]]:
    """Return (attacker ID, victim ID) pairs eligible for chase accounting."""
    board = parse_fen(fen)
    attacks = attacked_squares(board, side)
    pairs: set[tuple[str, str]] = set()
    for target, sources in attacks.items():
        victim = board.get(target)
        victim_id = identities.get(target)
        if victim is None or victim_id is None or _is_red(victim) == (side == "red"):
            continue
        if victim.upper() == "K" or _ignored_target(victim, target):
            continue
        for source_info in sources:
            source = source_info["square"]
            attacker = board.get(source)
            attacker_id = identities.get(source)
            if attacker is None or attacker_id is None:
                continue
            # Allowed chasers never create a prohibited perpetual-chase event.
            if _allowed_chaser(attacker, source):
                continue
            if _capture_is_profitable(fen, source, target, attacker, victim):
                pairs.add((attacker_id, victim_id))
    return pairs


def _is_lower_value_attacker(
    fen: str, identities: dict[str, str], pair: tuple[str, str]
) -> bool:
    board = parse_fen(fen)
    pieces_by_id = {identity: board[square] for square, identity in identities.items() if square in board}
    attacker = pieces_by_id.get(pair[0])
    victim = pieces_by_id.get(pair[1])
    return (
        attacker is not None
        and victim is not None
        and PIECE_VALUE[attacker.upper()] < PIECE_VALUE[victim.upper()]
    )


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


def chase_events(
    previous_fen: str,
    previous_identities: dict[str, str],
    next_fen: str,
    next_identities: dict[str, str],
    side: str,
    moved_piece_id: str | None,
    latches: set[tuple[str, str]],
) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """Return newly re-established chase victims and updated relation latches.

    A persistent attack is not repeatedly a chase.  Every move refreshes the
    complete set of ordered attacker/victim relations: a relation disappears
    when either participant moves away or a screen changes, and can only be a
    new chase if that same ordered pair is later re-established.  Relations
    that merely remain true through unrelated moves do not create events.
    """
    before = qualifying_chase_pairs(previous_fen, previous_identities, side)
    after = qualifying_chase_pairs(next_fen, next_identities, side)
    all_after = (
        qualifying_chase_pairs(next_fen, next_identities, "red")
        | qualifying_chase_pairs(next_fen, next_identities, "black")
    )
    prior_latches = set(latches)
    updated_latches = prior_latches & all_after
    events = {
        pair for pair in after
        if pair not in before
        and pair not in updated_latches
        # A stationary third piece must not turn a broken A→B relation into a
        # newly counted B→A chase merely by exposing B's attack.  If B itself
        # moved (as in a cannon or horse escaping and counter-chasing), it is
        # a genuine new B→A chase and must be retained.
        and (
            (pair[1], pair[0]) not in prior_latches
            or pair[0] == moved_piece_id
            # A lower-value piece newly pursuing a higher-value piece remains
            # a chase even when the earlier relationship pointed the other
            # way: cannon/horse → rook is materially profitable after a
            # recapture and must not be suppressed as a mere counter-attack.
            or _is_lower_value_attacker(next_fen, next_identities, pair)
        )
    }
    updated_latches.update(events)
    pins = forced_rook_pins(next_fen, next_identities, side)
    pinned_rook_targets = {
        victim_id
        for attacker_id, victim_id in events
        # The horse establishes the permitted pin; another friendly piece
        # must be the one that effectively chases the constrained rook.
        if victim_id in pins and attacker_id != pins[victim_id]
    }
    return sorted({victim_id for _, victim_id in events}), sorted(pinned_rook_targets), updated_latches


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

    if red_score != black_score:
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
