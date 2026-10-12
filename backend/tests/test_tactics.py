from backend.app.tactics import _absolute_pins, _capture_material_loss, _escape_material_loss, _is_protected, _piece_protects, _pins, _sacrifice_eligible, analyze_tactics
from backend.app.board import START_FEN, parse_fen


def _labels(fen: str, move: str) -> set[str]:
    annotation = analyze_tactics(fen, [move])[0]
    return {item["id"] for item in annotation["occurrences"]}


def test_sacrificial_interception_is_not_a_durable_block() -> None:
    # h9-h5 enters the rook file but the blocker can be safely captured.
    fen = "4k2r1/4a4/9/9/9/9/9/9/9/4K2R1 b - - 0 1"
    labels = _labels(fen, "h9h5")
    assert "sacrifice" in labels
    assert "block" not in labels


def test_seal_marks_an_existing_rook_blocker_moving_closer() -> None:
    fen = "4k4/4a4/7c1/9/9/9/9/9/9/4K2R1 b - - 0 1"
    labels = _labels(fen, "h7h3")
    assert "seal" in labels
    assert "block" not in labels


def test_protected_piece_leaving_an_attack_is_not_an_escape() -> None:
    # Red's b2 cannon attacks the b9 horse through the b7 cannon, but Black's
    # rook on a9 can legally recapture on b9.  b9c7 is therefore not an
    # escape; any pre-existing protection is not relabelled as a new protect.
    fen = "rnbakabr1/9/1c4nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/9/RNBAKABR1 b - - 5 3"
    labels = _labels(fen, "b9c7")
    assert "escape" not in labels


def test_capturing_the_attacker_is_not_an_escape() -> None:
    fen = "1rbaka1r1/9/2R1b1n2/p1p5p/4p1p2/1NP6/P5PcP/BC2CcN2/9/3AKABR1 b - - 1 13"
    assert "escape" not in _labels(fen, "f2b2")


def test_existing_pin_relationship_is_not_repeated_when_pinner_moves_on_line() -> None:
    fen = "2rakabnr/3n5/1c2b2c1/p2Pp1p1p/9/9/P3P1P1P/NC5C1/9/R1BAKABNR b - - 6 5"
    assert "pin" not in _labels(fen, "c9c1")


def test_pin_ignores_pawn_elephant_and_advisor_material() -> None:
    # A rook faces a pawn and horse on one file.  Since the pawn is not one of
    # 车、马、炮, this must not create a 牵制 relation.
    board = parse_fen("4k4/n8/9/9/p8/9/9/9/R8/4K4 w - - 0 1")
    assert _pins(board, "red") == set()

    # Replacing the pawn with a cannon makes all three involved pieces
    # rook/cannon/horse, so the same geometry is eligible.
    major_only_board = parse_fen("4k4/n8/9/9/c8/9/9/9/R8/4K4 w - - 0 1")
    assert ("a1", "a5", "a8") in _pins(major_only_board, "red")


def test_absolute_pin_allows_any_blocker_in_front_of_the_general() -> None:
    # The black cannon e7 is pinned to its general by the red rook e6. It is
    # an absolute pin even though the general (and its advisors/elephants) are
    # not ordinary 车、马、炮 material.
    rook_pin = parse_fen("2bakab2/9/4c4/4R4/9/9/9/9/9/4K4 w - - 0 1")
    assert ("e6", "e7", "e9") in _absolute_pins(rook_pin, "red")

    # A cannon can also absolutely pin: e7 is its screen, and moving the
    # horse e8 would leave exactly one screen to the black general e9.
    cannon_pin = parse_fen("4k4/4n4/4p4/4C4/9/9/9/9/9/4K4 w - - 0 1")
    assert ("e6", "e8", "e9") in _absolute_pins(cannon_pin, "red")


def test_advisor_pressure_is_not_a_direct_escape_threat() -> None:
    fen = "3akabnr/3n5/1c2b2c1/p2Pp1p1p/9/9/P3P1P1P/NC4NC1/2r6/R1BAKAB1R b - - 8 6"
    assert "escape" not in _labels(fen, "c1c4")


def test_effective_attack_can_trigger_escape_from_an_imported_fen() -> None:
    fen = "3akabnr/3n5/1c2b2c1/p2Pp1p1p/9/2r6/P3P1P1P/NC2B1NC1/9/R1BAKA2R b - - 10 7"
    assert "escape" in _labels(fen, "c4d4")


def test_escape_requires_the_immediately_prior_move_to_create_the_chase() -> None:
    # b5-a5 opens the b2 cannon's attack on the black rook b9 through b7.
    # Only the immediately following b9-c9, which takes that rook away from
    # the newly created losing chase, is an escape.
    fen = "1r1k5/9/1p7/9/1R7/9/9/1C7/9/4K4 w - - 0 1"
    annotations = analyze_tactics(fen, ["b5a5", "b9c9"])
    assert "escape" not in {item["id"] for item in annotations[0]["occurrences"]}
    assert "escape" in {item["id"] for item in annotations[1]["occurrences"]}


def test_mutually_attacking_rooks_do_not_create_an_escape() -> None:
    # h7-i7 opens Black's h9 rook line to Red's h6 rook, but Red can play
    # h6xh9 immediately.  The contact is a mutual trade, so h6-g6 is not 逃.
    fen = "r1bakabr1/9/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2 b - - 9 5"
    annotations = analyze_tactics(fen, ["h7i7", "h6g6"])
    assert "escape" not in {item["id"] for item in annotations[1]["occurrences"]}


def test_elephant_leaving_a_cannon_attack_is_an_escape() -> None:
    fen = "r1bakabr1/9/2n3n2/p1p1p3p/6p2/2P6/P1c1P1PcP/1CN1C1N2/R8/2BAKABR1 w - - 0 1"
    assert "escape" in _labels(fen, "c0a2")


def test_existing_trap_is_not_repeated_by_a_later_chase() -> None:
    fen = "3akabnr/3n5/1c2b2c1/p2Pp1p1p/9/2r6/P3P1P1P/NC2B1NC1/9/R1BAKA2R b - - 10 7"
    # The crossed red pawn on d6 has no safe continuation both before and
    # after c4d4, so the rook's chase must not create a duplicate trap label.
    assert "trap" not in _labels(fen, "c4d4")


def test_moving_a_horse_leg_blocker_can_create_protection() -> None:
    fen = "rnbakab1r/9/1c5cn/p1p1p1p1p/9/9/P1P1P1P1P/1CN3C2/9/R1BAKABNR b - - 3 2"
    occurrences = analyze_tactics(fen, ["h7f7"])[0]["occurrences"]
    assert any(item["id"] == "protect" and item["squares"] == ["f7", "g6", "i7"] for item in occurrences)


def test_losing_exchange_can_trigger_escape_even_with_recapture() -> None:
    fen = "3rkabr1/4a4/1cn1bc2n/p3p1p1p/2p6/1CP4NP/P3P1P2/2N1B2C1/9/R2AKAB1R b - - 17 9"
    assert "escape" in _labels(fen, "h9i9")


def test_rook_for_cannon_exchange_remains_a_five_point_loss_after_recapture() -> None:
    board = parse_fen("3rkabr1/4a4/1cn1bc2n/p3p1p1p/2p6/1CP4NP/P3P1P2/2N1B2C1/9/R2AKAB1R b - - 17 9")
    assert _capture_material_loss(board, "h9", "black", "h2") == 5


def test_existing_enemy_rook_moving_closer_seals_a_cannon_line() -> None:
    fen = "3ak4/4a4/9/9/R4c2r/9/9/4B4/9/2BAKA3 w - - 0 1"
    occurrences = analyze_tactics(fen, ["a5e5"])[0]["occurrences"]
    assert any(item["id"] == "seal" and item["squares"] == ["f5", "a5", "e5"] for item in occurrences)


def test_h7_cannon_is_not_abandoned_when_h9_rook_can_recapture() -> None:
    board = parse_fen("rnbakabr1/9/1c4nc1/p1p1p1p1p/9/9/P1P1P1P1P/1C2C1N2/9/RNBAKABR1 b - - 5 3")
    assert _is_protected(board, "h7", "black")


def test_central_cannon_does_not_trap_a_pawn_before_it_crosses_the_river() -> None:
    labels = _labels(START_FEN, "h2e2")
    assert "trap" not in labels


def test_protected_cannon_is_not_trapped_and_protected_rear_is_not_pinned() -> None:
    fen = "2bakabr1/r8/2n3n2/p1p1p3p/6p2/2P1P4/Pc4PcP/1CN1C1N2/9/R1BAKAB1R w - - 14 8"
    result = analyze_tactics(fen, ["i0h0"])[0]["occurrences"]
    assert "trap" not in {item["id"] for item in result}
    # h9 has effective defence, so the same-line relation is not 牵制.
    assert not any(item["id"] == "pin" and item["squares"] == ["h0", "h3", "h9"] for item in result)
    assert not any(item["id"] == "pin" and item["squares"] == ["h9", "h3", "h0"] for item in result)


def test_uncrossed_pawn_attack_does_not_create_escape() -> None:
    fen = "2bakabr1/9/2n3n2/p1p1p3p/3rP1p2/2P6/Pc4PcP/1CN1C1N2/9/R1BAKABR1 w - - 18 10"
    assert "escape" not in _labels(fen, "e5d5")


def test_continued_protection_does_not_create_a_new_protect_label() -> None:
    fen = "r1bakabr1/9/2n3n2/p1p1p3p/6p2/2P1P4/Pc4PcP/1CN1C1N2/R8/2BAKABR1 b - - 13 7"
    assert "protect" not in _labels(fen, "b3c3")


def test_new_chase_does_not_relabel_an_existing_rook_defence_as_protect() -> None:
    # e3-e4 opens an attack on a3, but the rook a0 already defends that pawn
    # before the move.  A new chase is not a new 保 relationship.
    fen = "r1bakabr1/9/1cn3n2/p1p1p3p/6p2/2P6/P3P1PcP/1CN1C1N2/9/R1BAKABR1 w - - 10 6"
    assert "protect" not in _labels(fen, "e3e4")


def test_unattacked_target_gaining_a_defender_is_not_protect() -> None:
    fen = "r1bakabr1/9/2n3n2/p1p1p3p/6p2/2P1P4/P1c3PcP/1CN1C1N2/R8/2BAKABR1 w - - 14 8"
    assert "protect" not in _labels(fen, "c0a2")


def test_low_value_piece_does_not_count_as_protection_for_a_rook() -> None:
    # Red horse h4 could recapture on f5, but it cannot be a tactical
    # protector for the higher-value red rook there.
    board = parse_fen("4k4/9/9/9/4PR3/3n3N1/9/9/9/4K4 w - - 0 1")
    assert "f5" not in _piece_protects(board, "h4", "red")


def test_horse_attack_on_a_protected_rook_is_still_a_material_chase() -> None:
    # The black horse can take the red rook on f5.  Red's horse can then
    # recapture, but N-for-R still wins five points, so this is a real 捉.
    board = parse_fen("4k4/9/9/9/4PR3/3n3N1/9/9/9/4K4 w - - 0 1")
    assert _escape_material_loss(board, "f5", "red") == 5


def test_existing_protection_does_not_create_an_additional_protect_label() -> None:
    fen = "1rbakabr1/9/2R3n2/p1p1p3p/6p2/2P1P4/P5PcP/BCN1CcN2/9/3AKABR1 b - - 0 11"
    labels = _labels(fen, "g9e7")
    assert "protect" not in labels
    assert "block" in labels


def test_sacrifice_excludes_uncrossed_pawns() -> None:
    assert not _sacrifice_eligible("p", "e6", "black")
    assert not _sacrifice_eligible("p", "e4", "black")
    assert _sacrifice_eligible("C", "e2", "red")


def test_crossing_pawn_that_is_immediately_attacked_is_a_sacrifice() -> None:
    fen = "1rbaka1r1/9/2R1b1n2/p1p1p3p/6p2/2P1P4/P5PcP/BCN1CcN2/9/3AKABR1 w - - 1 12"
    assert "sacrifice" in _labels(fen, "e4e5")


def test_horse_for_two_elephants_is_a_sacrifice() -> None:
    # Nc6xe7 takes one elephant; the other may take the horse, after which
    # Rc7xe7 takes that last elephant.  This is a strategic sacrifice, not a
    # normal exchange, even though the final recapture exists.
    fen = "1rbaka1r1/9/2R1b1n2/p1N5p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    assert "sacrifice" in _labels(fen, "c6e7")


def test_checked_side_geometrically_defending_rear_piece_is_not_pinned() -> None:
    fen = "1r1aka1r1/9/2R1b1n2/p7p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    assert "pin" not in _labels(fen, "c7e7")


def test_check_response_that_leaves_a_horse_is_sacrifice_not_protect_or_block() -> None:
    # Black must block Re7-e9 with Ae9-e8.  This saves the general but leaves
    # Ng7 to the rook, so the move is a sacrifice rather than an ordinary
    # protection or route block.
    fen = "1r1aka1r1/9/4R1n2/p1p5p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 b - - 0 1"
    occurrences = analyze_tactics(fen, ["f9e8"])[0]["occurrences"]
    labels = {item["id"] for item in occurrences}
    assert "sacrifice" in labels
    assert "protect" not in labels
    assert "block" not in labels


def test_sacrificial_blocker_is_reported_as_sacrifice_only() -> None:
    fen = "1rbakabr1/9/2R3n2/p1p1p3p/6p2/2P1P4/P5PcP/BCN1CcN2/9/3AKABR1 w - - 0 13"
    occurrences = analyze_tactics(fen, ["c2b4"])[0]["occurrences"]
    labels = {item["id"] for item in occurrences}
    assert "sacrifice" in labels
    assert "block" not in labels
    assert any(item["id"] == "sacrifice" and item["squares"] == ["b2", "f2"] for item in occurrences)


def test_protected_destination_does_not_count_as_a_trap() -> None:
    fen = "1rbakabr1/9/2nR2n2/p1p1p3p/6p2/2P1P4/P4cPcP/BCN1C1N2/9/3AKABR1 b - - 19 10"
    occurrences = analyze_tactics(fen, ["f3f2"])[0]["occurrences"]
    assert not any(item["id"] == "trap" and item["squares"] == ["g0"] for item in occurrences)
