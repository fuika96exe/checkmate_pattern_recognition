from backend.app.tactical_categories import analyze_tactical_categories
from backend.app.tactics import analyze_tactics
from backend.app.models import LiveGameReportRequest
from backend.app.service import advance, analyze_live_game_report, create_initial


def _labels(fen: str, move: str) -> set[str]:
    return {item["id"] for item in analyze_tactical_categories(fen, [move])[0]["occurrences"]}


def test_capturing_a_defender_without_attacking_its_target_is_not_removal() -> None:
    # The black cannon h7 protects the black horse c7 through the bishop e7.
    # Red takes the cannon, but the horse on c7 does not become attacked.
    # Removing a relation alone is not 消除保护.
    fen = "4k4/9/2n1b2c1/7R1/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "h6h7")


def test_capturing_last_defender_that_exposes_an_attacked_target_is_removal() -> None:
    # The rook c6 already attacks c7.  h7 protects c7 through e7; after
    # h6xh7 the horse has no other defender and remains under attack.
    fen = "4k4/9/2n1b2c1/2R4R1/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" in _labels(fen, "h6h7")


def test_capturing_the_protected_target_is_not_removal_of_defender() -> None:
    # Here h7 protects c7, but Red takes c7 itself.  This must not be labelled
    # as 消除保护 merely because the h7 -> c7 relation disappears with c7.
    fen = "4k4/9/2n1b2c1/2R6/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "c6c7")


def test_horse_for_two_elephants_is_not_an_exchange() -> None:
    fen = "1rbaka1r1/9/2R1b1n2/p1N5p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    assert "exchange" not in _labels(fen, "c6e7")


def test_check_with_a_pawn_target_is_not_fork_or_line_tactic() -> None:
    # Rc7-e7 checks the general.  The apparent h-file relation is not a
    # pin/skewer because Ng7 geometrically protects Rh9, even though Black
    # must answer check before it can move that knight.
    fen = "1r1aka1r1/9/2R1b1n2/p7p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    labels = _labels(fen, "c7e7")
    assert "fork" not in labels
    assert "skewer" not in labels
    assert "pin" not in labels


def test_protected_second_target_does_not_create_a_fork() -> None:
    # e2-e5 attacks both black horses.  The i5 horse is protected by the
    # black rook i7, which can immediately recapture a rook on i5; only a5 is
    # a safe target, so the move is not 捉双.
    fen = "9/3k5/3a4r/9/n7n/9/9/4R4/9/4K4 w - - 0 1"
    assert "fork" not in _labels(fen, "e2e5")


def test_uncrossed_pawn_does_not_count_as_a_fork_target() -> None:
    fen = "1rbakabr1/9/2nR2n2/p1p1p3p/6p2/2P1P4/P5PcP/BCN1CcN2/9/3AKABR1 w - - 20 11"
    assert "fork" not in _labels(fen, "d7c7")


def test_existing_safe_target_can_be_part_of_a_new_fork() -> None:
    # Before h5-d5, Red's rook already attacks a5.  On d5 it keeps that safe
    # attack and gains a second safe attack on d7, so the move forms 捉双.
    fen = "3k1a3/9/3c5/9/c6R1/9/9/9/9/4K4 w - - 0 1"
    assert "fork" in _labels(fen, "h5d5")


def test_cannon_skewer_tracks_front_and_rear_targets_not_the_screen() -> None:
    # Red cannon f7 attacks the unprotected c7 horse through e7 as a screen.
    # If c7 leaves, b7 becomes the next unprotected target; e7 is only a
    # cannon screen, not a 串打 target.
    fen = "3aka3/9/1cn1c4/9/9/9/9/5C3/9/4K4 w - - 0 1"
    assert "skewer" in _labels(fen, "f2f7")


def test_protected_rear_target_is_not_pin_even_when_front_is_protected() -> None:
    # Adding a rook on c8 protects the front horse c7, but its rear target is
    # also effectively defended.  The line is neither 串打 nor 牵制.
    fen = "3k5/2r6/1cn1c4/9/9/9/9/5C3/9/4K4 w - - 0 1"
    labels = _labels(fen, "f2f7")
    assert "pin" not in labels
    assert "skewer" not in labels


def test_protected_rear_target_is_not_a_material_pin() -> None:
    # Rook g0-h0 would align rook -> cannon h7 -> rook h9.  The rear rook is
    # defended by the horse f8, so this is not a material 牵制.
    fen = "4k2r1/5n3/7c1/9/9/9/9/9/4A4/4K1R2 w - - 0 1"
    assert "pin" not in _labels(fen, "g0h0")


def test_undefended_rear_target_forms_a_same_line_material_pin() -> None:
    fen = "4k2r1/9/7c1/9/9/9/9/9/4A4/4K1R2 w - - 0 1"
    assert "pin" in _labels(fen, "g0h0")


def test_uncrossed_pawns_do_not_create_a_material_pin() -> None:
    # h0-h6 lines the rook up with black's protected e6 pawn and c6 pawn.
    # Pawns, and especially uncrossed pawns, are not valid 牵制 material.
    fen = "r1bakabr1/9/1cn3nc1/p1p1p3p/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKABR1 w - - 8 5"
    assert "pin" not in _labels(fen, "h0h6")


def test_uncrossed_pawn_cannot_be_the_rear_target_of_a_skewer() -> None:
    # Rf0 attacks Nf6.  Once the horse leaves, the same file reaches the
    # black pawn on f9, but that pawn has not crossed the river and therefore
    # cannot turn the line into a 串打.
    fen = "4kp3/4a4/9/5n3/9/9/9/9/9/4K2R1 w - - 0 1"
    assert "skewer" not in _labels(fen, "h0f0")


def test_cannon_move_can_prepare_a_pawn_sacrifice_breakthrough() -> None:
    fen = "r1bakab1r/9/1cn2cn2/p3p1p1p/2p6/6P2/P1P1P3P/1C2C1N2/9/RNBAKABR1 w - - 8 5"
    assert "cannon_pawn_breakthrough" in _labels(fen, "b2c2")


def test_pawn_sacrifice_breakthrough_can_win_a_protected_rook() -> None:
    fen = "rnbakab1r/9/1c4nc1/p1p1p1p1p/9/8P/P1P1P1P2/1C4N1C/9/RNBAKAB1R w - - 0 1"
    assert "cannon_pawn_breakthrough" in _labels(fen, "i4i5")


def test_pawn_sacrifice_breakthrough_rejects_a_protected_horse() -> None:
    fen = "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/6P2/P1P1P3P/1C4C2/9/RNBAKABNR w - - 0 1"
    assert "cannon_pawn_breakthrough" not in _labels(fen, "g4g5")


def test_pawn_screen_check_is_a_cannon_pawn_breakthrough() -> None:
    fen = "r1bakab1r/9/1cn3nc1/p1p1p1p1p/9/4P4/P1P3P1P/1C2C4/9/RNBAKABNR w - - 0 1"
    assert "cannon_pawn_breakthrough" in _labels(fen, "e4e5")


def test_protected_rook_chased_by_cannon_can_be_trapped() -> None:
    # Ca4 attacks the protected black rook on a7.  Its b7/a8/a9 exits are
    # all still losing: a cannon-for-rook exchange remains a material gain.
    fen = "2bakabnr/9/r1n4c1/p2Np1p1p/9/1C7/P1P1P1P1P/7C1/9/R1BAKABNR w - - 0 1"
    assert "trap" in _labels(fen, "b4a4")


def test_analysis_does_not_capture_the_opposing_general() -> None:
    # After e5-a5, the red cannon geometrically sees e9 through the advisor
    # e8.  The tactical analysis must not construct a position without the
    # black general from that pseudo king-capture.
    fen = "1r1ak4/4a4/9/9/4R4/9/9/4C4/9/3K5 w - - 0 1"
    assert analyze_tactical_categories(fen, ["e5a5"])[0]["ucci"] == "e5a5"


def test_discovered_check_does_not_also_count_as_removing_protection() -> None:
    # Moving the rook creates a cannon check, but it captures no black
    # defender.  Tactical side effects must not manufacture 消除保护.
    fen = "1r1ak4/4a4/9/9/4R4/9/9/4C4/9/3K5 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "e5b5")


def test_opening_an_attack_on_an_uncrossed_pawn_is_not_discovered_attack() -> None:
    fen = "1rbakabr1/9/2nR2n2/p1p1p3p/6p2/2P1P4/P4cPcP/BCN1C1N2/9/3AKABR1 b - - 19 10"
    assert "discovered_attack" not in _labels(fen, "f3f2")


def test_preemptively_capturable_attacker_does_not_create_discovered_attack() -> None:
    # c2-b4 opens the b2 cannon's line, but black can safely play f2xb2
    # before Red gets to use that cannon.  The apparent line is no 闪击.
    fen = "1rbaka1r1/9/2R1b1n2/p1p5p/4p1p2/2P6/P5PcP/BCN1CcN2/9/3AKABR1 w - - 0 13"
    assert "discovered_attack" not in _labels(fen, "c2b4")


def test_reciprocal_rook_capture_is_an_exchange_not_a_discovered_attack() -> None:
    # b5-e5 uncovers the b2 cannon's attack on b9 through b7.  Black's rook
    # on b7 can immediately capture that cannon on b9, so the line only
    # offers a mutual exchange, not a usable flash attack.
    fen = "1r2k4/9/1r7/9/1R7/9/9/1C7/9/4K4 w - - 0 1"
    assert "discovered_attack" not in _labels(fen, "b5e5")


def test_reciprocal_rooks_after_h7i7_are_not_a_discovered_attack() -> None:
    # h7-i7 opens Black's h9 rook line to the red rook on h6.  But h6-h9
    # is an immediate legal recapture, so the rooks merely face a trade.
    fen = "r1bakabr1/9/1cn3nc1/p1p1p2Rp/6p2/2P6/P3P1P1P/1C2C1N2/9/RNBAKAB2 b - - 9 5"
    assert "discovered_attack" not in _labels(fen, "h7i7")


def test_unanswerable_new_capture_remains_a_discovered_attack() -> None:
    # Here b7 is only the cannon's screen, not a defender of the rook on b9.
    # The same blocker move creates a genuine, unanswerable cannon capture.
    fen = "1r2k4/9/1p7/9/1R7/9/9/1C7/9/4K4 w - - 0 1"
    assert "discovered_attack" in _labels(fen, "b5e5")


def test_king_escape_restoring_a_rook_move_is_not_discovered_attack() -> None:
    # The rook b6 already geometrically attacks g6.  Black's king leaves the
    # horse check on f9, which merely makes that existing rook capture legal;
    # no blocking piece moved off the rook's attack line, so this is not 闪击.
    fen = "3a1k3/4a2N1/9/1r4R2/9/9/9/4C4/9/3K5 b - - 0 1"
    assert "discovered_attack" not in _labels(fen, "f9f8")


def test_new_hunter_completes_a_preexisting_trap() -> None:
    # The pawn g7 already leaves the black horse i9 with no safe escape.
    # Rook a1-i1 newly attacks that horse, completing the required 围 + 困.
    fen = "2bak3n/4a4/4b1P2/9/9/9/9/9/R8/3K5 w - - 0 1"
    assert "trap" in _labels(fen, "a1i1")


def test_live_game_advance_returns_an_auditable_report() -> None:
    result = advance(create_initial().state, "h2e2", include_live_report=True)
    assert result.live_report is not None
    assert result.live_report.legal is True
    assert result.live_report.ucci == "h2e2"
    assert all(event.source in {"rule", "tactical_category", "move_purpose"} for event in result.live_report.events)


def test_async_live_report_uses_the_accepted_move_snapshot() -> None:
    initial = create_initial().state
    advanced = advance(initial, "h2e2")
    report = analyze_live_game_report(LiveGameReportRequest(
        initial_fen=initial.fen,
        ucci_moves=["h2e2"],
        target_index=1,
        ply=advanced.state.ply,
        repetition_decision=advanced.state.repetition_decision,
    ))
    assert report.legal is True
    assert report.ply == advanced.state.ply
    assert report.ucci == "h2e2"


def test_live_report_reuses_the_full_line_results_from_both_labs() -> None:
    """The merged board is a coordinator, not a third tactical ruleset."""
    initial = create_initial().state
    moves = ["h2e2", "h7e7", "a0a1"]
    state = initial
    for move in moves:
        state = advance(state, move).state

    report = analyze_live_game_report(LiveGameReportRequest(
        initial_fen=initial.fen,
        ucci_moves=moves,
        target_index=3,
        ply=state.ply,
        repetition_decision=state.repetition_decision,
    ))
    actual = [
        (event.source, event.id, event.label_zh, event.squares, event.detail)
        for event in report.events
        if event.source in {"move_purpose", "tactical_category"}
    ]
    purpose_occurrences = analyze_tactics(initial.fen, moves)[2]["occurrences"]
    category_occurrences = analyze_tactical_categories(initial.fen, moves)[2]["occurrences"]
    expected = [
        ("move_purpose", item["id"], item["label_zh"], item["squares"], item["detail"])
        for item in purpose_occurrences
    ] + [
        ("tactical_category", item["id"], item["label_zh"], item["squares"], item["detail"])
        for item in category_occurrences
        if item["id"] not in {purpose_item["id"] for purpose_item in purpose_occurrences}
    ]
    assert actual == expected
