"""Sample capturing puzzles from a CSV and label each with the tactical-category recognizer."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT.parent))

from backend.app.board import apply_move, parse_fen  # noqa: E402
from backend.app.tactical_categories import CATEGORY_RULES_VERSION, LABELS, _piece_value, analyze_tactical_categories  # noqa: E402

MAIN_PIECES = {"R", "C", "N"}
GAIN_LABELS = {"big": "得子(大子)", "small": "得子(小子)", "none": "並非得子"}


def material_gain(fens: list[str], pv: list[str]) -> dict[str, object]:
    """Net material the solver wins between the position after the blunder and the end of pv.

    Walks the pv moves from fens[1] (after the blunder), valuing each captured piece
    at its square when it is taken (so a pawn's river status is judged at capture time).
    Gain = value the solver captured - value the solver lost; main gain only counts R/C/N.
    """
    board = parse_fen(fens[1])
    solver_is_red = board[pv[0][:2]].isupper()
    total = main = 0
    captures: list[dict[str, object]] = []
    for move in pv:
        source, target = move[:2], move[2:]
        mover = board[source]
        victim = board.get(target)
        if victim and victim.upper() != "K":
            mover_red = mover.isupper()
            value = _piece_value(victim, target, "black" if mover_red else "red")
            sign = 1 if mover_red == solver_is_red else -1
            total += sign * value
            if victim.upper() in MAIN_PIECES:
                main += sign * value
            captures.append({"move": move, "piece": victim, "value": value, "by": "solver" if sign > 0 else "opponent"})
        board[target] = mover
        del board[source]
    kind = "big" if total >= 2 and main >= 2 else "small" if total >= 2 else "none"
    return {"kind": kind, "gain": total, "mainGain": main, "captures": captures}


def label_puzzle(row: dict[str, str]) -> dict[str, object]:
    pv = ast.literal_eval(row["Pv"])
    moves = [row["Blunder Move"], *pv]
    record: dict[str, object] = {
        "id": row["Encrypted Id"], "rating": int(row["Rating"]) if row["Rating"] else None,
        "initialFen": row["Initial Fen"], "blunderMove": row["Blunder Move"],
        "solverSide": row["Player Turn"], "pv": pv, "url": row["View Link"],
    }
    try:
        annotations = analyze_tactical_categories(row["Initial Fen"], moves)
    except Exception as error:  # noqa: BLE001 - keep the puzzle, report why it failed
        return {**record, "status": "invalid", "error": str(error), "tactics": [], "fens": [], "plies": [], "material": None}
    fens = [row["Initial Fen"]]
    for move in moves:
        fens.append(apply_move(fens[-1], move))
    plies = []
    tactics: list[str] = []
    for ply, (move, item) in enumerate(zip(moves, annotations), start=1):
        solver = ply > 1 and ply % 2 == 0
        occurrences = item["occurrences"]
        plies.append({"ply": ply, "ucci": move, "solver": solver, "occurrences": occurrences})
        # Exchange is a bilateral outcome: it is only confirmed when the
        # other side actually recaptures, so retain it in the puzzle summary
        # regardless of which side made that confirming move.  All other
        # tactical labels remain scoped to the solver's moves.
        if solver:
            for occurrence in occurrences:
                if occurrence["id"] not in tactics:
                    tactics.append(occurrence["id"])
        else:
            for occurrence in occurrences:
                if occurrence["id"] == "exchange" and occurrence["id"] not in tactics:
                    tactics.append(occurrence["id"])
    return {**record, "status": "matched" if tactics else "unmatched", "tactics": tactics, "fens": fens, "plies": plies,
            "material": material_gain(fens, pv)}


def row_from_existing_record(record: dict[str, object]) -> dict[str, str]:
    """Adapt a stored puzzle record so the current rules can relabel it."""
    return {
        "Pv": repr(record["pv"]),
        "Blunder Move": str(record["blunderMove"]),
        "Encrypted Id": str(record["id"]),
        "Rating": "" if record.get("rating") is None else str(record["rating"]),
        "Initial Fen": str(record["initialFen"]),
        "Player Turn": str(record.get("solverSide") or ""),
        "View Link": str(record.get("url") or ""),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = BACKEND_ROOT.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path(r"C:\Coding\puzzle_batch_update_test\All_Capturing_Puzzles_2026-10-14_10-18-45.csv"))
    parser.add_argument("--output", type=Path, default=root / "public" / "data" / "capturing-tactics.json")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260702)
    parser.add_argument("--existing-dataset", type=Path,
                        help="Relabel every puzzle already stored in this JSON dataset; no source CSV is needed.")
    parser.add_argument("--start", type=int, default=0,
                        help="First existing-dataset puzzle index to relabel (default: 0).")
    parser.add_argument("--limit", type=int,
                        help="Maximum existing-dataset puzzles to relabel; omit to relabel the remainder.")
    args = parser.parse_args()

    if args.existing_dataset:
        existing = json.loads(args.existing_dataset.read_text(encoding="utf-8"))
        stored_puzzles = list(existing["puzzles"])
        start = max(0, args.start)
        end = len(stored_puzzles) if args.limit is None else min(len(stored_puzzles), start + max(0, args.limit))
        indexes = list(range(start, end))
        sample = [row_from_existing_record(stored_puzzles[index]) for index in indexes]
        source = str(existing.get("source", args.existing_dataset.name))
        seed = int(existing.get("seed", args.seed))
        eligible_rows = int(existing.get("eligibleRows", len(stored_puzzles)))
    else:
        with args.csv.open(encoding="utf-8-sig", newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row["State"] == "PUBLISHED" and row["Theme"] == "CAPTURING"]
        sample = random.Random(args.seed).sample(rows, min(args.count, len(rows)))
        source = args.csv.name
        seed = args.seed
        eligible_rows = len(rows)

    if args.existing_dataset:
        # This mode is commonly used in short, resumable local runs.  Avoid
        # paying Windows process-pool startup cost for every small segment.
        relabelled = [label_puzzle(row) for row in sample]
    else:
        with ProcessPoolExecutor() as pool:
            relabelled = list(pool.map(label_puzzle, sample, chunksize=4))
    if args.existing_dataset:
        puzzles = stored_puzzles
        for index, puzzle in zip(indexes, relabelled):
            puzzles[index] = puzzle
    else:
        puzzles = relabelled
    summary: dict[str, int] = {"unmatched": 0, "invalid": 0}
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
        "schemaVersion": "1.0", "rulesVersion": CATEGORY_RULES_VERSION, "labels": LABELS, "gainLabels": GAIN_LABELS,
        "source": source, "seed": seed, "eligibleRows": eligible_rows,
        "generatedAt": datetime.now(timezone.utc).isoformat(), "puzzleCount": len(puzzles),
        "summary": summary, "puzzles": puzzles,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(puzzles)} puzzles of {eligible_rows} eligible -> {args.output}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
