from pathlib import Path

import pytest

from app.board import START_FEN
from app.main import _load_cases, _run_case
from app.models import InspectRequest, MemoryPreset, OpeningMemory, SideMemory
from app.recognizer import (
    _add_choice,
    _add_composite,
    _add_shape,
    _detect_flat_cannon_exchange,
    resolve_classification,
)
from app.service import advance, create_initial, inspect


def test_all_built_in_cases_pass() -> None:
    cases = [case for case in _load_cases() if case.source == "built_in"]
    assert len(cases) == 10
    results = [_run_case(case) for case in cases]
    assert [(item.id, item.actual_name) for item in results if not item.passed] == []


def test_cannon_move_uses_standard_chinese_notation() -> None:
    result = advance(create_initial().state, "h2e2")
    assert result.move.chinese_notation == "炮二平五"
    assert result.state.classification.display_name == "中炮"


def test_red_palace_corner_cannon_has_no_winged_main_name() -> None:
    result = advance(create_initial().state, "h2f2")
    assert result.state.classification.display_name == "仕角炮"


def test_horse_choice_can_transition_to_central_cannon() -> None:
    state = create_initial().state
    state = advance(state, "b0c2").state
    state = advance(state, "a6a5").state
    state = advance(state, "h2e2").state
    assert state.classification.display_name == "起馬轉中炮"
    assert [item.id for item in state.opening_memory.red.choice_path] == [
        "proper_horse_opening",
        "central_cannon",
    ]


def test_cross_palace_history_blocks_screen_horse() -> None:
    fen = "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    result = inspect(
        InspectRequest(
            fen=fen,
            memory_preset=MemoryPreset(
                black_choice_path=["cross_palace_cannon"]
            ),
        )
    )
    assert result.state.classification.black_system == "cross_palace_cannon"
    assert not result.state.opening_memory.black.composite_systems


def test_invalid_move_is_rejected() -> None:
    with pytest.raises(ValueError):
        advance(create_initial().state, "a0a9")


def test_same_physical_cannon_side_is_same_side_cannons() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "h7e7").state
    assert state.classification.display_name == "順炮"
    assert state.classification.base_matchup_id == "same_side_cannons"


def test_opposite_physical_cannon_sides_is_opposite_side_cannons() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "列炮"
    assert state.classification.base_matchup_id == "opposite_side_cannons"


def test_symmetric_three_seven_pawns_is_opposing_pawns() -> None:
    state = create_initial().state
    state = advance(state, "g3g4").state
    state = advance(state, "a6a5").state
    state = advance(state, "a3a4").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name == "對兵局"
    assert state.classification.base_matchup_id == "opposing_pawns"


def test_other_pawn_pair_is_not_opposing_pawns() -> None:
    state = create_initial().state
    state = advance(state, "c3c4").state
    state = advance(state, "a6a5").state
    state = advance(state, "a3a4").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name != "對兵局"


def test_red_three_and_seven_files_follow_red_notation() -> None:
    three = advance(create_initial().state, "g3g4").state
    assert "advance_three_pawn" in three.current_shapes["red"]
    assert "advance_seven_pawn" not in three.current_shapes["red"]

    seven = advance(create_initial().state, "c3c4").state
    assert "advance_seven_pawn" in seven.current_shapes["red"]
    assert "advance_three_pawn" not in seven.current_shapes["red"]


def test_red_seven_pawn_keeps_its_name_after_opening_history() -> None:
    state = create_initial().state
    for move in ("h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "b9c7", "c3c4"):
        state = advance(state, move).state

    assert "advance_seven_pawn" in state.current_shapes["red"]
    assert "advance_three_pawn" not in state.current_shapes["red"]
    assert "進七兵" in state.classification.display_name


def test_right_three_step_tiger_waits_for_rook_shift() -> None:
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "a6a5").state
    state = advance(state, "h2i2").state
    assert not state.opening_memory.red.composite_systems
    state = advance(state, "i6i5").state
    state = advance(state, "i0h0").state
    assert state.classification.red_system == "right_three_step_tiger"


def test_five_cannon_replaces_central_cannon_label() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "a6a5").state
    state = advance(state, "e2d2").state
    assert state.classification.display_name == "\u4e94\u516d\u70ae"
    assert [item.id for item in state.opening_memory.red.choice_path] == ["central_cannon"]
    assert [item.id for item in state.opening_memory.red.formed_shapes] == ["five_six_cannon"]


def test_river_cannon_requires_direct_original_file_move() -> None:
    direct = advance(create_initial().state, "h2h4").state
    assert "river_cannon" in [item.id for item in direct.opening_memory.red.formed_shapes]

    state = create_initial().state
    state = advance(state, "h2h3").state
    state = advance(state, "a6a5").state
    state = advance(state, "h3h4").state
    assert "river_cannon" not in [item.id for item in state.opening_memory.red.formed_shapes]


def test_rook_naming_uses_swapped_project_convention() -> None:
    horizontal = advance(create_initial().state, "a0a1").state
    assert "horizontal_rook" in [item.id for item in horizontal.opening_memory.red.formed_shapes]

    state = create_initial().state
    state = advance(state, "b0c2").state
    state = advance(state, "a6a5").state
    straight = advance(state, "a0b0").state
    assert "straight_rook" in [item.id for item in straight.opening_memory.red.formed_shapes]


def test_mutually_exclusive_shape_groups_keep_first_formation() -> None:
    memory = SideMemory()
    assert _add_shape(memory, "five_six_cannon", 1, lock_group="cannon_formation")
    assert not _add_shape(memory, "five_seven_cannon", 2, lock_group="cannon_formation")
    assert _add_shape(memory, "river_rook", 3, lock_group="rook_river_stage")
    assert not _add_shape(memory, "cross_river_rook", 4, lock_group="rook_river_stage")
    cannon_memory = SideMemory()
    assert _add_shape(cannon_memory, "river_cannon", 1, lock_group="cannon_formation")
    assert not _add_shape(cannon_memory, "five_nine_cannon", 2, lock_group="cannon_formation")
    suppressed = cannon_memory.formed_shapes[-1]
    assert suppressed.id == "five_nine_cannon"
    assert not suppressed.eligible_for_name
    assert suppressed.suppressed_by == "river_cannon"


def test_classification_components_drive_modifier_display() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "a6a5").state
    state = advance(state, "b2b4").state
    assert state.classification.display_name == "中炮巡河炮"
    assert state.classification.red_main_id == "central_cannon"
    assert state.classification.red_main_label == "中炮"
    assert state.classification.red_modifiers == ["river_cannon"]
    assert state.classification.template_id == "red_only"


def test_later_cannon_formation_is_evidence_only() -> None:
    state = create_initial().state
    for move in ("h2e2", "a6a5", "b2b4", "i6i5", "e2d2"):
        state = advance(state, move).state
    assert state.classification.display_name == "中炮巡河炮緩開車"
    five_six = next(
        item for item in state.opening_memory.red.formed_shapes if item.id == "five_six_cannon"
    )
    assert not five_six.eligible_for_name
    assert five_six.suppressed_by == "river_cannon"
    assert any("five_six_cannon" in item and "抑制" in item for item in state.classification.evidence)


def test_modifier_without_main_is_only_a_side_description() -> None:
    memory = OpeningMemory()
    _add_shape(memory.red, "horizontal_rook", 1, source="move")
    classification = resolve_classification(memory, {"red": [], "black": []})
    assert classification.red_main_id is None
    assert classification.red_modifiers == ["horizontal_rook"]
    assert classification.display_name == "紅方橫車"


def test_slow_rook_suppresses_same_side_rook_style_modifiers() -> None:
    memory = OpeningMemory()
    _add_choice(memory.red, "central_cannon", 1)
    _add_shape(memory.red, "slow_rook", 3, source="memory")
    _add_shape(memory.red, "straight_rook", 4, source="move")
    _add_shape(memory.red, "horizontal_rook", 5, source="move")

    classification = resolve_classification(memory, {"red": [], "black": []})

    assert classification.red_modifiers == ["slow_rook"]
    assert classification.display_name == "中炮緩開車"


def test_same_side_cannon_templates_cover_slow_and_horizontal_rook() -> None:
    slow = create_initial().state
    for move in ("h2e2", "h7e7", "h0g2", "a6a5", "i0h0", "c6c5"):
        slow = advance(slow, move).state
    assert slow.classification.display_name == "順炮直車對緩開車"
    assert slow.classification.template_id == "same_side_straight_vs_slow_rook"

    horizontal = create_initial().state
    for move in ("h2e2", "h7e7", "h0g2", "i9i8", "i0h0"):
        horizontal = advance(horizontal, move).state
    assert horizontal.classification.display_name == "順炮直車對橫車"
    assert horizontal.classification.template_id == "same_side_straight_vs_horizontal"


def test_same_side_cannon_templates_cover_horizontal_vs_straight_rook() -> None:
    state = create_initial().state
    for move in ("h2e2", "h7e7", "i0i1", "h9g7", "h0g2", "i9h9"):
        state = advance(state, move).state

    assert state.classification.display_name == "順炮橫車對直車"
    assert state.classification.template_id == "same_side_horizontal_vs_straight"


def test_delayed_opposite_cannons_requires_left_horse_then_cannon_two() -> None:
    state = create_initial().state
    for move in ("h2e2", "h9g7", "a3a4", "b7e7"):
        state = advance(state, move).state
    assert state.classification.base_matchup_id == "opposite_side_cannons"
    assert state.classification.template_id == "delayed_opposite_side_cannons_after_left_horse"
    assert state.classification.display_name == "後補列炮"

    wrong_horse = create_initial().state
    for move in ("h2e2", "a6a5", "a3a4", "b7e7"):
        wrong_horse = advance(wrong_horse, move).state
    assert wrong_horse.classification.display_name == "列炮"


def test_left_blockade_and_tiger_transitions_get_specific_templates() -> None:
    for composite_id, expected_template, expected_name in (
        (
            "left_cannon_blockade",
            "left_cannon_blockade_to_opposite_cannons",
            "中炮對左炮封車轉列炮",
        ),
        (
            "left_three_step_tiger",
            "left_three_step_tiger_to_opposite_cannons",
            "中炮對左三步虎轉列炮",
        ),
    ):
        memory = OpeningMemory()
        _add_choice(memory.red, "central_cannon", 1, origin_file="h")
        _add_choice(memory.black, "proper_horse_opening", 2, wing="left")
        _add_composite(memory.black, composite_id, 4)
        _add_choice(memory.black, "central_cannon", 6, origin_file="b")
        result = resolve_classification(memory, {"red": [], "black": []})
        assert result.template_id == expected_template
        assert result.display_name == expected_name


def test_cannon_matchup_name_survives_cannon_leaving_the_centre() -> None:
    state = create_initial().state
    for move in ("h2e2", "h7e7", "a3a4", "a6a5", "e2d2"):
        state = advance(state, move).state
    assert state.classification.base_matchup_id == "same_side_cannons"
    assert state.classification.display_name == "順炮"


def test_ecco_c2_c3_c4_templates_use_formation_components() -> None:
    c2 = OpeningMemory()
    _add_choice(c2.red, "central_cannon", 1, origin_file="h")
    _add_composite(c2.black, "screen_horse", 2)
    _add_shape(c2.red, "cross_river_rook", 3, lock_group="rook_river_stage")
    _add_shape(c2.red, "seven_route_horse", 4)
    _add_shape(c2.black, "two_headed_snake", 5)
    result = resolve_classification(c2, {"red": [], "black": []})
    assert result.display_name == "中炮過河車七路馬對屏風馬兩頭蛇"

    c3 = OpeningMemory()
    _add_choice(c3.red, "central_cannon", 1, origin_file="h")
    _add_composite(c3.black, "screen_horse", 2)
    _add_shape(c3.red, "cross_river_rook", 3, lock_group="rook_river_stage")
    _add_shape(c3.red, "advance_seven_pawn", 4)
    _add_shape(c3.black, "advance_seven_soldier", 5)
    result = resolve_classification(c3, {"red": [], "black": []})
    assert result.display_name == "中炮過河車互進七兵對屏風馬"

    _add_shape(c3.black, "flat_cannon_exchange", 6)
    result = resolve_classification(c3, {"red": [], "black": []})
    assert result.display_name == "中炮過河車互進七兵對屏風馬平炮兌車"


def test_flat_cannon_exchange_binds_the_same_black_rook_and_horse() -> None:
    before = "1r7/9/1cn6/9/9/9/9/9/1R7/9 b - - 0 1"
    after = "1r7/9/c1n6/9/9/9/9/9/1R7/9 w - - 1 2"
    black = SideMemory(facts=["right_straight_rook_move"])
    assert _detect_flat_cannon_exchange(before, after, "black", "b7a7", black)
    assert not _detect_flat_cannon_exchange(before, after, "red", "b7a7", black)


def test_angle_pawn_left_central_vs_pawn_bottom_fly_left_elephant_template() -> None:
    memory = OpeningMemory()
    _add_choice(memory.red, "angle_pawn", 1, wing="left")
    _add_choice(memory.black, "pawn_bottom_cannon", 2)
    _add_choice(memory.red, "central_cannon", 3, origin_file="b")
    _add_shape(memory.black, "fly_left_elephant", 4, source="move")
    result = resolve_classification(memory, {"red": [], "black": []})
    assert result.display_name == "仙人指路轉左中炮對卒底炮飛左象"
    assert result.template_id == "angle_pawn_to_left_central_vs_pawn_bottom_fly_left_elephant"


def test_palace_advisor_opening() -> None:
    # 1. Test Red's advisor-raising opening move (d0e1/f0e1)
    state_red_left = advance(create_initial().state, "d0e1")
    assert state_red_left.state.classification.display_name == "上士局"
    assert "palace_advisor_opening" in [c.id for c in state_red_left.state.opening_memory.red.choice_path]

    state_red_right = advance(create_initial().state, "f0e1")
    assert state_red_right.state.classification.display_name == "上士局"

    # 2. Test Black's advisor-raising opening move (d9e8/f9e8)
    state = create_initial().state
    state = advance(state, "h2e2").state # Red plays central cannon
    state = advance(state, "d9e8").state # Black plays advisor-raising move
    assert "palace_advisor_opening" in [c.id for c in state.opening_memory.black.choice_path]

    # 3. Test FEN-only inspect detection
    # Starting FEN with Red's advisor on e1
    fen_red_left = "rnbakabnr/9/9/p1p1p1p1p/9/9/P1P1P1P1P/9/9/RNBAK1BNR w - - 0 1" # A at e1 (index 5 of row 9: 'E1' is index 5 in FEN)
    # Let's construct a correct FEN with advisor on e1
    # Standard: r n b a k a b n r / 9 / 9 / p 1 p 1 p 1 p 1 p / 9 / 9 / P 1 P 1 P 1 P 1 P / 9 / 9 / R N B A K A B N R (Row 9 has R N B A K A B N R at index 0-8)
    # If left advisor moves to E1 (row 8 in FEN, index 4):
    # R N B . K A B N R -> R N B 1 K A B N R (Row 9)
    # . . . A . . . . . -> 3 A 5 (Row 8)
    # Let's test with the inspect function using a simpler FEN or just setting A at e1
    # Coordinate mapping: e1 is row 8 (0-indexed from top, so 9 - 1 = 8), column e (4).
    # Starting FEN: rnbakabnr/9/9/p1p1p1p1p/9/9/P1P1P1P1P/9/9/RNBAKABNR w
    # After d0e1: rnbakabnr/9/9/p1p1p1p1p/9/9/P1P1P1P1P/9/4A4/RNB1KABNR w
    # Let's test inspect with this FEN:
    fen_inferred = "rnbakabnr/9/9/p1p1p1p1p/9/9/P1P1P1P1P/9/4A4/RNB1KABNR w"
    result = inspect(InspectRequest(fen=fen_inferred, memory_preset=MemoryPreset()))
    assert result.state.classification.display_name == "上士局"


def test_new_batch_openings() -> None:
    # 1. Edge Horse Opening
    assert advance(create_initial().state, "h0i2").state.classification.display_name == "邊馬局"
    assert advance(create_initial().state, "b0a2").state.classification.display_name == "邊馬局"

    # 2. Edge Cannon Opening
    assert advance(create_initial().state, "h2i2").state.classification.display_name == "邊炮局"
    assert advance(create_initial().state, "b2a2").state.classification.display_name == "邊炮局"

    # 3. River Cannon Opening
    assert advance(create_initial().state, "h2h4").state.classification.display_name == "巡河炮局"
    assert advance(create_initial().state, "b2b4").state.classification.display_name == "巡河炮局"

    # 4. Cross River Cannon Opening
    assert advance(create_initial().state, "h2h6").state.classification.display_name == "過河炮局"
    assert advance(create_initial().state, "b2b6").state.classification.display_name == "過河炮局"

    # 5. Pawn Bottom Cannon Opening
    assert advance(create_initial().state, "h2g2").state.classification.display_name == "兵底炮局"
    assert advance(create_initial().state, "b2c2").state.classification.display_name == "兵底炮局"

    # 6. Golden Hooked Cannon Opening
    assert advance(create_initial().state, "h2c2").state.classification.display_name == "金鉤炮局"
    assert advance(create_initial().state, "b2g2").state.classification.display_name == "金鉤炮局"

    # 7. Edge Pawn Opening
    assert advance(create_initial().state, "i3i4").state.classification.display_name == "邊兵局"
    assert advance(create_initial().state, "a3a4").state.classification.display_name == "邊兵局"

    # 8. Fly Elephant Opening
    assert advance(create_initial().state, "g0e2").state.classification.display_name == "飛相"
    assert advance(create_initial().state, "c0e2").state.classification.display_name == "飛相"


def test_elephant_matchups() -> None:
    # 1. Red E3+5 (g0e2, right/g) + Black E7+5 (g9e7, left/g) -> 順相局
    state = create_initial().state
    state = advance(state, "g0e2").state # Red fly right相 (column g)
    state = advance(state, "g9e7").state # Black fly left象 (column g)
    assert state.classification.display_name == "順相局"
    assert state.classification.template_id == "same_direction_elephant"

    # 2. Red E7+5 (c0e2, left/c) + Black E3+5 (c9e7, right/c) -> 順相局
    state = create_initial().state
    state = advance(state, "c0e2").state # Red fly left相 (column c)
    state = advance(state, "c9e7").state # Black fly right象 (column c)
    assert state.classification.display_name == "順相局"

    # 3. Red E3+5 (g0e2, right/g) + Black E3+5 (c9e7, right/c) -> 列相局
    state = create_initial().state
    state = advance(state, "g0e2").state # Red fly right相 (column g)
    state = advance(state, "c9e7").state # Black fly right象 (column c)
    assert state.classification.display_name == "列相局"
    assert state.classification.template_id == "opposite_direction_elephant"

    # 4. FEN inference test for SDE
    # Red right 相 moved to e2 (c0 is present, g0 is empty), Black left 象 moved to e7 (c9 is present, g9 is empty)
    fen = "rnbaka1nr/9/4b4/p1p1p1p1p/9/9/P1P1P1P1P/4B4/9/RNBAKA1NR w - - 0 1"
    result = inspect(InspectRequest(fen=fen, memory_preset=MemoryPreset()))
    assert result.state.classification.display_name == "順相局"


def test_elephant_vs_horse_matchups() -> None:
    # 1. Red right 相 (g0e2, g) + Black left 馬 (h9g7, left) -> 飛相對進左馬
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "飛相對進左馬"
    assert state.classification.template_id == "elephant_vs_left_proper_horse"

    # 2. Red left 相 (c0e2, c) + Black right 馬 (b9c7, right) -> 飛相對進左馬
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b9c7").state
    assert state.classification.display_name == "飛相對進左馬"

    # 3. Red right 相 (g0e2, g) + Black right 馬 (b9c7, right) -> 飛相(其他)對進右馬
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b9c7").state
    assert state.classification.display_name == "飛相(其他)對進右馬"
    assert state.classification.template_id == "elephant_vs_right_proper_horse"

    # 4. Red left 相 (c0e2, c) + Black left 馬 (h9g7, left) -> 飛相(其他)對進右馬
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "飛相(其他)對進右馬"


def test_elephant_pawn_vs_horse_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black H2+3 (b9c7, right/c) + Red P3+1 (g3g4, g) -> 飛相進三兵對進右馬
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "g3g4").state
    assert state.classification.display_name == "飛相進三兵對進右馬"
    assert state.classification.template_id == "elephant_pawn3_vs_right_proper_horse"

    # 2. Red E7+5 (c0e2, c) + Black H8+7 (h9g7, left/g) + Red P7+1 (c3c4, c) -> 飛相進三兵對進右馬
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "飛相進三兵對進右馬"

    # 3. Red E3+5 (g0e2, g) + Black H2+3 (b9c7, right/c) + Red P7+1 (c3c4, c) -> 飛相進七兵對進右馬
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "飛相進七兵對進右馬"
    assert state.classification.template_id == "elephant_pawn7_vs_right_proper_horse"

    # 4. Red E7+5 (c0e2, c) + Black H8+7 (h9g7, left/g) + Red P3+1 (g3g4, g) -> 飛相進七兵對進右馬
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "g3g4").state
    assert state.classification.display_name == "飛相進七兵對進右馬"


def test_elephant_vs_palcorner_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C8=6 (h7f7, left/h -> g) -> 飛相對左士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7f7").state
    assert state.classification.display_name == "飛相對左士角炮"
    assert state.classification.template_id == "elephant_vs_left_palcorner_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=4 (b7d7, right/b -> c) -> 飛相對左士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7d7").state
    assert state.classification.display_name == "飛相對左士角炮"

    # 3. Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/b -> c) -> 飛相(其他)對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    assert state.classification.display_name == "飛相(其他)對右士角炮"
    assert state.classification.template_id == "elephant_vs_right_palcorner_cannon"

    # 4. Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/h -> g) -> 飛相(其他)對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    assert state.classification.display_name == "飛相(其他)對右士角炮"


def test_elephant_horse_vs_palcorner_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/c) + Red H8+7 (b0c2, left/c) -> 飛相進左馬對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    state = advance(state, "b0c2").state
    assert state.classification.display_name == "飛相進左馬對右士角炮"
    assert state.classification.template_id == "elephant_proper_horse_vs_right_palcorner_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/g) + Red H2+3 (h0g2, right/g) -> 飛相進左馬對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    state = advance(state, "h0g2").state
    assert state.classification.display_name == "飛相進左馬對右士角炮"

    # 3. Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/c) + Red H8+9 (b0a2, left/a) -> 飛相左邊馬對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    state = advance(state, "b0a2").state
    assert state.classification.display_name == "飛相左邊馬對右士角炮"
    assert state.classification.template_id == "elephant_edge_horse_vs_right_palcorner_cannon"

    # 4. Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/g) + Red H2+1 (h0i2, right/i) -> 飛相左邊馬對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    state = advance(state, "h0i2").state
    assert state.classification.display_name == "飛相左邊馬對右士角炮"


def test_elephant_pawn_rook_vs_palcorner_cannon_matchups() -> None:
    # A24: Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/c) + Red R9+1 (a0a1, left/a) -> 飛相橫車對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    state = advance(state, "a0a1").state
    assert state.classification.display_name == "飛相橫車對右士角炮"
    assert state.classification.template_id == "elephant_ranked_chariot_vs_right_palcorner_cannon"

    # A24: Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/g) + Red R1+1 (i0i1, right/i) -> 飛相橫車對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    state = advance(state, "i0i1").state
    assert state.classification.display_name == "飛相橫車對右士角炮"

    # A25: Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/c) + Red P3+1 (g3g4, g) -> 飛相進三兵對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    state = advance(state, "g3g4").state
    assert state.classification.display_name == "飛相進三兵對右士角炮"
    assert state.classification.template_id == "elephant_pawn3_vs_right_palcorner_cannon"

    # A25: Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/g) + Red P7+1 (c3c4, c) -> 飛相進三兵對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "飛相進三兵對右士角炮"

    # A26: Red E3+5 (g0e2, g) + Black C2=4 (b7d7, right/c) + Red P7+1 (c3c4, c) -> 飛相進七兵對右士角炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7d7").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "飛相進七兵對右士角炮"
    assert state.classification.template_id == "elephant_pawn7_vs_right_palcorner_cannon"

    # A26: Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/g) + Red P3+1 (g3g4, g) -> 飛相進七兵對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    state = advance(state, "g3g4").state
    assert state.classification.display_name == "飛相進七兵對右士角炮"


def test_elephant_vs_central_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C8=5 (h7e7, left/h) -> 飛相(轉其他)對左中炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7e7").state
    assert state.classification.display_name == "飛相(轉其他)對左中炮"
    assert state.classification.template_id == "elephant_vs_left_central_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=5 (b7e7, right/b) -> 飛相(轉其他)對左中炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "飛相(轉其他)對左中炮"

    # 3. Red E3+5 (g0e2, g) + Black C2=5 (b7e7, right/b) -> 飛相對右中炮 (opposite wing)
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "飛相對右中炮"
    assert state.classification.template_id == "elephant_vs_right_central_cannon"

    # Red E7+5 (c0e2, c) + Black C8=5 (h7e7, left/h) -> 飛相對右中炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7e7").state
    assert state.classification.display_name == "飛相對右中炮"

    # 4. FEN diagnostics test: Red flies right elephant, Black Left Cannon in center
    fen = "rnbakab1r/9/1c2c4/p1p1p1p1p/9/9/P1P1P1P1P/4B4/9/RNBAKA1NR w - - 0 1"
    result = inspect(InspectRequest(fen=fen, memory_preset=MemoryPreset()))
    assert result.state.classification.display_name == "飛相(轉其他)對左中炮"


def test_elephant_vs_cross_palace_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C8=4 (h7d7, left) -> 飛相(其他)對左過宮炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7d7").state
    assert state.classification.display_name == "飛相(其他)對左過宮炮"
    assert state.classification.template_id == "elephant_vs_left_cross_palace_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=6 (b7f7, right) -> 飛相(其他)對左過宮炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7f7").state
    assert state.classification.display_name == "飛相(其他)對左過宮炮"

    # 3. FEN diagnostics test: Red flies right elephant, Black Left Cannon in Cross Palace
    # Left CPC FEN: black left cannon at d7, other cannon at b7.
    # black row 3 (rank 7): column b is c, column d is c -> 1c1c5
    fen = "rnbakab1r/9/1c1c5/p1p1p1p1p/9/9/P1P1P1P1P/4B4/9/RNBAKA1NR w - - 0 1"
    result = inspect(InspectRequest(fen=fen, memory_preset=MemoryPreset()))
    assert result.state.classification.display_name == "飛相(其他)對左過宮炮"


def test_elephant_horse_vs_cross_palace_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C8=4 (h7d7, left) + Red H2+3 (h0g2, right) -> 飛相進右馬對左過宮炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7d7").state
    state = advance(state, "h0g2").state
    assert state.classification.display_name == "飛相進右馬對左過宮炮"
    assert state.classification.template_id == "elephant_right_proper_horse_vs_left_cross_palace_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=6 (b7f7, right) + Red H8+7 (b0c2, left) -> 飛相進右馬對左過宮炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7f7").state
    state = advance(state, "b0c2").state
    assert state.classification.display_name == "飛相進右馬對左過宮炮"


def test_elephant_filed_chariot_vs_cross_palace_cannon_matchups() -> None:
    # A32: Red E3+5 (g0e2) + Black C8=4 (h7d7) + Red H2+3 (h0g2) + Black H8+7 (h9g7) + Red R1=2 (i0h0) + Black P7+1 (g6g5) -> 飞相进右马对左过宫炮(红直车对黑进7卒)
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7d7").state
    state = advance(state, "h0g2").state
    state = advance(state, "h9g7").state
    state = advance(state, "i0h0").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name == "飛相進右馬對左過宮炮(紅直車對黑進7卒)"
    assert state.classification.template_id == "elephant_proper_horse_filed_chariot_vs_left_cross_palace_cannon_7pawn"

    # A33: Red same-side edge cannon -> C2=1 (h2i2) -> 飞相进右马对左过宫炮(红直车边炮)
    state = advance(state, "h2i2").state
    assert state.classification.display_name == "飛相進右馬對左過宮炮(紅直車邊炮)"
    assert state.classification.template_id == "elephant_proper_horse_filed_chariot_side_cannon_vs_left_cross_palace_cannon_7pawn"

    # A34: E7+5 (c0e2) + C2=6 (b7f7) + H8+7 (b0c2) + H2+3 (b9c7) + R9=8 (a0b0) + P3+1 (c6c5) + P3+1 (g3g4) -> 飞相进右马对左过宫炮(互进七兵)
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7f7").state
    state = advance(state, "b0c2").state
    state = advance(state, "b9c7").state
    state = advance(state, "a0b0").state
    state = advance(state, "c6c5").state
    state = advance(state, "g3g4").state
    assert state.classification.display_name == "飛相進右馬對左過宮炮(互進七兵)"
    assert state.classification.template_id == "elephant_7pawn_proper_horse_vs_left_cross_palace_cannon_7pawn"


def test_opening_matchups_a35_to_a53() -> None:
    # A35: Red E3+5 (g0e2) + Black C2=6 (b7f7, opposite wing) -> 飛相對右過宮炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "b7f7").state
    assert state.classification.display_name == "飛相對右過宮炮"
    assert state.classification.template_id == "elephant_vs_right_cross_palace_cannon"

    # A36: Red E3+5 (g0e2) + Black P7+1 (g6g5, same wing) -> 飛相(其他)對進7卒
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name == "飛相(其他)對進7卒"
    assert state.classification.template_id == "elephant_vs_same_side_pawn"

    # A37: Red E3+5 (g0e2) + Black P7+1 (g6g5) + Red H8+7 (b0c2, opposite horse) -> 飛相進左馬對進7卒
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "g6g5").state
    state = advance(state, "b0c2").state
    assert state.classification.display_name == "飛相進左馬對進7卒"
    assert state.classification.template_id == "elephant_left_proper_horse_vs_same_side_pawn"

    # A38: Red E3+5 (g0e2) + Black P7+1 (g6g5) + Red P7+1 (c3c4, opposite pawn) -> 飛相互進七兵局
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "g6g5").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "飛相互進七兵局"
    assert state.classification.template_id == "elephant_7pawn_vs_same_side_pawn"

    # A39: Red E3+5 (g0e2) + Black P3+1 (c6c5, opposite wing) -> 飛相對進3卒
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "c6c5").state
    assert state.classification.display_name == "飛相對進3卒"
    assert state.classification.template_id == "elephant_vs_opposite_side_pawn"

    # A41: Red H2+3 (h0g2) + Black P7+1 (g6g5, same side) -> 起馬對進７卒
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name == "起馬對進７卒"
    assert state.classification.template_id == "proper_horse_vs_same_side_pawn"

    # A42: Red H2+3 (h0g2) + Black P7+1 (g6g5) + Red C2=1 (h2i2, same side edge cannon) -> 起馬轉邊炮對進７卒
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "g6g5").state
    state = advance(state, "h2i2").state
    assert state.classification.display_name == "起馬轉邊炮對進７卒"
    assert state.classification.template_id == "proper_horse_side_cannon_vs_same_side_pawn"

    # A43: Red H2+3 (h0g2) + Black P7+1 (g6g5) + Red C8=6 (b2d2, opposite palcorner cannon) -> 起馬轉仕角炮對進７卒
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "g6g5").state
    state = advance(state, "b2d2").state
    assert state.classification.display_name == "起馬轉仕角炮對進７卒"
    assert state.classification.template_id == "proper_horse_palcorner_cannon_vs_same_side_pawn"

    # A44: Red H2+3 (h0g2) + Black P7+1 (g6g5) + Red C8=5 (b2e2, opposite central cannon) -> 起馬轉中炮對進７卒
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "g6g5").state
    state = advance(state, "b2e2").state
    assert state.classification.display_name == "起馬轉中炮對進７卒"
    assert state.classification.template_id == "proper_horse_central_cannon_vs_same_side_pawn"

    # A45: Red H2+3 (h0g2) + Black P7+1 (g6g5) + Red P7+1 (c3c4, opposite pawn) -> 起馬互進七兵局
    state = create_initial().state
    state = advance(state, "h0g2").state
    state = advance(state, "g6g5").state
    state = advance(state, "c3c4").state
    assert state.classification.display_name == "起馬互進七兵局"
    assert state.classification.template_id == "proper_horse_7pawn_vs_same_side_pawn"

    # A51: Red C2=4 (h2f2) + Black H8+7 (h9g7, same side proper horse) -> 仕角炮對進左馬
    state = create_initial().state
    state = advance(state, "h2f2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "仕角炮對進左馬"
    assert state.classification.template_id == "palcorner_cannon_vs_same_side_proper_horse"

    # A52: Red C2=4 (h2f2) + Black C2=5 (b7e7, opposite wing central cannon) -> 仕角炮對右中炮
    state = create_initial().state
    state = advance(state, "h2f2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "仕角炮對右中炮"
    assert state.classification.template_id == "palcorner_cannon_vs_opposite_side_central_cannon"

    # A53: Red C2=4 (h2f2) + Black C2=5 (b7e7) + Red H8+7 (b0c2) + Black H2+3 (b9c7) + Red H2+3 (h0g2) -> 仕角炮轉反宮馬對右中炮
    state = create_initial().state
    state = advance(state, "h2f2").state
    state = advance(state, "b7e7").state
    state = advance(state, "b0c2").state
    state = advance(state, "b9c7").state
    state = advance(state, "h0g2").state
    assert state.classification.display_name == "仕角炮轉反宮馬對右中炮"
    assert state.classification.template_id == "palcorner_cannon_sandwiched_horse_vs_opposite_side_central_cannon"

    # A40: Red H2+3 (h0g2) + Black plays nothing -> 起馬局
    state = create_initial().state
    state = advance(state, "h0g2").state
    assert state.classification.display_name == "起馬局"
    assert state.classification.template_id == "proper_horse_opening_base"

    # A54: Red C2=4 (h2f2) + Black P7+1 (g6g5, same side) -> 仕角炮對進７卒
    state = create_initial().state
    state = advance(state, "h2f2").state
    state = advance(state, "g6g5").state
    assert state.classification.display_name == "仕角炮對進７卒"
    assert state.classification.template_id == "palcorner_cannon_vs_same_side_pawn"

    # A60: Red C2=6 (h2d2) + Black plays nothing -> 過宮炮局
    state = create_initial().state
    state = advance(state, "h2d2").state
    assert state.classification.display_name == "過宮炮局"
    assert state.classification.template_id == "cross_palace_cannon_base"

    # A61: Red C2=6 (h2d2) + Black H8+7 (h9g7, same side proper horse) -> 過宮炮對進左馬
    state = create_initial().state
    state = advance(state, "h2d2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "過宮炮對進左馬"
    assert state.classification.template_id == "cross_palace_cannon_vs_same_side_proper_horse"

    # A62: Red C2=6 (h2d2) + Black R9+1 (i9i8, same side ranked chariot) -> 過宮炮對橫車
    state = create_initial().state
    state = advance(state, "h2d2").state
    state = advance(state, "i9i8").state
    assert state.classification.display_name == "過宮炮對橫車"
    assert state.classification.template_id == "cross_palace_cannon_vs_same_side_ranked_chariot"

    # A63: Red C2=6 (h2d2) + Black C8=5 (h7e7, same side central cannon) -> 過宮炮對左中炮
    state = create_initial().state
    state = advance(state, "h2d2").state
    state = advance(state, "h7e7").state
    assert state.classification.display_name == "過宮炮對左中炮"
    assert state.classification.template_id == "cross_palace_cannon_vs_same_side_central_cannon"

    # A65: Red C2=6 (h2d2) + Black C8=5 (h7e7) + Red H2+3 (h0g2) + Black H8+7 (h9g7) + Red R1=2 (i0h0) + Black R9+1 (i9i8) -> 過宮炮直車對左中炮橫車
    state = create_initial().state
    state = advance(state, "h2d2").state
    state = advance(state, "h7e7").state
    state = advance(state, "h0g2").state
    state = advance(state, "h9g7").state
    state = advance(state, "i0h0").state
    state = advance(state, "i9i8").state
    assert state.classification.display_name == "過宮炮直車對左中炮橫車"
    assert state.classification.template_id == "cross_palace_cannon_filed_chariot_vs_left_central_cannon_ranked_chariot"

    # A65 Symmetric: Red C8=4 (b2f2) + Black C2=5 (b7e7) + Red H8+7 (b0c2) + Black H2+3 (b9c7) + Red R9=8 (a0b0) + Black R1+1 (a9b9) -> 過宮炮直車對左中炮橫車
    state = create_initial().state
    state = advance(state, "b2f2").state
    state = advance(state, "b7e7").state
    state = advance(state, "b0c2").state
    state = advance(state, "b9c7").state
    state = advance(state, "a0b0").state
    state = advance(state, "a9a8").state
    assert state.classification.display_name == "過宮炮直車對左中炮橫車"
    assert state.classification.template_id == "cross_palace_cannon_filed_chariot_vs_left_central_cannon_ranked_chariot"

    # A65 Alternative (different order): Red C2=6 (h2d2) + Black C8=5 (h7e7) + Red H2+3 (h0g2) + Black R9+1 (i9i8) + Red R1=2 (i0h0) + Black H8+7 (h9g7) -> 過宮炮直車對左中炮橫車
    state = create_initial().state
    state = advance(state, "h2d2").state
    state = advance(state, "h7e7").state
    state = advance(state, "h0g2").state
    state = advance(state, "i9i8").state
    state = advance(state, "i0h0").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "過宮炮直車對左中炮橫車"
    assert state.classification.template_id == "cross_palace_cannon_filed_chariot_vs_left_central_cannon_ranked_chariot"

    # B00: Red C2=5 (h2e2) + Black plays a9a8 (rare move) -> 中炮局(對其他)
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "a9a8").state
    assert state.classification.display_name == "中炮局(對其他)"
    assert state.classification.template_id == "central_cannon_vs_rare_openings"

    # B01: Red C2=5 (h2e2) + Black H2+3 (b9c7, opposite side horse) -> 中炮對進右馬(其他)
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    assert state.classification.display_name == "中炮對進右馬(其他)"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse"

    # B02: Red C2=5 (h2e2) + Black H2+3 (b9c7) + Red H2+3 (h0g2) + Black P3+1 (c6c5) + Red R1=2 (i0h0) + Black A6+5 (d9e8, advisor) -> 中炮對進右馬先上士
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "h0g2").state
    state = advance(state, "c6c5").state
    state = advance(state, "i0h0").state
    state = advance(state, "d9e8").state
    assert state.classification.display_name == "中炮對進右馬先上士"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_early_advisor"

    # B03: Red C2=5 (h2e2) + Black H2+3 (b9c7) + Red H2+3 (h0g2) + Black P3+1 (c6c5) + Red R1=2 (i0h0) + Black R9+1 (i9i8, ranked chariot) -> 中炮對鴛鴦炮
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "h0g2").state
    state = advance(state, "c6c5").state
    state = advance(state, "i0h0").state
    state = advance(state, "i9i8").state
    assert state.classification.display_name == "中炮對鴛鴦炮"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_mandarin_duck_horse"

    # B04: Red C2=5 (h2e2) + Black H2+3 (b9c7) + Red H2+3 (h0g2) + Black C2=1 (b7a7, same-side edge cannon) -> 中炮對右三步虎
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "h0g2").state
    state = advance(state, "b7a7").state
    assert state.classification.display_name == "中炮對右三步虎"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_three_step_tiger"

    # B05: Red C2=5 (h2e2) + Black H8+7 (h9g7, same side horse) -> 中炮對進左馬(其他)
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "中炮對進左馬(其他)"
    assert state.classification.template_id == "central_cannon_vs_same_side_proper_horse"

    # B01 Symmetric: Red C8=5 (b2e2) + Black H8+7 (h9g7, opposite side horse) -> 中炮對進右馬(其他)
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "中炮對進右馬(其他)"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse"

    # B02 Symmetric: Red C8=5 (b2e2) + Black H8+7 (h9g7) + Red H8+7 (b0c2) + Black P7+1 (g6g5) + Red R9=8 (a0b0) + Black A4+5 (f9e8, advisor) -> 中炮對進右馬先上士
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "b0c2").state
    state = advance(state, "g6g5").state
    state = advance(state, "a0b0").state
    state = advance(state, "f9e8").state
    assert state.classification.display_name == "中炮對進右馬先上士"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_early_advisor"

    # B03 Symmetric: Red C8=5 (b2e2) + Black H8+7 (h9g7) + Red H8+7 (b0c2) + Black P7+1 (g6g5) + Red R9=8 (a0b0) + Black R1+1 (a9a8, ranked chariot) -> 中炮對鴛鴦炮
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "b0c2").state
    state = advance(state, "g6g5").state
    state = advance(state, "a0b0").state
    state = advance(state, "a9a8").state
    assert state.classification.display_name == "中炮對鴛鴦炮"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_mandarin_duck_horse"

    # B04 Symmetric: Red C8=5 (b2e2) + Black H8+7 (h9g7) + Red H8+7 (b0c2) + Black C8=9 (h7i7, same-side edge cannon) -> 中炮對右三步虎
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "b0c2").state
    state = advance(state, "h7i7").state
    assert state.classification.display_name == "中炮對右三步虎"
    assert state.classification.template_id == "central_cannon_vs_opposite_side_proper_horse_three_step_tiger"

    # B05 Symmetric: Red C8=5 (b2e2) + Black H2+3 (b9c7, same side horse) -> 中炮對進左馬(其他)
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "b9c7").state
    assert state.classification.display_name == "中炮對進左馬(其他)"
    assert state.classification.template_id == "central_cannon_vs_same_side_proper_horse"

    # B32: Red C2=5 (h2e2) + Black H2+3 (b9c7) + Red P7+1 (c3c4) + Black C8=6 (h7f7) + Red H8+7 (b0c2) -> 中炮急進左馬對反宮馬
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "c3c4").state
    state = advance(state, "h7f7").state
    state = advance(state, "b0c2").state
    assert state.classification.display_name == "中炮急進左馬對反宮馬"
    assert state.classification.template_id == "central_cannon_quick_left_proper_horse_vs_sandwiched_horse"

    # B32 Symmetric: Red C8=5 (b2e2) + Black H8+7 (h9g7) + Red P3+1 (g3g4) + Black C2=4 (b7d7) + Red H2+3 (h0g2) -> 中炮急進左馬對反宮馬
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "g3g4").state
    state = advance(state, "b7d7").state
    state = advance(state, "h0g2").state
    assert state.classification.display_name == "中炮急進左馬對反宮馬"
    assert state.classification.template_id == "central_cannon_quick_left_proper_horse_vs_sandwiched_horse"

    # B55: Red C2=5 (h2e2) + H2+3 (h0g2) + R1=2 (i0h0) + P3+1 (g3g4) + H8+9 (b0a2) + C8=7 (b2c2) + R9=8 (a0b0) + Black H2+3 (b9c7) + C8=6 (h7f7) + H8+7 (h9g7) + P3+1 (c6c5) + E7+5 (g9e7) + R1=2 (a9b9) + C2+4 (b7b3) -> 五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b9c7").state
    state = advance(state, "h0g2").state
    state = advance(state, "h7f7").state
    state = advance(state, "i0h0").state
    state = advance(state, "h9g7").state
    state = advance(state, "g3g4").state
    state = advance(state, "c6c5").state
    state = advance(state, "b0a2").state
    state = advance(state, "g9e7").state
    state = advance(state, "b2c2").state
    state = advance(state, "a9b9").state
    state = advance(state, "a0b0").state
    state = advance(state, "b7b3").state
    assert state.classification.display_name == "五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河"
    assert state.classification.template_id == "five_seven_cannon_vs_sandwiched_horse_right_ranked_cannon"

    # B56: ... + Red P7+1 (c3c4) + Black P3+1 (c5c4) + Red P3+1 (g4g5) -> 五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河
    state = advance(state, "c3c4").state
    state = advance(state, "c5c4").state
    state = advance(state, "g4g5").state
    assert state.classification.display_name == "五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河"
    assert state.classification.template_id == "five_seven_cannon_vs_sandwiched_horse_double_pawn_sacrifice"

    # B55 Symmetric: Red C8=5 (b2e2) + H8+7 (b0c2) + R9=8 (a0b0) + P7+1 (c3c4) + H2+1 (h0i2) + C2=3 (h2g2) + R1=2 (i0h0) + Black H8+7 (h9g7) + C2=4 (b7d7) + H2+3 (b9c7) + P7+1 (g6g5) + E3+5 (c9e7) + R9=8 (i9h9) + C8+4 (h7h3) -> 五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河
    state = create_initial().state
    state = advance(state, "b2e2").state
    state = advance(state, "h9g7").state
    state = advance(state, "b0c2").state
    state = advance(state, "b7d7").state
    state = advance(state, "a0b0").state
    state = advance(state, "b9c7").state
    state = advance(state, "c3c4").state
    state = advance(state, "g6g5").state
    state = advance(state, "h0i2").state
    state = advance(state, "c9e7").state
    state = advance(state, "h2g2").state
    state = advance(state, "i9h9").state
    state = advance(state, "i0h0").state
    state = advance(state, "h7h3").state
    assert state.classification.display_name == "五七炮互進三兵對反宮馬——(紅其他對)黑右炮過河"
    assert state.classification.template_id == "five_seven_cannon_vs_sandwiched_horse_right_ranked_cannon"

    # B56 Symmetric: ... + Red P3+1 (g3g4) + Black P7+1 (g5g4) + Red P7+1 (c4c5) -> 五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河
    state = advance(state, "g3g4").state
    state = advance(state, "g5g4").state
    state = advance(state, "c4c5").state
    assert state.classification.display_name == "五七炮互進三兵對反宮馬——紅棄雙兵對黑右炮過河"
    assert state.classification.template_id == "five_seven_cannon_vs_sandwiched_horse_double_pawn_sacrifice"


def test_c20_to_c49_matchups() -> None:
    # C20 Standard
    state = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "b0c2", "c6c5"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车七路马(其他)对屏风马两头蛇"
    assert state.classification.template_id == "central_cannon_pawn_ranked_chariot_7th_file_horse_vs_screen_horse_double_headed_snake"

    # C20 Symmetric
    state = create_initial().state
    for m in ["b2e2", "b9c7", "b0c2", "a9b9", "a0b0", "c6c5", "b0b6", "h9g7", "h0g2", "g6g5"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车七路马(其他)对屏风马两头蛇"

    # C21 Standard
    state = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "b0c2", "c6c5", "a0a1"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车七路马对屏风马两头蛇——红左横车(对黑其他)"

    # C22 Standard
    state_c22 = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "b0c2", "c6c5", "a0a1", "b7b6", "h6h4", "c9e7"]:
        state_c22 = advance(state_c22, m).state
    assert state_c22.classification.display_name == "中炮过河车七路马对屏风马两头蛇——红left横车(其他)对黑高右炮".replace("left", "左")

    # C23 (3rd Pawn Exchange)
    state_c23 = advance(state_c22, "g3g4").state
    assert state_c23.classification.display_name == "中炮过河车七路马对屏风马两头蛇——红左横车兑三兵对黑高右炮"

    # C24 (7th Pawn Exchange)
    state_c24 = advance(state_c22, "c3c4").state
    assert state_c24.classification.display_name == "中炮过河车七路马对屏风马两头蛇——红左横车兑七兵对黑高右炮"

    # C30 Standard
    state = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "c3c4"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车互进七兵对屏风马(其他)"

    # C31 Standard (A6+5)
    state_c31 = advance(state, "f9e8").state
    assert state_c31.classification.display_name == "中炮过河车互进七兵对屏风馬上士"

    # C32 Standard (E3+5)
    state_c32 = advance(state, "c9e7").state
    assert state_c32.classification.display_name == "中炮过河车互进七兵对屏风马飞象"

    # C33 Standard
    state_c33 = advance(state, "a9a8").state
    assert state_c33.classification.display_name == "中炮过河车互进七兵对屏风马右横车"

    # C34 Standard
    state_c34 = advance(state, "b7b3").state
    assert state_c34.classification.display_name == "中炮过河车互进七兵对屏风马右炮过河"

    # C35-C39 Left Riverbank Horse line
    state = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "c3c4", "g7f5"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车互进七兵(其他)对屏风马左马盘河"

    state = advance(state, "b0c2").state # C36
    assert state.classification.display_name == "中炮过河车互进七兵对屏风马左马盘河——红七路马(对黑其他)"

    state = advance(state, "c9e7").state # C37
    assert state.classification.display_name == "中炮过河车互进七兵对屏风马左马盘河——红七路马(其他)对黑飞右象"

    # C38
    state_c38 = advance(state, "b2b3").state
    assert state_c38.classification.display_name == "中炮过河车互进七兵对屏风马左马盘河——红七路马高左炮对黑飞右象"

    # C39
    state_c39 = advance(state, "b2a2").state
    assert state_c39.classification.display_name == "中炮过河车互进七兵对屏风马左马盘河——红七路马高左炮对黑飞右象"

    # C40-C49 Edge Cannon for Chariot Exchange line
    state = create_initial().state
    for m in ["h2e2", "h9g7", "h0g2", "i9h9", "i0h0", "g6g5", "h0h6", "b9c7", "c3c4", "h7i7"]:
        state = advance(state, m).state
    assert state.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车(其他)"

    # C41
    state_c41 = advance(state, "h6g6").state
    state_c41 = advance(state_c41, "i7i8").state
    assert state_c41.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——(红其他对)黑退边炮"

    # C42
    state_c42 = advance(state_c41, "b0c2").state
    assert state_c42.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红七路马对黑退边炮(其他)"

    # C43
    state_c43 = advance(state_c42, "d9e8").state
    assert state_c43.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红七路马(其他)对黑退边炮上右士"

    # C44
    state_c44 = advance(state_c42, "d9e8").state
    state_c44 = advance(state_c44, "c2d4").state
    assert state_c44.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红left马盘河对黑退边炮上右士".replace("left", "左")

    # C45
    state_c45 = advance(state_c41, "b2a2").state
    state_c45 = advance(state_c45, "d9e8").state
    assert state_c45.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红左边炮对黑退边炮上右士(其他)"

    # C46
    state_c46 = advance(state_c45, "a0a1").state
    state_c46 = advance(state_c46, "a9b9").state
    assert state_c46.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红left边炮对黑退边炮上右士右直车".replace("left", "左")

    # C47
    state_c47 = advance(state_c41, "b0a2").state
    assert state_c47.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红左边马对黑退边炮"

    # C48
    state_c48 = advance(state_c41, "b2d2").state
    assert state_c48.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红仕角炮对黑退边炮"

    # C49
    state_c49 = advance(state_c41, "e3e4").state
    assert state_c49.classification.display_name == "中炮过河车互进七兵对屏风马平炮兑车——红进中兵对黑退边炮"





