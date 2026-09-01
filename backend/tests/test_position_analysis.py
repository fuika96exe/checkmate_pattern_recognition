from app.board import position_analysis
from app.patterns import (
    recognize_crowned_checkmate,
    recognize_cannons_sandwiching_chariot_checkmate,
    recognize_double_horses_drinking_spring_checkmate,
    recognize_double_toast_checkmate,
    recognize_eunuchs_chasing_emperor_checkmate,
    recognize_discovered_horse_checkmate,
    recognize_drawer_checkmate,
    recognize_throat_cutting_checkmate,
    recognize_tiger_silhouette_checkmate,
    recognize_two_devils_knocking_checkmate,
    recognize_three_chariots_attacking_advisor_checkmate,
    recognize_angler_horse_checkmate,
    analyze_patterns,
    recognize_double_check_checkmate,
    recognize_double_cannon_checkmate,
    recognize_double_chariots_checkmate,
    recognize_elbow_horse_checkmate,
    recognize_centroid_chariot_checkmate,
    recognize_heaven_and_earth_cannon_checkmate,
    recognize_horse_cannon_checkmate,
    recognize_iron_bolt_checkmate,
    recognize_palcorner_horse_checkmate,
    recognize_pattern,
    recognize_smothered_checkmate,
    recognize_smothered_cannon_checkmate,
    recognize_stalemate,
    recognize_white_face_general,
)


def test_start_position_is_not_checkmate() -> None:
    result = position_analysis(
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    )
    assert result["is_check"] is False
    assert result["is_checkmate"] is False
    assert result["legal_moves"]


def test_analysis_exposes_legal_moves_and_checking_pieces() -> None:
    result = position_analysis(
        "4k4/9/9/9/4R4/9/9/9/9/4K4 b - - 0 1"
    )
    assert result["side_to_move"] == "black"
    assert result["king_square"] == "e9"
    assert result["is_check"] is True
    assert result["checking_pieces"]


def test_white_face_general_requires_every_block_to_fail() -> None:
    result = recognize_white_face_general(
        "3k5/9/1r4c2/4R4/9/9/9/9/9/4K4 w - - 0 1",
        ["e6d6"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["b7d7", "g7d7"]
    assert result["detected"] is False


def test_white_face_general_accepts_forced_block_capture_when_all_blocks_lose() -> None:
    result = recognize_white_face_general(
        "3k5/9/1r7/4R4/9/9/9/9/9/4K4 w - - 0 1",
        ["e6d6"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["b7d7"]
    assert result["detected"] is True


def test_white_face_general_accepts_cannon_checkmate_with_open_central_file() -> None:
    result = recognize_white_face_general(
        "3k5/9/9/9/9/9/9/9/3NA4/3CK4 w - - 0 1",
        ["e1f2"],
    )
    assert result["analysis"]["is_check"] is True
    assert result["analysis"]["is_checkmate"] is True
    assert result["features"]["central_file_open"] is True
    assert result["features"]["checking_piece_types"] == ["C"]
    assert result["detected"] is True


def test_white_face_general_rejects_cannon_case_when_defender_can_interpose() -> None:
    result = recognize_white_face_general(
        "3k5/9/9/9/1n7/9/9/9/3NA4/3CK4 w - - 0 1",
        ["e1f2"],
    )
    assert result["analysis"]["is_check"] is True
    assert result["analysis"]["is_checkmate"] is False
    assert result["detected"] is False


def test_white_face_general_rejects_cannon_case_when_central_file_is_blocked() -> None:
    result = recognize_white_face_general(
        "3k5/9/9/9/9/9/4P4/9/3NA4/3CK4 w - - 0 1",
        ["e1f2"],
    )
    assert result["analysis"]["is_check"] is True
    assert result["features"]["central_file_open"] is False
    assert result["detected"] is False


def test_stalemate_pattern_detects_kun_bi() -> None:
    result = recognize_stalemate(
        "4k4/3R1R3/4P4/9/9/9/9/9/9/4K4 b - - 0 1"
    )
    assert result["analysis"]["is_check"] is False
    assert result["analysis"]["legal_moves"] == []
    assert result["detected"] is True


def test_old_check_bug_example_is_true_stalemate_after_fix() -> None:
    result = recognize_stalemate(
        "3k5/9/9/9/9/4R4/9/9/9/5K3 w - - 0 1",
        ["e4e8"],
    )
    assert result["analysis"]["is_check"] is False
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == []
    assert result["detected"] is True


def test_centroid_chariot_checkmate_examples() -> None:
    cases = [
        ("3k5/4R4/9/9/1N7/9/9/9/9/4K4 w - - 0 1", ["b5c7"]),
        ("3k5/4R4/2R6/9/9/9/9/9/9/4K4 w - - 0 1", ["c7c9"]),
        ("3k5/4R4/2R6/9/9/9/9/9/9/4K4 w - - 0 1", ["c7d7"]),
        ("3k1P3/4R4/9/9/9/9/9/9/9/4K4 w - - 0 1", ["f9e9"]),
        ("3k2P2/4R4/7C1/9/9/9/9/9/9/4K4 w - - 0 1", ["h7h9"]),
    ]
    for fen, moves in cases:
        result = recognize_centroid_chariot_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is True
        assert result["detected"] is True
        assert result["features"]["centroid_square"] == "e8"
        assert result["features"]["centroid_rook_present"] is True
        assert result["features"]["external_checker_count"] >= 1


def test_double_chariots_checkmate_examples() -> None:
    cases = [
        (
            "3a1k3/4a4/9/6R2/7R1/9/9/9/9/4K4 w - - 0 1",
            ["g6g9", "f9f8", "h5h8", "f8f7", "g9g7"],
        ),
        (
            "9/3k5/9/6R2/6R2/9/9/5A3/4A4/5K3 w - - 0 1",
            ["g6d6", "d8e8", "g5e5", "e8f8", "d6f6"],
        ),
    ]
    for fen, moves in cases:
        result = recognize_double_chariots_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is True
        assert result["detected"] is True
        assert result["features"]["alternating_rooks"] is True
        assert result["features"]["checking_sequence"] is True


def test_double_cannon_checkmate_examples() -> None:
    file_result = recognize_double_cannon_checkmate(
        "3aka3/9/9/9/4C4/5C3/9/9/9/3K5 w - - 0 1",
        ["f4e4"],
    )
    assert file_result["analysis"]["is_checkmate"] is True
    assert file_result["detected"] is True
    assert file_result["features"]["orientation"] == "file"

    rank_result = recognize_double_cannon_checkmate(
        "3ak3C/4a4/9/9/7C1/9/9/9/9/3K5 w - - 0 1",
        ["h5h9"],
    )
    assert rank_result["analysis"]["is_checkmate"] is True
    assert rank_result["detected"] is True
    assert rank_result["features"]["orientation"] == "rank"


def test_smothered_cannon_checkmate_examples() -> None:
    first = recognize_smothered_cannon_checkmate(
        "4ka3/4a4/9/9/9/9/9/7C1/4A4/4K4 w - - 0 1",
        ["h2h9"],
    )
    assert first["analysis"]["is_checkmate"] is True
    assert first["detected"] is True
    assert first["features"]["screen_square"] == "f9"
    assert first["features"]["screen_piece"] == "a"

    second = recognize_smothered_cannon_checkmate(
        "9/4a4/4ka3/9/9/9/9/7C1/4A4/4K4 w - - 0 1",
        ["h2h7"],
    )
    assert second["analysis"]["is_checkmate"] is True
    assert second["detected"] is True
    assert second["features"]["screen_square"] == "f7"
    assert second["features"]["screen_piece"] == "a"


def test_smothered_cannon_checkmate_rejects_escape_example() -> None:
    result = recognize_smothered_cannon_checkmate(
        "3k1a3/4a4/9/9/9/9/9/7C1/4A4/4K4 w - - 0 1",
        ["h2h9"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["d9d8"]
    assert result["detected"] is False


def test_smothered_checkmate_examples() -> None:
    rook_result = recognize_smothered_checkmate(
        "3aka3/4n4/9/3R5/9/9/9/9/9/3K5 w - - 0 1",
        ["d6d9"],
    )
    assert rook_result["analysis"]["is_checkmate"] is True
    assert rook_result["detected"] is True
    assert rook_result["features"]["checking_piece_types"] == ["R"]

    horse_result = recognize_smothered_checkmate(
        "3aka3/4n4/9/5N3/9/9/9/9/9/3K5 w - - 0 1",
        ["f6d7"],
    )
    assert horse_result["analysis"]["is_checkmate"] is True
    assert horse_result["detected"] is True
    assert horse_result["features"]["checking_piece_types"] == ["N"]

    second_horse_result = recognize_smothered_checkmate(
        "3aka3/4n4/9/5N3/9/9/9/9/9/3K5 w - - 0 1",
        ["f6g8"],
    )
    assert second_horse_result["analysis"]["is_checkmate"] is True
    assert second_horse_result["detected"] is True
    assert second_horse_result["features"]["checking_piece_types"] == ["N"]

    pawn_result = recognize_smothered_checkmate(
        "3aka3/3Pn4/2N6/9/9/9/9/9/9/3K5 w - - 0 1",
        ["d8d9"],
    )
    assert pawn_result["analysis"]["is_checkmate"] is True
    assert pawn_result["detected"] is True
    assert pawn_result["features"]["checking_piece_types"] == ["P"]


def test_smothered_checkmate_rejects_escape_example() -> None:
    result = recognize_smothered_checkmate(
        "3aka3/3Pn4/9/9/9/9/9/9/9/4K4 w - - 0 1",
        ["d8d9"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["e9d9"]
    assert result["detected"] is False


def test_iron_bolt_checkmate_examples() -> None:
    first = recognize_iron_bolt_checkmate(
        "2bak4/4a4/4b4/4CR3/9/9/9/9/9/5K3 w - - 0 1",
        ["f6f9"],
    )
    assert first["analysis"]["is_checkmate"] is True
    assert first["detected"] is True
    assert first["features"]["central_cannon_square"] == "e6"
    assert first["features"]["flank_checker_squares"] == ["f9"]

    second = recognize_iron_bolt_checkmate(
        "2bak4/4a4/4b4/4CR3/5R3/9/9/9/9/4K4 w - - 0 1",
        ["f6f9"],
    )
    assert second["analysis"]["is_checkmate"] is True
    assert second["detected"] is True
    assert second["features"]["flank_checker_squares"] == ["f9"]

    third = recognize_iron_bolt_checkmate(
        "2bak4/3Pa4/2N1b4/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["d8d9"],
    )
    assert third["analysis"]["is_checkmate"] is True
    assert third["detected"] is True
    assert third["features"]["flank_checker_squares"] == ["d9"]

    chain = recognize_iron_bolt_checkmate(
        "2bak2r1/4a4/4b4/4CR3/5R3/9/9/9/9/5K3 w - - 0 1",
        ["f6f9", "h9f9", "f5f9"],
    )
    assert chain["analysis"]["is_checkmate"] is True
    assert chain["detected"] is True
    assert chain["features"]["flank_checker_squares"] == ["f9"]

    double_exchange = recognize_iron_bolt_checkmate(
        "2bak2rr/4aP3/4b4/4CR3/5R3/9/9/9/9/5K3 w - - 0 1",
        ["f8f9", "h9f9", "f6f9", "i9f9", "f5f9"],
    )
    assert double_exchange["analysis"]["is_checkmate"] is True
    assert double_exchange["detected"] is True
    assert double_exchange["features"]["flank_checker_squares"] == ["f9"]


def test_iron_bolt_checkmate_rejects_escape_example() -> None:
    result = recognize_iron_bolt_checkmate(
        "3aka3/3Pn4/9/9/9/9/9/9/9/4K4 w - - 0 1",
        ["d8d9"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["e9d9"]
    assert result["detected"] is False


def test_heaven_and_earth_cannon_checkmate_examples() -> None:
    first = recognize_heaven_and_earth_cannon_checkmate(
        "1Cbak4/4a2R1/4b4/4C4/9/3R5/9/9/9/5K3 w - - 0 1",
        ["h8e8"],
    )
    assert first["analysis"]["is_checkmate"] is True
    assert first["detected"] is True
    assert first["features"]["final_destination"] == "e8"
    assert first["features"]["captured_piece"] == "a"

    second = recognize_heaven_and_earth_cannon_checkmate(
        "1Cbak4/4a2R1/4b4/4C4/9/3R5/9/9/9/5K3 w - - 0 1",
        ["d4d9"],
    )
    assert second["analysis"]["is_checkmate"] is True
    assert second["detected"] is True
    assert second["features"]["final_destination"] == "d9"
    assert second["features"]["captured_piece"] == "a"

    third = recognize_heaven_and_earth_cannon_checkmate(
        "1Cbak4/3Pa4/4b4/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["d8d9"],
    )
    assert third["analysis"]["is_checkmate"] is True
    assert third["detected"] is True
    assert third["features"]["final_piece_type"] == "P"

    fourth = recognize_heaven_and_earth_cannon_checkmate(
        "1Cbak4/4aP3/4b4/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["f8e8"],
    )
    assert fourth["analysis"]["is_checkmate"] is True
    assert fourth["detected"] is True
    assert fourth["features"]["final_destination"] == "e8"
    assert fourth["features"]["captured_piece"] == "a"


def test_heaven_and_earth_cannon_checkmate_rejects_iron_bolt_boundary() -> None:
    result = recognize_heaven_and_earth_cannon_checkmate(
        "1Cbak4/4aP3/4b4/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["f8f9"],
    )
    assert result["analysis"]["is_checkmate"] is True
    assert result["detected"] is False


def test_elbow_horse_checkmate_examples() -> None:
    rook_finish = recognize_elbow_horse_checkmate(
        "3aka3/9/9/7N1/9/2R6/9/9/4A4/3AK4 w - - 0 1",
        ["h6g8", "e9e8", "c4c8"],
    )
    assert rook_finish["analysis"]["is_checkmate"] is True
    assert rook_finish["detected"] is True
    assert rook_finish["features"]["elbow_square"] == "g8"
    assert rook_finish["features"]["final_piece_type"] == "R"

    chain_rook_finish = recognize_elbow_horse_checkmate(
        "3ak4/4a4/9/7N1/9/2R6/9/9/4A4/3AK4 w - - 0 1",
        ["h6g8", "e9f9", "c4f4", "e8f7", "f4f7"],
    )
    assert chain_rook_finish["analysis"]["is_checkmate"] is True
    assert chain_rook_finish["detected"] is True
    assert chain_rook_finish["features"]["forced_king_reply"] is True
    assert chain_rook_finish["features"]["final_piece_type"] == "R"

    cannon_finish = recognize_elbow_horse_checkmate(
        "3ak4/9/9/7N1/9/9/9/9/4AC3/3AK4 w - - 0 1",
        ["h6g8", "e9f9", "e1f2"],
    )
    assert cannon_finish["analysis"]["is_checkmate"] is True
    assert cannon_finish["detected"] is True
    assert cannon_finish["features"]["final_checker_types"] == ["C"]

    immediate_finish = recognize_elbow_horse_checkmate(
        "3aka3/3P5/9/7N1/9/9/9/9/4A2C1/3AK4 w - - 0 1",
        ["h6g8"],
    )
    assert immediate_finish["analysis"]["is_checkmate"] is True
    assert immediate_finish["detected"] is True
    assert immediate_finish["features"]["immediate_finish"] is True
    assert immediate_finish["features"]["final_piece_type"] == "N"

    pawn_finish = recognize_elbow_horse_checkmate(
        "4ka3/2P6/9/2N4N1/9/9/9/9/4A2C1/3AK4 w - - 0 1",
        ["h6g8", "e9d9", "c8d8"],
    )
    assert pawn_finish["analysis"]["is_checkmate"] is True
    assert pawn_finish["detected"] is True
    assert pawn_finish["features"]["final_piece_type"] == "P"


def test_palcorner_horse_checkmate_examples() -> None:
    rook_finish = recognize_palcorner_horse_checkmate(
        "2baka3/9/4b4/7N1/9/1R7/9/9/9/4K4 w - - 0 1",
        ["h6f7", "e9e8", "b4b8"],
    )
    assert rook_finish["analysis"]["is_checkmate"] is True
    assert rook_finish["detected"] is True
    assert rook_finish["features"]["palcorner_square"] == "f7"
    assert rook_finish["features"]["final_checker_types"] == ["R"]

    chain_rook_finish = recognize_palcorner_horse_checkmate(
        "2bak4/4a4/4b4/7N1/9/1R7/5R3/9/9/4K4 w - - 0 1",
        ["f3f9", "e8f9", "h6f7", "e9e8", "b4b8"],
    )
    assert chain_rook_finish["analysis"]["is_checkmate"] is True
    assert chain_rook_finish["detected"] is True
    assert chain_rook_finish["features"]["forced_king_reply"] is True
    assert chain_rook_finish["features"]["final_checker_types"] == ["R"]

    cannon_finish = recognize_palcorner_horse_checkmate(
        "2baka3/1P7/4b4/7N1/9/9/C8/9/9/4K4 w - - 0 1",
        ["h6f7", "e9e8", "a3a8"],
    )
    assert cannon_finish["analysis"]["is_checkmate"] is True
    assert cannon_finish["detected"] is True
    assert cannon_finish["features"]["final_checker_types"] == ["C"]

    immediate_double_horse = recognize_palcorner_horse_checkmate(
        "2baka3/9/2N1b4/7N1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f7"],
    )
    assert immediate_double_horse["analysis"]["is_checkmate"] is True
    assert immediate_double_horse["detected"] is True
    assert immediate_double_horse["features"]["immediate_finish"] is True
    assert immediate_double_horse["features"]["final_checker_types"] == ["N"]

    immediate_smothered = recognize_palcorner_horse_checkmate(
        "2baka3/4n4/4b4/7N1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f7"],
    )
    assert immediate_smothered["analysis"]["is_checkmate"] is True
    assert immediate_smothered["detected"] is True
    assert immediate_smothered["features"]["immediate_finish"] is True
    assert immediate_smothered["features"]["final_checker_types"] == ["N"]

    future_horse_behind_cannon = recognize_palcorner_horse_checkmate(
        "2b1ka3/5P3/4b4/1N5C1/9/9/9/9/9/4K4 w - - 0 1",
        ["b6d7", "e9d9", "h6d6"],
    )
    assert future_horse_behind_cannon["analysis"]["is_checkmate"] is True
    assert future_horse_behind_cannon["detected"] is True
    assert future_horse_behind_cannon["features"]["final_checker_types"] == ["C"]


def test_angler_horse_checkmate_examples() -> None:
    rook_finish = recognize_angler_horse_checkmate(
        "4k4/5R3/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["f8f9"],
    )
    assert rook_finish["analysis"]["is_checkmate"] is True
    assert rook_finish["detected"] is True
    assert rook_finish["features"]["angler_horse_squares"] == ["g7"]
    assert rook_finish["features"]["final_checker_types"] == ["R"]

    pawn_finish = recognize_angler_horse_checkmate(
        "4k1P2/9/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["g9f9"],
    )
    assert pawn_finish["analysis"]["is_checkmate"] is True
    assert pawn_finish["detected"] is True
    assert pawn_finish["features"]["final_checker_types"] == ["P"]

    cannon_finish = recognize_angler_horse_checkmate(
        "4k2P1/9/6N2/8C/9/9/9/9/9/3K5 w - - 0 1",
        ["i6i9"],
    )
    assert cannon_finish["analysis"]["is_checkmate"] is True
    assert cannon_finish["detected"] is True
    assert cannon_finish["features"]["final_checker_types"] == ["C"]

    dynamic_rook_file = recognize_angler_horse_checkmate(
        "5k3/9/9/1R7/7N1/9/9/9/9/3K5 w - - 0 1",
        ["h5g7", "f9e9", "b6b9"],
    )
    assert dynamic_rook_file["analysis"]["is_checkmate"] is True
    assert dynamic_rook_file["detected"] is True
    assert dynamic_rook_file["features"]["angler_move_square"] == "g7"
    assert dynamic_rook_file["features"]["forced_king_reply"] is True

    dynamic_rook_rank = recognize_angler_horse_checkmate(
        "5k3/9/9/1R7/7N1/9/9/9/9/3K5 w - - 0 1",
        ["h5g7", "f9f8", "b6f6"],
    )
    assert dynamic_rook_rank["analysis"]["is_checkmate"] is True
    assert dynamic_rook_rank["detected"] is True
    assert dynamic_rook_rank["features"]["angler_move_square"] == "g7"

    overlap_with_elbow = recognize_angler_horse_checkmate(
        "4k4/9/6N2/1N7/9/9/9/9/9/3K5 w - - 0 1",
        ["b6c8"],
    )
    assert overlap_with_elbow["analysis"]["is_checkmate"] is True
    assert overlap_with_elbow["detected"] is True
    assert overlap_with_elbow["features"]["angler_horse_squares"] == ["g7"]

    guarded_palace = recognize_angler_horse_checkmate(
        "3aka3/5R3/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["f8f9"],
    )
    assert guarded_palace["analysis"]["is_checkmate"] is True
    assert guarded_palace["detected"] is True
    assert guarded_palace["features"]["final_checker_types"] == ["R"]


def test_two_devils_knocking_checkmate_examples() -> None:
    double_rook = recognize_two_devils_knocking_checkmate(
        "4k4/2R1a2R1/9/9/9/9/9/4B4/9/4K4 w - - 0 1",
        ["c8e8", "e9f9", "h8f8"],
    )
    assert double_rook["analysis"]["is_checkmate"] is True
    assert double_rook["detected"] is True
    assert double_rook["features"]["ghost_piece_count"] == 2

    rook_pawn = recognize_two_devils_knocking_checkmate(
        "4k4/2R1aP3/9/9/9/9/9/4B4/9/4K4 w - - 0 1",
        ["f8e8", "e9d9", "c8c9"],
    )
    assert rook_pawn["analysis"]["is_checkmate"] is True
    assert rook_pawn["detected"] is True
    assert rook_pawn["features"]["starting_ghost_squares"] == ["c8", "f8"]

    double_pawn_with_cannon = recognize_two_devils_knocking_checkmate(
        "4kabC1/3PaP3/4b4/9/9/9/9/4B4/9/3K5 w - - 0 1",
        ["d8e8"],
    )
    assert double_pawn_with_cannon["analysis"]["is_checkmate"] is True
    assert double_pawn_with_cannon["detected"] is True
    assert double_pawn_with_cannon["features"]["starting_ghost_squares"] == ["d8", "f8"]
    assert double_pawn_with_cannon["features"]["cannon_restraint_squares"] == ["h9"]

    triple_pressure = recognize_two_devils_knocking_checkmate(
        "4ka3/3PaP1R1/9/9/9/9/9/9/9/3K5 w - - 0 1",
        ["d8e8", "f9e8", "f8e8", "e9f9", "h8h9"],
    )
    assert triple_pressure["analysis"]["is_checkmate"] is True
    assert triple_pressure["detected"] is False
    assert triple_pressure["features"]["starting_ghost_squares"] == ["d8", "f8", "h8"]


def test_two_devils_knocking_uses_exactly_two_main_rook_or_pawn_attackers() -> None:
    positive_cases = [
        ("4ka3/3P1P3/4b4/9/9/9/9/9/3p2p2/5K3 w - - 0 1", ["f8f9"]),
        ("4ka3/3R1R3/4b4/9/9/9/9/9/3p2p2/5K3 w - - 0 1", ["f8f9"]),
        ("4ka3/3P1R3/4b4/9/9/9/9/9/3p2p2/5K3 w - - 0 1", ["f8f9"]),
        ("4k4/3PaP3/9/9/9/9/9/9/4A4/5K3 w - - 0 1", ["f8e8"]),
        ("4kab1C/3PaP3/4b4/9/9/9/9/9/4A4/5K3 w - - 0 1", ["f8e8"]),
        (
            "4kab2/3PaP3/2N1b4/9/9/9/9/9/4A4/5K3 w - - 0 1",
            ["f8e8", "f9e8", "d8e8"],
        ),
    ]
    for fen, moves in positive_cases:
        result = recognize_two_devils_knocking_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is True
        assert result["detected"] is True
        assert result["features"]["ghost_piece_count"] == 2

    negative_cases = [
        (
            "4kab2/3PaP3/9/4R4/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "e6e8"],
        ),
        (
            "4kab2/3PaP3/9/4R4/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "d8e8", "e9d9", "e6d6"],
        ),
        (
            "4kab2/3Pa1RR1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["g8e8", "f9e8", "h8e8"],
        ),
        (
            "4kab2/3Pa1RR1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["d8e8", "e9d9", "e8d8", "d9e9", "g8e8", "f9e8", "h8e8"],
        ),
        (
            "4kab2/3PaP1R1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "h8e8"],
        ),
    ]
    for fen, moves in negative_cases:
        result = recognize_two_devils_knocking_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is True
        assert result["detected"] is False


def test_two_devils_knocking_checkmate_rejects_stalemate_finish() -> None:
    result = recognize_two_devils_knocking_checkmate(
        "4ka3/3PaP3/9/9/9/9/9/9/9/4K4 w - - 0 1",
        ["d8e8", "f9e8", "f8e8", "e9f9", "e0e1"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["is_stalemate"] is True
    assert result["detected"] is False


def test_three_chariots_attacking_advisor_checkmate_examples() -> None:
    cases = [
        (
            "4kab2/3PaP3/9/4R4/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "e6e8"],
        ),
        (
            "4kab2/3PaP3/9/4R4/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "d8e8", "e9d9", "e6d6"],
        ),
        (
            "4kab2/3Pa1RR1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["g8e8", "f9e8", "h8e8"],
        ),
        (
            "4kab2/3Pa1RR1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["d8e8", "e9d9", "e8d8", "d9e9", "g8e8", "f9e8", "h8e8"],
        ),
        (
            "4kab2/3PaP1R1/9/9/9/9/9/9/4p1p2/5K3 w - - 0 1",
            ["f8e8", "f9e8", "h8e8"],
        ),
    ]
    for fen, moves in cases:
        result = recognize_three_chariots_attacking_advisor_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is True
        assert result["detected"] is True
        assert len(result["features"]["starting_main_piece_squares"]) == 3


def test_double_toast_checkmate_examples() -> None:
    first = recognize_double_toast_checkmate(
        "2b1ka3/4a4/4b4/6C2/9/6B2/9/6C2/9/3K5 w - - 0 1",
        ["g6g9", "e7g9", "g2g9"],
    )
    assert first["analysis"]["is_checkmate"] is True
    assert first["detected"] is True
    assert first["features"]["sacrifice_square"] == "g9"
    assert first["features"]["capturing_elephant_from"] == "e7"
    assert first["features"]["reload_square"] == "g9"

    second = recognize_double_toast_checkmate(
        "4kab2/4a4/4b4/9/9/6B2/6C2/6C2/9/3K5 w - - 0 1",
        ["g3g9", "e7g9", "g2g9"],
    )
    assert second["analysis"]["is_checkmate"] is True
    assert second["detected"] is True
    assert second["features"]["sacrifice_square"] == "g9"
    assert second["features"]["capturing_elephant_from"] == "e7"
    assert second["features"]["reload_square"] == "g9"


def test_tiger_silhouette_checkmate_examples() -> None:
    immediate_finish = recognize_tiger_silhouette_checkmate(
        "3a1k3/4a4/7R1/6N2/9/9/9/9/9/4K4 w - - 0 1",
        ["h7h9"],
    )
    assert immediate_finish["analysis"]["is_checkmate"] is True
    assert immediate_finish["detected"] is True
    assert immediate_finish["features"]["tiger_horse_squares"] == ["g6"]

    file_chase = recognize_tiger_silhouette_checkmate(
        "3a5/4ak3/6R2/6N2/9/9/9/9/9/4K4 w - - 0 1",
        ["g7g8", "f8f9", "g8g9"],
    )
    assert file_chase["analysis"]["is_checkmate"] is True
    assert file_chase["detected"] is True
    assert file_chase["features"]["checking_rook_squares"] == ["g9"]

    rank_finish = recognize_tiger_silhouette_checkmate(
        "3a5/4ak3/6R2/6N2/9/9/9/9/9/4K4 w - - 0 1",
        ["g7g8", "f8f7", "g8f8"],
    )
    assert rank_finish["analysis"]["is_checkmate"] is True
    assert rank_finish["detected"] is True
    assert rank_finish["features"]["checking_rook_squares"] == ["f8"]

    delayed_horse = recognize_tiger_silhouette_checkmate(
        "3a1k3/4a4/7R1/9/9/5N3/9/9/9/4K4 w - - 0 1",
        ["h7h9", "f9f8", "f4g6", "f8f7", "h9h7"],
    )
    assert delayed_horse["analysis"]["is_checkmate"] is True
    assert delayed_horse["detected"] is True
    assert delayed_horse["features"]["tiger_horse_squares"] == ["g6"]
    assert delayed_horse["features"]["tiger_horse_move_ply"] == 3


def test_discovered_horse_checkmate_examples() -> None:
    rook_vacates_leg = recognize_discovered_horse_checkmate(
        "3a1k3/4a1R2/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["g8e8"],
    )
    assert rook_vacates_leg["analysis"]["is_checkmate"] is True
    assert rook_vacates_leg["detected"] is True
    assert rook_vacates_leg["features"]["discovered_horse_count"] == 1

    overlap_with_tiger = recognize_discovered_horse_checkmate(
        "3a2P2/4ak3/6R2/6N2/9/9/9/9/9/3K5 w - - 0 1",
        ["g7e7"],
    )
    assert overlap_with_tiger["analysis"]["is_checkmate"] is True
    assert overlap_with_tiger["detected"] is True
    assert overlap_with_tiger["features"]["final_unblocking_piece_type"] == "R"

    delayed_unblock = recognize_discovered_horse_checkmate(
        "3a2R2/4ak3/6N2/5P3/9/9/9/9/9/3K5 w - - 0 1",
        ["g9g8", "f8f9", "g8e8"],
    )
    assert delayed_unblock["analysis"]["is_checkmate"] is True
    assert delayed_unblock["detected"] is True
    assert delayed_unblock["features"]["final_unblocking_from"] == "g8"

    edge_horse = recognize_discovered_horse_checkmate(
        "3a5/4a1RN1/5k3/9/9/9/9/9/9/3K5 w - - 0 1",
        ["g8e8"],
    )
    assert edge_horse["analysis"]["is_checkmate"] is True
    assert edge_horse["detected"] is True
    assert edge_horse["features"]["discovered_horse_count"] == 1


def test_horse_cannon_checkmate_examples() -> None:
    direct_file = recognize_horse_cannon_checkmate(
        "3a1k3/9/3a1N3/7C1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f6"],
    )
    assert direct_file["analysis"]["is_checkmate"] is True
    assert direct_file["detected"] is True
    assert direct_file["features"]["final_cannon_finish"] is True
    assert direct_file["features"]["pair_count"] == 1

    direct_rank = recognize_horse_cannon_checkmate(
        "3a5/5k3/3a5/5N3/7C1/9/9/9/9/4K4 w - - 0 1",
        ["h5f5"],
    )
    assert direct_rank["analysis"]["is_checkmate"] is True
    assert direct_rank["detected"] is True
    assert direct_rank["features"]["pair_count"] == 1

    corner_finish = recognize_horse_cannon_checkmate(
        "3a5/9/3k1N3/9/7C1/9/9/9/9/4K4 w - - 0 1",
        ["h5h7"],
    )
    assert corner_finish["analysis"]["is_checkmate"] is True
    assert corner_finish["detected"] is True
    assert corner_finish["features"]["pair_count"] == 1

    screen_capture_finish = recognize_horse_cannon_checkmate(
        "3a5/9/3k5/9/3N5/2C3c2/9/9/9/4K4 w - - 0 1",
        ["c4d4"],
    )
    assert screen_capture_finish["analysis"]["is_checkmate"] is True
    assert screen_capture_finish["detected"] is True
    assert screen_capture_finish["features"]["pair_count"] == 1


def test_horse_cannon_checkmate_rejects_blockable_counterexample() -> None:
    result = recognize_horse_cannon_checkmate(
        "3a5/9/3k1N3/9/7C1/6c2/9/9/9/4K4 w - - 0 1",
        ["h5h7"],
    )
    assert result["analysis"]["is_checkmate"] is False
    assert result["analysis"]["legal_moves"] == ["g4g7"]
    assert result["detected"] is False


def test_double_check_checkmate_examples() -> None:
    horse_and_cannon = recognize_double_check_checkmate(
        "3a5/4ak3/9/5N3/5c3/5C3/9/9/9/3K5 w - - 0 1",
        ["f6h7"],
    )
    assert horse_and_cannon["analysis"]["is_checkmate"] is True
    assert horse_and_cannon["detected"] is True
    assert horse_and_cannon["features"]["checking_piece_types"] == ["C", "N"]

    chased_horse_and_cannon = recognize_double_check_checkmate(
        "3a5/4ak3/9/9/3c3N1/5C3/9/9/9/3K5 w - - 0 1",
        ["h5f6", "d5f5", "f6h7"],
    )
    assert chased_horse_and_cannon["analysis"]["is_checkmate"] is True
    assert chased_horse_and_cannon["detected"] is True
    assert chased_horse_and_cannon["features"]["checking_piece_count"] == 2

    direct_horse_and_cannon = recognize_double_check_checkmate(
        "3a5/5k3/5a3/9/9/5N3/5C3/9/9/4K4 w - - 0 1",
        ["f4g6"],
    )
    assert direct_horse_and_cannon["analysis"]["is_checkmate"] is True
    assert direct_horse_and_cannon["detected"] is True
    assert direct_horse_and_cannon["features"]["checking_piece_types"] == ["C", "N"]

    rook_and_cannon_corner = recognize_double_check_checkmate(
        "3ak3C/4aP1R1/9/9/9/9/9/9/9/3K5 w - - 0 1",
        ["h8h9", "e8f9", "h9f9"],
    )
    assert rook_and_cannon_corner["analysis"]["is_checkmate"] is True
    assert rook_and_cannon_corner["detected"] is True
    assert rook_and_cannon_corner["features"]["checking_piece_types"] == ["C", "R"]


def test_double_chariots_checkmate_accepts_immediate_finish() -> None:
    result = recognize_double_chariots_checkmate(
        "3a1k3/4a1R2/9/9/7R1/9/9/5A3/4A4/5K3 w - - 0 1",
        ["h5h9"],
    )
    assert result["analysis"]["is_checkmate"] is True
    assert result["detected"] is True
    assert result["features"]["immediate_rook_finish"] is True


def test_centroid_chariot_checkmate_rejects_defendable_counterexamples() -> None:
    cases = [
        (
            "3k5/4R4/9/9/1N7/9/9/2r1B4/4A4/4KAB2 w - - 0 1",
            ["b5c7"],
            ["c2c7"],
        ),
        (
            "3k5/4R4/9/4c3r/2pNp4/1C7/9/4B4/4A4/4KAB2 w - - 0 1",
            ["b4d4"],
            ["e6d6"],
        ),
    ]
    for fen, moves, expected_legal_moves in cases:
        result = recognize_centroid_chariot_checkmate(fen, moves)
        assert result["analysis"]["is_checkmate"] is False
        assert result["analysis"]["legal_moves"] == expected_legal_moves
        assert result["detected"] is False


def test_throat_cutting_checkmate_examples() -> None:
    direct_rook_finish = recognize_throat_cutting_checkmate(
        "2b1ka3/1R2a4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8", "f9e8", "g6g9"],
    )
    assert direct_rook_finish["analysis"]["is_checkmate"] is True
    assert direct_rook_finish["detected"] is True
    assert direct_rook_finish["features"]["penetration_piece_type"] == "R"

    chasing_finish = recognize_throat_cutting_checkmate(
        "2b1ka3/1R2a4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8", "e9d9", "e8e9", "d9d8", "g6g8", "d8d7", "e9d9"],
    )
    assert chasing_finish["analysis"]["is_checkmate"] is True
    assert chasing_finish["detected"] is True
    assert chasing_finish["features"]["final_piece_type"] == "R"

    pawn_penetration = recognize_throat_cutting_checkmate(
        "2b1ka3/3Pa4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1",
        ["d8e8", "f9e8", "g6g9"],
    )
    assert pawn_penetration["analysis"]["is_checkmate"] is True
    assert pawn_penetration["detected"] is True
    assert pawn_penetration["features"]["penetration_piece_type"] == "P"

    transfer_shape = recognize_throat_cutting_checkmate(
        "4kab1C/4aR3/2n1b4/6N2/9/5R3/9/9/9/4K4 w - - 0 1",
        ["f8e8", "e9e8", "f4f8", "e8e9", "f8f9", "e9e8", "f9f8"],
    )
    assert transfer_shape["analysis"]["is_checkmate"] is True
    assert transfer_shape["detected"] is True
    assert transfer_shape["features"]["reply_piece_type"] == "K"


def test_cannons_sandwiching_chariot_checkmate_examples() -> None:
    alternating_rook_finish = recognize_cannons_sandwiching_chariot_checkmate(
        "3k1a3/C3a4/1RC6/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b7b9", "d9d8", "c7c8", "d8d7", "b9b7"],
    )
    assert alternating_rook_finish["analysis"]["is_checkmate"] is True
    assert alternating_rook_finish["detected"] is True
    assert alternating_rook_finish["features"]["final_checker_types"] == ["R"]

    immediate_rook_finish = recognize_cannons_sandwiching_chariot_checkmate(
        "3k1a3/C1C1a4/1R7/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b7b9"],
    )
    assert immediate_rook_finish["analysis"]["is_checkmate"] is True
    assert immediate_rook_finish["detected"] is True
    assert immediate_rook_finish["features"]["flank_groups"][0]["flank"] == "left"

    cannon_finish_with_exchange = recognize_cannons_sandwiching_chariot_checkmate(
        "C4ab2/1CR1a4/2ckb4/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b8b7", "c7c6", "a9a7"],
    )
    assert cannon_finish_with_exchange["analysis"]["is_checkmate"] is True
    assert cannon_finish_with_exchange["detected"] is True
    assert cannon_finish_with_exchange["features"]["final_checker_types"] == ["C"]

    immediate_cannon_finish = recognize_cannons_sandwiching_chariot_checkmate(
        "C2k1ab2/1CR1a4/4b4/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b8b9"],
    )
    assert immediate_cannon_finish["analysis"]["is_checkmate"] is True
    assert immediate_cannon_finish["detected"] is True
    assert immediate_cannon_finish["features"]["final_checker_types"] == ["C"]

    alternating_cannon_finish = recognize_cannons_sandwiching_chariot_checkmate(
        "C2k1ab2/1CR1a4/4b4/9/9/9/9/9/9/4K4 w - - 0 1",
        ["c8c9", "d9d8", "a9a8", "d8d7", "c9c7"],
    )
    assert alternating_cannon_finish["analysis"]["is_checkmate"] is True
    assert alternating_cannon_finish["detected"] is True
    assert alternating_cannon_finish["features"]["final_checker_types"] == ["R"]


def test_drawer_checkmate_examples() -> None:
    classic_drawer = recognize_drawer_checkmate(
        "4kab1C/1R2a4/4b4/5R3/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8", "e9e8", "f6f8", "e8e9", "f8f9", "e9e8", "f9f8"],
    )
    assert classic_drawer["analysis"]["is_checkmate"] is True
    assert classic_drawer["detected"] is True
    assert classic_drawer["features"]["penetration_started"] is True

    supported_drawer = recognize_drawer_checkmate(
        "4kab1C/1R2a4/4b4/5RN2/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8", "e9e8", "f6f8", "e8e9", "f8f9", "e9e8", "f9f8"],
    )
    assert supported_drawer["analysis"]["is_checkmate"] is True
    assert supported_drawer["detected"] is True
    assert supported_drawer["features"]["home_cannon_squares"] == ["h9"]

    short_drawer = recognize_drawer_checkmate(
        "3akab1C/9/4b4/5R3/9/9/9/9/9/5K3 w - - 0 1",
        ["f6f9", "e9e8", "f9f8"],
    )
    assert short_drawer["analysis"]["is_checkmate"] is True
    assert short_drawer["detected"] is True
    assert short_drawer["features"]["penetration_started"] is False


def test_crowned_checkmate_examples() -> None:
    double_rook_crown = recognize_crowned_checkmate(
        "2bakab2/1R4R2/9/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8"],
    )
    assert double_rook_crown["analysis"]["is_checkmate"] is True
    assert double_rook_crown["detected"] is True
    assert double_rook_crown["features"]["front_piece"] == "R"

    horse_supported_crown = recognize_crowned_checkmate(
        "2bakab2/1R7/2N6/4C4/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8"],
    )
    assert horse_supported_crown["analysis"]["is_checkmate"] is True
    assert horse_supported_crown["detected"] is True
    assert horse_supported_crown["features"]["cannon_square"] == "e6"

    pawn_crown = recognize_crowned_checkmate(
        "2bakab2/1R3P3/9/4C4/9/9/9/9/9/4K4 w - - 0 1",
        ["f8e8"],
    )
    assert pawn_crown["analysis"]["is_checkmate"] is True
    assert pawn_crown["detected"] is True
    assert pawn_crown["features"]["front_piece"] == "P"


def test_double_horses_drinking_spring_checkmate_examples() -> None:
    file_finish = recognize_double_horses_drinking_spring_checkmate(
        "2bak4/4a2N1/4b4/7N1/9/9/4P4/9/9/4K4 w - - 0 1",
        ["h6g8", "e9f9", "g8e7", "f9e9", "e7c8"],
    )
    assert file_finish["analysis"]["is_checkmate"] is True
    assert file_finish["detected"] is True
    assert file_finish["features"]["final_checking_horse_squares"] == ["c8"]

    rank_finish = recognize_double_horses_drinking_spring_checkmate(
        "2bak4/4a2N1/4b4/7N1/9/9/4P4/9/9/4K4 w - - 0 1",
        ["h6g8", "e9f9", "g8e7", "f9f8", "e7g6"],
    )
    assert rank_finish["analysis"]["is_checkmate"] is True
    assert rank_finish["detected"] is True
    assert rank_finish["features"]["final_checking_horse_squares"] == ["g6"]

    side_attack = recognize_double_horses_drinking_spring_checkmate(
        "6b2/4a3c/4ka2b/9/N6N1/9/9/4p4/r4n3/3AKA3 w - - 0 1",
        ["a5c6", "e7d7", "h5f6"],
    )
    assert side_attack["analysis"]["is_checkmate"] is True
    assert side_attack["detected"] is True
    assert len(side_attack["features"]["horse_contributions"]) == 2

    overlap_double_check = recognize_double_horses_drinking_spring_checkmate(
        "Nc2ka3/1Nc1a4/4b4/9/9/5R3/9/4C4/4p1p2/3p1K3 w - - 0 1",
        ["f4f9", "b9f9", "a9c8", "e9d9", "c8e7", "d9e9", "e7g8"],
    )
    assert overlap_double_check["analysis"]["is_checkmate"] is True
    assert overlap_double_check["detected"] is True
    assert overlap_double_check["features"]["final_checking_horse_squares"] == ["g8"]


def test_eunuchs_chasing_emperor_checkmate_examples() -> None:
    rook_finish = recognize_eunuchs_chasing_emperor_checkmate(
        "2ba5/4ak3/4b4/6P2/8R/9/2pp5/4p4/4p4/p2K5 w - - 0 1",
        [
            "g6g7",
            "f8f9",
            "i5i9",
            "e7g9",
            "i9g9",
            "f9f8",
            "g9h9",
            "e8d7",
            "h9h8",
            "f8f9",
            "g7g8",
            "f9e9",
            "g8f8",
            "d9e8",
            "h8h9",
            "e8f9",
            "h9f9",
        ],
    )
    assert rook_finish["analysis"]["is_checkmate"] is True
    assert rook_finish["detected"] is True
    assert rook_finish["features"]["pawn_move_count"] >= 2
    assert rook_finish["features"]["repeated_pawn_ids"]

    pawn_finish = recognize_eunuchs_chasing_emperor_checkmate(
        "2ba5/4n4/4bk3/9/5P3/9/9/5A3/4K4/5C3 w - - 0 1",
        ["f5f6", "f7f8", "f6f7", "f8f9", "f7f8", "f9e9", "f8f9"],
    )
    assert pawn_finish["analysis"]["is_checkmate"] is True
    assert pawn_finish["detected"] is True
    assert pawn_finish["features"]["final_checking_piece_types"] == ["P"]


def test_pattern_dispatch_supports_stalemate_and_white_face_general() -> None:
    double_cannon = recognize_pattern(
        "DOUBLE_CANNON_CHECKMATE",
        "3aka3/9/9/9/4C4/5C3/9/9/9/3K5 w - - 0 1",
        ["f4e4"],
    )
    double_toast = recognize_pattern(
        "DOUBLE_TOAST_CHECKMATE",
        "2b1ka3/4a4/4b4/6C2/9/6B2/9/6C2/9/3K5 w - - 0 1",
        ["g6g9", "e7g9", "g2g9"],
    )
    smothered_cannon = recognize_pattern(
        "SMOTHERED_CANNON_CHECKMATE",
        "4ka3/4a4/9/9/9/9/9/7C1/4A4/4K4 w - - 0 1",
        ["h2h9"],
    )
    heaven_and_earth = recognize_pattern(
        "HEAVEN_AND_EARTH_CANNON_CHECKMATE",
        "1Cbak4/4a2R1/4b4/4C4/9/3R5/9/9/9/5K3 w - - 0 1",
        ["h8e8"],
    )
    drawer = recognize_pattern(
        "DRAWER_CHECKMATE",
        "4kab1C/1R2a4/4b4/5R3/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8", "e9e8", "f6f8", "e8e9", "f8f9", "e9e8", "f9f8"],
    )
    throat_cutting = recognize_pattern(
        "THROAT_CUTTING_CHECKMATE",
        "2b1ka3/1R2a4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8", "f9e8", "g6g9"],
    )
    tiger_silhouette = recognize_pattern(
        "TIGER_SILHOUETTE_CHECKMATE",
        "3a1k3/4a4/7R1/6N2/9/9/9/9/9/4K4 w - - 0 1",
        ["h7h9"],
    )
    discovered_horse = recognize_pattern(
        "DISCOVERED_HORSE_CHECKMATE",
        "3a1k3/4a1R2/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["g8e8"],
    )
    horse_cannon = recognize_pattern(
        "HORSE_CANNON_CHECKMATE",
        "3a1k3/9/3a1N3/7C1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f6"],
    )
    double_check = recognize_pattern(
        "DOUBLE_CHECK_CHECKMATE",
        "3a5/4ak3/9/5N3/5c3/5C3/9/9/9/3K5 w - - 0 1",
        ["f6h7"],
    )
    double_horses_drinking_spring = recognize_pattern(
        "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE",
        "2bak4/4a2N1/4b4/7N1/9/9/4P4/9/9/4K4 w - - 0 1",
        ["h6g8", "e9f9", "g8e7", "f9e9", "e7c8"],
    )
    two_devils = recognize_pattern(
        "TWO_DEVILS_KNOCKING_CHECKMATE",
        "4k4/2R1a2R1/9/9/9/9/9/4B4/9/4K4 w - - 0 1",
        ["c8e8", "e9f9", "h8f8"],
    )
    elbow_horse = recognize_pattern(
        "ELBOW_HORSE_CHECKMATE",
        "3aka3/9/9/7N1/9/2R6/9/9/4A4/3AK4 w - - 0 1",
        ["h6g8", "e9e8", "c4c8"],
    )
    angler_horse = recognize_pattern(
        "ANGLER_HORSE_CHECKMATE",
        "4k4/5R3/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["f8f9"],
    )
    palcorner_horse = recognize_pattern(
        "PALCORNER_HORSE_CHECKMATE",
        "2baka3/9/4b4/7N1/9/1R7/9/9/9/4K4 w - - 0 1",
        ["h6f7", "e9e8", "b4b8"],
    )
    iron_bolt = recognize_pattern(
        "IRON_BOLT_CHECKMATE",
        "2bak4/4a4/4b4/4CR3/9/9/9/9/9/5K3 w - - 0 1",
        ["f6f9"],
    )
    smothered = recognize_pattern(
        "SMOTHERED_CHECKMATE",
        "3aka3/4n4/9/3R5/9/9/9/9/9/3K5 w - - 0 1",
        ["d6d9"],
    )
    double_chariots = recognize_pattern(
        "DOUBLE_CHARIOTS_CHECKMATE",
        "3a1k3/4a4/9/6R2/7R1/9/9/9/9/4K4 w - - 0 1",
        ["g6g9", "f9f8", "h5h8", "f8f7", "g9g7"],
    )
    stalemate = recognize_pattern(
        "STALEMATE",
        "4k4/3R1R3/4P4/9/9/9/9/9/9/4K4 b - - 0 1",
    )
    centroid = recognize_pattern(
        "CENTROID_CHARIOT_CHECKMATE",
        "3k5/4R4/9/9/1N7/9/9/9/9/4K4 w - - 0 1",
        ["b5c7"],
    )
    white_face = recognize_pattern(
        "WHITE_FACE_GENERAL",
        "3k5/9/1r4c2/4R4/9/9/9/9/9/4K4 w - - 0 1",
        ["e6d6"],
    )
    cannons_sandwiching_chariot = recognize_pattern(
        "CANNONS_SANDWICHING_CHARIOT_CHECKMATE",
        "3k1a3/C1C1a4/1R7/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b7b9"],
    )
    crowned = recognize_pattern(
        "CROWNED_CHECKMATE",
        "2bakab2/1R4R2/9/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8"],
    )
    centroid_pawn = recognize_pattern(
        "CENTROID_PAWN_CHECKMATE",
        "9/9/3k1a3/R8/3P5/9/4pp3/4B4/3p2p2/5K3 w - - 0 1",
        ["d5d6", "d7d8", "a6a8", "d8d9", "d6d7", "d9e9", "d7e7", "f7e8", "e7e8", "e9d9", "a8d8"],
    )
    eunuchs_chasing_emperor = recognize_pattern(
        "EUNUCHS_CHASING_EMPEROR_CHECKMATE",
        "2ba5/4n4/4bk3/9/5P3/9/9/5A3/4K4/5C3 w - - 0 1",
        ["f5f6", "f7f8", "f6f7", "f8f9", "f7f8", "f9e9", "f8f9"],
    )
    assert double_cannon["pattern_id"] == "DOUBLE_CANNON_CHECKMATE"
    assert double_cannon["detected"] is True
    assert double_toast["pattern_id"] == "DOUBLE_TOAST_CHECKMATE"
    assert double_toast["detected"] is True
    assert smothered_cannon["pattern_id"] == "SMOTHERED_CANNON_CHECKMATE"
    assert smothered_cannon["detected"] is True
    assert heaven_and_earth["pattern_id"] == "HEAVEN_AND_EARTH_CANNON_CHECKMATE"
    assert heaven_and_earth["detected"] is True
    assert drawer["pattern_id"] == "DRAWER_CHECKMATE"
    assert drawer["detected"] is True
    assert throat_cutting["pattern_id"] == "THROAT_CUTTING_CHECKMATE"
    assert throat_cutting["detected"] is True
    assert tiger_silhouette["pattern_id"] == "TIGER_SILHOUETTE_CHECKMATE"
    assert tiger_silhouette["detected"] is True
    assert discovered_horse["pattern_id"] == "DISCOVERED_HORSE_CHECKMATE"
    assert discovered_horse["detected"] is True
    assert horse_cannon["pattern_id"] == "HORSE_CANNON_CHECKMATE"
    assert horse_cannon["detected"] is True
    assert double_check["pattern_id"] == "DOUBLE_CHECK_CHECKMATE"
    assert double_check["detected"] is True
    assert (
        double_horses_drinking_spring["pattern_id"]
        == "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE"
    )
    assert double_horses_drinking_spring["detected"] is True
    assert two_devils["pattern_id"] == "TWO_DEVILS_KNOCKING_CHECKMATE"
    assert two_devils["detected"] is True
    assert elbow_horse["pattern_id"] == "ELBOW_HORSE_CHECKMATE"
    assert elbow_horse["detected"] is True
    assert angler_horse["pattern_id"] == "ANGLER_HORSE_CHECKMATE"
    assert angler_horse["detected"] is True
    assert palcorner_horse["pattern_id"] == "PALCORNER_HORSE_CHECKMATE"
    assert palcorner_horse["detected"] is True
    assert iron_bolt["pattern_id"] == "IRON_BOLT_CHECKMATE"
    assert iron_bolt["detected"] is True
    assert smothered["pattern_id"] == "SMOTHERED_CHECKMATE"
    assert smothered["detected"] is True
    assert double_chariots["pattern_id"] == "DOUBLE_CHARIOTS_CHECKMATE"
    assert double_chariots["detected"] is True
    assert stalemate["pattern_id"] == "STALEMATE"
    assert stalemate["detected"] is True
    assert centroid["pattern_id"] == "CENTROID_CHARIOT_CHECKMATE"
    assert centroid["detected"] is True
    assert cannons_sandwiching_chariot["pattern_id"] == "CANNONS_SANDWICHING_CHARIOT_CHECKMATE"
    assert cannons_sandwiching_chariot["detected"] is True
    assert crowned["pattern_id"] == "CROWNED_CHECKMATE"
    assert crowned["detected"] is True
    assert centroid_pawn["pattern_id"] == "CENTROID_PAWN_CHECKMATE"
    assert centroid_pawn["detected"] is True
    assert eunuchs_chasing_emperor["pattern_id"] == "EUNUCHS_CHASING_EMPEROR_CHECKMATE"
    assert eunuchs_chasing_emperor["detected"] is True
    assert white_face["pattern_id"] == "WHITE_FACE_GENERAL"
    assert white_face["detected"] is False


def test_analyze_patterns_auto_detects_best_match() -> None:
    result = analyze_patterns(
        "4k4/3R1R3/4P4/9/9/9/9/9/9/4K4 b - - 0 1"
    )
    assert result["requested_pattern_id"] is None
    assert result["best_match"]["pattern_id"] == "STALEMATE"
    assert [match["pattern_id"] for match in result["matches"]] == ["STALEMATE"]


def test_analyze_patterns_auto_detects_centroid_chariot_checkmate() -> None:
    result = analyze_patterns(
        "3k5/4R4/9/9/1N7/9/9/9/9/4K4 w - - 0 1",
        ["b5c7"],
    )
    assert result["best_match"]["pattern_id"] == "CENTROID_CHARIOT_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "CENTROID_CHARIOT_CHECKMATE",
        "ANGLER_HORSE_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_crowned_before_double_chariots() -> None:
    result = analyze_patterns(
        "2bakab2/1R4R2/9/4C4/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8"],
    )
    assert result["best_match"]["pattern_id"] == "CROWNED_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "CROWNED_CHECKMATE",
        "DOUBLE_CHARIOTS_CHECKMATE",
        "CENTROID_CHARIOT_CHECKMATE",
        "DOUBLE_CHECK_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_eunuchs_chasing_emperor_before_two_devils() -> None:
    result = analyze_patterns(
        "2ba5/4ak3/4b4/6P2/8R/9/2pp5/4p4/4p4/p2K5 w - - 0 1",
        [
            "g6g7",
            "f8f9",
            "i5i9",
            "e7g9",
            "i9g9",
            "f9f8",
            "g9h9",
            "e8d7",
            "h9h8",
            "f8f9",
            "g7g8",
            "f9e9",
            "g8f8",
            "d9e8",
            "h8h9",
            "e8f9",
            "h9f9",
        ],
    )
    assert result["best_match"]["pattern_id"] == "EUNUCHS_CHASING_EMPEROR_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "EUNUCHS_CHASING_EMPEROR_CHECKMATE",
    ]


def test_analyze_patterns_keeps_centroid_pawn_as_overlap_label() -> None:
    result = analyze_patterns(
        "9/9/3k1a3/R8/3P5/9/4pp3/4B4/3p2p2/5K3 w - - 0 1",
        ["d5d6", "d7d8", "a6a8", "d8d9", "d6d7", "d9e9", "d7e7", "f7e8", "e7e8", "e9d9", "a8d8"],
    )
    assert result["best_match"]["pattern_id"] == "EUNUCHS_CHASING_EMPEROR_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "EUNUCHS_CHASING_EMPEROR_CHECKMATE",
        "CENTROID_PAWN_CHECKMATE",
        "TWO_DEVILS_KNOCKING_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_discovered_horse_before_centroid() -> None:
    result = analyze_patterns(
        "3a1k3/4a1R2/6N2/9/9/9/9/9/9/3K5 w - - 0 1",
        ["g8e8"],
    )
    assert result["best_match"]["pattern_id"] == "DISCOVERED_HORSE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DISCOVERED_HORSE_CHECKMATE",
        "CENTROID_CHARIOT_CHECKMATE",
        "ANGLER_HORSE_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_double_chariots_before_generic_patterns() -> None:
    result = analyze_patterns(
        "3a1k3/4a4/9/6R2/7R1/9/9/9/9/4K4 w - - 0 1",
        ["g6g9", "f9f8", "h5h8", "f8f7", "g9g7"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_CHARIOTS_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_CHARIOTS_CHECKMATE"
    ]


def test_analyze_patterns_auto_detects_double_cannon_checkmate() -> None:
    result = analyze_patterns(
        "3aka3/9/9/9/4C4/5C3/9/9/9/3K5 w - - 0 1",
        ["f4e4"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_CANNON_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_CANNON_CHECKMATE"
    ]


def test_analyze_patterns_auto_detects_cannons_sandwiching_chariot_before_double_cannon() -> None:
    result = analyze_patterns(
        "C2k1ab2/1CR1a4/4b4/9/9/9/9/9/9/4K4 w - - 0 1",
        ["b8b9"],
    )
    assert result["best_match"]["pattern_id"] == "CANNONS_SANDWICHING_CHARIOT_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "CANNONS_SANDWICHING_CHARIOT_CHECKMATE",
        "DOUBLE_CANNON_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_double_toast_before_smothered_cannon() -> None:
    result = analyze_patterns(
        "2b1ka3/4a4/4b4/6C2/9/6B2/9/6C2/9/3K5 w - - 0 1",
        ["g6g9", "e7g9", "g2g9"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_TOAST_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_TOAST_CHECKMATE",
        "SMOTHERED_CANNON_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_smothered_cannon_checkmate() -> None:
    result = analyze_patterns(
        "4ka3/4a4/9/9/9/9/9/7C1/4A4/4K4 w - - 0 1",
        ["h2h9"],
    )
    assert result["best_match"]["pattern_id"] == "SMOTHERED_CANNON_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "SMOTHERED_CANNON_CHECKMATE"
    ]


def test_analyze_patterns_auto_detects_smothered_checkmate() -> None:
    result = analyze_patterns(
        "3aka3/4n4/9/3R5/9/9/9/9/9/3K5 w - - 0 1",
        ["d6d9"],
    )
    assert result["best_match"]["pattern_id"] == "SMOTHERED_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "SMOTHERED_CHECKMATE"
    ]


def test_analyze_patterns_auto_detects_iron_bolt_before_generic_patterns() -> None:
    result = analyze_patterns(
        "2bak4/4a4/4b4/4CR3/5R3/9/9/9/9/4K4 w - - 0 1",
        ["f6f9"],
    )
    assert result["best_match"]["pattern_id"] == "IRON_BOLT_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "IRON_BOLT_CHECKMATE",
        "DOUBLE_CHARIOTS_CHECKMATE",
        "SMOTHERED_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_drawer_before_throat_cutting() -> None:
    result = analyze_patterns(
        "4kab1C/1R2a4/4b4/5R3/9/9/9/9/9/5K3 w - - 0 1",
        ["b8e8", "e9e8", "f6f8", "e8e9", "f8f9", "e9e8", "f9f8"],
    )
    assert result["best_match"]["pattern_id"] == "DRAWER_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DRAWER_CHECKMATE",
        "THROAT_CUTTING_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_throat_cutting_before_double_chariots() -> None:
    result = analyze_patterns(
        "2b1ka3/1R2a4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1",
        ["b8e8", "e9d9", "e8e9", "d9d8", "g6g8", "d8d7", "e9d9"],
    )
    assert result["best_match"]["pattern_id"] == "THROAT_CUTTING_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "THROAT_CUTTING_CHECKMATE",
        "DOUBLE_CHARIOTS_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_two_devils_before_double_chariots() -> None:
    result = analyze_patterns(
        "4k4/2R1a2R1/9/9/9/9/9/4B4/9/4K4 w - - 0 1",
        ["c8e8", "e9f9", "h8f8"],
    )
    assert result["best_match"]["pattern_id"] == "TWO_DEVILS_KNOCKING_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "TWO_DEVILS_KNOCKING_CHECKMATE",
        "DOUBLE_CHARIOTS_CHECKMATE",
        "CENTROID_CHARIOT_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_tiger_silhouette_before_white_face() -> None:
    result = analyze_patterns(
        "3a5/4ak3/6R2/6N2/9/9/9/9/9/4K4 w - - 0 1",
        ["g7g8", "f8f7", "g8f8"],
    )
    assert result["best_match"]["pattern_id"] == "TIGER_SILHOUETTE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "TIGER_SILHOUETTE_CHECKMATE",
        "WHITE_FACE_GENERAL",
    ]


def test_analyze_patterns_keeps_discovered_horse_with_tiger_overlap() -> None:
    result = analyze_patterns(
        "3a2P2/4ak3/6R2/6N2/9/9/9/9/9/3K5 w - - 0 1",
        ["g7e7"],
    )
    assert result["best_match"]["pattern_id"] == "DISCOVERED_HORSE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DISCOVERED_HORSE_CHECKMATE",
        "TIGER_SILHOUETTE_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_double_horses_drinking_spring() -> None:
    result = analyze_patterns(
        "2bak4/4a2N1/4b4/7N1/9/9/4P4/9/9/4K4 w - - 0 1",
        ["h6g8", "e9f9", "g8e7", "f9e9", "e7c8"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE",
    ]


def test_analyze_patterns_keeps_double_horses_drinking_spring_with_double_check() -> None:
    result = analyze_patterns(
        "Nc2ka3/1Nc1a4/4b4/9/9/5R3/9/4C4/4p1p2/3p1K3 w - - 0 1",
        ["f4f9", "b9f9", "a9c8", "e9d9", "c8e7", "d9e9", "e7g8"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE",
        "DOUBLE_CHECK_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_horse_cannon_before_white_face() -> None:
    result = analyze_patterns(
        "3a1k3/9/3a1N3/7C1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f6"],
    )
    assert result["best_match"]["pattern_id"] == "HORSE_CANNON_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "HORSE_CANNON_CHECKMATE",
        "WHITE_FACE_GENERAL",
    ]


def test_analyze_patterns_keeps_double_check_as_overlap_label() -> None:
    result = analyze_patterns(
        "3a5/4ak3/9/5N3/5c3/5C3/9/9/9/3K5 w - - 0 1",
        ["f6h7"],
    )
    assert result["best_match"]["pattern_id"] == "HORSE_CANNON_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "HORSE_CANNON_CHECKMATE",
        "DOUBLE_CHECK_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_heaven_and_earth_before_iron_bolt() -> None:
    result = analyze_patterns(
        "1Cbak4/4a2R1/4b4/4C4/9/3R5/9/9/9/5K3 w - - 0 1",
        ["d4d9"],
    )
    assert result["best_match"]["pattern_id"] == "HEAVEN_AND_EARTH_CANNON_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "HEAVEN_AND_EARTH_CANNON_CHECKMATE",
        "IRON_BOLT_CHECKMATE",
        "DOUBLE_CHARIOTS_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_elbow_horse_before_white_face() -> None:
    result = analyze_patterns(
        "3ak4/9/9/7N1/9/9/9/9/4AC3/3AK4 w - - 0 1",
        ["h6g8", "e9f9", "e1f2"],
    )
    assert result["best_match"]["pattern_id"] == "ELBOW_HORSE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "ELBOW_HORSE_CHECKMATE",
        "WHITE_FACE_GENERAL",
    ]


def test_analyze_patterns_auto_detects_palcorner_horse_before_smothered() -> None:
    result = analyze_patterns(
        "2baka3/4n4/4b4/7N1/9/9/9/9/9/4K4 w - - 0 1",
        ["h6f7"],
    )
    assert result["best_match"]["pattern_id"] == "PALCORNER_HORSE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "PALCORNER_HORSE_CHECKMATE",
        "SMOTHERED_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_angler_horse_and_keeps_overlap() -> None:
    result = analyze_patterns(
        "4k4/9/6N2/1N7/9/9/9/9/9/3K5 w - - 0 1",
        ["b6c8"],
    )
    assert result["best_match"]["pattern_id"] == "ELBOW_HORSE_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "ELBOW_HORSE_CHECKMATE",
        "ANGLER_HORSE_CHECKMATE",
    ]


def test_analyze_patterns_auto_detects_immediate_double_chariots_checkmate() -> None:
    result = analyze_patterns(
        "3a1k3/4a1R2/9/9/7R1/9/9/5A3/4A4/5K3 w - - 0 1",
        ["h5h9"],
    )
    assert result["best_match"]["pattern_id"] == "DOUBLE_CHARIOTS_CHECKMATE"
    assert [match["pattern_id"] for match in result["matches"]] == [
        "DOUBLE_CHARIOTS_CHECKMATE"
    ]


def test_analyze_patterns_can_filter_to_single_debug_pattern() -> None:
    result = analyze_patterns(
        "3k5/9/1r4c2/4R4/9/9/9/9/9/4K4 w - - 0 1",
        ["e6d6"],
        "WHITE_FACE_GENERAL",
    )
    assert result["requested_pattern_id"] == "WHITE_FACE_GENERAL"
    assert result["best_match"] is None
    assert result["matches"] == []
