"""Per-puzzle time and peak memory of the two classifiers on the pure-Python board.

Each suite runs in its own process over every puzzle of the golden snapshots, once, in dataset order with warm
caches, as a batch job would:
  checkmate  public/data/checkmate-puzzles.json
  midgame    the tactic upload CSV

Timings on one machine drift by more than 10% between sessions, so numbers from different sessions cannot be
compared. ``--baseline-root`` instead alternates this checkout with another one in the same session and exits 1
if this one is more than 10% slower on the mean, p95 or p99 (median over the rounds). The maximum is a single
puzzle and too noisy to gate on. The reference is 18bbdf7, the last commit before xq_classify existed.

Pin to one kind of core when the machine has several: on an i7-13650HX ``--cpus 0-11`` keeps the run on P-cores.

Usage (from the repository root):
  python backend/scripts/bench_classify.py --cpus 0-11
  python backend/scripts/bench_classify.py --cpus 0-11 --rounds 5 --baseline-root <checkout of 18bbdf7>
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import csv
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

THIS_ROOT = Path(__file__).resolve().parents[2]
CHECKMATE_DATASET = Path("public/data/checkmate-puzzles.json")
MIDGAME_CSV = Path("data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv")
SUITES = ("checkmate", "midgame")
METRICS = ("meanMs", "p50Ms", "p95Ms", "p99Ms", "maxMs", "peakMb")
GATED_METRICS = ("meanMs", "p95Ms", "p99Ms")
MAX_SLOWDOWN = 0.10


def load_cases(root: Path, suite: str) -> list[Any]:
    if suite == "checkmate":
        puzzles = json.loads((root / CHECKMATE_DATASET).read_text(encoding="utf-8"))["puzzles"]
        return [puzzle for puzzle in puzzles if puzzle["importStatus"] != "invalid"]
    with (root / MIDGAME_CSV).open(encoding="utf-8-sig", newline="") as handle:
        return [
            (row["fen_before"].strip(), row["blunder_move"].strip(), ast.literal_eval(row["pv"]),
             row["first_turn"].strip().lower())
            for row in csv.DictReader(handle)
        ]


def package_classifier(suite: str) -> tuple[Callable[[Any], Any], str]:
    """The public entry points; the package uses the pure-Python board unless told otherwise."""
    import xq_classify

    if suite == "checkmate":
        def classify(puzzle: dict[str, Any]) -> dict[str, Any]:
            return xq_classify.classify_checkmate(puzzle["initialFen"], puzzle["blunderMove"], puzzle["pv"]).to_dict()
    else:
        def classify(case: tuple[str, str, list[str], str]) -> dict[str, Any]:
            return xq_classify.classify_midgame(*case).to_dict()
    return classify, str(xq_classify.__file__)


def pre_package_classifier(suite: str) -> tuple[Callable[[Any], Any], str]:
    """The lab pipelines as they were before xq_classify, which is what the phase 0 baseline measured."""
    import app.board
    import backend.app.board

    app.board.pyffish = None
    backend.app.board.pyffish = None
    if suite == "checkmate":
        from scripts.generate_puzzle_recognition import recognize_puzzle

        loop = asyncio.new_event_loop()

        def classify(puzzle: dict[str, Any]) -> dict[str, Any]:
            return loop.run_until_complete(recognize_puzzle(puzzle))
    else:
        from backend.app.tactical_categories import analyze_midgame_categories

        def classify(case: tuple[str, str, list[str], str]) -> dict[str, Any]:
            return analyze_midgame_categories(*case)
    return classify, str(app.board.__file__)


def peak_memory_mb() -> float | None:
    try:
        import resource  # POSIX

        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**10, 1)
    except ImportError:
        pass
    try:
        import psutil  # Windows: peak working set

        info = psutil.Process().memory_info()
        return round(getattr(info, "peak_wset", info.rss) / 2**20, 1)
    except ImportError:
        return None


def percentile(ordered: list[float], fraction: float) -> float:
    """Nearest-rank percentile of an ascending list."""
    return ordered[max(1, math.ceil(len(ordered) * fraction)) - 1]


def parse_cpus(text: str) -> list[int]:
    cpus: list[int] = []
    for part in text.split(","):
        first, _, last = part.partition("-")
        cpus.extend(range(int(first), int(last or first) + 1))
    return cpus


def worker(root: Path, suite: str, limit: int | None, cpus: str | None) -> None:
    """Measure one suite of one checkout and print the summary as one JSON line."""
    sys.path[:1] = [str(root / "backend"), str(root)]  # nothing from the checkout running this script
    if cpus:
        import psutil

        psutil.Process().cpu_affinity(parse_cpus(cpus))
    cases = load_cases(root, suite)[:limit]
    has_package = (root / "backend" / "xq_classify").is_dir()
    classify, origin = package_classifier(suite) if has_package else pre_package_classifier(suite)
    if not Path(origin).resolve().is_relative_to(root.resolve()):
        raise SystemExit(f"measured the wrong checkout: {origin}")
    seconds: list[float] = []
    rejected = 0
    for case in cases:
        started = time.perf_counter()
        try:
            classify(case)
        except ValueError:  # a line that does not replay still costs time; the batch job records it as invalid
            rejected += 1
        seconds.append(time.perf_counter() - started)
    ordered = sorted(seconds)
    print(json.dumps({
        "origin": origin,
        "count": len(ordered),
        "rejected": rejected,
        "meanMs": round(statistics.fmean(ordered) * 1000, 3),
        "p50Ms": round(percentile(ordered, 0.50) * 1000, 3),
        "p95Ms": round(percentile(ordered, 0.95) * 1000, 3),
        "p99Ms": round(percentile(ordered, 0.99) * 1000, 3),
        "maxMs": round(ordered[-1] * 1000, 3),
        "peakMb": peak_memory_mb(),
    }))


def measure(root: Path, suite: str, args: argparse.Namespace) -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--root", str(root), "--suite", suite]
    if args.limit:
        command += ["--limit", str(args.limit)]
    if args.cpus:
        command += ["--cpus", args.cpus]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{suite} failed in {root}:\n{completed.stdout}\n{completed.stderr}")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def medians(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        key: statistics.median(run[key] for run in runs) for key in METRICS if runs[0][key] is not None
    }
    summary.update(count=runs[0]["count"], rejected=runs[0]["rejected"], origin=runs[0]["origin"])
    return summary


def short(metric: str) -> str:
    return metric.removesuffix("Ms").removesuffix("Mb")


def line(suite: str, name: str, summary: dict[str, Any]) -> str:
    cells = "  ".join(f"{short(key)} {summary[key]:>8.2f}" for key in METRICS if key in summary)
    return f"{suite:10}{name:10}{cells}"


def compare(current: dict[str, Any], baseline: dict[str, Any]) -> tuple[dict[str, float], bool]:
    """The relative change of every metric, and whether the gated ones stay within the budget."""
    if (current["count"], current["rejected"]) != (baseline["count"], baseline["rejected"]):
        raise SystemExit(f"the two checkouts did different work: {current} / {baseline}")
    changes = {key: current[key] / baseline[key] - 1 for key in METRICS if key in current and key in baseline}
    return changes, all(changes[key] <= MAX_SLOWDOWN for key in GATED_METRICS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Time the two classifiers on the pure-Python board.")
    parser.add_argument("--suite", choices=[*SUITES, "all"], default="all")
    parser.add_argument("--limit", type=int, help="only the first N puzzles of each suite")
    parser.add_argument("--cpus", help="CPU list to pin to, such as 0-11 (needs psutil)")
    parser.add_argument("--rounds", type=int, default=1, help="runs per suite and checkout; the median is reported")
    parser.add_argument("--baseline-root", type=Path, help="another checkout to alternate with")
    parser.add_argument("--json", type=Path, help="also write the results to this file")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--root", type=Path, default=THIS_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.root.resolve(), args.suite, args.limit, args.cpus)
        return 0

    sides = {"current": THIS_ROOT}
    if args.baseline_root:
        sides["baseline"] = args.baseline_root.resolve()
    suites = SUITES if args.suite == "all" else (args.suite,)
    runs: dict[tuple[str, str], list[dict[str, Any]]] = {(suite, name): [] for suite in suites for name in sides}
    for index in range(args.rounds):
        order = list(sides.items()) if index % 2 == 0 else list(reversed(sides.items()))  # cancels slow drift
        for suite in suites:
            for name, root in order:
                runs[suite, name].append(measure(root, suite, args))

    passed = True
    report: dict[str, Any] = {"rounds": args.rounds, "cpus": args.cpus, "suites": {}}
    for suite in suites:
        entry = {name: medians(runs[suite, name]) for name in sides}
        print(line(suite, "current", entry["current"]))
        if "baseline" in sides:
            print(line(suite, "baseline", entry["baseline"]))
            changes, within = compare(entry["current"], entry["baseline"])
            passed = passed and within
            entry["change"] = changes
            print(f"{suite:10}{'change':10}" + "  ".join(f"{short(key)} {change:+8.1%}" for key, change in changes.items()))
        report["suites"][suite] = entry
    report["passed"] = passed
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not passed:
        print(f"FAILED: more than {MAX_SLOWDOWN:.0%} slower than the baseline on the mean, p95 or p99")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
