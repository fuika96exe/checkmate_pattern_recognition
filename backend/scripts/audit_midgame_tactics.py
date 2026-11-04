"""Verify row accounting and export reproducible migration / blind-review reports."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.midgame_tactics import LABELS, material_result, replay  # noqa: E402
from backend.scripts.import_puzzles import adapt_upload_row  # noqa: E402

BASE = "ee36518e806bada0e3b4e9d2a73d01d1215a17c3"


def audit_record(item):
    row_number, raw, puzzle = item
    counts = Counter()
    row = adapt_upload_row(raw) if "fen_before" in raw else raw
    assert puzzle["sourceRow"] == row_number
    assert puzzle["id"] == row["Encrypted Id"]
    assert puzzle["initialFen"] == row["Initial Fen"]
    assert puzzle["blunderMove"] == row["Blunder Move"]
    assert puzzle["url"] == row.get("View Link", "")
    counts[puzzle["status"]] += 1
    if puzzle["status"] == "invalid":
        assert puzzle["material"] is None and not puzzle["tactics"]
        assert isinstance(puzzle["errorPly"], int) and puzzle["errorFen"]
        return counts
    assert puzzle["pv"] == ast.literal_eval(row["Pv"])
    assert puzzle["solverSide"] == row["Player Turn"].strip().lower()
    positions, events = replay(puzzle["initialFen"], puzzle["blunderMove"], puzzle["pv"], puzzle["solverSide"])
    assert [p.fen for p in positions] == puzzle["fens"]
    assert puzzle["material"] == material_result(puzzle["fens"][0], puzzle["fens"][-1], puzzle["solverSide"])
    counts["gain_" + puzzle["material"]["kind"]] += 1
    found = set()
    occurrence_keys = set()
    for event, ply in zip(events, puzzle["plies"], strict=True):
        assert event.ply == ply["ply"] and event.move == ply["ucci"]
        assert ply["solver"] == (event.ply > 1 and event.side == puzzle["solverSide"])
        for occurrence in ply["occurrences"]:
            assert ply["solver"]
            ev = occurrence["evidence"]
            assert ev["triggerPly"] == ply["ply"]
            assert ev["triggerPly"] <= ev["confirmedPly"] <= len(events)
            assert ev["key"] not in occurrence_keys
            occurrence_keys.add(ev["key"])
            assert all(ref["id"] and ref["square"] and ref["piece"] for ref in ev["actors"] + ev["targets"])
            for ref in ev["actors"] + ev["targets"]:
                assert any(pos.ids.get(ref["square"]) == ref["id"] for pos in positions)
            found.add(occurrence["id"])
    assert found == set(puzzle["tactics"]) and len(found) == len(puzzle["tactics"])
    assert puzzle["status"] == ("matched" if found else "unmatched")
    all_occurrences = [o for ply in puzzle["plies"] for o in ply["occurrences"]]
    for occurrence in puzzle["supportingEvidence"]:
        ev = occurrence["evidence"]
        assert ev["key"] not in occurrence_keys
        occurrence_keys.add(ev["key"])
        assert 2 <= ev["triggerPly"] <= ev["confirmedPly"] <= len(events)
        assert occurrence["id"] not in found and occurrence["suppressedBy"]
        assert all(any(pos.ids.get(ref["square"]) == ref["id"] for pos in positions)
                   for ref in ev["actors"] + ev["targets"])
        all_occurrences.append(occurrence)
    for occurrence in all_occurrences:
        parent = occurrence["evidence"].get("parentKey")
        if parent:
            assert parent in occurrence_keys
    raw_labels = {o["id"] for o in all_occurrences}
    assert raw_labels <= set(LABELS)
    if puzzle["material"]["kind"] == "gain":
        if found - {"exchange"}:
            assert "exchange" not in found
    else:
        assert not puzzle["supportingEvidence"]
    counts.update(found)

    return counts


def audit(dataset, rows, workers=4):
    assert dataset["schemaVersion"] == "2.1"
    assert set(dataset["labels"]) == set(LABELS)
    assert set(dataset["gainLabels"]) == {"gain", "no_gain"}
    assert len(rows) == dataset["puzzleCount"] == len(dataset["puzzles"])
    assert len({p["id"] for p in dataset["puzzles"]}) == len(rows)
    records = [(n, raw, p) for n, (raw, p) in enumerate(zip(rows, dataset["puzzles"]), 2)]
    counts = Counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for done, result in enumerate(pool.map(audit_record, records, chunksize=16), 1):
            counts.update(result)
            if done % 500 == 0:
                print(f"Audited {done}/{len(rows)}", flush=True)
    assert counts["gain_gain"] + counts["gain_no_gain"] + counts["invalid"] == len(rows)
    for key, value in dataset["summary"].items():
        assert counts[key] == value, (key, counts[key], value)
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "public/data/capturing-tactics.json")
    parser.add_argument("--csv", type=Path, default=ROOT / "data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/reports")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--baseline-dataset", type=Path, default=ROOT / "docs/reports/midgame-v20-baseline.json")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    source_digest = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    assert dataset["sourceSha256"] == source_digest
    with args.csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = audit(dataset, rows, args.workers)
    old_bytes = args.baseline_dataset.read_bytes()
    old = json.loads(old_bytes)
    assert old["sourceSha256"] == source_digest
    old_by_id = {p["id"]: p for p in old["puzzles"]}
    current_by_id = {p["id"]: p for p in dataset["puzzles"]}
    assert set(old_by_id) == set(current_by_id)
    assert all(p["material"] == old_by_id[p["id"]]["material"] for p in dataset["puzzles"])
    case_outcomes = []
    # Human-frozen regression set (backend/tests/fixtures/midgame_frozen). Report only; the gate is pytest.
    for frozen_file in sorted((ROOT / "backend/tests/fixtures/midgame_frozen").glob("v*.json")):
        for case in json.loads(frozen_file.read_text(encoding="utf-8"))["cases"]:
            puzzle = current_by_id.get(case["id"])
            if puzzle is None or not puzzle["material"]:
                case_outcomes.append({"id":case["id"], "kind":None, "tactics":[], "frozen":case["expected"], "match":False})
                continue
            case_outcomes.append({"id":case["id"], "kind":puzzle["material"]["kind"], "tactics":puzzle["tactics"],
                                  "frozen":case["expected"],
                                  "match":(sorted(puzzle["tactics"]) == case["expected"]["tactics"]
                                           and puzzle["material"]["kind"] == case["expected"]["material"])})
    cross = Counter((old_by_id[p["id"]]["material"]["kind"], p["material"]["kind"] if p["material"] else "invalid") for p in dataset["puzzles"])
    label_changes = {}
    for label in dict.fromkeys([*LABELS, *old.get("labels", {})]):
        before = {p["id"] for p in old["puzzles"] if label in p["tactics"]}
        after = {p["id"] for p in dataset["puzzles"] if label in p["tactics"]}
        label_changes[label] = {"added": len(after - before), "removed": len(before - after), "retained": len(before & after), "hits":len(after)}
    reasons = Counter((r["label"], r["reason"]) for p in dataset["puzzles"] for r in p["reviewReasons"])
    rng = random.Random(20261103)
    cohorts = {}
    for label in LABELS:
        ids = [p["id"] for p in dataset["puzzles"] if label in p["tactics"]]
        cohorts[label] = rng.sample(ids, min(30, len(ids)))
    unmatched = [p["id"] for p in dataset["puzzles"] if p["status"] == "unmatched"]
    cohorts["unmatched"] = rng.sample(unmatched, min(30, len(unmatched)))
    border = [p["id"] for p in dataset["puzzles"] if p["material"] and p["material"]["delta"] in (3, 4, 5)]
    cohorts["boundary_delta_3_4_5"] = rng.sample(border, min(30, len(border)))
    selected = sorted({identity for ids in cohorts.values() for identity in ids})
    rng.shuffle(selected)
    blind = [{**{key:current_by_id[i][key] for key in ("id", "initialFen", "blunderMove", "solverSide", "pv", "url")},
              "humanTactics": None, "humanClassification": None, "notes": None} for i in selected]
    candidates = [{"id":p["id"], "initialFen":p["initialFen"], "blunderMove":p["blunderMove"],
                   "pv":p["pv"], "reasons":p["reviewReasons"]} for p in dataset["puzzles"] if p["reviewReasons"]]
    report = {
        "baselineSha": BASE, "baselineRulesVersion": old["rulesVersion"],
        "baselineIndexSha256": old.get("indexSha256", hashlib.sha256(old_bytes).hexdigest()),
        "csvSha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        "indexSha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "generatedAt": dataset["generatedAt"], "elapsedSeconds": dataset["elapsedSeconds"],
        "summary":dataset["summary"], "classificationCrossTable": [
            {"old":a, "new":z, "count":n} for (a,z),n in sorted(cross.items())],
        "labelChanges":label_changes,
        "frozenCases":case_outcomes,
        "suppressionCounts": dict(Counter(o["suppressedBy"] for p in dataset["puzzles"] for o in p["supportingEvidence"])),
        "suppressionPuzzleCounts": dict(Counter(reason for p in dataset["puzzles"]
            for reason in {o["suppressedBy"] for o in p["supportingEvidence"]})),
        "rawLabelHits": {label:sum(label in {o["id"] for o in
            [*[o for ply in p["plies"] for o in ply["occurrences"]], *p["supportingEvidence"]]}
            for p in dataset["puzzles"]) for label in LABELS},
        "reviewReasons":[{"label":a, "reason":z, "count":n} for (a,z),n in sorted(reasons.items())],
        "humanReview": {"reviewed":0, "correct":None, "precision":None, "recall":None,
                        "byLabel": {label:{"reviewed":0,"correct":None} for label in LABELS}},
        "blindReviewCohorts":cohorts,
        "invalid":[{key:p.get(key) for key in ("id","sourceRow","errorPly","errorMove","errorFen","error")} for p in dataset["puzzles"] if p["status"] == "invalid"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (("midgame-v21-batch.json",report), ("midgame-v21-blind-review.json",blind), ("midgame-v21-review-candidates.json",candidates)):
        (args.output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 中局題 v2.1 批次報告", "", f"規則 `{dataset['rulesVersion']}`，資料 `{dataset['schemaVersion']}`。",
             "", f"基準 SHA：`{BASE}`。既有未提交的將殺／開局相關修改保留。",
             "", f"CSV SHA256：`{report['csvSha256']}`。",
             "", f"舊索引 SHA256：`{report['baselineIndexSha256']}`。",
             "", f"新索引 SHA256：`{report['indexSha256']}`。",
             "", f"生成時間：{dataset['generatedAt']}；分類批次耗時 {dataset['elapsedSeconds']} 秒。",
             "", f"輸入 {len(rows)} 列；有效 {len(rows)-counts['invalid']}，無效 {counts['invalid']}；得子 {counts['gain_gain']}，並非得子 {counts['gain_no_gain']}。",
             f"有標籤 {counts['matched']} 題；無標籤 {counts['unmatched']} 題。全部逐列核對來源列號、ID、原 FEN、PV、合法時間線、身份證據及 summary。",
             "", "## 與 v2.0 的分類交叉表", "", "全部由原棋譜重新分析；每題 material 與凍結的 v2.0 基準逐項一致。", "", "| 舊分類 | gain | no_gain | invalid |", "| --- | ---: | ---: | ---: |"]
    for kind in ("gain", "no_gain"):
        lines.append(f"| {kind} | {cross[kind,'gain']} | {cross[kind,'no_gain']} | {cross[kind,'invalid']} |")
    lines += ["", "## 逐標籤差異（按題去重）", "", "| ID | 新增 | 移除 | 保留 | 命中 |", "| --- | ---: | ---: | ---: | ---: |"]
    for label, change in label_changes.items():
        lines.append(f"| {label} | {change['added']} | {change['removed']} | {change['retained']} | {change['hits']} |")
    mismatched = [case for case in case_outcomes if not case["match"]]
    lines += ["", "## 凍結回歸集比對", "", f"凍結題 {len(case_outcomes)} 題，與目前資料不一致 {len(mismatched)} 題。", "",
              "| ID | 分類 | 目前標籤 | 凍結標籤 |", "| --- | --- | --- | --- |"]
    for case in mismatched:
        lines.append(f"| {case['id']} | {case['kind']} | {'、'.join(LABELS[t] for t in case['tactics']) or '無標籤'} | "
                     f"{'、'.join(LABELS[t] for t in case['frozen']['tactics']) or '無標籤'} |")
    lines += ["", "## 覆核與抽樣", "", "尚未經人工核對，已審數為 0；正確數、precision、recall 不提供。上述僅為命中分布，不是準確率。",
              "", f"固定 seed 20261103：每標籤最多 30 題，另抽無標籤及 delta 3/4/5 交界各最多 30 題，去重後 {len(blind)} 題。",
              "[盲審檔](midgame-v21-blind-review.json) 隱藏機器結果；人審欄位保持 null。[機讀批次報告](midgame-v21-batch.json) 另含各抽樣組的 ID。禁止把生成結果寫回人工期望。",
              "", f"待裁決涉及 {len(candidates)} 題，詳見 [FEN、步數及完整候選證據](midgame-v21-review-candidates.json)。", "", "| 標籤 | 覆核原因 | 候選數 |", "| --- | --- | ---: |"]
    for (label, reason), n in sorted(reasons.items()):
        lines.append(f"| {label} | {reason} | {n} |")
    lines += ["", "## 本輪規則與驗證", "", "加入 indirect suicide 逃路代價、真實應將後驗證第二威脅、立即被吃且交換收益 ≤0 的攻擊者過濾。串打兩段皆須有利。取消過載／迫走守子的唯一合法應法門檻，保留實際 PV 因果與兌現檢查。",
              "", "牽制承接對手應着、識別利用既有牽制、逐一檢查炮線兩個阻擋子；士相兵卒須有促成實際吃車馬炮的功能證據。純由牽制造成的無逃路放入牽制證據。新增 clearance 消除阻隔。",
              "", "得子題的閃擊＋抽將會抑制捉雙；有其他標籤時抑制交換。被抑制的有效證據放 supportingEvidence，父證據鍵保持可追溯；統計與篩選只計最終標籤。",
              "", "[驗證明細](midgame-v21-validation.json) 記錄本輪測試與限制。原 v2.0 的既有失敗清單見 [前輪驗證](midgame-v2-validation.json)。機器回歸通過不代表人工精確率。",
              "", "重建：", "", "```bash", "python backend/scripts/generate_capturing_tactics.py --csv data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv --output public/data/capturing-tactics.json", "python backend/scripts/audit_midgame_tactics.py", "python -m pytest backend/tests -q", "npm run lint", "npm run build", "```", ""]
    (args.output_dir / "midgame-v21-batch.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"rows":len(rows),"summary":dict(counts),"blindReviewCount":len(blind),"reviewCandidatePuzzles":len(candidates)}))


if __name__ == "__main__":
    main()
