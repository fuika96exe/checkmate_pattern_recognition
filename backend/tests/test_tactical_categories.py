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


def test_same_kind_reciprocal_contact_is_not_removing_protection() -> None:
    # Ng5 protects the black rook e6.  After Rg4xg5, Red's other rook e4 attacks
    # e6, but the black rook can legally reply e6xe4: rook-versus-rook
    # mutual contact is an exchange opportunity, not 消除保护.
    fen = "4k4/9/9/4r4/6n2/4R1R2/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "g4g5")


def test_lak8xo_potential_cannon_reply_is_not_an_exchange() -> None:
    # The old cached record called ...Ci1xf1 an exchange merely because f3-f1
    # was geometrically imaginable.  The line never completes a concrete,
    # valid recapture, so it has no 交换 label.
    fen = "3akab2/9/4b1n2/p3p3p/3n5/2PN3N1/P3PR3/4B4/4KCr2/2BA1A2c w - - 6 23"
    line = ["e1d1", "i0i1", "d0e1", "i1f1", "e1d2"]
    assert all(
        "exchange" not in {item["id"] for item in annotation["occurrences"]}
        for annotation in analyze_tactical_categories(fen, line)
    )


def test_rdajlo_pawn_relation_is_not_removing_protection() -> None:
    # The former label treated the pawn i3 as a protected tactical target
    # after ...Rg3xd3.  Pawn/soldier protection is outside 消除保护, and Red
    # has no concrete recapture of that black rook in this line.
    fen = "3akar2/4n4/4R4/p3p3p/3P5/9/2c1p3P/2C6/9/2BAKAB2 w - - 3 22"
    line = ["c2d2", "e3e2", "d2d3", "g9g3", "c0e2", "g3d3", "e7e6", "d3d5", "e6e4"]
    assert all(
        "remove_defender" not in {item["id"] for item in annotation["occurrences"]}
        for annotation in analyze_tactical_categories(fen, line)
    )


def test_qkmp8r_horse_for_rook_gain_is_not_effective_protection() -> None:
    # Before ...Cc0xc6, Black's horse d5 can already take the red rook e7.
    # Nc6 can recapture that horse, but a horse-for-rook trade still wins
    # material, so Nc6 is not an effective protector to be "removed".
    fen = "3a1k3/4a4/4R4/p1p5p/9/1NP2n3/P3P3P/3A5/3K1p3/2BA1cc2 w - - 1 26"
    line = ["b4c6", "f4d5", "d2e1", "f0c0", "d1d2", "c0c6", "e7e6"]
    assert all(
        "remove_defender" not in {item["id"] for item in annotation["occurrences"]}
        for annotation in analyze_tactical_categories(fen, line)
    )


def test_advisor_or_elephant_move_does_not_create_discovered_attack() -> None:
    # In qAbADL, Bc0-e2 uncovers the cannon g2-c2 line.  This is an
    # elephant move, so it is ordinary development rather than 闪击.
    fen = "2b1kab2/4a4/4c3r/p7p/2p6/3nC1B2/P1n1PR2P/2N1C4/9/2BAKA3 w - - 4 18"
    line = ["f0e1", "d4c2", "e2g2", "e9d9", "c0e2"]
    labels = {
        item["id"]
        for item in analyze_tactical_categories(fen, line)[4]["occurrences"]
    }
    assert "discovered_attack" not in labels


def test_user_regressions_reject_non_tactical_labels() -> None:
    cases = [
        # Cannon through an advisor to the general is not a 牵制 target.
        ("2bak1b1r/4a4/c1n1c1n2/p1p4Rp/1r4p2/P3PR3/2P3P1P/N2CC1N2/9/2BAKAB2 b - - 0 11", ["c7e6", "e2e6"], "pin"),
        # The pawn advance can also be captured by non-pawn pieces.
        ("4ka3/2c1a4/2n1C1n2/p1N5p/6p2/2P1p2r1/P5PcP/3R2N2/9/2BAKAB2 b - - 0 21", ["e8d7", "c6a7", "h4h8", "e7c7"], "cannon_pawn_breakthrough"),
        # A horse trading for a lower-value piece is not 交换.
        ("2bakab2/1r7/4c1n1c/p3p4/2p3p2/5R2C/P1n1P1P1P/2N1BC2N/4A4/2B1KA3 b - - 3 14", ["c3e2", "c0e2"], "exchange"),
        # A protected horse is not a fork target.
        ("2bak4/4a4/4b4/p1p5p/9/2c3r2/P3P3P/4C1NR1/4A4/1c2KAC2 w - - 0 24", ["e0d0", "c4c0"], "fork"),
    ]
    for fen, line, forbidden in cases:
        assert all(
            forbidden not in {item["id"] for item in annotation["occurrences"]}
            for annotation in analyze_tactical_categories(fen, line)
        )


def test_two_separate_black_pieces_can_form_a_fork() -> None:
    # ...Cb6-h6 simultaneously leaves the black rook attacking Rb4 and the
    # moved black cannon attacking Rh0.  This is 捉双 even though the two
    # attacks originate from different black pieces.
    # The supplied board must have Black to move; with ``w`` this black-cannon
    # move is necessarily illegal.
    fen = "1rbak4/4a4/4b1n2/pc6p/6pc1/1R1N1r3/P3P1P1P/4BC2N/4A4/4KABR1 b - - 9 17"
    labels = _labels(fen, "b6h6")
    assert "fork" in labels


def test_horse_for_crossed_pawn_is_not_an_exchange() -> None:
    # ...Ne7xe3 only trades a 4-point horse for a crossed 2-point pawn; the
    # value loss is not an equal exchange even though the capture is concrete.
    fen = "r1bakab1r/9/2c1c4/p1N1n1p1p/2p6/1CP6/P3p1P1P/B5N2/9/R2AKABR1 w - - 0 11"
    line = ["g2e3", "e7e3", "a0b0"]
    assert all(
        "exchange" not in {item["id"] for item in annotation["occurrences"]}
        for annotation in analyze_tactical_categories(fen, line)
    )


def test_capturing_an_advisor_defender_is_not_removal() -> None:
    # The advisor d8 protects Nc7.  Although Nf7xd8 leaves the horse exposed
    # to Rc6, 消除保护 only recognises rook/horse/cannon defenders.
    fen = "3k5/3a5/2n2N3/2R6/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "f7d8")


def test_removing_protection_of_pawns_is_not_remove_defender() -> None:
    # ...Rh9-h6 is met by Rh4xh6.  The rook had guarded black pawns e6/i6,
    # but a pawn/soldier is not a 消除保护 target.
    fen = "2bak2r1/4a4/n2cb4/p1p1p2Cp/3r5/1R4PR1/P3P3P/2N1B4/4A4/3AK1B2 b - - 4 20"
    labels = {
        item["id"]
        for item in analyze_tactical_categories(fen, ["h9h6", "h4h6"])[1]["occurrences"]
    }
    assert "remove_defender" not in labels


def test_capturing_the_protected_target_is_not_removal_of_defender() -> None:
    # Here h7 protects c7, but Red takes c7 itself.  This must not be labelled
    # as 消除保护 merely because the h7 -> c7 relation disappears with c7.
    fen = "4k4/9/2n1b2c1/2R6/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "c6c7")


def test_horse_for_two_elephants_is_not_an_exchange() -> None:
    fen = "1rbaka1r1/9/2R1b1n2/p1N5p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    assert "exchange" not in _labels(fen, "c6e7")


def test_check_with_a_safe_major_piece_target_is_fork_not_line_tactic() -> None:
    # Rc7-e7 checks the general and also safely attacks Rh9, so it is a
    # 捉双 under the check-plus-piece rule.  The apparent h-file relation is
    # still not a pin/skewer because Ng7 geometrically protects Rh9.
    fen = "1r1aka1r1/9/2R1b1n2/p7p/6p2/2P1p4/P5PcP/Bc2C1N2/9/3AKABR1 w - - 0 1"
    labels = _labels(fen, "c7e7")
    assert "fork" in labels
    assert "skewer" not in labels
    assert "pin" not in labels


def test_check_and_safe_major_piece_attack_is_a_fork() -> None:
    # ...Ra1xe1+ checks the red general and simultaneously attacks Ne2.
    # The black horse f3 protects the checking rook, so the knight capture
    # cannot be met by an immediate legal recapture.
    fen = "4k4/9/9/9/9/9/5n3/4N4/r3A4/4K4 b - - 0 1"
    assert "fork" in _labels(fen, "a1e1")


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


def test_two_new_attacks_from_two_pieces_are_a_fork() -> None:
    # Ra1-b1 newly attacks Nb3 and simultaneously clears one cannon screen:
    # Ca0 can then take Na4 through Pa2.  The two targets are attacked by
    # different red pieces but are created by the same move.
    fen = "4k4/9/9/9/4p4/n8/1n7/p8/R8/C3K4 w - - 0 1"
    assert "fork" in _labels(fen, "a1b1")


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


def test_cannon_rook_cannon_line_is_not_a_pin() -> None:
    # Ca0 attacks the protected Ra3, with a black cannon behind it.  Taking
    # the rook is already a profitable cannon-for-rook exchange, so this is
    # not a 牵制 even though Ca5 could recapture along the line afterwards.
    fen = "4k4/9/9/9/cn2p4/9/r8/9/p8/1C2K4 w - - 0 1"
    assert "pin" not in _labels(fen, "b0a0")


def test_rook_line_relation_is_not_a_skewer() -> None:
    # After ...Ce7-e6, Rf4-e4 aligns a rook with e6/e9.  A rook line is not
    # the cannon 串打 category, even though the absolute pin still exists.
    fen = "2bakabn1/r8/1c2c4/p5C1p/6p2/4nR3/P5P1P/1CN3N2/4A4/2BAK1B2 b - - 1 14"
    labels = {
        item["id"]
        for item in analyze_tactical_categories(fen, ["e7e6", "f4e4"])[1]["occurrences"]
    }
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


def test_exchange_requires_the_actual_immediate_recapture() -> None:
    # Red's a4xa5 merely offers a possible rook trade.  It becomes an
    # exchange only when Black actually replies a6xa5 on the same square.
    fen = "4k4/9/9/r8/r3p4/R8/9/9/9/4K4 w - - 0 1"
    first = analyze_tactical_categories(fen, ["a4a5"])[0]
    assert "exchange" not in {item["id"] for item in first["occurrences"]}

    reply = analyze_tactical_categories(fen, ["a4a5", "a6a5"])[1]
    assert "exchange" in {item["id"] for item in reply["occurrences"]}


def test_baseline_rook_through_advisor_is_not_a_pin() -> None:
    # Rg9 attacks the black advisor on f9 before the general on e9.  A
    # bottom-rank rook against a guard is ordinary pressure, not 牵制.
    fen = "1r1akabn1/9/bcn3C2/p3p1p1p/5r3/7R1/P1P1P1P1P/2N1C1N2/4A4/R1B1KAB2 b - - 0 11"
    result = analyze_tactical_categories(fen, ["b7b2", "h4h9", "c7d5", "h9g9"])[3]
    assert "pin" not in {item["id"] for item in result["occurrences"]}


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


def test_forced_check_response_is_not_a_piece_trap() -> None:
    # In oQ2DNq, ...Cc3-c0 checks the red general.  Rc1 has moves in the
    # position itself, but Red must answer the check; that temporary global
    # restriction is not 围困 of the rook.
    fen = "4kabr1/2r1a4/4b1nc1/p5p1p/4C4/2N3P2/P1c1n3P/1C7/2R6/2BAKABR1 w - - 1 15"
    assert "trap" not in {
        item["id"]
        for item in analyze_tactical_categories(fen, ["c4e3", "c3c0"])[1]["occurrences"]
    }


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
