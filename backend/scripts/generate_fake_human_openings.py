"""Pre-compute the frozen ply-20 opening classification for every fake-human game.

The Fake Human tab reads the output index instead of replaying all games in
the browser each time it opens. Regenerate after the opening recognizer or
``public/data/fake-human-games.json`` changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models import RecognitionState  # noqa: E402
from app.opening_sample import OPENING_PLIES, replay_sample  # noqa: E402

OPENING_RULES_VERSION = RecognitionState.model_fields["rules_version"].default


def dataset_version(games: list[dict[str, Any]]) -> str:
    canonical = json.dumps(games, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def analyse_game(game: dict[str, Any]) -> dict[str, Any]:
    try:
        line = replay_sample(game["moves"][:OPENING_PLIES])
        if not line:
            raise ValueError("棋譜沒有走法")
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    state = line[-1].state
    classification = state.classification
    return {
        "status": "done",
        "name": classification.display_name,
        "nameEn": classification.display_name_en,
        "certainty": classification.certainty,
        "baseMatchupId": classification.base_matchup_id,
        "plies": state.ply,
    }


def generate_openings(dataset: dict[str, Any]) -> dict[str, Any]:
    games = dataset["games"]
    results: dict[str, dict[str, Any]] = {}
    for completed, game in enumerate(games, start=1):
        results[game["id"]] = analyse_game(game)
        if completed % 50 == 0:
            print(f"Analysed {completed}/{len(games)} fake-human openings", flush=True)
    return {
        "schemaVersion": "1.0",
        "datasetVersion": dataset_version(games),
        "rulesVersion": OPENING_RULES_VERSION,
        "openingPlies": OPENING_PLIES,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "gameCount": len(results),
        "results": results,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data_dir = Path(__file__).resolve().parents[2] / "public" / "data"
    parser = argparse.ArgumentParser(description="預先分析假人對局第 20 個半手的開局判斷")
    parser.add_argument("--dataset", type=Path, default=data_dir / "fake-human-games.json")
    parser.add_argument("--output", type=Path, default=data_dir / "fake-human-openings.json")
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    index = generate_openings(dataset)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary_output.replace(args.output)
    errors = sum(result["status"] == "error" for result in index["results"].values())
    print(f"已分析 {index['gameCount']} 局（失敗 {errors}），資料版本 {index['datasetVersion']}，"
          f"規則版本 {index['rulesVersion']}")


if __name__ == "__main__":
    main()
