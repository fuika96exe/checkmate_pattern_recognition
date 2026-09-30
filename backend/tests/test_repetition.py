from backend.app.board import apply_move, build_piece_identity
from backend.app.repetition import adjudicate, classify_cycle, forced_rook_pins, position_key


def _positions(count: int) -> list[dict]:
    return [
        {"ply": ply * 4, "key": "same-position w"}
        for ply in range(count)
    ]


def _actions(red: list[dict], black: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for index, (red_action, black_action) in enumerate(zip(red, black)):
        actions.append({"ply": index * 4 + 1, "side": "red", **red_action})
        actions.append({"ply": index * 4 + 2, "side": "black", **black_action})
        actions.append({"ply": index * 4 + 3, "side": "red", **red_action})
        actions.append({"ply": index * 4 + 4, "side": "black", **black_action})
    return actions


IDLE = {"is_check": False, "chase_target_ids": []}
CHECK = {"is_check": True, "chase_target_ids": ["n:1"]}


def test_position_key_ignores_fen_clocks_but_keeps_side_to_move() -> None:
    board = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"
    assert position_key(f"{board} w - - 0 1") == position_key(f"{board} w - - 38 19")
    assert position_key(f"{board} w - - 0 1") != position_key(f"{board} b - - 0 1")


def test_third_occurrence_blocks_only_higher_ranked_check_side() -> None:
    decision = adjudicate(_positions(3), _actions([IDLE, CHECK], [IDLE, IDLE]))
    assert decision["status"] == "must_change"
    assert decision["restricted_side"] == "red"
    assert decision["occurrence_count"] == 3


def test_chase_tracks_a_moving_piece_by_identity_not_square() -> None:
    actions = [
        {"ply": 1, "side": "red", "is_check": False, "chase_target_ids": ["black-horse:1"]},
        {"ply": 2, "side": "black", **IDLE},
        {"ply": 3, "side": "red", "is_check": False, "chase_target_ids": ["black-horse:1", "black-rook:1"]},
        {"ply": 4, "side": "black", **IDLE},
    ]
    cycle = classify_cycle(actions, 0, 4)
    assert cycle.red == "chase"


def test_alternating_chase_victims_is_idle() -> None:
    actions = [
        {"ply": 1, "side": "red", "is_check": False, "chase_target_ids": ["black-horse:1"]},
        {"ply": 2, "side": "black", **IDLE},
        {"ply": 3, "side": "red", "is_check": False, "chase_target_ids": ["black-rook:1"]},
        {"ply": 4, "side": "black", **IDLE},
    ]
    assert classify_cycle(actions, 0, 4).red == "idle"


def test_equal_behaviour_warns_on_third_and_draws_on_fourth_occurrence() -> None:
    actions = _actions([IDLE, IDLE, IDLE], [IDLE, IDLE, IDLE])
    assert adjudicate(_positions(3), actions)["status"] == "warning"
    assert adjudicate(_positions(4), actions)["status"] == "draw"


def test_pinned_rook_chase_outranks_an_ordinary_chase() -> None:
    pinned = {"is_check": False, "chase_target_ids": ["black-rook:1"], "pinned_rook_chase_target_ids": ["black-rook:1"]}
    ordinary = {"is_check": False, "chase_target_ids": ["red-rook:1"]}
    decision = adjudicate(_positions(3), _actions([pinned, pinned], [ordinary, ordinary]))
    assert decision["status"] == "must_change"
    assert decision["restricted_side"] == "red"


def test_wocao_horse_pin_requires_the_rook_to_be_its_only_capture() -> None:
    # Red N on g8 attacks the black general on e9 through f8.  The black
    # rook on f8 cannot leave that horse-leg square; its only legal rook move
    # is to capture the red horse on g8.
    start = "2baka3/C4rN2/4b1n2/1Rp5p/6p2/2P6/4c1P1c/4B3C/4A4/4KAB2 w - - 0 1"
    after_red_rook_move = apply_move(start, "b6b8")
    identities = build_piece_identity(after_red_rook_move)
    pins = forced_rook_pins(after_red_rook_move, identities, "red")
    assert pins == {identities["f8"]: identities["g8"]}
