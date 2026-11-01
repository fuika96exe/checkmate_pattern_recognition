import pytest

from app.patterns import (
    recognize_centroid_chariot_checkmate,
    recognize_double_cannon_checkmate,
    recognize_smothered_cannon_checkmate,
    recognize_smothered_checkmate,
    recognize_throat_cutting_checkmate,
    recognize_tiger_silhouette_checkmate,
    recognize_two_devils_knocking_checkmate,
)


@pytest.mark.parametrize("fen, expected", [
    ("1R2k1b2/4c4/4c4/9/9/9/9/4B4/4A4/2BAK4 b - - 0 1", True),
    ("3R2b2/9/3kb4/9/9/9/9/4B4/4A4/2BAK4 b - - 0 1", True),
    ("3R1ab2/2R1k4/4bcn2/1r2p3p/9/9/P3P1r1P/C5N2/9/2BAKAB2 b - - 2 23", False),
    ("3a1ab2/1R2k4/4bN3/7P1/9/9/P1p1r4/B8/4A4/c3KA3 b - - 8 39", False),
    ("6C2/5k3/b3b4/p3c3p/6p2/3p5/8P/4n3B/4A4/1r2K4 w - - 4 56", False),
])
def test_smothered_user_positions(fen, expected):
    result = recognize_smothered_checkmate(fen)
    assert result["analysis"]["is_checkmate"]
    assert result["detected"] is expected


def test_smothered_excludes_horse_and_double_cannon():
    assert not recognize_smothered_checkmate("3aka3/4n4/9/5N3/9/9/9/9/9/3K5 w - - 0 1", ["f6g8"])["detected"]
    fen = "3aka3/9/9/9/4C4/5C3/9/9/9/3K5 w - - 0 1"
    assert recognize_double_cannon_checkmate(fen, ["f4e4"])["detected"]
    assert not recognize_smothered_checkmate(fen, ["f4e4"])["detected"]


def test_centroid_requires_a_different_checker():
    result = recognize_centroid_chariot_checkmate("3k5/4R4/9/9/1N7/9/9/9/9/4K4 w - - 0 1", ["b5c7"])
    assert result["detected"] and result["pattern_id"] == "CENTROID_CHECKMATE"
    result = recognize_centroid_chariot_checkmate("3k5/4P4/2R6/9/9/9/9/9/9/4K4 w - - 0 1", ["c7c9"])
    assert result["detected"] and result["features"]["centroid_piece"] == "P"
    result = recognize_centroid_chariot_checkmate("3k5/4R4/2R6/9/9/9/9/9/9/4K4 w - - 0 1", ["c7c9"])
    assert result["detected"] == (not result["features"]["centroid_is_checker"])


def test_throat_cutting_requires_center_advisor_and_support():
    fen = "2b1ka3/1R2a4/4b4/4C1R2/9/9/9/9/9/4K4 w - - 0 1"
    result = recognize_throat_cutting_checkmate(fen, ["b8e8", "f9e8", "g6g9"])
    assert result["detected"] and result["features"]["qualifying_captures"][0]["other_advisors"]
    protected = recognize_throat_cutting_checkmate("4k4/1R2a4/9/9/9/9/9/9/9/5K3 w - - 0 1", ["b8e8"])
    capture = protected["features"]["qualifying_captures"][0]
    assert not capture["other_advisors"] and capture["protectors"] == ["e9"]


def test_smothered_palace_requires_both_advisor_screen_and_blockers():
    positive = recognize_smothered_cannon_checkmate("4ka3/4a4/9/9/9/9/9/7C1/4A4/4K4 w - - 0 1", ["h2h9"])
    assert positive["detected"]
    negative = recognize_smothered_cannon_checkmate("4C1b2/2C3R2/3ak4/p5p2/4r2c1/2P6/P8/4r4/4A4/3AK4 b - - 13 36", ["h5h0", "c8c7"])
    assert negative["analysis"]["is_checkmate"] and not negative["detected"]


def test_two_devils_requires_simultaneous_eye_occupancy():
    positive = recognize_two_devils_knocking_checkmate("4ka3/3P1P3/4b4/9/9/9/9/9/3p2p2/5K3 w - - 0 1", ["f8f9"])
    assert positive["detected"] and positive["features"]["occurrence_plies"] == [0]
    negative = recognize_two_devils_knocking_checkmate("4k4/2R1a2R1/9/9/9/9/9/4B4/9/4K4 w - - 0 1", ["c8e8", "e9f9", "h8f8"])
    assert negative["analysis"]["is_checkmate"] and not negative["detected"]


def test_tiger_horse_must_actually_control_general():
    result = recognize_tiger_silhouette_checkmate("3a1k3/4a4/7R1/6N2/9/9/9/9/9/4K4 w - - 0 1", ["h7h9"])
    assert result["analysis"]["is_checkmate"]
    assert result["detected"] == bool(result["features"]["king_control_plies"])


def test_double_horses_every_check_must_be_by_horses():
    from app.patterns import recognize_double_horses_drinking_spring_checkmate
    positive = recognize_double_horses_drinking_spring_checkmate("2bak4/4a2N1/4b4/7N1/9/9/4P4/9/9/4K4 w - - 0 1", ["h6g8", "e9f9", "g8e7", "f9e9", "e7c8"])
    assert positive["detected"] and positive["features"]["all_checks_by_horses"]
    negative = recognize_double_horses_drinking_spring_checkmate("Nc2ka3/1Nc1a4/4b4/9/9/5R3/9/4C4/4p1p2/3p1K3 w - - 0 1", ["f4f9", "b9f9", "a9c8", "e9d9", "c8e7", "d9e9", "e7g8"])
    assert negative["analysis"]["is_checkmate"] and not negative["features"]["all_checks_by_horses"] and not negative["detected"]
