from pathlib import Path

from app.main import api_analyze_puzzle_line
from app.models import PuzzleLineRequest
from scripts.import_puzzles import import_csv


def test_puzzle_line_returns_full_timeline_and_all_matches() -> None:
    response = api_analyze_puzzle_line(
        PuzzleLineRequest(
            fen="4kab2/4a4/4b4/2p5C/4c4/2n6/P5R1P/9/1r2A4/4KA3 w - - 2 37",
            blunder_move="e1d2",
            pv=["b1b0", "e0e1", "c4e3"],
        )
    )

    assert response.valid is True
    assert response.analysis is not None
    assert response.analysis.analysis.is_checkmate is True
    assert len(response.timeline) == 5
    assert response.timeline[1].move == "e1d2"


def test_puzzle_line_keeps_invalid_case_visible() -> None:
    response = api_analyze_puzzle_line(
        PuzzleLineRequest(
            fen="4kab2/4a4/4b4/2p5C/4c4/2n6/P5R1P/9/1r2A4/4KA3 w - - 2 37",
            blunder_move="a0a9",
            pv=[],
        )
    )

    assert response.valid is False
    assert response.failed_move_index == 1
    assert len(response.timeline) == 1
    assert "a0a9" in (response.error or "")


def test_importer_preserves_invalid_rows(tmp_path: Path) -> None:
    source = tmp_path / "puzzles.csv"
    source.write_text(
        "Rating,Encrypted Id,Initial Fen,Blunder Move,Player Turn,Pv\n"
        "900,valid-id,4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1,e0e1,black,\"['e9e8']\"\n"
        "bad,,broken,z9z9,green,not-a-list\n",
        encoding="utf-8",
    )

    dataset = import_csv(source)

    assert dataset["puzzleCount"] == 2
    assert dataset["invalidCount"] == 1
    assert dataset["puzzles"][0]["importStatus"] == "ready"
    assert dataset["puzzles"][1]["importStatus"] == "invalid"
    assert dataset["puzzles"][1]["importErrors"]
