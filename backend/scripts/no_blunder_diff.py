"""Differential check of the no-blunder entry (``blunder=None``) against the frozen sets.

For every effective frozen case (newest entry per puzzle, as the gates read
them) the script plays the blunder, then classifies the resulting position with
``blunder=None`` and the same PV.  It compares the result with:

* the frozen expectation (restricted to the version's vocabulary, as the gates
  compare), which is the verdict that matters; and
* the package's own output with the blunder (unrestricted), to show which
  occurrences or patterns appear or disappear.

Differences are reported, never "fixed": they come from rules that read the
blunder, and an expert decides what the no-blunder path should say.  The frozen
files are read only.

Usage (from the repository root):
  python backend/scripts/no_blunder_diff.py --board python --out docs/reports/no-blunder-diff
  python backend/scripts/no_blunder_diff.py --board native --json-only --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.board as lab_board  # noqa: E402 - the lab's pyffish adapter, for --board native
from xq_classify import (  # noqa: E402
    CHECKMATE_RULES_VERSION,
    MIDGAME_RULES_VERSION,
    PACKAGE_VERSION,
    ReplayError,
    board,
    classify_checkmate,
    classify_midgame,
    clear_caches,
)
from xq_classify.labels import CHECKMATE_PATTERNS_ZH_TW, MATING_MATERIAL_ZH_TW, MIDGAME_LABELS_ZH_TW  # noqa: E402

FIXTURES = BACKEND_ROOT / "tests" / "fixtures"


def effective_cases(suite: str) -> list[tuple[dict, dict]]:
    """Newest frozen entry per puzzle, with its version file (the gates' ``effective_cases``)."""
    folder = FIXTURES / suite
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    files = [json.loads((folder / name).read_text(encoding="utf-8")) for name in manifest["frozen"]]
    effective: dict[str, tuple[dict, dict]] = {}
    for data in sorted(files, key=lambda d: d["version"]):
        for case in data["cases"]:
            effective[case["id"]] = (case, data)
    return list(effective.values())


def _occurrences(result: dict) -> set[tuple[str, int, str]]:
    """``(label, triggerPly, relationKind)`` of every occurrence, visible or suppressed."""
    found = {
        (o["id"], o["evidence"]["triggerPly"], o["evidence"]["relationKind"])
        for ply in result["plies"]
        for o in ply["occurrences"]
    }
    found.update(
        (o["id"], o["evidence"]["triggerPly"], o["evidence"]["relationKind"]) for o in result["supportingEvidence"]
    )
    return found


def _midgame_row(case: dict, data: dict) -> dict[str, Any]:
    vocabulary = set(data["vocabulary"])
    fen, blunder, pv, solver = case["initialFen"], case["blunderMove"], list(case["pv"]), case["solverSide"]
    start = board.apply_move(fen, blunder)
    base = classify_midgame(fen, blunder, pv, solver).to_dict()
    row: dict[str, Any] = {
        "id": case["id"],
        "version": data["version"],
        "sourceRow": case.get("sourceRow"),
        "url": case.get("url"),
        "startFen": start,
        "blunder": blunder,
        "pv": pv,
        "solver": solver,
        "frozen": {"tactics": sorted(case["expected"]["tactics"]), "material": case["expected"]["material"]},
        "withBlunder": {"tactics": base["tactics"], "material": base["material"]},
    }
    try:
        new = classify_midgame(start, None, pv, solver).to_dict()
    except ReplayError as error:
        row.update(verdict="error", error=f"ply {error.ply}: {error}")
        return row
    got = (sorted(set(new["tactics"]) & vocabulary), new["material"]["kind"])
    old_occ, new_occ = _occurrences(base), _occurrences(new)
    row.update(
        noBlunder={"tactics": new["tactics"], "material": new["material"]},
        verdict="same" if got == (row["frozen"]["tactics"], row["frozen"]["material"]) else "differs",
        engineSame=set(base["tactics"]) == set(new["tactics"]) and base["material"] == new["material"],
        occurrencesLost=sorted(old_occ - new_occ),
        occurrencesGained=sorted(new_occ - old_occ),
    )
    return row


def _checkmate_row(case: dict, data: dict) -> dict[str, Any]:
    vocabulary = set(data["vocabulary"])
    fen, blunder, pv = case["initialFen"], case["blunderMove"], list(case["pv"])
    start = board.apply_move(fen, blunder)
    base = classify_checkmate(fen, blunder, pv).to_dict()
    new = classify_checkmate(start, None, pv).to_dict()
    frozen = {"patterns": sorted(case["expected"]["patterns"]), "material": case["expected"]["material"]}
    got = {"patterns": sorted(set(new["patternIds"]) & vocabulary), "material": new.get("materialId")}
    return {
        "id": case["id"],
        "version": data["version"],
        "puzzleNumber": case.get("puzzleNumber"),
        "url": case.get("url"),
        "startFen": start,
        "blunder": blunder,
        "pv": pv,
        "frozen": frozen,
        "withBlunder": base,
        "noBlunder": new,
        "verdict": "same" if new["status"] != "invalid" and got == frozen else "differs",
        "engineSame": base == new,
    }


def run(board_name: str) -> dict[str, Any]:
    board.use_backend(lab_board.NATIVE_BACKEND if board_name == "native" else board.PURE_BACKEND)
    clear_caches()
    midgame = [_midgame_row(case, data) for case, data in effective_cases("midgame_frozen")]
    checkmate = [_checkmate_row(case, data) for case, data in effective_cases("checkmate_frozen")]
    return {
        "board": board_name,
        "packageVersion": PACKAGE_VERSION,
        "midgameRulesVersion": MIDGAME_RULES_VERSION,
        "checkmateRulesVersion": CHECKMATE_RULES_VERSION,
        "midgame": midgame,
        "checkmate": checkmate,
    }


def _names(ids: list[str], table: dict[str, str]) -> str:
    return "、".join(f"{table.get(i, i)}（{i}）" for i in ids) if ids else "—"


def _material(m: dict) -> str:
    return f"{m['kind']}（start {m['start']}，end {m['end']}，delta {m['delta']}）"


def _occ(items: list) -> str:
    return "；".join(f"{MIDGAME_LABELS_ZH_TW.get(i, i)} 第 {p} 手 {k}" for i, p, k in items) if items else "—"


def _material_only_note(r: dict) -> list[str]:
    """Name the cause when only ``material.kind`` moved: the blunder's capture now sits before the start."""
    if r["occurrencesLost"] or r["occurrencesGained"] or set(r["withBlunder"]["tactics"]) != set(r["noBlunder"]["tactics"]):
        return []
    taken = r["withBlunder"]["material"]["start"] - r["noBlunder"]["material"]["start"]
    return [
        f"- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 {taken} 分，"
        "回吃只算扯平；無失著時從失著後計算，回吃算作得子。"
    ]


def _midgame_section(rows: list[dict]) -> list[str]:
    differs = [r for r in rows if r["verdict"] != "same"]
    quiet = [r for r in rows if r["verdict"] == "same" and not r["engineSame"]]
    lines = [
        "## 中局",
        "",
        f"有效凍結題 {len(rows)} 題：與凍結標籤相同 {len(rows) - len(differs)} 題，不同 {len(differs)} 題"
        f"（其中重播錯誤 {sum(r['verdict'] == 'error' for r in rows)} 題）。",
        "",
    ]
    for r in differs:
        lines += [
            f"### {r['id']}（v{r['version']}，CSV 第 {r['sourceRow']} 列）",
            "",
            f"- 題目：{r['url']}",
            f"- 起始局面（已走失著 `{r['blunder']}`）：`{r['startFen']}`",
            f"- 解答：`{' '.join(r['pv'])}`，解題方 {r['solver']}",
            f"- 凍結標籤：{_names(r['frozen']['tactics'], MIDGAME_LABELS_ZH_TW)}；得子 {r['frozen']['material']}",
        ]
        if r["verdict"] == "error":
            lines += [f"- 無失著入口錯誤：{r['error']}", ""]
            continue
        lines += [
            f"- 無失著標籤：{_names(r['noBlunder']['tactics'], MIDGAME_LABELS_ZH_TW)}",
            f"- 得子：有失著 {_material(r['withBlunder']['material'])} → 無失著 {_material(r['noBlunder']['material'])}",
            f"- 消失的出現：{_occ(r['occurrencesLost'])}",
            f"- 新增的出現：{_occ(r['occurrencesGained'])}",
            *_material_only_note(r),
            "",
        ]
    if quiet:
        lines += ["### 凍結比對相同、但引擎輸出有變的題目", ""]
        lines += [
            f"- {r['id']}：消失 {_occ(r['occurrencesLost'])}；新增 {_occ(r['occurrencesGained'])}；"
            f"得子 {_material(r['withBlunder']['material'])} → {_material(r['noBlunder']['material'])}"
            for r in quiet
        ]
        lines.append("")
    return lines


def _mate(record: dict) -> str:
    if record["status"] == "invalid":
        return f"invalid（{record['error']}）"
    material = record.get("materialId")
    material_text = f"；子力 {MATING_MATERIAL_ZH_TW.get(material, material)}（{material}）" if material else ""
    return f"{record['status']}：{_names(record['patternIds'], CHECKMATE_PATTERNS_ZH_TW)}{material_text}"


def _checkmate_section(rows: list[dict]) -> list[str]:
    differs = [r for r in rows if r["verdict"] != "same"]
    quiet = [r for r in rows if r["verdict"] == "same" and not r["engineSame"]]
    lines = [
        "## 殺法",
        "",
        f"有效凍結題 {len(rows)} 題：與凍結標籤相同 {len(rows) - len(differs)} 題，不同 {len(differs)} 題。",
        "",
    ]
    for r in differs:
        frozen_material = r["frozen"]["material"]
        lines += [
            f"### {r['id']}（v{r['version']}，第 {r['puzzleNumber']} 題）",
            "",
            f"- 題目：{r['url']}",
            f"- 起始局面（已走失著 `{r['blunder']}`）：`{r['startFen']}`",
            f"- 解答：`{' '.join(r['pv'])}`",
            f"- 凍結：{_names(r['frozen']['patterns'], CHECKMATE_PATTERNS_ZH_TW)}；子力 {frozen_material or '—'}",
            f"- 有失著：{_mate(r['withBlunder'])}",
            f"- 無失著：{_mate(r['noBlunder'])}",
            "",
        ]
    if quiet:
        lines += ["### 凍結比對相同、但引擎輸出有變的題目", ""]
        lines += [f"- {r['id']}：{_mate(r['withBlunder'])} → {_mate(r['noBlunder'])}" for r in quiet]
        lines.append("")
    return lines


def markdown(report: dict, other: dict | None) -> str:
    lines = [
        "# 無失著入口差分報告",
        "",
        f"package `{report['packageVersion']}`，中局規則 `{report['midgameRulesVersion']}`，"
        f"殺法規則 `{report['checkmateRulesVersion']}`，棋盤 `{report['board']}`。",
        "",
        "做法：每題先走失著，再以 `blunder=None` 和原 PV 分類，與凍結標籤比較（限該版本詞彙，與關卡相同）。"
        "差異只報告，不改規則；由專家裁定無失著路徑應有的標籤。",
        "",
    ]
    if other is not None:
        same = _verdicts(report) == _verdicts(other)
        lines += [f"另一種棋盤（`{other['board']}`）的逐題結論：{'完全相同' if same else '不同，見 JSON'}。", ""]
    lines += _midgame_section(report["midgame"])
    lines += _checkmate_section(report["checkmate"])
    return "\n".join(lines).rstrip() + "\n"


def _verdicts(report: dict) -> list:
    return [
        (r["id"], r["verdict"], r.get("noBlunder", {}).get("tactics") or r.get("noBlunder", {}).get("patternIds"))
        for r in report["midgame"] + report["checkmate"]
    ]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--board", choices=("python", "native", "both"), default="both")
    parser.add_argument("--out", type=Path, required=True, help="Output path without extension (.json and .md)")
    args = parser.parse_args()
    boards = ["python", "native"] if args.board == "both" else [args.board]
    if "native" in boards and lab_board.NATIVE_BACKEND is None:
        parser.error("pyffish is unavailable")
    reports = {name: run(name) for name in boards}
    main_report = reports[boards[0]]
    other = reports.get("native") if len(boards) == 2 else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    args.out.with_suffix(".md").write_text(markdown(main_report, other), encoding="utf-8", newline="\n")
    for name, report in reports.items():
        for suite in ("midgame", "checkmate"):
            rows = report[suite]
            differs = sum(r["verdict"] != "same" for r in rows)
            changed = sum(not r.get("engineSame", False) for r in rows)
            print(f"{name:6} {suite:9} cases {len(rows):3}  differ from frozen {differs:3}  engine output changed {changed:3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
