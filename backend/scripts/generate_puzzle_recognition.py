from __future__ import annotations

import argparse
import asyncio
import faulthandler
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import api_analyze_puzzle_line  # noqa: E402
from app.models import PuzzleLineRequest  # noqa: E402
from app.patterns import CHECKMATE_RULES_VERSION  # noqa: E402


async def recognize_puzzle(puzzle: dict[str, Any]) -> dict[str, Any]:
    if puzzle["importStatus"] == "invalid":
        return {"status": "invalid", "patternIds": [], "error": "；".join(puzzle["importErrors"])}
    response = await api_analyze_puzzle_line(
        PuzzleLineRequest(fen=puzzle["initialFen"], blunder_move=puzzle["blunderMove"], pv=puzzle["pv"])
    )
    if not response.valid or response.analysis is None:
        return {"status": "invalid", "patternIds": [], "error": response.error or "无法分析棋题"}
    pattern_ids = [match.pattern_id for match in response.analysis.matches]
    fallback = response.analysis.material_fallback
    return {"status": "matched" if pattern_ids or fallback else "unmatched", "patternIds": pattern_ids,
            "materialId": fallback.id if fallback else None}


def recognize_puzzle_worker(puzzle: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(recognize_puzzle(puzzle))


async def generate_recognition(dataset: dict[str, Any], workers: int = 1) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    if workers == 1:
        for puzzle in dataset["puzzles"]:
            results[str(puzzle["key"])] = await recognize_puzzle(puzzle)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=faulthandler.enable) as pool:
            records = pool.map(recognize_puzzle_worker, dataset["puzzles"], chunksize=4)
            for completed, (puzzle, result) in enumerate(zip(dataset["puzzles"], records), start=1):
                results[str(puzzle["key"])] = result
                if completed % 100 == 0:
                    print(f"Analysed {completed}/{len(dataset['puzzles'])} checkmate puzzles", flush=True)

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
    parser.add_argument("--workers", type=int, default=4, help="Number of analysis worker processes.")
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
    recognition = asyncio.run(generate_recognition(dataset, workers=args.workers))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_text(
        json.dumps(recognition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_output.replace(args.output)
    print(
        f"已分析 {recognition['puzzleCount']} 题，"
        f"资料版本 {recognition['datasetVersion']}，规则版本 {recognition['rulesVersion']}"
    )


if __name__ == "__main__":
    main()
