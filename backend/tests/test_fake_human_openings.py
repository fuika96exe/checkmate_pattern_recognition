import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "scripts"))

from generate_fake_human_openings import (  # noqa: E402
    OPENING_RULES_VERSION,
    dataset_version,
    generate_openings,
)

DATA_DIR = BACKEND_ROOT.parent / "public" / "data"


def test_generated_index_freezes_opening_at_twenty_plies_and_keeps_errors() -> None:
    # First 22 plies of fake-human game -pR8rJa7Fu.
    line = ["c3c4", "h7e7", "h0g2", "h9g7", "i0h0", "i9h9", "h2h6", "g6g5", "b0c2", "b7c7",
            "c2d4", "b9a7", "b2e2", "a9b9", "h6h8", "d9e8", "d0e1", "b9b4", "h8h4", "b4b5",
            "d4e6", "g7e6"]
    dataset = {"games": [
        {"id": "full", "botSide": "red", "moves": line},
        {"id": "short", "botSide": "black", "moves": ["h2e2"]},
        {"id": "illegal", "botSide": "black", "moves": ["h2e2", "a0a9"]},
    ]}

    index = generate_openings(dataset)

    assert index["datasetVersion"] == dataset_version(dataset["games"])
    assert index["rulesVersion"] == OPENING_RULES_VERSION
    assert index["gameCount"] == 3
    assert index["results"]["full"]["status"] == "done"
    assert index["results"]["full"]["plies"] == 20
    assert index["results"]["short"]["plies"] == 1
    assert index["results"]["illegal"]["status"] == "error"
    assert "第 2 個半手" in index["results"]["illegal"]["message"]


def test_committed_index_matches_committed_games_and_opening_rules() -> None:
    games = json.loads((DATA_DIR / "fake-human-games.json").read_text(encoding="utf-8"))["games"]
    index = json.loads((DATA_DIR / "fake-human-openings.json").read_text(encoding="utf-8"))

    # A mismatch means the games file or the opening recognizer changed without
    # regenerating: python backend/scripts/generate_fake_human_openings.py
    assert index["datasetVersion"] == dataset_version(games)
    assert index["rulesVersion"] == OPENING_RULES_VERSION
    assert set(index["results"]) == {game["id"] for game in games}
