import pytest

from app.models import InspectRequest, MemoryPreset, OpeningMemory, SideMemory
from app.recognizer import (
    _add_choice,
    _add_composite,
    _add_shape,
    _detect_flat_cannon_exchange,
    _replace_rook_style,
    resolve_classification,
)
from app.service import advance, create_initial, inspect


def test_cannon_move_uses_standard_chinese_notation() -> None:
    result = advance(create_initial().state, "h2e2")
    assert result.move.chinese_notation == "炮二平五"
    assert result.state.classification.display_name == "中炮"


def test_advance_uses_browser_case_for_repetition_action_fields() -> None:
    result = advance(create_initial().state, "h2e2")
    action = result.state.repetition_actions[-1]
    assert action["isCheck"] is False
    assert action["chaseTargetIds"] == []
    assert "chase_target_ids" not in action


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


def test_opposite_physical_cannon_sides_is_opposite_side_cannons() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "列炮局"
    assert state.classification.base_matchup_id == "opposite_side_cannons"


@pytest.mark.parametrize(
    ("moves", "expected_template", "expected_name"),
    (
        (("h2e2", "b7e7", "a3a4", "h9i7"), "big_lie_shou_cannon", "大列手炮局"),
        (("b2e2", "h7e7", "a3a4", "b9a7"), "big_lie_shou_cannon", "大列手炮局"),
        (("h2e2", "b7e7", "a3a4", "h9g7"), "small_lie_shou_cannon", "小列手炮局"),
        (("b2e2", "h7e7", "a3a4", "b9c7"), "small_lie_shou_cannon", "小列手炮局"),
    ),
)
def test_lie_shou_cannon_horse_variants_and_mirrors(
    moves: tuple[str, ...], expected_template: str, expected_name: str,
) -> None:
    state = create_initial().state
    for move in moves:
        state = advance(state, move).state
    assert state.classification.template_id == expected_template
    assert state.classification.display_name == expected_name


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


def test_two_headed_snake_replaces_individual_pawn_names() -> None:
    state = create_initial().state
    for move in ("h2e2", "a6a5", "g3g4", "a5a4", "c3c4"):
        state = advance(state, move).state

    assert "two_headed_snake" in state.current_shapes["red"]
    assert state.classification.red_modifiers == ["two_headed_snake"]
    assert "進三兵" not in state.classification.display_name
    assert "進七兵" not in state.classification.display_name


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


def test_same_rook_replaces_its_earlier_style_with_its_latest_style() -> None:
    memory = SideMemory()
    _replace_rook_style(
        memory, "straight_rook", 1, wing="right", source_piece_id="r:2"
    )
    _replace_rook_style(
        memory, "cross_river_rook", 2, wing="right", source_piece_id="r:2"
    )

    assert [(item.id, item.source_piece_id) for item in memory.formed_shapes] == [
        ("cross_river_rook", "r:2")
    ]


def test_screen_horse_family_hides_straight_rook_modifier() -> None:
    memory = OpeningMemory()
    _add_choice(memory.red, "central_cannon", 1)
    _add_composite(memory.black, "screen_horse", 2)
    _add_shape(memory.black, "straight_rook", 3, wing="right", source="move")
    _add_shape(memory.black, "slow_rook", 4, source="memory")

    classification = resolve_classification(memory, {"red": [], "black": []})

    assert classification.display_name == "中炮對屏風馬"
    assert classification.black_modifiers == []


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


def test_initial_same_side_cannons_are_named_shun_pao_not_slow_rook() -> None:
    state = create_initial().state
    state = advance(state, "h2e2").state
    state = advance(state, "h7e7").state

    assert state.classification.display_name == "顺炮局"


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
    assert state.classification.display_name == "飛相對進右馬"
    assert state.classification.template_id == "elephant_vs_right_proper_horse"

    # 4. Red left 相 (c0e2, c) + Black left 馬 (h9g7, left) -> 飛相(其他)對進右馬
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h9g7").state
    assert state.classification.display_name == "飛相對進右馬"


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
    assert state.classification.display_name == "飛相對右士角炮"
    assert state.classification.template_id == "elephant_vs_right_palcorner_cannon"

    # 4. Red E7+5 (c0e2, c) + Black C8=6 (h7f7, left/h -> g) -> 飛相(其他)對右士角炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "h7f7").state
    assert state.classification.display_name == "飛相對右士角炮"


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
    assert state.classification.display_name == "飛相對左中炮"
    assert state.classification.template_id == "elephant_vs_left_central_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=5 (b7e7, right/b) -> 飛相(轉其他)對左中炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7e7").state
    assert state.classification.display_name == "飛相對左中炮"

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
    assert result.state.classification.display_name == "飛相對左中炮"


def test_elephant_vs_cross_palace_cannon_matchups() -> None:
    # 1. Red E3+5 (g0e2, g) + Black C8=4 (h7d7, left) -> 飛相(其他)對左過宮炮
    state = create_initial().state
    state = advance(state, "g0e2").state
    state = advance(state, "h7d7").state
    assert state.classification.display_name == "飛相對左過宮炮"
    assert state.classification.template_id == "elephant_vs_left_cross_palace_cannon"

    # 2. Red E7+5 (c0e2, c) + Black C2=6 (b7f7, right) -> 飛相(其他)對左過宮炮
    state = create_initial().state
    state = advance(state, "c0e2").state
    state = advance(state, "b7f7").state
    assert state.classification.display_name == "飛相對左過宮炮"

    # 3. FEN diagnostics test: Red flies right elephant, Black Left Cannon in Cross Palace
    # Left CPC FEN: black left cannon at d7, other cannon at b7.
    # black row 3 (rank 7): column b is c, column d is c -> 1c1c5
    fen = "rnbakab1r/9/1c1c5/p1p1p1p1p/9/9/P1P1P1P1P/4B4/9/RNBAKA1NR w - - 0 1"
    result = inspect(InspectRequest(fen=fen, memory_preset=MemoryPreset()))
    assert result.state.classification.display_name == "飛相對左過宮炮"


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


