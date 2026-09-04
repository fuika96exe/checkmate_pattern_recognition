from __future__ import annotations

import argparse
import ast
import asyncio
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


UCCI_RE = re.compile(r"^[a-i][0-9][a-i][0-9]$")
PIECES = frozenset("rnbakcpRNBAKCP")
REQUIRED_COLUMNS = {
    "Rating",
    "Encrypted Id",
    "Initial Fen",
    "Blunder Move",
    "Player Turn",
    "Pv",
}


def validate_fen(fen: str) -> list[str]:
    errors: list[str] = []
    parts = fen.strip().split()
    if len(parts) < 2:
        return ["FEN 必須包含棋盤及行棋方"]
    if parts[1] not in {"w", "b"}:
        errors.append("FEN 行棋方必須是 w 或 b")
    ranks = parts[0].split("/")
    if len(ranks) != 10:
        return [*errors, "中國象棋 FEN 必須有 10 行"]
    for rank_index, rank in enumerate(ranks, start=1):
        files = 0
        for character in rank:
            if character.isdigit():
                files += int(character)
            elif character in PIECES:
                files += 1
            else:
                errors.append(f"FEN 第 {rank_index} 行包含不支援字元 {character!r}")
        if files != 9:
            errors.append(f"FEN 第 {rank_index} 行不是 9 路")
    return errors


def parse_pv(raw: str) -> tuple[list[str], list[str]]:
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as exc:
        return [], [f"PV 格式無法解析：{exc}"]
    if not isinstance(value, list) or not all(isinstance(move, str) for move in value):
        return [], ["PV 必須是 UCCI 字串陣列"]
    errors = [f"PV 包含無效 UCCI 着法：{move}" for move in value if not UCCI_RE.fullmatch(move)]
    return value, errors


def normalize_row(row: dict[str, str], row_number: int, seen_ids: dict[str, int]) -> dict[str, object]:
    errors: list[str] = []
    puzzle_id = (row.get("Encrypted Id") or "").strip()
    if not puzzle_id:
        puzzle_id = f"row-{row_number}"
        errors.append("缺少 Encrypted Id")
    seen_ids[puzzle_id] = seen_ids.get(puzzle_id, 0) + 1
    occurrence = seen_ids[puzzle_id]
    key = puzzle_id if occurrence == 1 else f"{puzzle_id}:{occurrence}"
    if occurrence > 1:
        errors.append(f"Encrypted Id 重複出現（第 {occurrence} 次）")

    fen = (row.get("Initial Fen") or "").strip()
    errors.extend(validate_fen(fen))

    blunder_move = (row.get("Blunder Move") or "").strip()
    if not UCCI_RE.fullmatch(blunder_move):
        errors.append(f"Blunder Move 不是有效 UCCI 着法：{blunder_move or '空白'}")

    pv, pv_errors = parse_pv(row.get("Pv") or "")
    errors.extend(pv_errors)

    solver_side = (row.get("Player Turn") or "").strip().lower()
    if solver_side not in {"red", "black"}:
        errors.append(f"Player Turn 必須是 red 或 black：{solver_side or '空白'}")

    fen_parts = fen.split()
    if len(fen_parts) >= 2 and fen_parts[1] in {"w", "b"} and solver_side in {"red", "black"}:
        expected_solver = "black" if fen_parts[1] == "w" else "red"
        if solver_side != expected_solver:
            errors.append(
                f"Player Turn 與失着後行棋方不一致：預期 {expected_solver}，實際 {solver_side}"
            )

    rating_raw = (row.get("Rating") or "").strip()
    try:
        rating: int | None = int(rating_raw)
    except ValueError:
        rating = None
        errors.append(f"Rating 不是整數：{rating_raw or '空白'}")

    return {
        "key": key,
        "id": puzzle_id,
        "rating": rating,
        "initialFen": fen,
        "blunderMove": blunder_move,
        "solverSide": solver_side if solver_side in {"red", "black"} else None,
        "pv": pv,
        "moveCount": len(pv),
        "importStatus": "invalid" if errors else "ready",
        "importErrors": errors,
    }


def import_csv(source: Path) -> dict[str, object]:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"CSV 缺少必要欄位：{', '.join(missing)}")
        seen_ids: dict[str, int] = {}
        puzzles = [
            normalize_row(row, row_number, seen_ids)
            for row_number, row in enumerate(reader, start=2)
        ]

    canonical = json.dumps(puzzles, ensure_ascii=False, separators=(",", ":"))
    dataset_version = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    invalid_count = sum(puzzle["importStatus"] == "invalid" for puzzle in puzzles)
    return {
        "schemaVersion": "1.0",
        "datasetVersion": dataset_version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceFile": source.name,
        "puzzleCount": len(puzzles),
        "invalidCount": invalid_count,
        "puzzles": puzzles,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="將象棋棋題 CSV 轉換成前端使用的標準 JSON")
    parser.add_argument("source", type=Path, help="CSV 檔案路徑")
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "public" / "data" / "checkmate-puzzles.json",
        help="輸出 JSON 路徑",
    )
    args = parser.parse_args()

    dataset = import_csv(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    from generate_puzzle_recognition import generate_recognition

    recognition = asyncio.run(generate_recognition(dataset))
    recognition_output = args.output.with_name("checkmate-puzzle-recognition.json")
    recognition_output.write_text(
        json.dumps(recognition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"已匯入 {dataset['puzzleCount']} 題，"
        f"無效 {dataset['invalidCount']} 題，版本 {dataset['datasetVersion']}；"
        f"已生成 {recognition['puzzleCount']} 題识别结果"
    )


if __name__ == "__main__":
    main()
