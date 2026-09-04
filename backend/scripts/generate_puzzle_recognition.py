from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import api_analyze_puzzle_line  # noqa: E402
from app.models import PuzzleLineRequest  # noqa: E402
from app.patterns import CHECKMATE_RULES_VERSION  # noqa: E402


async def generate_recognition(dataset: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}

    for puzzle in dataset["puzzles"]:
        key = str(puzzle["key"])
        if puzzle["importStatus"] == "invalid":
            results[key] = {
                "status": "invalid",
                "patternIds": [],
                "error": "；".join(puzzle["importErrors"]),
            }
            continue

        response = await api_analyze_puzzle_line(
            PuzzleLineRequest(
                fen=puzzle["initialFen"],
                blunder_move=puzzle["blunderMove"],
                pv=puzzle["pv"],
            )
        )
        if not response.valid or response.analysis is None:
            results[key] = {
                "status": "invalid",
                "patternIds": [],
                "error": response.error or "无法分析棋题",
            }
            continue

        pattern_ids = [match.pattern_id for match in response.analysis.matches]
        results[key] = {
            "status": "matched" if pattern_ids else "unmatched",
            "patternIds": pattern_ids,
        }

    return {
        "schemaVersion": "1.0",
        "datasetVersion": dataset["datasetVersion"],
        "rulesVersion": CHECKMATE_RULES_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "puzzleCount": len(results),
        "results": results,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="用当前全部杀法规则生成棋题识别索引")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=project_root / "public" / "data" / "checkmate-puzzles.json",
        help="标准棋题 JSON 路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "public" / "data" / "checkmate-puzzle-recognition.json",
        help="识别索引输出路径",
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    recognition = asyncio.run(generate_recognition(dataset))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(recognition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"已分析 {recognition['puzzleCount']} 题，"
        f"资料版本 {recognition['datasetVersion']}，规则版本 {recognition['rulesVersion']}"
    )


if __name__ == "__main__":
    main()
