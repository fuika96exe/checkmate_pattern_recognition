"""Sample capturing puzzles from a CSV and label each with the tactical-category recognizer."""
from __future__ import annotations

import argparse
import ast
import csv
import faulthandler
import json
import hashlib
import time
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT.parent))

from backend.app.midgame_tactics import LABELS, RULES_VERSION, ReplayError, material_result
from backend.app.notation import chinese_notation
from backend.app.tactical_categories import analyze_midgame_categories
from backend.scripts.import_puzzles import adapt_upload_row

GAIN_LABELS = {"gain": "得子", "no_gain": "並非得子"}


def material_gain(fens: list[str], pv: list[str]) -> dict[str, object]:
    """Compatibility helper; score the complete timeline, including the blunder."""
    from backend.app.board import side_to_move
    if not pv or len(fens) < 3:
        raise ValueError("A complete replay is required")
    return material_result(fens[0], fens[-1], side_to_move(fens[1]))


def label_puzzle(row: dict[str, str]) -> dict[str, object]:
    original = dict(row)
    record = {"id": row.get("Encrypted Id") or row.get("url") or "unknown",
              "rating": None, "initialFen": row.get("Initial Fen", row.get("fen_before", "")),
              "blunderMove": row.get("Blunder Move", row.get("blunder_move", "")),
              "solverSide": row.get("Player Turn", row.get("first_turn", "")),
              "pv": [], "url": row.get("View Link", row.get("url", "")),
              "sourceRow": row.get("_sourceRow"), "rulesVersion": RULES_VERSION}
    try:
        if "fen_before" in row:
            row = {**adapt_upload_row(row), "_sourceRow": row.get("_sourceRow")}
        record.update(id=row["Encrypted Id"], initialFen=row["Initial Fen"].strip(),
                      blunderMove=row["Blunder Move"].strip(), solverSide=row["Player Turn"].strip().lower(),
                      url=row.get("View Link", ""))
        try:
            parsed_pv = ast.literal_eval(row["Pv"])
        except (ValueError, SyntaxError) as error:
            raise ValueError("PV must parse as a UCCI string list") from error
        if not isinstance(parsed_pv, list) or not all(isinstance(move, str) for move in parsed_pv):
            raise ValueError("PV must parse as a UCCI string list")
        record["pv"] = parsed_pv
        try:
            record["rating"] = int(row["Rating"]) if row.get("Rating") else None
        except ValueError:
            pass  # metadata does not invalidate a legal puzzle
    except (ReplayError, ValueError, SyntaxError, KeyError, TypeError) as error:
        return {**record, "status": "invalid", "error": str(error),
                "errorPly": getattr(error, "ply", 0), "errorFen": getattr(error, "fen", record["initialFen"]),
                "errorMove": getattr(error, "move", None), "sourceInput": original,
                "tactics": [], "fens": [], "plies": [], "material": None, "reviewReasons": [], "supportingEvidence": []}
    try:
        result = analyze_midgame_categories(record["initialFen"], record["blunderMove"], record["pv"], record["solverSide"])
        # Display only: Chinese notation of each ply, read from the position before it.
        for ply, fen_before in zip(result["plies"], result["fens"]):
            ply["chinese"] = chinese_notation(fen_before, ply["ucci"])
        return {**record, **result}
    except ReplayError as error:
        return {**record, "status": "invalid", "error": str(error),
                "errorPly": error.ply, "errorFen": error.fen, "errorMove": error.move,
                "sourceInput": original, "tactics": [], "fens": [], "plies": [],
                "material": None, "reviewReasons": [], "supportingEvidence": []}
    # Detector/programming failures propagate and leave the public index intact;
    # they must not be silently counted as malformed input.


def row_from_existing_record(record: dict[str, object]) -> dict[str, str]:
    """Adapt a stored puzzle record so the current rules can relabel it."""
    if record.get("sourceInput"):
        original = dict(record["sourceInput"])
        if record.get("sourceRow") is not None:
            original["_sourceRow"] = record["sourceRow"]
        return original
    return {
        "Pv": repr(record["pv"]),
        "_sourceRow": record.get("sourceRow"),
        "Blunder Move": str(record["blunderMove"]),
        "Encrypted Id": str(record["id"]),
        "Rating": "" if record.get("rating") is None else str(record["rating"]),
        "Initial Fen": str(record["initialFen"]),
        "Player Turn": str(record.get("solverSide") or ""),
        "View Link": str(record.get("url") or ""),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    started = time.perf_counter()
    root = BACKEND_ROOT.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=root / "data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv")
    parser.add_argument("--output", type=Path, default=root / "public" / "data" / "capturing-tactics.json")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260702)
    parser.add_argument("--workers", type=int, default=4, help="Number of analysis worker processes.")
    parser.add_argument("--progress-every", type=int, default=100, help="Report progress every N puzzles (0 disables).")
    parser.add_argument("--existing-dataset", type=Path,
                        help="Relabel every puzzle already stored in this JSON dataset; no source CSV is needed.")
    parser.add_argument("--start", type=int, default=0,
                        help="First puzzle index (0-based) to label from an upload CSV or an existing dataset (default: 0).")
    parser.add_argument("--limit", type=int,
                        help="Maximum puzzles to label from an upload CSV or an existing dataset; omit for the remainder.")
    args = parser.parse_args()

    if args.existing_dataset:
        existing = json.loads(args.existing_dataset.read_text(encoding="utf-8"))
        stored_puzzles = list(existing["puzzles"])
        source_hash = existing.get("sourceSha256")
        start = max(0, args.start)
        end = len(stored_puzzles) if args.limit is None else min(len(stored_puzzles), start + max(0, args.limit))
        if start != 0 or end != len(stored_puzzles):
            if args.output.resolve() == (root / "public/data/capturing-tactics.json").resolve():
                parser.error("Partial relabels require an independent --output outside the public index")
        indexes = list(range(start, end))
        sample = [row_from_existing_record(stored_puzzles[index]) for index in indexes]
        source = str(existing.get("source", args.existing_dataset.name))
        seed = int(existing.get("seed", args.seed))
        eligible_rows = int(existing.get("eligibleRows", len(stored_puzzles)))
    else:
        source_hash = hashlib.sha256(args.csv.read_bytes()).hexdigest()
        with args.csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows = [{**row, "_sourceRow": index} for index, row in enumerate(rows, 2)]
        if rows and "fen_before" in rows[0]:
            # Upload exports are labelled in source order; --start/--limit pick a contiguous slice.
            start = max(0, args.start)
            end = len(rows) if args.limit is None else min(len(rows), start + max(0, args.limit))
            sample = rows[start:end]
        else:
            rows = [row for row in rows if row["State"] == "PUBLISHED" and row["Theme"] == "CAPTURING"]
            sample = random.Random(args.seed).sample(rows, min(args.count, len(rows)))
        source = args.csv.name
        seed = args.seed
        eligible_rows = len(rows)

    if args.workers == 1 or (args.existing_dataset and len(sample) < 32):
        # Short resumable ranges should not pay Windows process-pool startup
        # cost.  A full-dataset relabel below benefits substantially from
        # using all available cores.
        relabelled = [label_puzzle(row) for row in sample]
    else:
        print(f"Analysing {len(sample)} puzzles with {args.workers} workers", flush=True)
        with ProcessPoolExecutor(max_workers=args.workers, initializer=faulthandler.enable) as pool:
            relabelled = []
            for completed, puzzle in enumerate(pool.map(label_puzzle, sample, chunksize=4), start=1):
                relabelled.append(puzzle)
                if args.progress_every > 0 and completed % args.progress_every == 0:
                    print(f"Analysed {completed}/{len(sample)} puzzles", flush=True)
    # A partial export contains only newly analyzed rows, never mixed rule versions.
    puzzles = relabelled
    summary: dict[str, int] = {"matched": 0, "unmatched": 0, "invalid": 0, "gain_gain": 0, "gain_no_gain": 0, **{label: 0 for label in LABELS}}
    for puzzle in puzzles:
        if puzzle["status"] in summary:
            summary[str(puzzle["status"])] += 1
        material = puzzle["material"]
        if material:
            key = "gain_" + str(material["kind"])  # type: ignore[index]
            summary[key] = summary.get(key, 0) + 1
        for tactic in puzzle["tactics"]:  # type: ignore[union-attr]
            summary[tactic] = summary.get(tactic, 0) + 1
    payload = {
        "schemaVersion": "2.1", "rulesVersion": RULES_VERSION, "labels": LABELS, "gainLabels": GAIN_LABELS,
        "source": source, "sourceSha256": source_hash, "seed": seed, "eligibleRows": eligible_rows,
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "partial": len(puzzles) != eligible_rows,
        "generatedAt": datetime.now(timezone.utc).isoformat(), "puzzleCount": len(puzzles),
        "summary": summary, "puzzles": puzzles,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    temporary_output.replace(args.output)
    print(f"wrote {len(puzzles)} puzzles of {eligible_rows} eligible -> {args.output}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
