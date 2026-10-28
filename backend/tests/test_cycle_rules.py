from backend.app.cycle_rules import evaluate_cycle


START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
QUIET_CYCLE = ["b0a2", "b9a7", "a2b0", "a7b9"]


def test_abbreviated_cycle_can_be_judged_without_mutating_game_state() -> None:
    # Empty move list is an assumed, equal-behaviour cycle: it verifies the
    # isolated evaluator contract without touching service or recognizer code.
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    result = evaluate_cycle(fen, [], assume_cycle=True)
    assert result.verdict == "draw"
    assert result.red_kind == result.black_kind == "idle"


def test_real_third_occurrence_warns_before_a_draw() -> None:
    result = evaluate_cycle(START_FEN, QUIET_CYCLE * 2)

    assert result.repeated is True
    assert result.verdict == "warning"


def test_real_fourth_occurrence_is_a_draw_for_equal_cycles() -> None:
    result = evaluate_cycle(START_FEN, QUIET_CYCLE * 3)

    assert result.repeated is True
    assert result.verdict == "draw"
