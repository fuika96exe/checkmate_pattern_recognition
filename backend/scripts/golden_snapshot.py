"""Golden snapshot of the checkmate and midgame classifiers (phase-0 refactor guard).

The phase-0 refactor (``backend/xq_classify``) must not change any label,
evidence field or rules version.  This script records the complete output of
the lab pipelines on the pure-Python board and diffs later runs against it.

Suites (each runs in its own process: clean caches, separate peak memory):
  checkmate  every puzzle in public/data/checkmate-puzzles.json:
             ``recognize_puzzle`` (status / patternIds / materialId / error) and
             the full ``/api/analyze-puzzle-line`` response (matches, evidence,
             position flags, timeline), serialised by alias as the API serves it.
  midgame    every row of the tactic upload CSV, in source order:
             ``generate_capturing_tactics.label_puzzle`` (tactics, material,
             status, plies with evidence, review reasons, invalid-row errors).

Modes:
  snapshot  write <out>/<suite>.jsonl, <suite>.meta.json, <suite>.timing.json
  compare   diff two snapshot directories puzzle by puzzle; exit 1 on any diff
  verify    snapshot into <golden>/current, then compare with <golden>/baseline
            (``--board native``: current-native against baseline-native)

Timing covers only the classifier entry point (``recognize_puzzle`` and
``analyze_midgame_categories``), processed in dataset order with warm caches,
as in a batch run.  Output lives under backend/.golden/ (not tracked by git).

The two boards are not interchangeable here.  Labels agree, but:
  * the pure-Python fallback never resets the FEN halfmove clock on a capture
    (pyffish does), so FEN strings in the timeline, ``fens`` and evidence differ;
  * legal moves come out in a different order, which shows in the API's
    ``legalMoves`` and in evidence that cites the first defending reply.
Python and native snapshots therefore each need their own baseline.

Usage (from the repository root):
  python backend/scripts/golden_snapshot.py snapshot --out backend/.golden/baseline
  python backend/scripts/golden_snapshot.py verify
  python backend/scripts/golden_snapshot.py compare backend/.golden/baseline backend/.golden/run2
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for _path in (BACKEND_ROOT, REPO_ROOT):  # `app.*` (checkmate gate) and `backend.app.*` (midgame gate)
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

SUITES = ("checkmate", "midgame")
GOLDEN_ROOT = BACKEND_ROOT / ".golden"
CHECKMATE_DATASET = REPO_ROOT / "public" / "data" / "checkmate-puzzles.json"
MIDGAME_CSV = REPO_ROOT / "data" / "puzzle-sources" / "Puzzles_2026-10-22_08-12-00_tactic_upload.csv"
MAX_PATHS_PER_PUZZLE = 25
MAX_VALUE_CHARS = 240


# --------------------------------------------------------------------------- board

def use_board(name: str) -> None:
    """Select the move generator before any analysis runs (``xq_classify.board.use_backend``).

    Importing ``app.board`` installs pyffish as the lab default, and the suites
    import it under two names (``app.board``, ``backend.app.board``), each one
    installing on first import.  Both are imported first, so neither can
    override the choice made here.
    """
    import app.board
    import backend.app.board  # noqa: F401 - see above
    from xq_classify import board as package_board

    if name == "python":
        package_board.use_backend(package_board.PURE_BACKEND)
    elif app.board.NATIVE_BACKEND is None:
        raise SystemExit("pyffish is unavailable; cannot snapshot the native board")
    else:
        package_board.use_backend(app.board.NATIVE_BACKEND)


# --------------------------------------------------------------------------- suites

def checkmate_records(limit: int | None, timings: list[tuple[str, float]]) -> Iterator[dict[str, Any]]:
    from app.main import api_analyze_puzzle_line
    from app.models import PuzzleLineRequest
    from scripts.generate_puzzle_recognition import recognize_puzzle

    dataset = json.loads(CHECKMATE_DATASET.read_text(encoding="utf-8"))
    puzzles = dataset["puzzles"][:limit]
    loop = asyncio.new_event_loop()
    try:
        for puzzle in puzzles:
            key = str(puzzle["key"])
            started = time.perf_counter()
            recognized = loop.run_until_complete(recognize_puzzle(puzzle))
            timings.append((key, time.perf_counter() - started))
            record: dict[str, Any] = {"key": key, "recognize": recognized}
            if puzzle["importStatus"] != "invalid":
                request = PuzzleLineRequest(fen=puzzle["initialFen"], blunder_move=puzzle["blunderMove"],
                                            pv=puzzle["pv"])
                response = loop.run_until_complete(api_analyze_puzzle_line(request))
                record["api"] = response.model_dump(mode="json", by_alias=True)
            yield record
    finally:
        loop.close()


def midgame_rows(limit: int | None) -> list[dict[str, Any]]:
    with MIDGAME_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    # Same row numbering as generate_capturing_tactics.main (header is row 1).
    return [{**row, "_sourceRow": index} for index, row in enumerate(rows, 2)][:limit]


def midgame_records(limit: int | None, timings: list[tuple[str, float]]) -> Iterator[dict[str, Any]]:
    import backend.scripts.generate_capturing_tactics as capturing

    core = capturing.analyze_midgame_categories
    current: dict[str, Any] = {}

    def timed_core(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return core(*args, **kwargs)
        finally:
            timings.append((current["key"], time.perf_counter() - started))

    capturing.analyze_midgame_categories = timed_core  # label_puzzle looks the name up at call time
    try:
        for row in midgame_rows(limit):
            key = f"row-{row['_sourceRow']}"
            current["key"] = key
            try:
                yield {"key": key, "result": capturing.label_puzzle(row)}
            except Exception as error:  # a programming failure is part of the observable behaviour
                yield {"key": key, "exception": {"type": type(error).__name__, "message": str(error)}}
    finally:
        capturing.analyze_midgame_categories = core


SUITE_RUNNERS: dict[str, Callable[[int | None, list[tuple[str, float]]], Iterator[dict[str, Any]]]] = {
    "checkmate": checkmate_records,
    "midgame": midgame_records,
}
SUITE_INPUTS = {"checkmate": CHECKMATE_DATASET, "midgame": MIDGAME_CSV}


# --------------------------------------------------------------------------- measurements

def peak_memory_mb() -> float | None:
    try:
        import resource  # POSIX
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(peak / (2**20 if sys.platform == "darwin" else 2**10), 1)
    except ImportError:
        pass
    try:
        import psutil  # Windows: peak working set
        info = psutil.Process().memory_info()
        return round(getattr(info, "peak_wset", info.rss) / 2**20, 1)
    except ImportError:
        return None


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile of an ascending list."""
    if not sorted_values:
        return 0.0
    return sorted_values[max(1, math.ceil(len(sorted_values) * fraction)) - 1]


def timing_summary(timings: list[tuple[str, float]]) -> dict[str, Any]:
    values = sorted(seconds for _, seconds in timings)
    ms = lambda seconds: round(seconds * 1000, 3)  # noqa: E731
    slowest = sorted(timings, key=lambda item: item[1], reverse=True)[:10]
    return {
        "count": len(values),
        "totalSeconds": round(sum(values), 3),
        "meanMs": ms(sum(values) / len(values)) if values else 0.0,
        "p50Ms": ms(percentile(values, 0.50)),
        "p95Ms": ms(percentile(values, 0.95)),
        "p99Ms": ms(percentile(values, 0.99)),
        "maxMs": ms(values[-1]) if values else 0.0,
        "peakMemoryMb": peak_memory_mb(),
        "slowest": [{"key": key, "ms": ms(seconds)} for key, seconds in slowest],
    }


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()

    return {"head": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(run("status", "--porcelain", "--untracked-files=no"))}


# --------------------------------------------------------------------------- snapshot

def snapshot_suite(suite: str, out: Path, board: str, limit: int | None, cpus: str | None) -> None:
    use_board(board)
    out.mkdir(parents=True, exist_ok=True)
    timings: list[tuple[str, float]] = []
    rules_versions: set[str] = set()
    statuses: dict[str, int] = {}
    count = 0
    started = time.perf_counter()
    with (out / f"{suite}.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in SUITE_RUNNERS[suite](limit, timings):
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
            status, version = record_status(record)
            statuses[status] = statuses.get(status, 0) + 1
            if version:
                rules_versions.add(version)
            if count % 500 == 0:
                print(f"  {suite}: {count}", flush=True)
    elapsed = time.perf_counter() - started
    source = SUITE_INPUTS[suite]
    meta = {
        "suite": suite, "board": board, "count": count, "limit": limit, "cpus": cpus, "statuses": statuses,
        "rulesVersions": sorted(rules_versions), "elapsedSeconds": round(elapsed, 3),
        "input": {"path": source.relative_to(REPO_ROOT).as_posix(),
                  "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "git": git_state(), "python": platform.python_version(), "platform": platform.platform(),
    }
    (out / f"{suite}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / f"{suite}.timing.json").write_text(json.dumps(timing_summary(timings), indent=2) + "\n", encoding="utf-8")
    print(f"  {suite}: {count} records, {statuses}, {elapsed:.1f} s -> {out}", flush=True)


def record_status(record: dict[str, Any]) -> tuple[str, str | None]:
    if "exception" in record:
        return "exception", None
    if "recognize" in record:
        return str(record["recognize"].get("status")), (record.get("api") or {}).get("rulesVersion")
    result = record["result"]
    return str(result.get("status")), result.get("rulesVersion")


def parse_cpus(text: str) -> list[int]:
    cpus: list[int] = []
    for part in text.split(","):
        first, _, last = part.partition("-")
        cpus.extend(range(int(first), int(last or first) + 1))
    return cpus


def pin_cpus(text: str | None) -> None:
    """Pin to the given logical CPUs.  On hybrid CPUs (P/E cores) unpinned timings vary about 2x."""
    if not text:
        return
    import psutil  # only needed for timing runs

    psutil.Process().cpu_affinity(parse_cpus(text))


def run_snapshot(args: argparse.Namespace) -> None:
    suites = SUITES if args.suite == "all" else (args.suite,)
    if len(suites) == 1:
        pin_cpus(args.cpus)
        snapshot_suite(suites[0], args.out, args.board, args.limit, args.cpus)
        return
    for suite in suites:  # one fresh process per suite
        command = [sys.executable, str(Path(__file__).resolve()), "snapshot", "--suite", suite,
                   "--out", str(args.out), "--board", args.board]
        if args.limit is not None:
            command += ["--limit", str(args.limit)]
        if args.cpus:
            command += ["--cpus", args.cpus]
        print(f"snapshot {suite} ({args.board} board)", flush=True)
        subprocess.run(command, check=True)


# --------------------------------------------------------------------------- compare

def short(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + "…"


def diff_values(old: Any, new: Any, path: str, out: list[str]) -> None:
    if len(out) >= MAX_PATHS_PER_PUZZLE:
        return
    if isinstance(old, dict) and isinstance(new, dict):
        for key in [*old, *(k for k in new if k not in old)]:
            child = f"{path}.{key}" if path else str(key)
            if key not in new:
                out.append(f"{child}: removed (was {short(old[key])})")
            elif key not in old:
                out.append(f"{child}: added {short(new[key])}")
            else:
                diff_values(old[key], new[key], child, out)
        if old.keys() == new.keys() and list(old) != list(new):
            out.append(f"{path or '<root>'}: key order {list(old)} -> {list(new)}")
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            out.append(f"{path}: length {len(old)} -> {len(new)}")
        for index, (a, b) in enumerate(zip(old, new)):
            diff_values(a, b, f"{path}[{index}]", out)
        for index in range(len(new), len(old)):
            out.append(f"{path}[{index}]: removed (was {short(old[index])})")
        for index in range(len(old), len(new)):
            out.append(f"{path}[{index}]: added {short(new[index])}")
    elif old != new or type(old) is not type(new):
        out.append(f"{path}: {short(old)} -> {short(new)}")


def load_lines(path: Path) -> dict[str, str]:
    lines: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            key = json.loads(line)["key"]
            if key in lines:
                raise SystemExit(f"duplicate key {key} in {path}")
            lines[key] = line.rstrip("\n")
    return lines


def compare_suite(suite: str, old_dir: Path, new_dir: Path) -> dict[str, Any]:
    old_lines, new_lines = load_lines(old_dir / f"{suite}.jsonl"), load_lines(new_dir / f"{suite}.jsonl")
    changed: dict[str, list[str]] = {}
    for key in old_lines.keys() & new_lines.keys():
        if old_lines[key] == new_lines[key]:
            continue
        paths: list[str] = []
        diff_values(json.loads(old_lines[key]), json.loads(new_lines[key]), "", paths)
        changed[key] = paths or ["serialisation differs (whitespace or number formatting)"]
    order = list(old_lines)
    return {
        "suite": suite, "old": len(old_lines), "new": len(new_lines),
        "identical": len(old_lines.keys() & new_lines.keys()) - len(changed),
        "missing": sorted(old_lines.keys() - new_lines.keys(), key=order.index),
        "extra": sorted(new_lines.keys() - old_lines.keys()),
        "changed": dict(sorted(changed.items(), key=lambda item: order.index(item[0]))),
    }


def timing_line(suite: str, old_dir: Path, new_dir: Path) -> str | None:
    try:
        old = json.loads((old_dir / f"{suite}.timing.json").read_text(encoding="utf-8"))
        new = json.loads((new_dir / f"{suite}.timing.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None

    def cell(field: str) -> str:
        a, b = old.get(field), new.get(field)
        if not a or b is None:
            return f"{field} {a} -> {b}"
        return f"{field} {a} -> {b} ({(b - a) / a:+.0%})"

    return "  timing  " + ", ".join(cell(f) for f in ("meanMs", "p95Ms", "p99Ms", "maxMs", "peakMemoryMb"))


def run_compare(old_dir: Path, new_dir: Path, report: Path | None) -> int:
    suites = [s for s in SUITES if (old_dir / f"{s}.jsonl").exists() and (new_dir / f"{s}.jsonl").exists()]
    if not suites:
        raise SystemExit(f"no common suite between {old_dir} and {new_dir}")
    results = [compare_suite(suite, old_dir, new_dir) for suite in suites]
    failed = False
    for result in results:
        bad = len(result["changed"]) + len(result["missing"]) + len(result["extra"])
        failed |= bad > 0
        print(f"{result['suite']}: {result['identical']}/{result['old']} identical, "
              f"{len(result['changed'])} changed, {len(result['missing'])} missing, {len(result['extra'])} extra")
        for key in result["missing"][:10]:
            print(f"  missing {key}")
        for key in result["extra"][:10]:
            print(f"  extra   {key}")
        for key, paths in list(result["changed"].items())[:20]:
            print(f"  changed {key}")
            for line in paths[:8]:
                print(f"      {line}")
        line = timing_line(result["suite"], old_dir, new_dir)
        if line:
            print(line)
    report = report or new_dir / f"diff-vs-{old_dir.name}.json"
    report.write_text(json.dumps({"old": str(old_dir), "new": str(new_dir), "suites": results},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("DIFFERENCES FOUND" if failed else "0 differences") + f"; report: {report}")
    return 1 if failed else 0


# --------------------------------------------------------------------------- cli

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    def add_run_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("--suite", choices=("all", *SUITES), default="all")
        command.add_argument("--board", choices=("python", "native"), default="python")
        command.add_argument("--limit", type=int, help="Only the first N puzzles of each suite (smoke runs).")
        command.add_argument("--cpus", help="Pin to these logical CPUs for timing, e.g. 0-11 (needs psutil).")

    snapshot = commands.add_parser("snapshot", help="Record the current code's output.")
    snapshot.add_argument("--out", type=Path, default=GOLDEN_ROOT / "current")
    add_run_options(snapshot)

    compare = commands.add_parser("compare", help="Diff two snapshot directories.")
    compare.add_argument("old", type=Path)
    compare.add_argument("new", type=Path)
    compare.add_argument("--report", type=Path)

    verify = commands.add_parser("verify", help="Snapshot into <golden>/current and compare with <golden>/baseline.")
    verify.add_argument("--golden", type=Path, default=GOLDEN_ROOT)
    add_run_options(verify)

    args = parser.parse_args()
    if args.command == "snapshot":
        run_snapshot(args)
        return 0
    if args.command == "compare":
        return run_compare(args.old, args.new, args.report)
    suffix = "" if args.board == "python" else f"-{args.board}"
    baseline = args.golden / f"baseline{suffix}"
    if not baseline.exists():
        raise SystemExit(f"no baseline at {baseline}; run `snapshot --board {args.board} --out {baseline}` "
                         "on the pre-refactor code")
    args.out = args.golden / f"current{suffix}"
    run_snapshot(args)
    return run_compare(baseline, args.out, None)


if __name__ == "__main__":
    sys.exit(main())
