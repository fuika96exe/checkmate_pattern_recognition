from __future__ import annotations

from copy import deepcopy

from .board import START_FEN, build_piece_identity, parse_fen
from .models import (
    ChoiceOccurrence,
    Classification,
    MemoryPreset,
    OpeningMemory,
    RecognitionState,
    SideMemory,
)


CHOICE_NAMES = {
    "red": {
        "central_cannon": "中炮",
        "fly_elephant": "飛相",
        "proper_horse_opening": "起馬",
        "palcorner_cannon": "仕角炮",
        "cross_palace_cannon": "過宮炮",
        "angle_pawn": "仙人指路",
        "palace_advisor_opening": "上士局",
        "edge_horse_opening": "邊馬局",
        "edge_cannon_opening": "邊炮局",
        "river_cannon_opening": "巡河炮局",
        "cross_river_cannon_opening": "過河炮局",
        "pawn_bottom_cannon_opening": "兵底炮局",
        "golden_hook_cannon_opening": "金鉤炮局",
        "edge_pawn_opening": "邊兵局",
    },
    "black": {
        "central_cannon": "中炮",
        "fly_elephant": "飛象",
        "proper_horse_opening": "起馬",
        "palcorner_cannon": "仕角炮",
        "cross_palace_cannon": "過宮炮",
        "angle_pawn": "挺卒",
        "pawn_bottom_cannon": "卒底炮",
        "palace_advisor_opening": "上士局",
        "edge_horse_opening": "邊馬局",
        "edge_cannon_opening": "邊炮局",
        "river_cannon_opening": "巡河炮局",
        "cross_river_cannon_opening": "過河炮局",
        "pawn_bottom_cannon_opening": "兵底炮局",
        "golden_hook_cannon_opening": "金鉤炮局",
        "edge_pawn_opening": "邊兵局",
    },
}

FIRST_MOVE_MAP = {
    "red": {
        "d0e1": ("palace_advisor_opening", None),
        "f0e1": ("palace_advisor_opening", None),
        "h0i2": ("edge_horse_opening", None),
        "b0a2": ("edge_horse_opening", None),
        "h2i2": ("edge_cannon_opening", None),
        "b2a2": ("edge_cannon_opening", None),
        "h2h4": ("river_cannon_opening", None),
        "b2b4": ("river_cannon_opening", None),
        "h2h6": ("cross_river_cannon_opening", None),
        "b2b6": ("cross_river_cannon_opening", None),
        "h2g2": ("pawn_bottom_cannon_opening", None),
        "b2c2": ("pawn_bottom_cannon_opening", None),
        "h2c2": ("golden_hook_cannon_opening", None),
        "b2g2": ("golden_hook_cannon_opening", None),
        "i3i4": ("edge_pawn_opening", None),
        "a3a4": ("edge_pawn_opening", None),
        "g0e2": ("fly_elephant", "g"),
        "c0e2": ("fly_elephant", "c"),
    },
    "black": {
        "d9e8": ("palace_advisor_opening", None),
        "f9e8": ("palace_advisor_opening", None),
        "g9e7": ("fly_elephant", "g"),
        "c9e7": ("fly_elephant", "c"),
    }
}

FEN_INFERENCE_MAP = {
    "red": {
        ("A", "e1"): ("palace_advisor_opening", None),
        ("N", "i2"): ("edge_horse_opening", None),
        ("N", "a2"): ("edge_horse_opening", None),
        ("C", "i2"): ("edge_cannon_opening", None),
        ("C", "a2"): ("edge_cannon_opening", None),
        ("C", "h4"): ("river_cannon_opening", None),
        ("C", "b4"): ("river_cannon_opening", None),
        ("C", "h6"): ("cross_river_cannon_opening", None),
        ("C", "b6"): ("cross_river_cannon_opening", None),
        ("P", "i4"): ("edge_pawn_opening", None),
        ("P", "a4"): ("edge_pawn_opening", None),
        ("C", "d2"): ("cross_palace_cannon", "right"),
        ("C", "f2"): ("cross_palace_cannon", "left"),
        ("B", "e2"): ("fly_elephant", None),
    },
    "black": {
        ("a", "e8"): ("palace_advisor_opening", None),
        ("c", "d7"): ("cross_palace_cannon", "left"),
        ("c", "f7"): ("cross_palace_cannon", "right"),
    }
}

COMPOSITE_NAMES = {
    "screen_horse": "屏風馬",
    "reverse_palace_horse": "反宮馬",
    "single_horse": "單提馬",
    "left_three_step_tiger": "左三步虎",
    "right_three_step_tiger": "右三步虎",
    "left_cannon_blockade": "左炮封車",
}

# Formation names are kept separate from the historical choice path.  A
# formation may be added after the opening choice has already been locked, and
# some formations are mutually exclusive (the first one formed wins).
SHAPE_NAMES = {
    "five_six_cannon": "\u4e94\u516d\u70ae",
    "five_seven_cannon": "\u4e94\u4e03\u70ae",
    "five_eight_cannon": "\u4e94\u516b\u70ae",
    "five_nine_cannon": "\u4e94\u4e5d\u70ae",
    "seven_route_horse": "\u4e03\u8def\u99ac",
    "edge_horse_left": "\u908a\u99ac",
    "edge_horse_right": "\u908a\u99ac",
    "horizontal_rook": "\u6a6b\u8eca",
    "straight_rook": "\u76f4\u8eca",
    "double_horizontal_rooks": "\u96d9\u6a6b\u8eca",
    "river_cannon": "\u5de1\u6cb3\u70ae",
    "river_rook": "\u5de1\u6cb3\u8eca",
    "riding_river_rook": "\u9a0e\u6cb3\u8eca",
    "cross_river_rook": "\u904e\u6cb3\u8eca",
    "flat_cannon_exchange": "\u5e73\u70ae\u514c\u8eca",
    "advance_three_pawn": "\u9032\u4e09\u5175",
    "advance_seven_pawn": "\u9032\u4e03\u5175",
    "advance_three_soldier": "\u633a\u4e09\u5352",
    "advance_seven_soldier": "\u633a\u4e03\u5352",
    "two_headed_snake": "\u5169\u982d\u86c7",
    "double_proper_horses": "\u96d9\u6b63\u99ac",
    "slow_rook": "\u7de9\u958b\u8eca",
    "fly_left_elephant": "\u98db\u5de6\u8c61",
    "fly_right_elephant": "\u98db\u53f3\u8c61",
}

FIVE_CANNON_IDS = (
    "five_six_cannon",
    "five_seven_cannon",
    "five_eight_cannon",
    "five_nine_cannon",
)

PALCORNER_MOVES = {
    "red": {"h2f2": "right", "b2d2": "left"},
    "black": {"b7d7": "right", "h7f7": "left"},
}
CROSS_PALACE_MOVES = {
    "red": {"h2d2": "right", "b2f2": "left"},
    "black": {"b7f7": "right", "h7d7": "left"},
}


def _side_memory(memory: OpeningMemory, side: str) -> SideMemory:
    return memory.red if side == "red" else memory.black


def _has_choice(side_memory: SideMemory, choice_id: str) -> bool:
    return any(choice.id == choice_id for choice in side_memory.choice_path)


def _choice_ids(side_memory: SideMemory) -> list[str]:
    return [choice.id for choice in side_memory.choice_path]


def _add_choice(
    side_memory: SideMemory,
    choice_id: str,
    ply: int,
    *,
    wing: str | None = None,
    origin_file: str | None = None,
    provisional: bool = False,
    source: str = "fen",
) -> None:
    if _has_choice(side_memory, choice_id):
        return
    side_memory.choice_path.append(
        ChoiceOccurrence(
            id=choice_id,
            formed_at_ply=ply,
            wing=wing,
            origin_file=origin_file,
            provisional=provisional,
            source=source,
        )
    )


def _add_composite(side_memory: SideMemory, system_id: str, ply: int) -> None:
    if any(item.id == system_id for item in side_memory.composite_systems):
        return
    side_memory.composite_systems.append(
        ChoiceOccurrence(id=system_id, formed_at_ply=ply, source="fen")
    )
    side_memory.locks["defensive_system"] = system_id


def _has_shape(side_memory: SideMemory, shape_id: str) -> bool:
    return any(item.id == shape_id for item in side_memory.formed_shapes)


def _add_shape(
    side_memory: SideMemory,
    shape_id: str,
    ply: int,
    *,
    wing: str | None = None,
    source: str = "fen",
    lock_group: str | None = None,
) -> bool:
    """Record a first-formed shape, optionally locking a mutually-exclusive group."""
    if _has_shape(side_memory, shape_id):
        return False
    if lock_group:
        lock_key = f"shape:{lock_group}"
        locked = side_memory.locks.get(lock_key)
        if locked and locked != shape_id:
            side_memory.formed_shapes.append(
                ChoiceOccurrence(
                    id=shape_id,
                    formed_at_ply=ply,
                    wing=wing,
                    source=source,
                    lock_group=lock_group,
                    eligible_for_name=False,
                    suppressed_by=locked,
                )
            )
            return False
    side_memory.formed_shapes.append(
        ChoiceOccurrence(
            id=shape_id,
            formed_at_ply=ply,
            wing=wing,
            source=source,
            lock_group=lock_group,
        )
    )
    if lock_group:
        side_memory.locks[f"shape:{lock_group}"] = shape_id
    return True


def detect_current_shapes(fen: str) -> dict[str, list[str]]:
    board = parse_fen(fen)
    shapes: dict[str, list[str]] = {"red": [], "black": []}

    def add(side: str, shape: str, condition: bool) -> None:
        if condition and shape not in shapes[side]:
            shapes[side].append(shape)

    add("red", "central_cannon", board.get("e2") == "C")
    add("black", "central_cannon", board.get("e7") == "c")
    # With both same-colour cannons still visible, the untouched cannon tells
    # us which original cannon moved into the centre.  This makes the
    # same/opposite-side cannon matchup a pure position rule.
    add(
        "red",
        "central_cannon_from_h_file",
        board.get("e2") == "C" and board.get("b2") == "C",
    )
    add(
        "red",
        "central_cannon_from_b_file",
        board.get("e2") == "C" and board.get("h2") == "C",
    )
    add(
        "black",
        "central_cannon_from_h_file",
        board.get("e7") == "c" and board.get("b7") == "c",
    )
    add(
        "black",
        "central_cannon_from_b_file",
        board.get("e7") == "c" and board.get("h7") == "c",
    )
    add("red", "fly_elephant", board.get("e2") == "B")
    add("black", "fly_elephant", board.get("e7") == "b")

    # A five-* cannon is the central cannon carried out along the home rank;
    # the number is the destination file from the mover's perspective.
    # Position-only five-* heuristics deliberately avoid the untouched
    # original cannon square (b2/h2 or b7/h7), which would otherwise make the
    # starting position look like a 五八炮. Move history remains authoritative
    # whenever a UCCI move is available.
    add("red", "five_six_cannon", (board.get("d2") == "C" and board.get("b2") == "C") or (board.get("f2") == "C" and board.get("h2") == "C") or (board.get("e2") == "C" and any(board.get(f"d{r}") == "C" or board.get(f"f{r}") == "C" for r in range(10))))
    add("red", "five_seven_cannon", (board.get("c2") == "C" and board.get("b2") != "C") or (board.get("g2") == "C" and board.get("h2") != "C") or (board.get("e2") == "C" and any(board.get(f"c{r}") == "C" or board.get(f"g{r}") == "C" for r in range(10))))
    add("red", "five_eight_cannon", board.get("e2") == "C" and (board.get("b6") == "C" or board.get("h6") == "C"))
    add("red", "five_nine_cannon", (board.get("a2") == "C" and board.get("b2") != "C") or (board.get("i2") == "C" and board.get("h2") != "C") or (board.get("e2") == "C" and any(board.get(f"a{r}") == "C" or board.get(f"i{r}") == "C" for r in range(10))))
    add("black", "five_six_cannon", (board.get("f7") == "c" and board.get("h7") == "c") or (board.get("d7") == "c" and board.get("b7") == "c") or (board.get("e7") == "c" and any(board.get(f"f{r}") == "c" or board.get(f"d{r}") == "c" for r in range(10))))
    add("black", "five_seven_cannon", (board.get("g7") == "c" and board.get("h7") != "c") or (board.get("c7") == "c" and board.get("b7") != "c") or (board.get("e7") == "c" and any(board.get(f"g{r}") == "c" or board.get(f"c{r}") == "c" for r in range(10))))
    add("black", "five_eight_cannon", board.get("e7") == "c" and (board.get("b3") == "c" or board.get("h3") == "c"))
    add("black", "five_nine_cannon", (board.get("i7") == "c" and board.get("h7") != "c") or (board.get("a7") == "c" and board.get("b7") != "c") or (board.get("e7") == "c" and any(board.get(f"i{r}") == "c" or board.get(f"a{r}") == "c" for r in range(10))))

    add("red", "seven_route_horse", board.get("c2") == "N")
    add("black", "seven_route_horse", board.get("g7") == "n")
    add("red", "edge_horse_left", board.get("a2") == "N")
    add("red", "edge_horse_right", board.get("i2") == "N")
    add("black", "edge_horse_left", board.get("i7") == "n")
    add("black", "edge_horse_right", board.get("a7") == "n")
    add("red", "double_proper_horses", board.get("c2") == "N" and board.get("g2") == "N")
    add("black", "double_proper_horses", board.get("g7") == "n" and board.get("c7") == "n")

    for side, piece, squares in (
        ("red", "N", (("c2", "left"), ("g2", "right"))),
        ("black", "n", (("g7", "left"), ("c7", "right"))),
    ):
        for square, wing in squares:
            add(side, f"proper_horse_{wing}", board.get(square) == piece)
        add(
            side,
            "double_proper_horses",
            all(board.get(square) == piece for square, _ in squares),
        )

    for side, piece, squares in (
        ("red", "P", (("c4", "left"), ("g4", "right"))),
        ("black", "p", (("g5", "left"), ("c5", "right"))),
    ):
        for square, wing in squares:
            add(side, f"angle_pawn_{wing}", board.get(square) == piece)

    # Red's Chinese file numbers run from right to left: g is the red
    # three-file and c is the red seven-file. Black's c/g mapping is the
    # opposite physical direction and remains unchanged.
    add("red", "advance_three_pawn", board.get("g4") == "P")
    add("red", "advance_seven_pawn", board.get("c4") == "P")
    add("black", "advance_three_soldier", board.get("c5") == "p")
    add("black", "advance_seven_soldier", board.get("g5") == "p")
    add(
        "red",
        "two_headed_snake",
        board.get("c4") == "P" and board.get("g4") == "P",
    )
    add(
        "black",
        "two_headed_snake",
        board.get("c5") == "p" and board.get("g5") == "p",
    )

    # Current rook river stages are useful when a position is inspected from
    # FEN.  Move-time promotion below is what locks the first stage formed.
    red_rooks = [square for square, piece in board.items() if piece == "R"]
    black_rooks = [square for square, piece in board.items() if piece == "r"]
    add("red", "river_rook_shape", any(square[1] == "4" for square in red_rooks))
    add("red", "riding_river_rook_shape", any(square[1] == "5" for square in red_rooks))
    add("red", "cross_river_rook_shape", any(square[1] == "6" for square in red_rooks))
    add("black", "river_rook_shape", any(square[1] == "5" for square in black_rooks))
    add("black", "riding_river_rook_shape", any(square[1] == "4" for square in black_rooks))
    add("black", "cross_river_rook_shape", any(square[1] == "3" for square in black_rooks))
    add("red", "palace_advisor_shape", board.get("e1") == "A")
    add("black", "palace_advisor_shape", board.get("e8") == "a")
    add("red", "pawn_seven_at_starting_rank", board.get("c3") == "P")
    add("red", "pawn_three_at_starting_rank", board.get("g3") == "P")
    add("black", "cannon_at_b3", board.get("b3") == "c")
    add("black", "cannon_at_h3", board.get("h3") == "c")

    add("red", "palcorner_cannon_left", board.get("d2") == "C")
    add("red", "palcorner_cannon_right", board.get("f2") == "C")
    add("black", "palcorner_cannon_left", board.get("f7") == "c")
    add("black", "palcorner_cannon_right", board.get("d7") == "c")

    add(
        "black",
        "screen_horse_shape",
        board.get("c7") == "n"
        and board.get("g7") == "n"
        and all(board.get(square) != "c" for square in ("d7", "e7", "f7")),
    )
    add(
        "black",
        "reverse_palace_horse_shape",
        board.get("c7") == "n"
        and board.get("g7") == "n"
        and (board.get("d7") == "c" or board.get("f7") == "c"),
    )

    add(
        "black",
        "pawn_bottom_cannon_shape",
        (board.get("c7") == "c" and board.get("c4") == "P")
        or (board.get("g7") == "c" and board.get("g4") == "P"),
    )
    add(
        "red",
        "pawn_bottom_cannon_shape",
        (board.get("c2") == "C" and board.get("c5") == "p")
        or (board.get("g2") == "C" and board.get("g5") == "p"),
    )
    add("red", "horizontal_rook_left", board.get("a0") != "R" and board.get("a1") == "R")
    add("red", "horizontal_rook_right", board.get("i0") != "R" and board.get("i1") == "R")
    add("black", "horizontal_rook_left", board.get("i9") != "r" and board.get("i8") == "r")
    add("black", "horizontal_rook_right", board.get("a9") != "r" and board.get("a8") == "r")
    add("red", "edge_cannon_left", board.get("a2") == "C")
    add("red", "edge_cannon_right", board.get("i2") == "C")
    add("black", "edge_cannon_left", board.get("i7") == "c")
    add("black", "edge_cannon_right", board.get("a7") == "c")

    for side in shapes:
        shapes[side].sort()
    return shapes


def _record_move_facts(
    side_memory: SideMemory,
    side: str,
    ucci: str,
    side_move_number: int,
) -> None:
    fact_moves = {
        "red": {
            "b0c2": "left_proper_horse_move",
            "h0g2": "right_proper_horse_move",
            "b0a2": "left_edge_horse_move",
            "h0i2": "right_edge_horse_move",
            "a0b0": "left_rook_shift",
            "i0h0": "right_rook_shift",
            "b2a2": "left_cannon_edge",
            "h2i2": "right_cannon_edge",
            "b2b4": "left_river_cannon_move",
            "h2h4": "right_river_cannon_move",
            "e2d2": "five_six_cannon_move",
            "e2c2": "five_seven_cannon_move",
            "e2b2": "five_eight_cannon_move",
            "e2a2": "five_nine_cannon_move",
            "g3g4": "advance_three_pawn_move",
            "c3c4": "advance_seven_pawn_move",
            "b2b6": "left_cannon_blockade_move",
        },
        "black": {
            "h9g7": "left_proper_horse_move",
            "b9c7": "right_proper_horse_move",
            "h9i7": "left_edge_horse_move",
            "b9a7": "right_edge_horse_move",
            "i9h9": "left_rook_shift",
            "a9b9": "right_rook_shift",
            "h7i7": "left_cannon_edge",
            "b7a7": "right_cannon_edge",
            "b7b5": "left_river_cannon_move",
            "h7h5": "right_river_cannon_move",
            "e7f7": "five_six_cannon_move",
            "e7g7": "five_seven_cannon_move",
            "e7h7": "five_eight_cannon_move",
            "e7i7": "five_nine_cannon_move",
            "c6c5": "advance_three_soldier_move",
            "g6g5": "advance_seven_soldier_move",
            "h7h3": "left_cannon_blockade_move",
            "g9e7": "left_elephant_move",
            "c9e7": "right_elephant_move",
        },
    }
    fact = fact_moves[side].get(ucci)
    if fact and fact not in side_memory.facts:
        side_memory.facts.append(fact)

    # The project deliberately uses the user's naming convention: a rook
    # advancing on its original file is 橫車, while a rook moving sideways on
    # its home rank is 直車.
    from_square, to_square = ucci[:2], ucci[2:]
    original_rook_files = {"red": {"a", "i"}, "black": {"a", "i"}}[side]
    original_rank = "0" if side == "red" else "9"
    if from_square[0] in original_rook_files and from_square[1] == original_rank:
        if to_square[0] == from_square[0] and to_square[1] == ("1" if side == "red" else "8"):
            direction = "left" if from_square[0] == ("a" if side == "red" else "i") else "right"
            name = f"{direction}_horizontal_rook_move"
            if name not in side_memory.facts:
                side_memory.facts.append(name)
        elif to_square[1] == original_rank and to_square[0] != from_square[0]:
            direction = "left" if from_square[0] == ("a" if side == "red" else "i") else "right"
            name = f"{direction}_straight_rook_move"
            if name not in side_memory.facts:
                side_memory.facts.append(name)

    if side_move_number == 3:
        rook_moved = any(
            fact.endswith(("horizontal_rook_move", "straight_rook_move"))
            for fact in side_memory.facts
        )
        if not rook_moved and "third_move_without_rook" not in side_memory.facts:
            side_memory.facts.append("third_move_without_rook")


def _allowed_transition(side: str, from_id: str, to_id: str) -> bool:
    allowed = {
        ("red", "proper_horse_opening", "central_cannon"),
        ("black", "proper_horse_opening", "central_cannon"),
        ("red", "proper_horse_opening", "palcorner_cannon"),
        ("black", "proper_horse_opening", "palcorner_cannon"),
        ("red", "angle_pawn", "central_cannon"),
        ("red", "angle_pawn", "fly_elephant"),
    }
    return (side, from_id, to_id) in allowed


def _may_add(side: str, side_memory: SideMemory, to_id: str) -> bool:
    if not side_memory.choice_path:
        return True
    return _allowed_transition(side, side_memory.choice_path[-1].id, to_id)


def _promote_direct_choices(
    memory: OpeningMemory,
    side: str,
    shapes: dict[str, list[str]],
    ucci: str,
    ply: int,
    side_move_number: int,
) -> None:
    side_memory = _side_memory(memory, side)
    current = set(shapes[side])
    _record_move_facts(side_memory, side, ucci, side_move_number)

    if side_move_number == 1 and not side_memory.choice_path:
        first_choice = FIRST_MOVE_MAP[side].get(ucci)
        if first_choice:
            choice_id, wing = first_choice
            _add_choice(side_memory, choice_id, ply, wing=wing, source="move")
            return

    # Preserve the historical 中炮 choice even when the cannon immediately
    # leaves the central square to form a 五六/五七/五八/五九炮.
    if (
        not side_memory.choice_path
        and ((side == "red" and ucci.startswith("e2") and ucci[2] in "dcba")
             or (side == "black" and ucci.startswith("e7") and ucci[2] in "fghi"))
    ):
        _add_choice(side_memory, "central_cannon", ply, source="move")
        side_memory.locks["central_square_choice"] = "central_cannon"
        return

    central_locked = side_memory.locks.get("central_square_choice")
    if "central_cannon" in current and not central_locked and _may_add(side, side_memory, "central_cannon"):
        origin_file = {
            "red": {"b2e2": "b", "h2e2": "h"},
            "black": {"b7e7": "b", "h7e7": "h"},
        }[side].get(ucci)
        _add_choice(
            side_memory,
            "central_cannon",
            ply,
            origin_file=origin_file,
            source="move" if origin_file else "fen",
        )
        side_memory.locks["central_square_choice"] = "central_cannon"
        return
    if "fly_elephant" in current and not central_locked and _may_add(side, side_memory, "fly_elephant"):
        _add_choice(side_memory, "fly_elephant", ply, source="fen")
        side_memory.locks["central_square_choice"] = "fly_elephant"
        return

    palcorner_wing = PALCORNER_MOVES[side].get(ucci)
    if palcorner_wing and _may_add(side, side_memory, "palcorner_cannon"):
        _add_choice(
            side_memory,
            "palcorner_cannon",
            ply,
            wing=palcorner_wing,
            source="move",
        )
        return

    cross_wing = CROSS_PALACE_MOVES[side].get(ucci)
    if cross_wing and not side_memory.choice_path:
        _add_choice(
            side_memory,
            "cross_palace_cannon",
            ply,
            wing=cross_wing,
            source="move",
        )
        return

    if side_move_number != 1 or side_memory.choice_path:
        return

    horse_wing = None
    if "proper_horse_left" in current:
        horse_wing = "left"
    elif "proper_horse_right" in current:
        horse_wing = "right"
    if horse_wing:
        _add_choice(
            side_memory,
            "proper_horse_opening",
            ply,
            wing=horse_wing,
            provisional=side == "black",
            source="fen",
        )
        return

    pawn_wing = None
    if "angle_pawn_left" in current:
        pawn_wing = "left"
    elif "angle_pawn_right" in current:
        pawn_wing = "right"
    if pawn_wing:
        _add_choice(
            side_memory,
            "angle_pawn",
            ply,
            wing=pawn_wing,
            source="fen",
        )


def _horse_attacks(board: dict[str, str], horse_square: str, target_square: str) -> bool:
    hf, hr = ord(horse_square[0]) - ord("a"), int(horse_square[1])
    tf, tr = ord(target_square[0]) - ord("a"), int(target_square[1])
    df, dr = tf - hf, tr - hr
    if (abs(df), abs(dr)) not in {(1, 2), (2, 1)}:
        return False
    if abs(df) == 2:
        leg = f"{chr(ord('a') + hf + (1 if df > 0 else -1))}{hr}"
    else:
        leg = f"{chr(ord('a') + hf)}{hr + (1 if dr > 0 else -1)}"
    return leg not in board


def _facing_rook_pairs(board: dict[str, str]) -> list[tuple[str, str]]:
    red_rooks = [square for square, piece in board.items() if piece == "R"]
    black_rooks = [square for square, piece in board.items() if piece == "r"]
    pairs: list[tuple[str, str]] = []
    for red_square in red_rooks:
        for black_square in black_rooks:
            if red_square[0] != black_square[0]:
                continue
            low, high = sorted((int(red_square[1]), int(black_square[1])))
            if all(f"{red_square[0]}{rank}" not in board for rank in range(low + 1, high)):
                pairs.append((red_square, black_square))
    return pairs


def _detect_flat_cannon_exchange(
    previous_fen: str | None,
    next_fen: str,
    side: str | None,
    ucci: str | None,
    side_memory: SideMemory,
) -> bool:
    if not previous_fen or side != "black" or not ucci:
        return False
    from_square, to_square = ucci[:2], ucci[2:]
    if ucci not in {"b7a7", "h7i7"}:
        return False
    before = parse_fen(previous_fen)
    after = parse_fen(next_fen)
    if before.get(from_square) != "c":
        return False
    if not any(fact.endswith("straight_rook_move") for fact in side_memory.facts):
        return False
    black_horses = [square for square, piece in after.items() if piece == "n"]
    for red_rook, black_rook in _facing_rook_pairs(after):
        # Before the cannon leaves the file it must lie on the same line and
        # between this exact facing rook pair.
        if from_square[0] != red_rook[0]:
            continue
        low, high = sorted((int(red_rook[1]), int(black_rook[1])))
        if not low < int(from_square[1]) < high:
            continue
        # Under this project's naming convention a black 直車 is an original
        # rook that shifted along Black's home rank.
        if black_rook[1] != "9" or black_rook[0] in {"a", "i"}:
            continue
        if any(_horse_attacks(after, horse, black_rook) for horse in black_horses):
            return True
    return False


def _river_stage_for_destination(side: str, square: str) -> str | None:
    if side == "red":
        return {"4": "river_rook", "5": "riding_river_rook", "6": "cross_river_rook"}.get(square[1])
    return {"5": "river_rook", "4": "riding_river_rook", "3": "cross_river_rook"}.get(square[1])


def _promote_shapes(
    memory: OpeningMemory,
    previous_fen: str | None,
    next_fen: str,
    shapes: dict[str, list[str]],
    ply: int,
    moving_side: str | None,
    ucci: str | None,
) -> None:
    """Promote position/move evidence into first-formed, persistent shapes."""
    for side in ("red", "black"):
        if moving_side not in {None, side}:
            continue
        side_memory = _side_memory(memory, side)
        current = set(shapes[side])
        facts = set(side_memory.facts)
        is_five_cannon_allowed = _has_choice(side_memory, "central_cannon")
        for shape_id in FIVE_CANNON_IDS:
            is_position_safe = True
            if ((is_five_cannon_allowed and (ucci is None or is_position_safe)) and shape_id in current) or f"{shape_id}_move" in facts:
                _add_shape(side_memory, shape_id, ply, source="move" if f"{shape_id}_move" in facts else "fen", lock_group="cannon_formation")
        if "seven_route_horse" in current and not {
            "proper_horse_left",
            "proper_horse_right",
        }.issubset(current):
            _add_shape(side_memory, "seven_route_horse", ply)
        if "edge_horse_left" in current:
            _add_shape(side_memory, "edge_horse_left", ply, wing="left")
        if "edge_horse_right" in current:
            _add_shape(side_memory, "edge_horse_right", ply, wing="right")
        if "double_proper_horses" in current:
            _add_shape(side_memory, "double_proper_horses", ply)
        for shape_id in (
            "advance_three_pawn",
            "advance_seven_pawn",
            "advance_three_soldier",
            "advance_seven_soldier",
        ):
            if shape_id in current:
                _add_shape(side_memory, shape_id, ply)
        if "two_headed_snake" in current:
            _add_shape(side_memory, "two_headed_snake", ply)
        if "left_elephant_move" in facts:
            _add_shape(side_memory, "fly_left_elephant", ply, source="move")
        if "right_elephant_move" in facts:
            _add_shape(side_memory, "fly_right_elephant", ply, source="move")
        if {"left_river_cannon_move", "right_river_cannon_move"}.intersection(facts):
            _add_shape(
                side_memory,
                "river_cannon",
                ply,
                source="move",
                lock_group="cannon_formation",
            )

        if ucci and moving_side == side and previous_fen:
            before = parse_fen(previous_fen)
            after = parse_fen(next_fen)
            from_square, to_square = ucci[:2], ucci[2:]
            rook_piece = "R" if side == "red" else "r"
            if before.get(from_square) == rook_piece and after.get(to_square) == rook_piece:
                stage = _river_stage_for_destination(side, to_square)
                if stage:
                    _add_shape(side_memory, stage, ply, source="move", lock_group="rook_river_stage")
        elif not ucci:
            for shape_id, current_id in (
                ("river_rook", "river_rook_shape"),
                ("riding_river_rook", "riding_river_rook_shape"),
                ("cross_river_rook", "cross_river_rook_shape"),
            ):
                if current_id in current:
                    _add_shape(side_memory, shape_id, ply, source="fen", lock_group="rook_river_stage")
                    break

        if _detect_flat_cannon_exchange(previous_fen, next_fen, side, ucci, side_memory):
            _add_shape(side_memory, "flat_cannon_exchange", ply, source="move")
        if {"left_horizontal_rook_move", "right_horizontal_rook_move"}.issubset(facts):
            _add_shape(side_memory, "double_horizontal_rooks", ply, source="move")
        elif "left_horizontal_rook_move" in facts:
            _add_shape(side_memory, "horizontal_rook", ply, wing="left", source="move")
        elif "right_horizontal_rook_move" in facts:
            _add_shape(side_memory, "horizontal_rook", ply, wing="right", source="move")
        elif "horizontal_rook_left" in current:
            _add_shape(side_memory, "horizontal_rook", ply, wing="left", source="fen")
        elif "horizontal_rook_right" in current:
            _add_shape(side_memory, "horizontal_rook", ply, wing="right", source="fen")
        if "left_straight_rook_move" in facts:
            _add_shape(side_memory, "straight_rook", ply, wing="left", source="move")
        if "right_straight_rook_move" in facts:
            _add_shape(side_memory, "straight_rook", ply, wing="right", source="move")

    # 緩開車 is a historical timing fact rather than a current-board shape.
    # It may be promoted after the third move if the red central-cannon system
    # becomes known later.
    if _has_choice(memory.red, "central_cannon"):
        for side in ("red", "black"):
            side_memory = _side_memory(memory, side)
            if "third_move_without_rook" in side_memory.facts:
                has_moved_rook = any(s.id == "straight_rook" for s in side_memory.formed_shapes)
                if has_moved_rook:
                    _add_shape(side_memory, "slow_rook", ply, source="memory")


def _promote_composites(
    memory: OpeningMemory,
    fen: str,
    shapes: dict[str, list[str]],
    ply: int,
    moving_side: str | None,
) -> None:
    board = parse_fen(fen)
    black = memory.black
    black_shapes = set(shapes["black"])
    black_choices = set(_choice_ids(black))
    may_promote_black = moving_side in {None, "black"}

    if may_promote_black and "defensive_system" not in black.locks:
        if (
            "reverse_palace_horse_shape" in black_shapes
            and "palcorner_cannon" in black_choices
            and "central_cannon" not in black_choices
            and "cross_palace_cannon" not in black_choices
        ):
            _add_composite(black, "reverse_palace_horse", ply)
        elif (
            "screen_horse_shape" in black_shapes
            and not black_choices.intersection(
                {"central_cannon", "palcorner_cannon", "cross_palace_cannon"}
            )
        ):
            _add_composite(black, "screen_horse", ply)
        else:
            proper_count = int("proper_horse_left" in black_shapes) + int(
                "proper_horse_right" in black_shapes
            )
            edge_horse = board.get("a7") == "n" or board.get("i7") == "n"
            if (
                proper_count == 1
                and edge_horse
                and not black_choices.intersection(
                    {"central_cannon", "palcorner_cannon", "cross_palace_cannon"}
                )
            ):
                _add_composite(black, "single_horse", ply)

    if may_promote_black and not black.choice_path:
        if "pawn_bottom_cannon_shape" in black_shapes and _has_choice(memory.red, "angle_pawn"):
            _add_choice(black, "pawn_bottom_cannon", ply, source="fen")

    for side in ("red", "black"):
        if moving_side not in {None, side}:
            continue
        side_memory = _side_memory(memory, side)
        facts = set(side_memory.facts)
        if "defensive_system" in side_memory.locks:
            continue
        if {"left_proper_horse_move", "left_rook_shift", "left_cannon_edge"}.issubset(facts):
            _add_composite(side_memory, "left_three_step_tiger", ply)
        elif {
            "right_proper_horse_move",
            "right_rook_shift",
            "right_cannon_edge",
        }.issubset(facts):
            _add_composite(side_memory, "right_three_step_tiger", ply)
        elif side == "black" and {
            "left_proper_horse_move",
            "left_rook_shift",
            "left_cannon_blockade_move",
        }.issubset(facts):
            _add_composite(side_memory, "left_cannon_blockade", ply)


def _winged_name(choice: ChoiceOccurrence, side: str) -> str:
    base = CHOICE_NAMES[side].get(choice.id, choice.id)
    if choice.id == "proper_horse_opening" and side == "black" and choice.wing:
        return f"起{'左' if choice.wing == 'left' else '右'}馬"
    return base


def _side_label(side: str, side_memory: SideMemory) -> tuple[str | None, str | None]:
    if side_memory.composite_systems:
        system = side_memory.composite_systems[-1].id
        return system, COMPOSITE_NAMES.get(system, system)

    five_shape = next(
        (
            item
            for item in reversed(side_memory.formed_shapes)
            if item.id in FIVE_CANNON_IDS and item.eligible_for_name
        ),
        None,
    )
    if five_shape:
        shape_name = SHAPE_NAMES[five_shape.id]
        if side_memory.choice_path and side_memory.choice_path[0].id != "central_cannon":
            first = side_memory.choice_path[0]
            return five_shape.id, f"{_winged_name(first, side)}\u8f49{shape_name}"
        return five_shape.id, shape_name

    if not side_memory.choice_path:
        return None, None

    path = side_memory.choice_path
    if len(path) >= 2:
        first, latest = path[0], path[-1]
        first_name = _winged_name(first, side)
        latest_name = _winged_name(latest, side)
        return latest.id, f"{first_name}轉{latest_name}"
    latest = path[-1]
    return latest.id, _winged_name(latest, side)


PAWN_MODIFIERS = {
    "advance_three_pawn",
    "advance_seven_pawn",
    "advance_three_soldier",
    "advance_seven_soldier",
}
HORSE_MODIFIERS = {
    "double_proper_horses",
    "seven_route_horse",
    "edge_horse_left",
    "edge_horse_right",
}


def _eligible_shape_ids(side_memory: SideMemory) -> list[str]:
    result: list[str] = []
    for item in side_memory.formed_shapes:
        if item.eligible_for_name and item.id not in result:
            result.append(item.id)
    return result


def _collect_modifiers(
    side: str,
    memory: OpeningMemory,
    main_id: str | None,
) -> list[str]:
    side_memory = _side_memory(memory, side)
    ids = set(_eligible_shape_ids(side_memory))
    ids.difference_update(FIVE_CANNON_IDS)
    if main_id:
        ids.discard(main_id)
        if main_id == "edge_horse_opening":
            ids.difference_update({"edge_horse_left", "edge_horse_right"})
        elif main_id == "river_cannon_opening":
            ids.discard("river_cannon")
        elif main_id == "edge_pawn_opening":
            ids.difference_update(PAWN_MODIFIERS)
        elif main_id == "fly_elephant":
            ids.discard("fly_left_elephant")
            ids.discard("fly_right_elephant")

    if not _has_choice(memory.red, "central_cannon"):
        ids.difference_update(PAWN_MODIFIERS)

    if "two_headed_snake" in ids:
        ids.difference_update(PAWN_MODIFIERS)

    black_horse_composite = side == "black" and any(
        item.id in {"screen_horse", "reverse_palace_horse", "single_horse"}
        for item in side_memory.composite_systems
    )
    if black_horse_composite:
        ids.difference_update(HORSE_MODIFIERS)
    elif "double_proper_horses" in ids:
        ids.difference_update({"seven_route_horse", "edge_horse_left", "edge_horse_right"})
    elif "seven_route_horse" in ids:
        ids.difference_update({"edge_horse_left", "edge_horse_right"})
    elif "edge_horse_left" in ids and "edge_horse_right" in ids:
        ids.discard("edge_horse_right")

    opening_horse = next(
        (item for item in side_memory.choice_path if item.id == "proper_horse_opening"),
        None,
    )
    if opening_horse and opening_horse.wing == "left":
        ids.discard("seven_route_horse")

    if "double_horizontal_rooks" in ids:
        ids.discard("horizontal_rook")

    # 緩開車 records that both original rooks were still unmoved at the
    # side's third move.  A later rook move can still leave historical
    # straight_rook/horizontal_rook shapes in memory, but those labels are
    # mutually exclusive with the opening's 緩開車 name.
    if "slow_rook" in ids:
        ids.difference_update({"straight_rook", "horizontal_rook"})

    side_pawns = (
        ["advance_three_pawn", "advance_seven_pawn"]
        if side == "red"
        else ["advance_three_soldier", "advance_seven_soldier"]
    )
    order = [
        "river_cannon",
        "double_proper_horses",
        "seven_route_horse",
        "edge_horse_left",
        "edge_horse_right",
        *side_pawns,
        "double_horizontal_rooks",
        "horizontal_rook",
        "straight_rook",
        "slow_rook",
        "river_rook",
        "riding_river_rook",
        "cross_river_rook",
        "flat_cannon_exchange",
        "two_headed_snake",
        "fly_left_elephant",
        "fly_right_elephant",
    ]
    return [shape_id for shape_id in order if shape_id in ids]


def _modifier_text(modifier_ids: list[str]) -> str:
    labels: list[str] = []
    for modifier_id in modifier_ids:
        label = SHAPE_NAMES[modifier_id]
        if label not in labels:
            labels.append(label)
    return "".join(labels)


def _compose_side(
    side: str,
    main_id: str | None,
    main_label: str | None,
    modifiers: list[str],
) -> str | None:
    modifier_text = _modifier_text(modifiers)
    if not main_label:
        return f"{'紅' if side == 'red' else '黑'}方{modifier_text}" if modifier_text else None
    if side == "black" and main_id == "angle_pawn":
        pawn_ids = [item for item in modifiers if item in PAWN_MODIFIERS]
        if pawn_ids:
            remaining = [item for item in modifiers if item not in PAWN_MODIFIERS]
            return _modifier_text(pawn_ids + remaining)
    return main_label + modifier_text


def _central_choice(side_memory: SideMemory) -> ChoiceOccurrence | None:
    return next((item for item in side_memory.choice_path if item.id == "central_cannon"), None)


def _cannon_matchup(memory: OpeningMemory, shapes: dict[str, list[str]]) -> str | None:
    red = _central_choice(memory.red)
    black = _central_choice(memory.black)
    if not red or not black:
        return None
    if red.origin_file and black.origin_file:
        return "same_side_cannons" if red.origin_file == black.origin_file else "opposite_side_cannons"

    red_shapes = set(shapes["red"])
    black_shapes = set(shapes["black"])
    same_origin = (
        "central_cannon_from_h_file" in red_shapes
        and "central_cannon_from_h_file" in black_shapes
    ) or (
        "central_cannon_from_b_file" in red_shapes
        and "central_cannon_from_b_file" in black_shapes
    )
    opposite_origin = (
        "central_cannon_from_h_file" in red_shapes
        and "central_cannon_from_b_file" in black_shapes
    ) or (
        "central_cannon_from_b_file" in red_shapes
        and "central_cannon_from_h_file" in black_shapes
    )
    if same_origin:
        return "same_side_cannons"
    if opposite_origin:
        return "opposite_side_cannons"
    if memory.base_matchup_id in {"same_side_cannons", "opposite_side_cannons"}:
        return memory.base_matchup_id
    return None


def _lookup_c20_c49(memory: OpeningMemory) -> tuple[str, str] | None:
    if not memory.fen:
        return None
    board_part = memory.fen.split(' ')[0]
    ranks = board_part.split('/')
    mirrored_board_part = '/'.join(rank[::-1] for rank in ranks)

    mapping = {
        "r1bakabr1/9/1cn3nc1/p3p2Rp/2p3p2/9/P1P1P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake",
            "中炮过河车七路马(其他)对屏风马两头蛇"
        ),
        "r1bakabr1/9/1cn3nc1/p3p2Rp/2p3p2/9/P1P1P1P1P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake",
            "中炮过河车七路马对屏风马两头蛇——红左横车(对黑其他)"
        ),
        # Move 12 of C22
        "r1bakabr1/9/2n3nc1/pc2p2Rp/2p3p2/9/P1P1P1P1P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake_high_cannon",
            "中炮过河车七路马对屏风马两头蛇——红左横车(其他)对黑高右炮"
        ),
        # Move 13 of C22
        "r1bakabr1/9/2n3nc1/pc2p3p/2p3p2/7R1/P1P1P1P1P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake_high_cannon",
            "中炮过河车七路马对屏风马两头蛇——红左横车(其他)对黑高右炮"
        ),
        # Move 14 of C22
        "r2akabr1/9/2n1b1nc1/pc2p3p/2p3p2/7R1/P1P1P1P1P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake_high_cannon",
            "中炮过河车七路马对屏风马两头蛇——红左横车(其他)对黑高右炮"
        ),
        "r2akabr1/9/2n1b1nc1/pc2p3p/2p3p2/6PR1/P1P1P3P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_with_3rd_pawn_exchange_vs_screen_horse_double_headed_snake_high_cannon",
            "中炮过河车七路马对屏风马两头蛇——红左横车兑三兵对黑高右炮"
        ),
        "r2akabr1/9/2n1b1nc1/pc2p3p/2p3p2/2P4R1/P3P1P1P/1CN1C1N2/R8/2BAKAB2": (
            "central_cannon_pawn_ranked_chariot_left_ranked_chariot_7th_file_horse_with_7th_pawn_exchange_vs_screen_horse_double_headed_snake_high_cannon",
            "中炮过河车七路马对屏风马两头蛇——红左横车兑七兵对黑高右炮"
        ),
        "r1bakabr1/9/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement",
            "中炮过河车互进七兵对屏风马(其他)"
        ),
        "r1bak1br1/4a4/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_early_advisor",
            "中炮过河车互进七兵对屏风馬上士"
        ),
        "r1b1kabr1/4a4/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_early_advisor",
            "中炮过河车互进七兵对屏风馬上士"
        ),
        "r1baka1r1/9/1cn1b1nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_early_elephant",
            "中炮过河车互进七兵对屏风马飞象"
        ),
        "r2akabr1/9/1cn1b1nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_early_elephant",
            "中炮过河车互进七兵对屏风马飞象"
        ),
        "2bakabr1/r8/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_right_ranked_chariot",
            "中炮过河车互进七兵对屏风马右横车"
        ),
        "r1bakabr1/9/2n3nc1/p1p1p2Rp/6p2/2P6/Pc2P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_right_pawn_ranked_cannon",
            "中炮过河车互进七兵对屏风马右炮过河"
        ),
        "r1bakabr1/9/1cn4c1/p1p1p2Rp/5np2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse",
            "中炮过河车互进七兵(其他)对屏风马left马盘河" # Use Chinese translation exactly: 中炮过河车互进七兵(其他)对屏风马左马盘河
        ),
        "r1bakabr1/9/1cn4c1/p1p1p2Rp/5np2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse",
            "中炮过河车互进七兵对屏风马左马盘河——红七路马(对黑其他)"
        ),
        "r2akabr1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红七路马(其他)对黑飞右象"
        ),
        "r1baka1r1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红七路马(其他)对黑飞右象"
        ),
        "r2akabr1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/PC2P1P1P/2N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_with_high_left_cannon_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红七路马高左炮对黑飞右象"
        ),
        "r1baka1r1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/PC2P1P1P/2N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_with_high_left_cannon_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红七路马高左炮对黑飞右象"
        ),
        "r2akabr1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/P3P1P1P/C1N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_with_side_left_cannon_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红边炮对黑飞右象"
        ),
        "r1baka1r1/9/1cn1b2c1/p1p1p2Rp/5np2/2P6/P3P1P1P/C1N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_with_side_left_cannon_vs_screen_horse_7th_pawn_advancement_left_riverbank_horse_right_central_elephant",
            "中炮过河车互进七兵对屏风马左马盘河——红边炮对黑飞右象"
        ),
        "r1bakabr1/9/1cn3n1c/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车(其他)"
        ),
        "r1bakabr1/9/c1n3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车(其他)"
        ),
        "r1bakabr1/8c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_side_cannon_retreating",
            "中炮过河车互进七兵对屏风马平炮兑车——(红其他对)黑退边炮"
        ),
        "r1bakabr1/c8/2n3nc1/p1p1p1R1p/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_side_cannon_retreating",
            "中炮过河车互进七兵对屏风马平炮兑车——(红其他对)黑退边炮"
        ),
        "r1bakabr1/8c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_side_cannon_retreating",
            "中炮过河车互进七兵对屏风马平炮兑车——红七路马对黑退边炮(其他)"
        ),
        "r1bakabr1/c8/2n3nc1/p1p1p1R1p/6p2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_side_cannon_retreating",
            "中炮过河车互进七兵对屏风马平炮兑车——红七路马对黑退边炮(其他)"
        ),
        "r1b1kabr1/4a3c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/1CN1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_7th_filed_horse_edge_cannon_for_chariot_exchange_right_advisor",
            "中炮过河车互进七兵对屏风马平炮兑车——红七路马(其他)对黑退边炮上右士"
        ),
        "r1b1kabr1/4a3c/1cn3n2/p1p1p1R1p/6p2/2PN5/P3P1P1P/1C2C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_riverbank_horse_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor",
            "中炮过河车互进七兵对屏风马平炮兑车——红left马盘河对黑退边炮上右士" # Use standard name: 中炮过河车互进七兵对屏风马平炮兑车——红左马盘河对黑退边炮上右士
        ),
        "r1b1kabr1/4a3c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/C3C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士(其他)"
        ),
        "1rb1kabr1/4a3c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/C3C1N2/R8/1NBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor_right_filed_chariot",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士右直车"
        ),
        "1rb1kabr1/2c1a4/2n3nc1/p1p1pR2p/6p2/2P6/P3P1P1P/C1N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor_right_filed_chariot",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士右直车"
        ),
        "1rb1kabr1/4a1c2/1cn3n2/p1p1pR2p/6p2/2P6/P3P1P1P/C1N1C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor_right_filed_chariot",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士右直车"
        ),
        "r1b1kabr1/4a3c/2n3n2/pcp1p1R1p/6p2/2P6/P3P1P1P/C3C1N2/R8/1NBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange_right_advisor_right_filed_chariot",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士右直车"
        ),
        "r1bakabr1/8c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/NC2C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_horse_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红左边马对黑退边炮"
        ),
        "r1bakabr1/c8/2n3nc1/p1p1p1R1p/6p2/2P6/P3P1P1P/NC2C1N2/9/R1BAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_side_horse_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红left边马对黑退边炮".replace("left", "左")
        ),
        "r1bakabr1/8c/1cn3n2/p1p1p1R1p/6p2/2P6/P3P1P1P/3CC1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_palcorner_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红仕角炮对黑退边炮"
        ),
        "r1bakabr1/c8/2n3nc1/p1p1p1R1p/6p2/2P6/P3P1P1P/3CC1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_pawn_advancement_left_palcorner_cannon_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红仕角炮对黑退边炮"
        ),
        "r1bakabr1/8c/1cn3n2/p1p1p1R1p/6p2/2P1P4/P5P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_and_5th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红进中兵对黑退边炮"
        ),
        "r1bakabr1/c8/2n3nc1/p1p1p1R1p/6p2/2P1P4/P5P1P/1C2C1N2/9/RNBAKAB2": (
            "central_cannon_pawn_ranked_chariot_with_7th_and_5th_pawn_advancement_vs_screen_horse_7th_pawn_advancement_edge_cannon_for_chariot_exchange",
            "中炮过河车互进七兵对屏风马平炮兑车——红进中兵对黑退边炮"
        ),
        "1rbakabr1/9/1cn3nc1/p1p1p3p/6p2/9/P1P1P1P1P/N2CC1N2/9/1RBAKABR1": (
            "five_six_cannon_left_side_horse_vs_screen_horse_7th_pawn_right_straight_chariot",
            "五六炮左边马对屏风马——黑进７卒右直车(其他)"
        ),
        "1rbakabr1/9/2n3nc1/p1p1p3p/6p2/9/PcP1P1P1P/N2CC1N2/9/1RBAKABR1": (
            "five_six_cannon_left_side_horse_vs_screen_horse_7th_pawn_right_straight_chariot_right_ranked_cannon",
            "五六炮左边马对屏风马——黑进７卒右直车右炮过河"
        ),
        "1rbakabr1/9/1cn3nc1/p1p1p2Rp/6p2/9/P1P1P1P1P/3CC1N2/9/RNBAKAB2": (
            "five_six_cannon_cross_river_chariot_vs_screen_horse_7th_pawn_right_straight_chariot",
            "五六炮过河车对屏风马——黑进７卒右直车"
        ),
        "r1bakabr1/9/1cn3nc1/p3p2Rp/2p3p2/9/P1P1P1P1P/3CC1N2/9/RNBAKAB2": (
            "five_six_cannon_cross_river_chariot_vs_screen_horse_two_headed_snake",
            "五六炮过河车对屏风马——黑两头蛇"
        ),
        "r1bakabr1/9/1cn3nc1/p1p1p3p/6p2/9/P1P1P1P1P/N1C1C1N2/9/R1BAKABR1": (
            "57_cannons_others_vs_screen_horse_defense_with_7th_pawn_advancement",
            "五七炮对屏风马进７卒(其他)"
        ),
        "1rbakab1r/9/1cn3nc1/p3p1p1p/2p6/9/P1P1P1P1P/2N1C1C1N/9/1RBAKAB1R": (
            "57_cannons_others_vs_screen_horse_defense_with_7th_pawn_advancement",
            "五七炮对屏风马进７卒(其他)"
        ),
        "1rbakabr1/9/1cn3nc1/p1p1p3p/6p2/9/P1P1P1P1P/N1C1C1N2/9/R1BAKABR1": (
            "57_cannons_others_vs_screen_horse_defense_with_7th_pawn_advancement_and_right_filed_chariot",
            "五七炮对屏风马进７卒——(红其他对)黑右直车"
        ),
        "1rbakabr1/9/1cn3nc1/p3p1p1p/2p6/9/P1P1P1P1P/2N1C1C1N/9/1RBAKAB1R": (
            "57_cannons_others_vs_screen_horse_defense_with_7th_pawn_advancement_and_right_filed_chariot",
            "五七炮对屏风马进７卒——(红其他对)黑右直车"
        ),
        "1rbakabr1/9/1cn3nc1/p1p1p3p/6p2/9/P1P1P1P1P/N1C1C1N2/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_and_right_filed_chariot",
            "五七炮对屏风马进７卒——红左直车对黑右直车(其他)"
        ),
        "1rbakabr1/9/1cn3nc1/p3p1p1p/2p6/9/P1P1P1P1P/2N1C1C1N/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_and_right_filed_chariot",
            "五七炮对屏风马进７卒——红左直车对黑右直车(其他)"
        ),
        "1rbakabr1/9/1cn3n2/p1p1p3p/6p2/9/P1P1P1PcP/N1C1C1N2/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_left_pawn_ranked_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车左炮过河"
        ),
        "1rbakabr1/9/2n3nc1/p3p1p1p/2p6/9/PcP1P1P1P/2N1C1C1N/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_left_pawn_ranked_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车左炮过河"
        ),
        "1rbakabr1/9/2n3nc1/p1p1p3p/1c4p2/9/P1P1P1P1P/N1C1C1N2/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_right_riverbank_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车右炮巡河"
        ),
        "1rbakabr1/9/1cn3n2/p3p1p1p/2p4c1/9/P1P1P1P1P/2N1C1C1N/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_right_riverbank_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车右炮巡河"
        ),
        "1rbakabr1/9/2n3nc1/p1p1p3p/6p2/9/PcP1P1P1P/N1C1C1N2/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_right_pawn_ranked_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车右炮过河"
        ),
        "1rbakabr1/9/1cn3n2/p3p1p1p/2p6/9/P1P1P1PcP/2N1C1C1N/9/1RBAKABR1": (
            "57_cannons_left_filed_chariot_vs_screen_horse_defense_with_7th_pawn_advancement_right_filed_chariot_and_right_pawn_ranked_cannon",
            "五七炮对屏风马进７卒——红左直车对黑右直车右炮过河"
        ),
        "r1bakabr1/9/2n3nc1/p1p1p3p/1c4p2/9/P1P1P1P1P/N1C1C1N2/9/R1BAKABR1": (
            "57_cannons_vs_screen_horse_defense_with_7th_pawn_advancement_right_river_bank_cannon",
            "五七炮对屏风马进７卒——黑右炮巡河"
        ),
        "1rbakab1r/9/1cn3n2/p3p1p1p/2p4c1/9/P1P1P1P1P/2N1C1C1N/9/1RBAKAB1R": (
            "57_cannons_vs_screen_horse_defense_with_7th_pawn_advancement_right_river_bank_cannon",
            "五七炮对屏风马进７卒——黑右炮巡河"
        ),
        "r1bakabr1/9/1c4nc1/4p1p1p/pnp6/6P2/P1P1P3P/N1C1C1N2/9/R1BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_side_pawn_exchange_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑兑边卒"
        ),
        "1rbakab1r/9/1cn4c1/p1p1p4/6pnp/2P6/P3P1P1P/2N1C1C1N/9/1RBAKAB1R": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_side_pawn_exchange_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑兑边卒"
        ),
        "r1bakabr1/9/1cn4c1/p1p1p3p/6pn1/1CPN5/P3P1P1P/4C1N2/9/R1BAKAB1R": (
            "central_cannon_with_riverbank_cannon_left_riverbank_horse_others_vs_screen_horse_defense_with_left_riverbank_horse_variation",
            "中炮巡河炮对屏风马——红左马盘河(其他)对黑左马外盘河"
        ),
        "1rbakab1r/9/1c4nc1/p3p1p1p/1np6/5NPC1/P1P1P3P/2N1C4/9/R1BAKAB1R": (
            "central_cannon_with_riverbank_cannon_left_riverbank_horse_others_vs_screen_horse_defense_with_left_riverbank_horse_variation",
            "中炮巡河炮对屏风马——红左马盘河(其他)对黑左马外盘河"
        ),
        "rnbakabnr/9/1c2c4/p1p1p1p1p/9/9/P1P1P1P1P/1C2C4/9/RNBAKABNR": (
            "same_direction_cannons_deferred_chariot_vs_others",
            "顺炮缓开车对其他"
        ),
        "rnbakabnr/9/4c2c1/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/9/RNBAKABNR": (
            "same_direction_cannons_deferred_chariot_vs_others",
            "顺炮缓开车对其他"
        ),
        "rnbakabnr/9/1c2c4/p1p1p1p1p/9/9/P1P1P1P1P/1C2C4/8R/RNBAKABN1": (
            "same_direction_cannons_ranked_vs_deferred_chariot_including_sdc_rr_vs_rr",
            "顺炮横车对缓开车(包括顺炮顺横车)"
        ),
        "rnbakabnr/9/4c2c1/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/R8/1NBAKABNR": (
            "same_direction_cannons_ranked_vs_deferred_chariot_including_sdc_rr_vs_rr",
            "顺炮横车对缓开车(包括顺炮顺横车)"
        ),
        "rnbakab1r/9/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/8R/RNBAKAB2": (
            "same_direction_cannons_ranked_vs_deferred_chariot_including_sdc_rr_vs_rr",
            "顺炮横车对缓开车(包括顺炮顺横车)"
        ),
        "r1bakabnr/9/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2C1/R8/2BAKABNR": (
            "same_direction_cannons_ranked_vs_deferred_chariot_including_sdc_rr_vs_rr",
            "顺炮横车对缓开车(包括顺炮顺横车)"
        ),
        "rnbakabr1/9/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/8R/RNBAKAB2": (
            "same_direction_cannons_ranked_chariot_vs_filed_chariot_others",
            "顺炮横车对直车(其他)"
        ),
        "1rbakabnr/9/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2C1/R8/2BAKABNR": (
            "same_direction_cannons_ranked_chariot_vs_filed_chariot_others",
            "顺炮横车对直车(其他)"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/9/RNBAKABR1": (
            "same_direction_cannons_filed_chariot_others_vs_ranked_chariot",
            "顺炮直车(其他)对横车"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2C1/9/1RBAKABNR": (
            "same_direction_cannons_filed_chariot_others_vs_ranked_chariot",
            "顺炮直车(其他)对横车"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/4A4/RNB1KABR1": (
            "same_direction_cannons_filed_chariot_with_early_advisor_vs_ranked_chariot",
            "顺炮直车对横车——红先上仕"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2C1/4A4/1RBAK1BNR": (
            "same_direction_cannons_filed_chariot_with_early_advisor_vs_ranked_chariot",
            "顺炮直车对横车——红先上仕"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/4A4/RNBAK1BR1": (
            "same_direction_cannons_filed_chariot_with_early_advisor_vs_ranked_chariot",
            "顺炮直车对横车——红先上仕"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2C1/4A4/1RB1KABNR": (
            "same_direction_cannons_filed_chariot_with_early_advisor_vs_ranked_chariot",
            "顺炮直车对横车——红先上仕"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/NC2C1N2/9/R1BAKABR1": (
            "same_direction_cannons_filed_chariot_with_left_side_horse_vs_ranked_chariot",
            "顺炮直车对横车——红左边马"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1C2CN/9/1RBAKAB1R": (
            "same_direction_cannons_filed_chariot_with_left_side_horse_vs_ranked_chariot",
            "顺炮直车对横车——红左边马"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/7R1/P1P1P1P1P/1C2C1N2/9/RNBAKAB2": (
            "same_direction_cannons_filed_chariot_with_riverbank_chariot_vs_ranked_chariot",
            "顺炮直车对横车——红巡河车"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/1R7/P1P1P1P1P/2N1C2C1/9/2BAKABNR": (
            "same_direction_cannons_filed_chariot_with_riverbank_chariot_vs_ranked_chariot",
            "顺炮直车对横车——红巡河车"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1pRp/9/9/P1P1P1P1P/1C2C1N2/9/RNBAKAB2": (
            "same_direction_cannons_filed_chariot_with_pawn_ranked_chariot_vs_ranked_chariot",
            "顺炮直车对横车——红过河车"
        ),
        "2bakabnr/r8/2n1c2c1/pRp1p1p1p/9/9/P1P1P1P1P/2N1C2C1/9/2BAKABNR": (
            "same_direction_cannons_filed_chariot_with_pawn_ranked_chariot_vs_ranked_chariot",
            "顺炮直车对横车——红过河车"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/9/P1P1P1P1P/3CC1N2/9/RNBAKABR1": (
            "same_direction_cannons_filed_chariot_with_palcorner_cannon_vs_ranked_chariot",
            "顺炮直车对横车——红仕角炮"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/9/P1P1P1P1P/2N1CC3/9/1RBAKABNR": (
            "same_direction_cannons_filed_chariot_with_palcorner_cannon_vs_ranked_chariot",
            "顺炮直车对横车——红仕角炮"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/6P2/P1P1P3P/1C2C1N2/9/RNBAKABR1": (
            "same_direction_cannons_filed_chariot_with_3rd_pawn_advancement_vs_ranked_chariot_excluding_doubleheaded_snake_pawn_formation",
            "顺炮直车对横车——红进三兵(不包括两头蛇)"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/2P6/P3P1P1P/2N1C2C1/9/1RBAKABNR": (
            "same_direction_cannons_filed_chariot_with_3rd_pawn_advancement_vs_ranked_chariot_excluding_doubleheaded_snake_pawn_formation",
            "顺炮直车对横车——红进三兵(不包括两头蛇)"
        ),
        "rnbakab2/8r/1c2c1n2/p1p1p1p1p/9/2P6/P3P1P1P/1C2C1N2/9/RNBAKABR1": (
            "same_direction_cannons_filed_chariot_with_7th_pawn_advancement_vs_ranked_chariot_excluding_doubleheaded_snake_pawn_formation",
            "顺炮直车对横车——红进七兵(不包括两头蛇)"
        ),
        "2bakabnr/r8/2n1c2c1/p1p1p1p1p/9/6P2/P1P1P3P/2N1C2C1/9/1RBAKABNR": (
            "same_direction_cannons_filed_chariot_with_7th_pawn_advancement_vs_ranked_chariot_excluding_doubleheaded_snake_pawn_formation",
            "顺炮直车对横车——红进七兵(不包括两头蛇)"
        ),
        "rnbakabr1/9/4c1n2/p1p1p1p1p/9/6P2/P1P1P2cP/1C2C1N2/9/RNBAKABR1": (
            "central_cannon_with_3rd_pawn_advancement_others_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵(其他)对左炮封车转列炮"
        ),
        "1rbakabnr/9/2n1c4/p1p1p1p1p/9/2P6/Pc2P1P1P/2N1C2C1/9/1RBAKABNR": (
            "central_cannon_with_3rd_pawn_advancement_others_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵(其他)对左炮封车转列炮"
        ),
        "rnbakabr1/9/4c1n2/p1p1p1p1p/9/5NP2/P1P1P2cP/1C2C4/9/RNBAKABR1": (
            "central_cannon_with_3rd_pawn_advancement_right_riverbank_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红右马盘河"
        ),
        "1rbakabnr/9/2n1c4/p1p1p1p1p/9/2PN5/Pc2P1P1P/4C2C1/9/1RBAKABNR": (
            "central_cannon_with_3rd_pawn_advancement_right_riverbank_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红右马盘河"
        ),
        "rnbakabr1/9/4c1n2/p1p1p1p1p/9/6P2/P1P1P2cP/1CN1C1N2/9/R1BAKABR1": (
            "central_cannon_with_3rd_pawn_advancement_7th_file_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红七路马"
        ),
        "1rbakabnr/9/2n1c4/p1p1p1p1p/9/2P6/Pc2P1P1P/2N1C1NC1/9/1RBAKAB1R": (
            "central_cannon_with_3rd_pawn_advancement_7th_file_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红七路马"
        ),
        "rnbakabr1/9/4c1n2/p1p1p1p1p/9/6P2/P1P1P2cP/NC2C1N2/9/R1BAKABR1": (
            "central_cannon_with_3rd_pawn_advancement_lt_side_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红左边马"
        ),
        "1rbakabnr/9/2n1c4/p1p1p1p1p/9/2P6/Pc2P1P1P/2N1C2CN/9/1RBAKAB1R": (
            "central_cannon_with_3rd_pawn_advancement_lt_side_horse_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红左边马"
        ),
        "rnbakabr1/9/1C2c1n2/p1p1p1p1p/9/6P2/P1P1P2cP/4C1N2/9/RNBAKABR1": (
            "central_cannon_with_3rd_pawn_advancement_cannon_attacking_horse_variation_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红进炮打马"
        ),
        "1rbakabnr/9/2n1c2C1/p1p1p1p1p/9/2P6/Pc2P1P1P/2N1C4/9/1RBAKABNR": (
            "central_cannon_with_3rd_pawn_advancement_cannon_attacking_horse_variation_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红进炮打马"
        ),
        "rnbakabr1/9/4c1n2/p1p1p1p1p/9/2P3P2/P3P2cP/1C2C1N2/9/RNBAKABR1": (
            "central_cannon_3rd_pawn_advancement_with_doubleheaded_snake_pawn_formation_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红两头蛇"
        ),
        "1rbakabnr/9/2n1c4/p1p1p1p1p/9/2P3P2/Pc2P3P/2N1C2C1/9/1RBAKABNR": (
            "central_cannon_3rd_pawn_advancement_with_doubleheaded_snake_pawn_formation_vs_left_cannon_blockade_with_deferred_opposite_direction_cannon_variation",
            "中炮进三兵对左炮封车转列炮——红两头蛇"
        ),
        "rnbakabnr/9/4c2c1/p1p1p1p1p/9/9/P1P1P1P1P/1C2C4/9/RNBAKABNR": (
            "opposite_direction_cannons",
            "中炮对列炮"
        ),
        "rnbakabnr/9/1c2c4/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/9/RNBAKABNR": (
            "opposite_direction_cannons",
            "中炮对列炮"
        ),
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_others",
            "仙人指路局(对其他)"
        ),
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_others",
            "仙人指路局(对其他)"
        ),
        "rnbakabnr/9/1c2c4/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_central_cannon",
            "仙人指路对中炮"
        ),
        "rnbakabnr/9/4c2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_central_cannon",
            "仙人指路对中炮"
        ),
        "rnbakabnr/9/4c2c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_central_cannon",
            "仙人指路对中炮"
        ),
        "rnbakabnr/9/1c2c4/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_central_cannon",
            "仙人指路对中炮"
        ),
        "rnbakabnr/9/1c3c3/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/3c3c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/3c3c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/1c3c3/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/1c1c5/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/5c1c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/5c1c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/1c1c5/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_palcorner_cannon_or_cross_palace_cannon",
            "仙人指路对仕角炮或过宫炮"
        ),
        "rnbakabnr/9/6cc1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_golden_hooked_cannon",
            "仙人指路对金钩炮"
        ),
        "rnbakabnr/9/1cc6/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_golden_hooked_cannon",
            "仙人指路对金钩炮"
        ),
        "r1bakabnr/9/1cn4c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_right_horse_advancement",
            "仙人指路(其他)对进右马"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_right_horse_advancement",
            "仙人指路(其他)对进右马"
        ),
        "r1bakabnr/9/1cn4c1/p1p1p1p1p/9/6P2/P1P1P3P/1C4NC1/9/RNBAKAB1R": (
            "pawn_with_right_horse_advancement_others_vs_right_horse_advancement",
            "仙人指路互进右马局(不包括转对兵互进右马局)"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p1p1p/9/2P6/P3P1P1P/1CN4C1/9/R1BAKABNR": (
            "pawn_with_right_horse_advancement_others_vs_right_horse_advancement",
            "仙人指路互进右马局(不包括转对兵互进右马局)"
        ),
        "r1bakabnr/9/1cn4c1/p1p1p1p1p/9/2P3P2/P3P3P/1C5C1/9/RNBAKABNR": (
            "doubleheaded_snake_pawn_formation_vs_right_horse_advancement_others",
            "两头蛇对进右马(其他)"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p1p1p/9/2P3P2/P3P3P/1C5C1/9/RNBAKABNR": (
            "doubleheaded_snake_pawn_formation_vs_right_horse_advancement_others",
            "两头蛇对进右马(其他)"
        ),
        "r1bakabnr/9/1cn3c2/p1p1p1p1p/9/2P3P2/P3P3P/1C5C1/9/RNBAKABNR": (
            "doubleheaded_snake_pawn_formation_vs_right_horse_advancement_with_thundering_defense_variation",
            "两头蛇对进右马转卒底炮"
        ),
        "rnbakab1r/9/2c3nc1/p1p1p1p1p/9/2P3P2/P3P3P/1C5C1/9/RNBAKABNR": (
            "doubleheaded_snake_pawn_formation_vs_right_horse_advancement_with_thundering_defense_variation",
            "两头蛇对进右马转卒底炮"
        ),
        "rnbakabnr/9/1c4c2/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_thundering_defense",
            "仙人指路(其他)对卒底炮"
        ),
        "rnbakabnr/9/2c4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_thundering_defense",
            "仙人指路(其他)对卒底炮"
        ),
        "rnbakabnr/9/1c4c2/p1p1p1p1p/9/6P2/P1P1P3P/1C2C4/9/RNBAKABNR": (
            "pawn_with_right_central_cannon_vs_thundering_defense",
            "仙人指路转右中炮对卒底炮"
        ),
        "rnbakabnr/9/2c4c1/p1p1p1p1p/9/2P6/P3P1P1P/4C2C1/9/RNBAKABNR": (
            "pawn_with_right_central_cannon_vs_thundering_defense",
            "仙人指路转右中炮对卒底炮"
        ),
        "rnbakabnr/9/1c4c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2C1/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_others",
            "仙人指路转左中炮对卒底炮(其他)"
        ),
        "rnbakabnr/9/2c4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C4/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_others",
            "仙人指路转左中炮对卒底炮(其他)"
        ),
        "rnbakabnr/9/4c1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2C1/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_same_direction_cannons_variation",
            "仙人指路转左中炮对卒底炮转顺炮"
        ),
        "rnbakabnr/9/2c1c4/p1p1p1p1p/9/2P6/P3P1P1P/1C2C4/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_same_direction_cannons_variation",
            "仙人指路转左中炮对卒底炮转顺炮"
        ),
        "rnbakabnr/9/1c5c1/p3p1p1p/2p6/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_pawn_with_metamorphosis_to_other_openings",
            "对兵局(转其他)"
        ),
        "rnbakabnr/9/1c5c1/p1p1p3p/6p2/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_vs_pawn_with_metamorphosis_to_other_openings",
            "对兵局(转其他)"
        ),
        "rnbakabnr/9/1c5c1/p3p1p1p/2p6/6P2/P1P1P3P/1C4NC1/9/RNBAKAB1R": (
            "pawn_with_right_horse_variation_vs_pawn_others",
            "对兵互进右马局(红走其他)"
        ),
        "rnbakabnr/9/1c5c1/p1p1p3p/6p2/2P6/P3P1P1P/1CN4C1/9/R1BAKABNR": (
            "pawn_with_right_horse_variation_vs_pawn_others",
            "对兵互进右马局(红走其他)"
        ),
        "r1bakabnr/9/1cn4c1/p3p1p1p/2p6/6P2/P1P1P3P/1C4NC1/9/RNBAKAB1R": (
            "pawn_with_right_horse_variation_others_vs_pawn_with_right_horse_variation",
            "对兵互进右马局(红走其他)"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p3p/6p2/2P6/P3P1P1P/1CN4C1/9/R1BAKABNR": (
            "pawn_with_right_horse_variation_others_vs_pawn_with_right_horse_variation",
            "对兵互进右马局(红走其他)"
        ),
        "r1bakabnr/9/1cn4c1/p3p1p1p/2p6/6P2/P1P1P3P/1C4NC1/8R/RNBAKAB2": (
            "pawn_with_right_horse_right_ranked_chariot_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红横车"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p3p/6p2/2P6/P3P1P1P/1CN4C1/R8/2BAKABNR": (
            "pawn_with_right_horse_right_ranked_chariot_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红横车"
        ),
        "r1bakabnr/9/1cn4c1/p3p1p1p/2p6/6P2/P1P1P3P/1C4N1C/9/RNBAKAB1R": (
            "pawn_with_right_horse_right_side_cannon_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红边炮"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p3p/6p2/2P6/P3P1P1P/C1N4C1/9/R1BAKABNR": (
            "pawn_with_right_horse_right_side_cannon_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红边炮"
        ),
        "rnbakabnr/9/1c5c1/p3p1p1p/2p6/6P2/P1P1P3P/2C4C1/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_others",
            "对兵转兵底炮(对其他)"
        ),
        "rnbakabnr/9/1c5c1/p1p1p3p/6p2/2P6/P3P1P1P/1C4C2/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_others",
            "对兵转兵底炮(对其他)"
        ),
        "rnbakabnr/9/4c2c1/p3p1p1p/2p6/6P2/P1P1P3P/2C4C1/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_with_right_central_cannon_variation",
            "对兵转兵底炮对右中炮"
        ),
        "rnbakabnr/9/1c2c4/p1p1p3p/6p2/2P6/P3P1P1P/1C4C2/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_with_right_central_cannon_variation",
            "对兵转兵底炮对右中炮"
        ),
        "rnbakabnr/9/1c2c4/p3p1p1p/2p6/6P2/P1P1P3P/2C4C1/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_with_left_central_cannon_variation",
            "对兵转兵底炮对左中炮"
        ),
        "rnbakabnr/9/4c2c1/p1p1p3p/6p2/2P6/P3P1P1P/1C4C2/9/RNBAKABNR": (
            "pawn_with_thundering_cannon_thundering_defense_variation_vs_pawn_with_left_central_cannon_variation",
            "对兵转兵底炮对左中炮"
        ),
        "rn1akabnr/9/1c2b2c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_elephant_opening",
            "仙人指路(其他)对飞象"
        ),
        "rnbaka1nr/9/1c2b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_elephant_opening",
            "仙人指路(其他)对飞象"
        ),
        "rnbaka1nr/9/1c2b2c1/p1p1p1p1p/9/6P2/P1P1P3P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_elephant_opening",
            "仙人指路(其他)对飞象"
        ),
        "rn1akabnr/9/1c2b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR": (
            "pawn_others_vs_elephant_opening",
            "仙人指路(其他)对飞象"
        ),
        "rn1akabnr/9/1c2b2c1/p1p1p1p1p/9/6P2/P1P1P3P/1C4NC1/9/RNBAKAB1R": (
            "pawn_with_rt_filed_horse_vs_elephant_opening",
            "仙人指路(进右马)对飞象"
        ),
        "rnbaka1nr/9/1c2b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1CN4C1/9/R1BAKABNR": (
            "pawn_with_rt_filed_horse_vs_elephant_opening",
            "仙人指路(进右马)对飞象"
        ),
        "rnbaka1nr/9/1c2b2c1/p1p1p1p1p/9/6P2/P1P1P3P/1C4NC1/9/RNBAKAB1R": (
            "pawn_with_rt_filed_horse_vs_elephant_opening",
            "仙人指路(进右马)对飞象"
        ),
        "rn1akabnr/9/1c2b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1CN4C1/9/R1BAKABNR": (
            "pawn_with_rt_filed_horse_vs_elephant_opening",
            "仙人指路(进右马)对飞象"
        ),
        "rnbakabnr/9/1c4c2/p1p1p1p1p/9/6P2/P1P1P3P/1C2B2C1/9/RNBAKA1NR": (
            "pawn_with_left_or_right_elephant_vs_thundering_defense",
            "仙人指路飞相对卒底炮"
        ),
        "rnbakabnr/9/2c4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2B2C1/9/RN1AKABNR": (
            "pawn_with_left_or_right_elephant_vs_thundering_defense",
            "仙人指路飞相对卒底炮"
        ),
        "rnbakabnr/9/1c4c2/p1p1p1p1p/9/6P2/P1P1P3P/1C2B2C1/9/RN1AKABNR": (
            "pawn_with_left_or_right_elephant_vs_thundering_defense",
            "仙人指路飞相对卒底炮"
        ),
        "rnbakabnr/9/2c4c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2B2C1/9/RNBAKA1NR": (
            "pawn_with_left_or_right_elephant_vs_thundering_defense",
            "仙人指路飞相对卒底炮"
        ),
        "rn1akabnr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2C1/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_right_central_elephant_others",
            "仙人指路转左中炮(其他)对卒底炮飞右象"
        ),
        "rnbaka1nr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C4/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_right_central_elephant_others",
            "仙人指路转左中炮(其他)对卒底炮飞右象"
        ),
        "rn1akabnr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2CN/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_right_side_horse_variation_vs_thundering_defense_with_right_central_elephant_others",
            "仙人指路转左中炮对卒底炮飞右象——红右边马(对黑其他)"
        ),
        "rnbaka1nr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/NC2C4/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_right_side_horse_variation_vs_thundering_defense_with_right_central_elephant_others",
            "仙人指路转左中炮对卒底炮飞右象——红右边马(对黑其他)"
        ),
        "rn1akab1r/9/1c2b1c1n/p1p1p1p1p/9/6P2/P1P1P3P/4C2CN/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_right_side_horse_variation_vs_thundering_defense_with_right_central_elephant_with_left_side_horse_variation",
            "仙人指路转左中炮对卒底炮飞右象——互进边马"
        ),
        "r1baka1nr/9/n1c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/NC2C4/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_right_side_horse_variation_vs_thundering_defense_with_right_central_elephant_with_left_side_horse_variation",
            "仙人指路转左中炮对卒底炮飞右象——互进边马"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2C1/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮(其他)对卒底炮飞左象"
        ),
        "rn1akabnr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C4/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮(其他)对卒底炮飞左象"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2C1/4A4/RNBAK1BNR": (
            "pawn_with_left_central_cannon_and_early_advisor_variation_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红先上仕"
        ),
        "rn1akabnr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C4/4A4/RNB1KABNR": (
            "pawn_with_left_central_cannon_and_early_advisor_variation_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红先上仕"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/2N1C2C1/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_and_left_file_horse_variation_vs_thundering_defense_with_left_central_elephant_others",
            "仙人指路转左中炮对卒底炮飞左象——红进左马(对黑其他)"
        ),
        "rn1akabnr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_file_horse_variation_vs_thundering_defense_with_left_central_elephant_others",
            "仙人指路转左中炮对卒底炮飞左象——红进左马(对黑其他)"
        ),
        "1nbaka1nr/r8/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/2N1C2C1/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_and_left_file_horse_variation_others_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红进左马(其他)对黑右横车"
        ),
        "rn1akabn1/8r/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_file_horse_variation_others_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红进左马(其他)对黑右横车"
        ),
        "1nbaka2r/5n1r1/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/2N1C1NC1/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_others_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车(其他)对黑右横车"
        ),
        "r2akabn1/1r1n5/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/1CN1C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_others_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车(其他)对黑右横车"
        ),
        "2baka2r/5n1r1/nc2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/2N1C1N1C/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_1st_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车边卒"
        ),
        "r2akab2/1r1n5/2c1b2cn/p1p1p1p1p/9/2P6/P3P1P1P/C1N1C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_1st_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车边卒"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p3p/6p2/6P2/P1P1P3P/2N1C2C1/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——黑进７卒(其他)"
        ),
        "rn1akabnr/9/2c1b2c1/p3p1p1p/2p6/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——黑进７卒(其他)"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2CN/9/R1BAKAB1R": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice",
            "仙人指路转左中炮对卒底炮飞左象——(红其他对)黑连进７卒"
        ),
        "rn1akabnr/9/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/NC2C1N2/9/R1BAKAB1R": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice",
            "仙人指路转左中炮对卒底炮飞左象——(红其他对)黑连进７卒"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2C1/9/1RBAKABNR": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice",
            "仙人指路转左中炮对卒底炮飞左象——(红其他对)黑连进７卒"
        ),
        "rn1akabnr/9/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/1C2C1N2/9/RNBAKABR1": (
            "pawn_with_left_central_cannon_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice",
            "仙人指路转左中炮对卒底炮飞左象——(红其他对)黑连进７卒"
        ),
        "rnbaka2r/5n3/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2CN/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_lame_horse_variation",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马对黑连进７卒拐角马"
        ),
        "r2akabnr/3n5/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/NC2C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_lame_horse_variation",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马对黑连进７卒拐角马"
        ),
        "1nbaka1nr/r8/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2CN/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马(其他)对黑连进７卒右横车"
        ),
        "rn1akabn1/8r/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/NC2C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_others_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马(其他)对黑连进７卒右横车"
        ),
        "1nbaka1nr/r8/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2CN/4A4/1RBAK1B1R": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_with_early_advisor_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马上仕对黑连进７卒右横车"
        ),
        "rn1akabn1/8r/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/NC2C1N2/4A4/R1B1KABR1": (
            "pawn_with_left_central_cannon_left_filed_chariot_and_right_side_horse_with_early_advisor_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右边马上仕对黑连进７卒右横车"
        ),
        "1nbaka1nr/r8/1c2b1c2/p1p1p3p/9/1R4p2/P1P1P3P/2N1C2CN/9/2BAKAB1R": (
            "pawn_with_left_central_cannon_riverbank_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红巡河车右边马对黑连进７卒右横车"
        ),
        "rn1akabn1/8r/2c1b2c1/p3p1p1p/9/2p4R1/P3P1P1P/NC2C1N2/9/R1BAKAB2": (
            "pawn_with_left_central_cannon_riverbank_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红巡河车右边马对黑连进７卒右横车"
        ),
        "1nbaka1nr/r8/1c2b1c2/p1p1p3p/9/6p2/P1P1P3P/2N1C2CN/9/1RBAKABR1": (
            "pawn_with_left_central_cannon_double_filed_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红双直车右边马对黑连进７卒右横车"
        ),
        "rn1akabn1/8r/2c1b2c1/p3p1p1p/9/2p6/P3P1P1P/NC2C1N2/9/1RBAKABR1": (
            "pawn_with_left_central_cannon_double_filed_chariot_and_right_side_horse_vs_thundering_defense_with_left_central_elephant_and_7th_pawn_advancement_twice_and_right_ranked_chariot",
            "仙人指路转左中炮对卒底炮飞左象——红双直车右边马对黑连进７卒右横车"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1p1p1p/9/6P2/P1P1P3P/4C2CN/9/RNBAKAB1R": (
            "pawn_with_left_central_cannon_right_side_horse_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红右边马"
        ),
        "rn1akabnr/9/2c1b2c1/p1p1p1p1p/9/2P6/P3P1P1P/NC2C4/9/R1BAKABNR": (
            "pawn_with_left_central_cannon_right_side_horse_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红右边马"
        ),
        "rnbaka1nr/9/1c2b1c2/p1p1C1p1p/9/6P2/P1P1P3P/7C1/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_with_cannon_taking_central_pawn_variation_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红炮打中卒"
        ),
        "rn1akabnr/9/2c1b2c1/p1p1C1p1p/9/2P6/P3P1P1P/1C7/9/RNBAKABNR": (
            "pawn_with_left_central_cannon_with_cannon_taking_central_pawn_variation_vs_thundering_defense_with_left_central_elephant",
            "仙人指路转左中炮对卒底炮飞左象——红炮打中卒"
        ),
        "r1bakabnr/9/1cn4c1/p3p1p1p/2p6/6P2/P1P1P3P/1C2B1NC1/9/RNBAKA2R": (
            "pawn_with_right_horse_leftright_central_elephant_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红飞相"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p3p/6p2/2P6/P3P1P1P/1CN1B2C1/9/R2AKABNR": (
            "pawn_with_right_horse_leftright_central_elephant_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红飞相"
        ),
        "r1bakabnr/9/1cn4c1/p3p1p1p/2p6/6P2/P1P1P3P/1C2B1NC1/9/RN1AKAB1R": (
            "pawn_with_right_horse_leftright_central_elephant_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红飞相"
        ),
        "rnbakab1r/9/1c4nc1/p1p1p3p/6p2/2P6/P3P1P1P/1CN1B2C1/9/R1BAKA1NR": (
            "pawn_with_right_horse_leftright_central_elephant_variation_vs_pawn_with_right_horse_variation",
            "对兵对进右马局——红飞相"
        ),
        "r1bakabr1/9/1c4nc1/4p1p1p/pnp6/6P2/P1P1P3P/N1C1C1N2/R8/2BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_and_right_riverbank_horse_variation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车(对黑其他)"
        ),
        "1rbakab1r/9/1cn4c1/p1p1p4/6pnp/2P6/P3P1P1P/2N1C1C1N/8R/1RBAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_and_right_riverbank_horse_variation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车(对黑其他)"
        ),
        "r1baka1r1/9/1c2b1nc1/4p1p1p/pnp6/6P2/P1P1P3P/N1C1C1N2/R8/2BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车(其他)对黑飞左象"
        ),
        "1r1akab1r/9/1cn1b2c1/p1p1p4/6pnp/2P6/P3P1P1P/2N1C1C1N/8R/1RBAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车(其他)对黑飞左象"
        ),
        "r1baka1r1/9/1c2b1nc1/4p1p1p/pnp6/5NP2/P1P1P3P/N1C1C4/R8/2BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_right_riverbank_horse_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车右马盘河对黑飞左象"
        ),
        "1r1akab1r/9/1cn1b2c1/p1p1p4/6pnp/2PN5/P3P1P1P/4C1C1N/8R/1RBAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_right_riverbank_horse_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车右马盘河对黑飞左象"
        ),
        "r1baka1r1/9/1c2b1nc1/4p1p1p/pnp6/6PR1/P1P1P3P/N1C1C1N2/R8/2BAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_and_right_riverbank_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车右车巡河对黑飞左象"
        ),
        "1r1akab1r/9/1cn1b2c1/p1p1p4/6pnp/1RP6/P3P1P1P/2N1C1C1N/8R/2BAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_and_right_riverbank_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_left_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车右车巡河对黑飞左象"
        ),
        "r2akabr1/9/1c2b1nc1/4p1p1p/pnp6/6P2/P1P1P3P/N1C1C1N2/R8/2BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_right_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑飞右象"
        ),
        "1rbaka2r/9/1cn1b2c1/p1p1p4/6pnp/2P6/P3P1P1P/2N1C1C1N/8R/1RBAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_right_central_elephant_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑飞右象"
        ),
        "r1bakabr1/9/1c4nc1/4p1p1p/1np6/p5P2/P1P1P3P/N1C1C1N2/R8/2BAKABR1": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_side_pawn_exchange_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑兑边卒"
        ),
        "1rbakab1r/9/1cn4c1/p1p1p4/6pn1/2P5p/P3P1P1P/2N1C1C1N/8R/1RBAKAB2": (
            "57_cannons_3rd_pawn_advancement_left_ranked_chariot_vs_screen_horse_defense_with_1st_and_3rd_pawn_advancement_right_riverbank_horse_variation_with_side_pawn_exchange_subvariation",
            "五七炮互进三兵对屏风马边卒右马外盘河——红左横车对黑兑边卒"
        ),
        "2baka2r/5n3/nc2b1c2/p1p1p1p1p/9/5NP2/P1P1P3P/2N1C2rC/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_early_advisor_variation",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车过河"
        ),
        "r2akab2/3n5/2c1b2cn/p1p1p1p1p/9/2PN5/P3P1P1P/Cr2C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_early_advisor_variation",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车过河"
        ),
        "2baka2r/5n1r1/nc2b1c2/2p1p1p1p/p8/5NP2/P1P1P3P/2N1C3C/9/1RBAKAB1R": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_1st_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车边卒"
        ),
        "r2akab2/1r1n5/2c1b2cn/p1p1p1p2/8p/2PN5/P3P1P1P/C3C1N2/9/R1BAKABR1": (
            "pawn_with_left_central_cannon_and_left_filed_chariot_variation_and_right_riverbank_horse_vs_thundering_defense_with_left_central_elephant_and_right_ranked_chariot_and_1st_pawn_advancement",
            "仙人指路转左中炮对卒底炮飞左象——红左直车右马盘河对黑右横车边卒"
        ),
        "r1bakabnr/9/1cn2c3/p1p1p1p1p/9/2P6/P3P1P1P/1CN1C4/9/R1BAKABNR": (
            "central_cannon_with_quick_left_proper_horse_vs_sandwiched_horse_defense",
            "中炮急进左马对反宫马"
        ),
        "rnbakab1r/9/3c2nc1/p1p1p1p1p/9/6P2/P1P1P3P/4C1NC1/9/RNBAKAB1R": (
            "central_cannon_with_quick_left_proper_horse_vs_sandwiched_horse_defense",
            "中炮急进左马对反宫马"
        ),
    }

    res = mapping.get(board_part)
    if res:
        name = res[1].replace("left", "左")
        return res[0], name

    res = mapping.get(mirrored_board_part)
    if res:
        name = res[1].replace("left", "左")
        # Wait, if we swap left/right for symmetric name:
        # e.g. "红左边马" becomes "红右边马".
        # This is correct and professional!
        return res[0], name

    return None


def _specific_template(
    memory: OpeningMemory,
    red_id: str | None,
    black_id: str | None,
    red_modifiers: list[str],
    black_modifiers: list[str],
    base_id: str | None,
    shapes: dict[str, list[str]] = None,
) -> tuple[str | None, str | None]:
    lookup = _lookup_c20_c49(memory)
    if lookup:
        return lookup

    red_shapes = set(red_modifiers)
    black_shapes = set(black_modifiers)
    raw_red_shapes = set(shapes["red"]) if shapes else set()
    raw_black_shapes = set(shapes["black"]) if shapes else set()

    red_elephant = next((item for item in memory.red.choice_path if item.id == "fly_elephant"), None)
    black_elephant = next((item for item in memory.black.choice_path if item.id == "fly_elephant"), None)
    red_horse = next((item for item in memory.red.choice_path if item.id == "proper_horse_opening"), None)
    red_cpc = next((item for item in memory.red.choice_path if item.id == "cross_palace_cannon"), None)
    if red_elephant and black_elephant:
        if red_elephant.wing == black_elephant.wing:
            return "same_direction_elephant", "順相局"
        else:
            return "opposite_direction_elephant", "列相局"

    if red_elephant and black_id == "proper_horse_opening":
        black_horse = next((item for item in memory.black.choice_path if item.id == "proper_horse_opening"), None)
        if red_elephant and black_horse:
            if red_elephant.wing is None or black_horse.wing is None:
                return None, None
            if (red_elephant.wing == "g" and black_horse.wing == "left") or (red_elephant.wing == "c" and black_horse.wing == "right"):
                return "elephant_vs_left_proper_horse", "飛相對進左馬"
            else:
                if (red_elephant.wing == "g" and "advance_three_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_seven_pawn" in raw_red_shapes):
                    return "elephant_pawn3_vs_right_proper_horse", "飛相進三兵對進右馬"
                elif (red_elephant.wing == "g" and "advance_seven_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_three_pawn" in raw_red_shapes):
                    return "elephant_pawn7_vs_right_proper_horse", "飛相進七兵對進右馬"
                return "elephant_vs_right_proper_horse", "飛相(其他)對進右馬"

    if red_elephant and black_id == "palcorner_cannon":
        black_cannon = next((item for item in memory.black.choice_path if item.id == "palcorner_cannon"), None)
        if red_elephant and black_cannon:
            if red_elephant.wing is None or black_cannon.wing is None:
                return None, None
            if (red_elephant.wing == "g" and black_cannon.wing == "left") or (red_elephant.wing == "c" and black_cannon.wing == "right"):
                return "elephant_vs_left_palcorner_cannon", "飛相對左士角炮"
            else:
                # 飛相(其他)對右士角炮 (A21)
                # Check for Red's Proper Horse (A22)
                if (red_elephant.wing == "g" and "proper_horse_left" in raw_red_shapes) or (red_elephant.wing == "c" and "proper_horse_right" in raw_red_shapes):
                    return "elephant_proper_horse_vs_right_palcorner_cannon", "飛相進左馬對右士角炮"
                
                # Check shapes for Red's Left Side Horse (A23)
                if (red_elephant.wing == "g" and "edge_horse_left" in raw_red_shapes) or (red_elephant.wing == "c" and "edge_horse_right" in raw_red_shapes):
                    return "elephant_edge_horse_vs_right_palcorner_cannon", "飛相左邊馬對右士角炮"
                
                # Check for Red's Ranked Chariot (A24)
                red_rook = next((item for item in memory.red.formed_shapes if item.id == "horizontal_rook"), None)
                if red_rook and ((red_elephant.wing == "g" and red_rook.wing == "left") or (red_elephant.wing == "c" and red_rook.wing == "right")):
                    return "elephant_ranked_chariot_vs_right_palcorner_cannon", "飛相橫車對右士角炮"
                
                # Check for Red's 3rd Pawn Advancement (A25)
                if (red_elephant.wing == "g" and "advance_three_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_seven_pawn" in raw_red_shapes):
                    return "elephant_pawn3_vs_right_palcorner_cannon", "飛相進三兵對右士角炮"
                
                # Check for Red's 7th Pawn Advancement (A26)
                if (red_elephant.wing == "g" and "advance_seven_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_three_pawn" in raw_red_shapes):
                    return "elephant_pawn7_vs_right_palcorner_cannon", "飛相進七兵對右士角炮"
                
                return "elephant_vs_right_palcorner_cannon", "飛相(其他)對右士角炮"

    if red_id == "fly_elephant" and black_id == "central_cannon":
        black_cannon = next((item for item in memory.black.choice_path if item.id == "central_cannon"), None)
        if red_elephant and black_cannon:
            if red_elephant.wing is None:
                return None, None
            if (red_elephant.wing == "g" and (black_cannon.origin_file == "h" or "central_cannon_from_h_file" in raw_black_shapes)) or (red_elephant.wing == "c" and (black_cannon.origin_file == "b" or "central_cannon_from_b_file" in raw_black_shapes)):
                return "elephant_vs_left_central_cannon", "飛相(轉其他)對左中炮"
            else:
                # 飛相對右中炮 (A29)
                return "elephant_vs_right_central_cannon", "飛相對右中炮"

    if red_elephant and black_id == "cross_palace_cannon":
        black_cannon = next((item for item in memory.black.choice_path if item.id == "cross_palace_cannon"), None)
        if red_elephant and black_cannon:
            if red_elephant.wing is None or black_cannon.wing is None:
                return None, None
            if (red_elephant.wing == "g" and black_cannon.wing == "left") or (red_elephant.wing == "c" and black_cannon.wing == "right"):
                # Check for Red's same-side proper horse (A31)
                if (red_elephant.wing == "g" and "proper_horse_right" in raw_red_shapes) or (red_elephant.wing == "c" and "proper_horse_left" in raw_red_shapes):
                    # Check for Red's same-side straight rook (A32, A33, A34)
                    red_rook = next((item for item in memory.red.formed_shapes if item.id == "straight_rook"), None)
                    has_same_side_rook = red_rook and ((red_elephant.wing == "g" and red_rook.wing == "right") or (red_elephant.wing == "c" and red_rook.wing == "left"))
                    # Check for Black's same-side advanced pawn
                    has_same_side_pawn = (red_elephant.wing == "g" and "advance_seven_soldier" in raw_black_shapes) or (red_elephant.wing == "c" and "advance_three_soldier" in raw_black_shapes)
                    if has_same_side_rook and has_same_side_pawn:
                        # Check for Red same-side edge cannon (A33)
                        if (red_elephant.wing == "g" and "edge_cannon_right" in raw_red_shapes) or (red_elephant.wing == "c" and "edge_cannon_left" in raw_red_shapes):
                            return "elephant_proper_horse_filed_chariot_side_cannon_vs_left_cross_palace_cannon_7pawn", "飛相進右馬對左過宮炮(紅直車邊炮)"
                        # Check for Red opposite-side advanced pawn (A34)
                        if (red_elephant.wing == "g" and "advance_seven_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_three_pawn" in raw_red_shapes):
                            return "elephant_7pawn_proper_horse_vs_left_cross_palace_cannon_7pawn", "飛相進右馬對左過宮炮(互進七兵)"
                        # Otherwise: A32
                        return "elephant_proper_horse_filed_chariot_vs_left_cross_palace_cannon_7pawn", "飛相進右馬對左過宮炮(紅直車對黑進7卒)"
                    return "elephant_right_proper_horse_vs_left_cross_palace_cannon", "飛相進右馬對左過宮炮"
                return "elephant_vs_left_cross_palace_cannon", "飛相(其他)對左過宮炮"
            else:
                # 飛相對右過宮炮 (A35)
                return "elephant_vs_right_cross_palace_cannon", "飛相對右過宮炮"

    if red_elephant and black_id == "angle_pawn":
        black_pawn = next((item for item in memory.black.choice_path if item.id == "angle_pawn"), None)
        if red_elephant and black_pawn:
            if red_elephant.wing is None or black_pawn.wing is None:
                return None, None
            # Same side (A36, A37, A38)
            if (red_elephant.wing == "g" and black_pawn.wing == "left") or (red_elephant.wing == "c" and black_pawn.wing == "right"):
                # Check for Red opposite-side pawn (A38)
                if (red_elephant.wing == "g" and "advance_seven_pawn" in raw_red_shapes) or (red_elephant.wing == "c" and "advance_three_pawn" in raw_red_shapes):
                    return "elephant_7pawn_vs_same_side_pawn", "飛相互進七兵局"
                # Check for Red opposite-side horse (A37)
                if (red_elephant.wing == "g" and "proper_horse_left" in raw_red_shapes) or (red_elephant.wing == "c" and "proper_horse_right" in raw_red_shapes):
                    return "elephant_left_proper_horse_vs_same_side_pawn", "飛相進左馬對進7卒"
                # Default A36
                return "elephant_vs_same_side_pawn", "飛相(其他)對進7卒"
            # Opposite side (A39)
            else:
                return "elephant_vs_opposite_side_pawn", "飛相對進3卒"

    if red_horse:
        if black_id == "angle_pawn":
            black_pawn = next((item for item in memory.black.choice_path if item.id == "angle_pawn"), None)
            if red_horse.wing and black_pawn and black_pawn.wing:
                # Same side (A41-A45)
                if (red_horse.wing == "right" and black_pawn.wing == "left") or (red_horse.wing == "left" and black_pawn.wing == "right"):
                    # Check for Red same-side edge cannon (A42)
                    if (red_horse.wing == "right" and "edge_cannon_right" in raw_red_shapes) or (red_horse.wing == "left" and "edge_cannon_left" in raw_red_shapes):
                        return "proper_horse_side_cannon_vs_same_side_pawn", "起馬轉邊炮對進７卒"
                    # Check for Red opposite-side palcorner cannon (A43)
                    red_pcc = next((item for item in memory.red.choice_path if item.id == "palcorner_cannon"), None)
                    if (red_horse.wing == "right" and ("palcorner_cannon_left" in raw_red_shapes or (red_pcc and red_pcc.wing == "left"))) or (red_horse.wing == "left" and ("palcorner_cannon_right" in raw_red_shapes or (red_pcc and red_pcc.wing == "right"))):
                        return "proper_horse_palcorner_cannon_vs_same_side_pawn", "起馬轉仕角炮對進７卒"
                    # Check for Red opposite-side central cannon (A44)
                    red_cc = next((item for item in memory.red.choice_path if item.id == "central_cannon"), None)
                    if (red_horse.wing == "right" and (red_cc and red_cc.origin_file == "b" or "central_cannon_from_b_file" in raw_red_shapes)) or (red_horse.wing == "left" and (red_cc and red_cc.origin_file == "h" or "central_cannon_from_h_file" in raw_red_shapes)):
                        return "proper_horse_central_cannon_vs_same_side_pawn", "起馬轉中炮對進７卒"
                    # Check for Red opposite-side pawn (A45)
                    if (red_horse.wing == "right" and "advance_seven_pawn" in raw_red_shapes) or (red_horse.wing == "left" and "advance_three_pawn" in raw_red_shapes):
                        return "proper_horse_7pawn_vs_same_side_pawn", "起馬互進七兵局"
                    # Default A41
                    return "proper_horse_vs_same_side_pawn", "起馬對進７卒"
        elif black_id is None and len(memory.red.choice_path) == 1:
            return "proper_horse_opening_base", "起馬局"

    if red_id == "palcorner_cannon":
        red_pcc = next((item for item in memory.red.choice_path if item.id == "palcorner_cannon"), None)
        if red_pcc:
            # Palcorner Cannon vs Left Proper Horse (A51)
            if black_id == "proper_horse_opening":
                black_horse = next((item for item in memory.black.choice_path if item.id == "proper_horse_opening"), None)
                if black_horse and black_horse.wing:
                    if (red_pcc.wing == "left" and black_horse.wing == "right") or (red_pcc.wing == "right" and black_horse.wing == "left"):
                        return "palcorner_cannon_vs_same_side_proper_horse", "仕角炮對進左馬"
            # Palcorner Cannon vs Right Central Cannon (A52-A53)
            elif black_id == "central_cannon":
                black_cannon = next((item for item in memory.black.choice_path if item.id == "central_cannon"), None)
                if black_cannon:
                    if (red_pcc.wing == "left" and (black_cannon.origin_file == "h" or "central_cannon_from_h_file" in raw_black_shapes)) or (red_pcc.wing == "right" and (black_cannon.origin_file == "b" or "central_cannon_from_b_file" in raw_black_shapes)):
                        # Check for Red's Sandwich Horse (A53)
                        if "double_proper_horses" in raw_red_shapes:
                            return "palcorner_cannon_sandwiched_horse_vs_opposite_side_central_cannon", "仕角炮轉反宮馬對右中炮"
                        return "palcorner_cannon_vs_opposite_side_central_cannon", "仕角炮對右中炮"
            # Palcorner Cannon vs 7th Pawn Advancement (A54)
            elif black_id == "angle_pawn":
                black_pawn = next((item for item in memory.black.choice_path if item.id == "angle_pawn"), None)
                if black_pawn and black_pawn.wing:
                    if (red_pcc.wing == "right" and black_pawn.wing == "left") or (red_pcc.wing == "left" and black_pawn.wing == "right"):
                        return "palcorner_cannon_vs_same_side_pawn", "仕角炮對進７卒"

    if red_cpc:
        if black_id == "proper_horse_opening":
            black_horse = next((item for item in memory.black.choice_path if item.id == "proper_horse_opening"), None)
            if black_horse and black_horse.wing:
                if (red_cpc.wing == "right" and black_horse.wing == "left") or (red_cpc.wing == "left" and black_horse.wing == "right"):
                    return "cross_palace_cannon_vs_same_side_proper_horse", "過宮炮對進左馬"
        elif black_id == "central_cannon":
            black_cannon = next((item for item in memory.black.choice_path if item.id == "central_cannon"), None)
            if black_cannon:
                if (red_cpc.wing == "right" and (black_cannon.origin_file == "h" or "central_cannon_from_h_file" in raw_black_shapes)) or (red_cpc.wing == "left" and (black_cannon.origin_file == "b" or "central_cannon_from_b_file" in raw_black_shapes)):
                    # Check for A65: cpc filed chariot vs lt cc ranked chariot
                    red_rook = next((item for item in memory.red.formed_shapes if item.id == "straight_rook"), None)
                    has_red_same_side_rook = red_rook and ((red_cpc.wing == "right" and red_rook.wing == "right") or (red_cpc.wing == "left" and red_rook.wing == "left"))
                    black_rook = next((item for item in memory.black.formed_shapes if item.id == "horizontal_rook"), None)
                    has_black_same_side_rook = black_rook and ((red_cpc.wing == "right" and black_rook.wing == "left") or (red_cpc.wing == "left" and black_rook.wing == "right"))
                    
                    has_red_same_side_horse = (red_cpc.wing == "right" and "proper_horse_right" in raw_red_shapes) or (red_cpc.wing == "left" and "proper_horse_left" in raw_red_shapes)
                    has_black_same_side_horse = (red_cpc.wing == "right" and "proper_horse_left" in raw_black_shapes) or (red_cpc.wing == "left" and "proper_horse_right" in raw_black_shapes)
                    
                    if has_red_same_side_rook and has_black_same_side_rook and has_red_same_side_horse and has_black_same_side_horse:
                        return "cross_palace_cannon_filed_chariot_vs_left_central_cannon_ranked_chariot", "過宮炮直車對左中炮橫車"
                    return "cross_palace_cannon_vs_same_side_central_cannon", "過宮炮對左中炮"
        elif black_id is None:
            # Check for same-side ranked chariot (A62)
            black_rook = next((item for item in memory.black.formed_shapes if item.id == "horizontal_rook"), None)
            if (red_cpc.wing == "right" and ((black_rook and black_rook.wing == "left") or "horizontal_rook_left" in raw_black_shapes)) or (red_cpc.wing == "left" and ((black_rook and black_rook.wing == "right") or "horizontal_rook_right" in raw_black_shapes)):
                return "cross_palace_cannon_vs_same_side_ranked_chariot", "過宮炮對橫車"
            # Default A60
            if len(memory.red.choice_path) == 1:
                return "cross_palace_cannon_base", "過宮炮局"

    if red_id == "central_cannon":
        red_cannon = next((item for item in memory.red.choice_path if item.id == "central_cannon"), None)
        if red_cannon:
            if black_id == "proper_horse_opening":
                black_horse = next((item for item in memory.black.choice_path if item.id == "proper_horse_opening"), None)
                if black_horse and black_horse.wing:
                    # Same physical side -> B05
                    if (red_cannon.origin_file == "h" and black_horse.wing == "left") or (red_cannon.origin_file == "b" and black_horse.wing == "right"):
                        return "central_cannon_vs_same_side_proper_horse", "中炮對進左馬(其他)"
                    # Opposite physical side -> B01, B02, B03, B04
                    elif (red_cannon.origin_file == "h" and black_horse.wing == "right") or (red_cannon.origin_file == "b" and black_horse.wing == "left"):
                        # Check for B02: early advisor
                        if "palace_advisor_shape" in raw_black_shapes:
                            return "central_cannon_vs_opposite_side_proper_horse_early_advisor", "中炮對進右馬先上士"
                        # Check for B03: mandarin duck horse (same-side ranked chariot)
                        black_rook = next((item for item in memory.black.formed_shapes if item.id == "horizontal_rook"), None)
                        if (red_cannon.origin_file == "h" and ((black_rook and black_rook.wing == "left") or "horizontal_rook_left" in raw_black_shapes)) or (red_cannon.origin_file == "b" and ((black_rook and black_rook.wing == "right") or "horizontal_rook_right" in raw_black_shapes)):
                            return "central_cannon_vs_opposite_side_proper_horse_mandarin_duck_horse", "中炮對鴛鴦炮"
                        # Check for B04: three step tiger (same-side edge cannon)
                        if (red_cannon.origin_file == "h" and "edge_cannon_right" in raw_black_shapes) or (red_cannon.origin_file == "b" and "edge_cannon_left" in raw_black_shapes):
                            return "central_cannon_vs_opposite_side_proper_horse_three_step_tiger", "中炮對右三步虎"
                        # Default B01
                        return "central_cannon_vs_opposite_side_proper_horse", "中炮對進右馬(其他)"
            elif black_id == "palcorner_cannon":
                black_horse = next((item for item in memory.black.choice_path if item.id == "proper_horse_opening"), None)
                black_cannon = next((item for item in memory.black.choice_path if item.id == "palcorner_cannon"), None)
                if black_horse and black_cannon:
                    is_black_horse_opposite = (red_cannon.origin_file == "h" and black_horse.wing == "right") or (red_cannon.origin_file == "b" and black_horse.wing == "left")
                    is_black_cannon_same = (red_cannon.origin_file == "h" and black_cannon.wing == "left") or (red_cannon.origin_file == "b" and black_cannon.wing == "right")
                    if is_black_horse_opposite and is_black_cannon_same:
                        has_red_same_side_pawn = (red_cannon.origin_file == "h" and "advance_seven_pawn" in raw_red_shapes) or (red_cannon.origin_file == "b" and "advance_three_pawn" in raw_red_shapes)
                        has_red_other_horse = (red_cannon.origin_file == "h" and "proper_horse_left" in raw_red_shapes) or (red_cannon.origin_file == "b" and "proper_horse_right" in raw_red_shapes)
                        if has_red_same_side_pawn and has_red_other_horse:
                            return "central_cannon_quick_left_proper_horse_vs_sandwiched_horse", "中炮急進左馬對反宮馬"
            elif black_id is None and len(raw_black_shapes) > 0:
                # Default B00
                if len(memory.red.choice_path) == 1:
                    return "central_cannon_vs_rare_openings", "中炮局(對其他)"

    if red_id == "five_seven_cannon":
        red_cannon = next((item for item in memory.red.choice_path if item.id == "central_cannon"), None)
        if red_cannon:
            black_sh = next((item for item in memory.black.composite_systems if item.id == "reverse_palace_horse"), None)
            if black_sh:
                    if red_cannon.origin_file == "h":
                        if _has_shape(memory.black, "fly_left_elephant"):
                            has_mutual_3pawn = _has_shape(memory.red, "advance_three_pawn") and _has_shape(memory.black, "advance_three_soldier")
                            if has_mutual_3pawn and _has_shape(memory.red, "edge_horse_left") and "cannon_at_b3" in raw_black_shapes:
                                if "pawn_seven_at_starting_rank" in raw_red_shapes:
                                    return "five_seven_cannon_vs_sandwiched_horse_right_ranked_cannon", "五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河"
                                else:
                                    return "five_seven_cannon_vs_sandwiched_horse_double_pawn_sacrifice", "五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河"
                    elif red_cannon.origin_file == "b":
                        if _has_shape(memory.black, "fly_right_elephant"):
                            has_mutual_7pawn = _has_shape(memory.red, "advance_seven_pawn") and _has_shape(memory.black, "advance_seven_soldier")
                            if has_mutual_7pawn and _has_shape(memory.red, "edge_horse_right") and "cannon_at_h3" in raw_black_shapes:
                                if "pawn_three_at_starting_rank" in raw_red_shapes:
                                    return "five_seven_cannon_vs_sandwiched_horse_right_ranked_cannon", "五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河"
                                else:
                                    return "five_seven_cannon_vs_sandwiched_horse_double_pawn_sacrifice", "五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河"

    black_central = _central_choice(memory.black)
    black_left_horse = next(
        (
            item
            for item in memory.black.choice_path
            if item.id == "proper_horse_opening" and item.wing == "left"
        ),
        None,
    )
    if base_id == "opposite_side_cannons" and black_central:
        for composite_id, template_id, label in (
            ("left_cannon_blockade", "left_cannon_blockade_to_opposite_cannons", "中炮對左炮封車轉列炮"),
            ("left_three_step_tiger", "left_three_step_tiger_to_opposite_cannons", "中炮對左三步虎轉列炮"),
        ):
            composite = next(
                (item for item in memory.black.composite_systems if item.id == composite_id),
                None,
            )
            if composite and composite.formed_at_ply < black_central.formed_at_ply:
                return template_id, label

    if (
        base_id == "opposite_side_cannons"
        and black_left_horse
        and black_central
        and black_central.origin_file == "b"
        and black_left_horse.formed_at_ply < black_central.formed_at_ply
    ):
        return "delayed_opposite_side_cannons_after_left_horse", "後補列炮"

    if base_id == "same_side_cannons":
        if "straight_rook" in red_shapes and "slow_rook" in black_shapes:
            return "same_side_straight_vs_slow_rook", "順炮直車對緩開車"
        if "straight_rook" in red_shapes and "horizontal_rook" in black_shapes:
            return "same_side_straight_vs_horizontal", "順炮直車對橫車"
        if "horizontal_rook" in red_shapes and "straight_rook" in black_shapes:
            return "same_side_horizontal_vs_straight", "順炮橫車對直車"

    if red_id == "central_cannon" and black_id == "screen_horse":
        mutual_seven = {
            "advance_seven_pawn",
        }.issubset(red_shapes) and {"advance_seven_soldier"}.issubset(black_shapes)
        if "cross_river_rook" in red_shapes and mutual_seven and "flat_cannon_exchange" in black_shapes:
            return "central_cross_river_mutual_seven_vs_screen_flat_exchange", "中炮過河車互進七兵對屏風馬平炮兌車"
        if "cross_river_rook" in red_shapes and mutual_seven:
            return "central_cross_river_mutual_seven_vs_screen", "中炮過河車互進七兵對屏風馬"
        if (
            "cross_river_rook" in red_shapes
            and "seven_route_horse" in red_shapes
            and "two_headed_snake" in black_shapes
        ):
            return "central_cross_river_seven_horse_vs_screen_two_headed_snake", "中炮過河車七路馬對屏風馬兩頭蛇"

    red_angle = next((item for item in memory.red.choice_path if item.id == "angle_pawn"), None)
    red_central = _central_choice(memory.red)
    if (
        red_angle
        and red_central
        and red_angle.formed_at_ply < red_central.formed_at_ply
        and red_central.origin_file == "b"
        and black_id == "pawn_bottom_cannon"
        and "fly_left_elephant" in black_shapes
    ):
        return "angle_pawn_to_left_central_vs_pawn_bottom_fly_left_elephant", "仙人指路轉左中炮對卒底炮飛左象"
    return None, None


def resolve_classification(memory: OpeningMemory, shapes: dict[str, list[str]]) -> Classification:
    red_id, red_label = _side_label("red", memory.red)
    black_id, black_label = _side_label("black", memory.black)
    red_modifiers = _collect_modifiers("red", memory, red_id)
    black_modifiers = _collect_modifiers("black", memory, black_id)

    evidence = [
        f"紅方目前棋形：{', '.join(shapes['red']) or '無'}",
        f"黑方目前棋形：{', '.join(shapes['black']) or '無'}",
    ]
    for side_memory, prefix in (
        (memory.red, "紅方"),
        (memory.black, "黑方"),
    ):
        for item in side_memory.formed_shapes:
            state = "可命名" if item.eligible_for_name else f"被 {item.suppressed_by} 抑制"
            evidence.append(f"{prefix}{item.id} 於第 {item.formed_at_ply} ply 形成（{state}）")

    red_shapes = set(shapes["red"])
    black_shapes = set(shapes["black"])
    pawn_matchup = (
        "advance_three_pawn" in red_shapes
        and "advance_seven_soldier" in black_shapes
    ) or (
        "advance_seven_pawn" in red_shapes
        and "advance_three_soldier" in black_shapes
    )
    if pawn_matchup and memory.base_matchup_id not in {
        "same_side_cannons",
        "opposite_side_cannons",
    }:
        memory.base_matchup_id = "opposing_pawns"

    base_id = memory.base_matchup_id
    if base_id != "opposing_pawns":
        cannon_matchup = _cannon_matchup(memory, shapes)
        if cannon_matchup:
            base_id = cannon_matchup
            memory.base_matchup_id = cannon_matchup
        elif base_id not in {"same_side_cannons", "opposite_side_cannons"}:
            base_id = None
            memory.base_matchup_id = None

    template_id, template_label = _specific_template(
        memory,
        red_id,
        black_id,
        red_modifiers,
        black_modifiers,
        base_id,
        shapes,
    )

    red_text = _compose_side("red", red_id, red_label, red_modifiers)
    black_text = _compose_side("black", black_id, black_label, black_modifiers)
    
    display_name_en = "Undecided"
    if template_label:
        display_name = template_label
        certainty = "confirmed"
        display_name_en = _to_title_case_en(template_id) if template_id else "Undecided"
    elif base_id == "opposing_pawns":
        template_id = "opposing_pawns"
        display_name = "對兵局"
        certainty = "confirmed"
        display_name_en = "Opposing Pawns"
        evidence.append("紅黑三、七路兵卒以對稱方向互進至三七線")
    elif base_id in {"same_side_cannons", "opposite_side_cannons"}:
        template_id = base_id
        display_name = "順炮" if base_id == "same_side_cannons" else "列炮"
        certainty = "confirmed"
        display_name_en = "Same-Direction Cannons" if base_id == "same_side_cannons" else "Opposite-Direction Cannons"
        evidence.append("雙方中炮來源已由形成歷史鎖定")
    elif red_text and black_text:
        template_id = template_id or "two_sided"
        display_name = f"{red_text}對{black_text}"
        certainty = "confirmed" if not any(
            item.provisional for item in memory.black.choice_path[-1:]
        ) else "provisional"
        red_text_en = _compose_side_en("red", red_id, red_modifiers)
        black_text_en = _compose_side_en("black", black_id, black_modifiers)
        if red_text_en and black_text_en:
            display_name_en = f"{red_text_en} vs. {black_text_en}"
        elif red_text_en:
            display_name_en = red_text_en
        elif black_text_en:
            display_name_en = black_text_en
    elif red_text:
        template_id = template_id or ("red_only" if red_id else "descriptions")
        display_name = red_text
        certainty = "confirmed" if red_id else "pending"
        display_name_en = _compose_side_en("red", red_id, red_modifiers) or "Undecided"
    elif black_text:
        template_id = template_id or ("black_only" if black_id else "descriptions")
        display_name = black_text
        certainty = (
            "provisional"
            if memory.black.choice_path and memory.black.choice_path[-1].provisional
            else ("confirmed" if black_id else "pending")
        )
        display_name_en = _compose_side_en("black", black_id, black_modifiers) or "Undecided"
    else:
        display_name = "未定型"
        certainty = "pending"
        display_name_en = "Undecided"

    return Classification(
        display_name=display_name,
        display_name_en=display_name_en,
        certainty=certainty,
        red_main_id=red_id,
        red_main_label=red_label,
        red_modifiers=red_modifiers,
        black_main_id=black_id,
        black_main_label=black_label,
        black_modifiers=black_modifiers,
        red_system=red_id,
        black_system=black_id,
        base_matchup_id=base_id,
        template_id=template_id,
        evidence=evidence,
    )


def initial_state() -> RecognitionState:
    shapes = detect_current_shapes(START_FEN)
    memory = OpeningMemory()
    memory.fen = START_FEN
    return RecognitionState(
        fen=START_FEN,
        piece_identity=build_piece_identity(START_FEN),
        current_shapes=shapes,
        opening_memory=memory,
        classification=resolve_classification(memory, shapes),
    )


def update_recognition(
    previous: RecognitionState,
    next_fen: str,
    side: str,
    ucci: str,
) -> RecognitionState:
    memory = deepcopy(previous.opening_memory)
    memory.fen = next_fen
    if ucci:
        memory.moves.append(ucci)
    shapes = detect_current_shapes(next_fen)
    ply = previous.ply + 1
    side_moves = dict(previous.side_moves)
    side_moves[side] = side_moves.get(side, 0) + 1
    _promote_direct_choices(memory, side, shapes, ucci, ply, side_moves[side])
    _promote_shapes(memory, previous.fen, next_fen, shapes, ply, side, ucci)
    _promote_composites(memory, next_fen, shapes, ply, side)
    classification = resolve_classification(memory, shapes)
    return RecognitionState(
        ply=ply,
        fen=next_fen,
        side_moves=side_moves,
        piece_identity=dict(previous.piece_identity),
        current_shapes=shapes,
        opening_memory=memory,
        classification=classification,
    )


def memory_from_preset(preset: MemoryPreset) -> OpeningMemory:
    memory = OpeningMemory()
    for side, ids, wing in (
        ("red", preset.red_choice_path, preset.red_wing),
        ("black", preset.black_choice_path, preset.black_wing),
    ):
        side_memory = _side_memory(memory, side)
        for index, choice_id in enumerate(ids):
            _add_choice(
                side_memory,
                choice_id,
                index + 1,
                wing=wing if index == len(ids) - 1 else None,
                source="memory",
                provisional=side == "black" and choice_id == "proper_horse_opening",
            )
            if choice_id in {"central_cannon", "fly_elephant"}:
                side_memory.locks["central_square_choice"] = choice_id
    if preset.black_composite:
        _add_composite(memory.black, preset.black_composite, 1)
    return memory


def inspect_position(
    fen: str,
    preset: MemoryPreset,
    infer_from_fen: bool = True,
) -> RecognitionState:
    shapes = detect_current_shapes(fen)
    memory = memory_from_preset(preset)
    memory.fen = fen

    if infer_from_fen:
        board = parse_fen(fen)
        for side in ("red", "black"):
            side_memory = _side_memory(memory, side)
            current = set(shapes[side])
            if not side_memory.choice_path:
                if "central_cannon" in current:
                    _add_choice(side_memory, "central_cannon", 0, source="fen")
                    side_memory.locks["central_square_choice"] = "central_cannon"
                elif "fly_elephant" in current:
                    if side == "red":
                        wing = "c" if board.get("c0") != "B" else "g"
                    else:
                        wing = "c" if board.get("c9") != "b" else "g"
                    _add_choice(side_memory, "fly_elephant", 0, wing=wing, source="fen")
                    side_memory.locks["central_square_choice"] = "fly_elephant"
                elif "proper_horse_left" in current or "proper_horse_right" in current:
                    wing = "left" if "proper_horse_left" in current else "right"
                    _add_choice(
                        side_memory,
                        "proper_horse_opening",
                        0,
                        wing=wing,
                        provisional=side == "black",
                        source="fen",
                    )
                elif "angle_pawn_left" in current or "angle_pawn_right" in current:
                    wing = "left" if "angle_pawn_left" in current else "right"
                    _add_choice(side_memory, "angle_pawn", 0, wing=wing, source="fen")
                else:
                    for (piece_type, square), (choice_id, wing) in FEN_INFERENCE_MAP[side].items():
                        if board.get(square) == piece_type:
                            _add_choice(side_memory, choice_id, 0, wing=wing, source="fen")
                            if choice_id in {"central_cannon", "fly_elephant"}:
                                side_memory.locks["central_square_choice"] = choice_id
                            break

        _promote_composites(memory, fen, shapes, 0, None)
        _promote_shapes(memory, None, fen, shapes, 0, None, None)

    classification = resolve_classification(memory, shapes)
    diagnostics = list(classification.diagnostics)
    diagnostics.append("FEN 檢視模式：形成先後由 RecognitionState／memory preset 決定")
    classification.diagnostics = diagnostics
    return RecognitionState(
        fen=fen,
        piece_identity=build_piece_identity(fen),
        current_shapes=shapes,
        opening_memory=memory,
        classification=classification,
    )
# ==========================================
# English Translation Helpers and Dicts
# ==========================================
ENGLISH_CHOICE_NAMES = {
    "central_cannon": "Central Cannon",
    "fly_elephant": "Elephant Opening",
    "proper_horse_opening": "Proper Horse Opening",
    "palcorner_cannon": "Palcorner Cannon",
    "cross_palace_cannon": "Cross-Palace Cannon",
    "angle_pawn": "Angle Pawn",
    "palace_advisor_opening": "Palace Advisor",
    "edge_horse_opening": "Edge Horse",
    "edge_cannon_opening": "Edge Cannon",
    "river_cannon_opening": "Riverbank Cannon",
    "cross_river_cannon_opening": "Crossed-River Cannon",
    "pawn_bottom_cannon_opening": "Pawn Bottom Cannon",
    "golden_hook_cannon_opening": "Golden Hook Cannon",
    "edge_pawn_opening": "Edge Pawn",
    "pawn_bottom_cannon": "Pawn Bottom Cannon",
}

ENGLISH_COMPOSITE_NAMES = {
    "screen_horse": "Screen Horse Defense",
    "reverse_palace_horse": "Sandwiched Horse Defense",
    "single_horse": "Single Horse Defense",
    "left_three_step_tiger": "Left Three-Step Tiger",
    "right_three_step_tiger": "Right Three-Step Tiger",
    "left_cannon_blockade": "Left Cannon Blockade",
}

ENGLISH_SHAPE_NAMES = {
    "five_six_cannon": "Five-Six Cannon",
    "five_seven_cannon": "Five-Seven Cannon",
    "five_eight_cannon": "Five-Eight Cannon",
    "five_nine_cannon": "Five-Nine Cannon",
    "seven_route_horse": "7-Route Horse",
    "edge_horse_left": "Edge Horse (Left)",
    "edge_horse_right": "Edge Horse (Right)",
    "horizontal_rook": "Ranked Chariot",
    "straight_rook": "Filed Chariot",
    "double_horizontal_rooks": "Double Ranked Chariots",
    "river_cannon": "Riverbank Cannon",
    "river_rook": "Riverbank Chariot",
    "riding_river_rook": "Riding-River Chariot",
    "cross_river_rook": "Crossed-River Chariot",
    "slow_rook": "Deferred Chariot",
    "fly_left_elephant": "Fly Left Elephant",
    "fly_right_elephant": "Fly Right Elephant",
    "advance_three_pawn": "3rd Pawn Advancement",
    "advance_seven_pawn": "7th Pawn Advancement",
    "advance_three_soldier": "3rd Pawn Advancement",
    "advance_seven_soldier": "7th Pawn Advancement",
    "two_headed_snake": "Two-Headed Snake",
}

def _to_title_case_en(name: str) -> str:
    words = name.replace("_", " ").split(" ")
    capitalized_words = []
    for w in words:
        if w.lower() == "vs":
            capitalized_words.append("vs.")
        else:
            capitalized_words.append(w.capitalize())
    return " ".join(capitalized_words)

def _compose_side_en(side: str, side_id: str | None, modifiers: list[str]) -> str | None:
    if not side_id and not modifiers:
        return None
    base = ENGLISH_CHOICE_NAMES.get(side_id) or ENGLISH_COMPOSITE_NAMES.get(side_id) or ""
    mod_list = []
    for mod in modifiers:
        translated = ENGLISH_SHAPE_NAMES.get(mod, _to_title_case_en(mod))
        mod_list.append(translated)
    if base:
        if mod_list:
            return f"{base} with " + " and ".join(mod_list)
        return base
    else:
        return " and ".join(mod_list)
