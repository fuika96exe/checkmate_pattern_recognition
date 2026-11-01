import asyncio

import pytest

from backend.app.board import BoardError, parse_fen
from backend.app.main import api_analyze_tactics
from backend.app.models import LiveGameReportRequest, TacticAnalysisRequest
from backend.app.service import analyze_live_game_report
from backend.app.tactics import _is_endgame, _material_threats, analyze_tactics


TICKET_FEN = "3ak4/4a4/2n1b4/4n1RCp/4c4/6P2/P3P3P/2r1B1N2/9/3AKAB2 w - - 0 1"
MIDGAME_PAWN_FEN = "3k2cnr/9/9/p8/9/9/9/9/R8/1C2K2N1 w - - 0 1"
ENDGAME_PAWN_FEN = "3k5/9/9/p8/9/9/9/9/R8/4K4 w - - 0 1"


def _occurrences(fen, move, identifier):
    return [item for item in analyze_tactics(fen, [move])[0]["occurrences"] if item["id"] == identifier]


@pytest.mark.parametrize(
    ("fen", "move", "expected"),
    [
        (TICKET_FEN, "h6e6", "capture"),  # CxN, NxC, RxN: +4, although the target is defended.
        (TICKET_FEN, "g6e6", None),  # Moving the rook removes the cannon screen: -5.
        ("3ak4/4a4/2n1b4/4n1pCp/4c4/6P2/P3P3P/2r1B1N2/9/3AKAB2 w - - 0 1", "h6e6", "exchange"),
        ("4k4/9/9/9/4p4/4P4/9/4R4/9/3K5 b - - 0 1", "e5e4", "exchange"),
        ("4k4/9/4r4/9/9/4p4/4P4/9/9/4K4 w - - 0 1", "e3e4", "capture"),
    ],
)
def test_capture_and_exchange_use_resolved_gain(fen, move, expected):
    occurrences = analyze_tactics(fen, [move])[0]["occurrences"]
    actual = {item["id"] for item in occurrences} & {"capture", "exchange"}
    assert actual == ({expected} if expected else set())
    assert all(item["squares"] == [move[:2], move[2:]] for item in occurrences if item["id"] in actual)
    if expected:
        assert not any(item["id"] == "sacrifice" for item in occurrences)
    else:
        sacrifice = next(item for item in occurrences if item["id"] == "sacrifice")
        assert "5 分" in sacrifice["detail"]


def test_quiet_move_is_neither_a_capture_nor_an_exchange():
    assert not _occurrences(ENDGAME_PAWN_FEN, "a1a2", "capture")
    assert not _occurrences(ENDGAME_PAWN_FEN, "a1a2", "exchange")


def test_invalid_move_cannot_be_labelled_an_even_exchange():
    with pytest.raises(BoardError):
        analyze_tactics(TICKET_FEN, ["a0a9"])


def test_chase_only_includes_profitable_targets():
    # Of the two horses attacked, only a5 is profitable: i5 has a rook defender.
    fen = "9/3k5/3a4r/9/n7n/9/9/4R4/9/4K4 w - - 0 1"
    found = _occurrences(fen, "e2e5", "chase")
    assert [item["squares"] for item in found] == [["e5", "a5"]]


def test_horse_can_chase_a_protected_rook_for_five_points():
    fen = "4k4/9/9/9/4PR3/7N1/1n7/9/9/4K4 b - - 0 1"
    found = _occurrences(fen, "b3d4", "chase")
    assert [item["squares"] for item in found] == [["d4", "f5"]]
    assert "5 分" in found[0]["detail"]


def test_uncovering_another_piece_can_create_a_chase():
    fen = "1r1k5/9/1p7/9/1R7/9/9/1C7/9/4K4 w - - 0 1"
    assert [item["squares"] for item in _occurrences(fen, "b5a5", "chase")] == [["b2", "b9"]]


def test_continuing_a_chase_is_not_new_but_reestablishing_it_is():
    fen = "3k5/n8/9/9/9/9/9/9/R8/4K4 w - - 0 1"
    annotations = analyze_tactics(fen, ["a1a2", "d9d8", "a2b2", "d8d9", "b2a2"])
    assert not any(item["id"] == "chase" for item in annotations[0]["occurrences"])
    assert [item["squares"] for item in annotations[4]["occurrences"] if item["id"] == "chase"] == [["a2", "a8"]]


def test_a_potential_even_trade_is_not_a_chase():
    fen = "3k5/9/r8/9/r8/9/9/4R4/9/4K4 w - - 0 1"
    assert not _occurrences(fen, "e2e5", "chase")


@pytest.mark.parametrize(
    ("fen", "chase_fen", "expected"),
    [
        (MIDGAME_PAWN_FEN, "3k2cnr/9/9/p8/9/9/9/1R7/9/1C2K2N1 w - - 0 1", False),
        (ENDGAME_PAWN_FEN, "3k5/9/9/p8/9/9/9/1R7/9/4K4 w - - 0 1", True),
    ],
)
def test_uncrossed_pawn_capture_and_chase_follow_endgame_policy(fen, chase_fen, expected):
    assert _is_endgame(parse_fen(fen)) is expected
    assert bool(_occurrences(fen, "a1a6", "capture")) is expected
    # Moving from b2 first creates the attack; simply advancing on the a-file would preserve it.
    assert bool(_occurrences(chase_fen, "b2a2", "chase")) is expected


def test_pawn_may_capture_an_uncrossed_pawn_outside_endgame():
    fen = "3k2cnr/9/9/p8/P8/9/9/9/9/1C2K2NR w - - 0 1"
    assert not _is_endgame(parse_fen(fen))
    assert _occurrences(fen, "a5a6", "capture")


@pytest.mark.parametrize(
    ("fen", "expected_gain_one"),
    [
        ("r3k4/9/1c5c1/4p4/4P4/9/9/9/9/N2KR4 w - - 0 1", False),
        ("4k4/9/9/4p4/4P4/9/9/9/9/3KR4 w - - 0 1", True),
    ],
)
def test_one_point_threat_requires_endgame(fen, expected_gain_one):
    threats = _material_threats(parse_fen(fen), "black")
    assert (("e6", "e5", 1) in threats) is expected_gain_one


def test_rookless_position_is_endgame_even_with_three_minors_each():
    fen = "3k2cnc/9/9/9/4p4/4P4/9/9/9/1C2K1NC1 w - - 0 1"
    assert _is_endgame(parse_fen(fen))


def test_checking_the_general_is_not_a_material_chase():
    fen = "4k4/9/9/9/R8/9/9/9/9/3K5 w - - 0 1"
    assert not _occurrences(fen, "a5e5", "chase")


def test_api_serializes_new_labels_and_evidence():
    response = asyncio.run(api_analyze_tactics(TacticAnalysisRequest(fen=TICKET_FEN, ucci_moves=["h6e6"])))
    payload = response.model_dump(by_alias=True)
    capture = next(item for item in payload["annotations"][0]["occurrences"] if item["id"] == "capture")
    assert capture["labelZh"] == "吃"
    assert capture["squares"] == ["h6", "e6"]
    assert "4 分" in capture["detail"]


def test_live_report_does_not_call_a_profitable_capture_an_even_exchange():
    # The independent category lab's approximate exchange rule also matches this +1 capture.
    fen = "4k4/9/4r4/9/9/4p4/4P4/9/9/4K4 w - - 0 1"
    report = analyze_live_game_report(LiveGameReportRequest(
        initial_fen=fen, ucci_moves=["e3e4"], target_index=1, ply=1,
    ))
    assert any(event.id == "capture" and event.source == "move_purpose" for event in report.events)
    assert not any(event.id == "exchange" for event in report.events)
