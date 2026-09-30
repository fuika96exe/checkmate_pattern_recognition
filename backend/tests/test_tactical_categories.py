from backend.app.tactical_categories import analyze_tactical_categories
from backend.app.models import LiveGameReportRequest
from backend.app.service import advance, analyze_live_game_report, create_initial


def _labels(fen: str, move: str) -> set[str]:
    return {item["id"] for item in analyze_tactical_categories(fen, [move])[0]["occurrences"]}


def test_capturing_a_defender_removes_its_specific_protection() -> None:
    # The black cannon h7 protects the black horse c7 through the bishop e7.
    # Red first takes the cannon, leaving the horse on c7.  That is removal of
    # the h7 -> c7 protection relationship, not an exchange on the horse.
    fen = "4k4/9/2n1b2c1/7R1/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" in _labels(fen, "h6h7")


def test_capturing_the_protected_target_is_not_removal_of_defender() -> None:
    # Here h7 protects c7, but Red takes c7 itself.  This must not be labelled
    # as 消除保护 merely because the h7 -> c7 relation disappears with c7.
    fen = "4k4/9/2n1b2c1/2R6/9/9/9/9/9/4K4 w - - 0 1"
    assert "remove_defender" not in _labels(fen, "c6c7")


def test_protected_second_target_does_not_create_a_fork() -> None:
    # e2-e5 attacks both black horses.  The i5 horse is protected by the
    # black rook i7, which can immediately recapture a rook on i5; only a5 is
    # a safe target, so the move is not 捉双.
    fen = "9/3k5/3a4r/9/n7n/9/9/4R4/9/4K4 w - - 0 1"
    assert "fork" not in _labels(fen, "e2e5")


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


def test_protected_front_target_is_pin_not_skewer() -> None:
    # Adding a rook on c8 protects the front horse c7.  The same cannon line
    # is now a 牵制, not a 串打.
    fen = "3k5/2r6/1cn1c4/9/9/9/9/5C3/9/4K4 w - - 0 1"
    labels = _labels(fen, "f2f7")
    assert "pin" in labels
    assert "skewer" not in labels


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
        before_fen=initial.fen,
        ucci_move="h2e2",
        ply=advanced.state.ply,
        repetition_decision=advanced.state.repetition_decision,
    ))
    assert report.legal is True
    assert report.ply == advanced.state.ply
    assert report.ucci == "h2e2"
