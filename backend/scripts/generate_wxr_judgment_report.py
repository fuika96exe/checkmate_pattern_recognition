"""Create a shareable Chinese review of all WXR-2018 chapter-5 fixtures.

Usage (from backend/):
  .\\.venv\\Scripts\\python.exe scripts\\generate_wxr_judgment_report.py PATH_TO/ch5_cases.json

The report extends a demonstrated final cycle only to reach the rule's normal
third/fourth-occurrence threshold.  It therefore distinguishes the book's
source verdict from the current engine's independent judgment.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from app.board import apply_move, build_piece_identity, move_piece_identity, side_to_move
from app.repetition import adjudicate, assess_move, position_key


UCI_MOVE = re.compile(r"([a-i])(10|[1-9])")
CLASS_LABEL = {
    "check": "长将",
    "chase": "长捉",
    "pinned_rook_chase": "捉被卧槽马牵制的车",
    "idle": "闲着／非连续有效追捉",
}
VERDICT_LABEL = {
    "red_must_change": "红方必须变着",
    "black_must_change": "黑方必须变着",
    "draw": "和棋",
    "warning": "继续观察（第三次重复但双方同级）",
    "watch": "发现重复，尚未到裁决阈值",
    "none": "未形成可裁决重复",
    "error": "回放失败",
}


def to_ucci(move: str) -> str:
    return UCI_MOVE.sub(lambda part: f"{part.group(1)}{int(part.group(2)) - 1}", move)


def extension_cycle(case: dict) -> list[str]:
    final_state = len(case["moves_uci"])
    for group in reversed(case.get("repeats_at", [])):
        if group and group[-1] == final_state and len(group) >= 2:
            return case["moves_uci"][group[-2] : group[-1]]
    return []


def final_reason(outcome: str, decision: dict, error: str | None) -> str:
    if error:
        return f"回放无法继续：{error}"
    red = CLASS_LABEL[decision["red_classification"]]
    black = CLASS_LABEL[decision["black_classification"]]
    count = decision["occurrence_count"]
    if outcome in {"red_must_change", "black_must_change"}:
        side = "红方" if outcome.startswith("red") else "黑方"
        return f"第 {count} 次同局面时，循环中红方为{red}、黑方为{black}；{side}的行为等级更高，因此须变着。"
    if outcome == "draw":
        return f"第 {count} 次同局面时，循环中红方为{red}、黑方为{black}；双方等级相同，按当前规则判和。"
    if outcome == "warning":
        return f"第 {count} 次同局面时，循环中红方为{red}、黑方为{black}；双方等级相同，先警告，尚不指定变着方。"
    if outcome == "watch":
        return f"已检测到重复，但只有第 {count} 次同局面；未达到裁决门槛。"
    return "给出的着法及其可证明的末段循环未达到当前裁决阈值。"


def replay(case: dict) -> tuple[str, dict, str | None, list[dict]]:
    fen = case["fen"]
    identities = build_piece_identity(fen)
    positions = [{"ply": 0, "key": position_key(fen)}]
    actions: list[dict] = []
    supplied_count = len(case["moves_uci"])
    moves = list(case["moves_uci"])
    moves.extend(extension_cycle(case) * 3)
    decision = adjudicate(positions, actions)

    for ply, external_move in enumerate(moves, start=1):
        move = to_ucci(external_move)
        side = side_to_move(fen)
        try:
            next_fen = apply_move(fen, move)
        except Exception as exc:  # The report must retain malformed fixtures too.
            return "error", decision, f"第 {ply} 手 {external_move}（{move}）：{exc}", actions
        identities = move_piece_identity(identities, move[:2], move[2:])
        action = assess_move(next_fen, identities, side).as_action(ply, side)
        action["source_move"] = case["moves_wxf"][ply - 1] if ply <= supplied_count else external_move
        action["extended"] = ply > supplied_count
        actions.append(action)
        fen = next_fen
        positions.append({"ply": ply, "key": position_key(fen)})
        decision = adjudicate(positions, actions)
        if decision["status"] in {"must_change", "draw"}:
            outcome = f"{decision['restricted_side']}_must_change" if decision["status"] == "must_change" else "draw"
            return outcome, decision, None, actions
    return decision["status"], decision, None, actions


def action_label(action: dict) -> str:
    if action["is_check"]:
        return "将"
    if action["pinned_rook_chase_target_ids"]:
        return "捉卧槽牵制车"
    if action["chase_target_ids"]:
        return "捉"
    return "闲"


def move_summary(actions: list[dict]) -> str:
    supplied = [action for action in actions if not action["extended"]]
    if not supplied:
        return "无可回放着法"
    chunks = []
    for action in supplied:
        side = "红" if action["side"] == "red" else "黑"
        chunks.append(f"{side}{action['source_move']}（{action_label(action)}）")
    return "；".join(chunks)


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: generate_wxr_judgment_report.py PATH_TO/ch5_cases.json [OUTPUT.md]", file=sys.stderr)
        return 2
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("wxr_ch5_judgments.md")

    rows: list[str] = [
        "# WXR-2018 第五章：长将／长捉 110 题逐题判断",
        "",
        "本报告按当前项目的 `backend/app/repetition.py` 回放。每题的书中线路如只展示了一轮循环，会仅重复其已经证明的末段循环，以触发第三／第四次同局面的裁决门槛。",
        "",
        "判定等级：长将（3）> 捉被卧槽马牵制的车（2）> 长捉（1）> 闲着（0）。第三次同局面时等级较高的一方必须变着；同级则警告，第四次同局面判和。",
        "",
        "“书中结论”是 `ch5_cases.json` 的标注；“当前判断”是本项目规则的实际结果。它们不一致的题目尤其适合作为后续规则改进参考。",
        "",
    ]
    matched = 0
    results: list[tuple[dict, str, dict, str | None, list[dict]]] = []
    for case in cases:
        outcome, decision, error, actions = replay(case)
        results.append((case, outcome, decision, error, actions))
        matched += outcome == case["expected"]

    rows.extend([
        "## 汇总",
        "",
        f"- 共 {len(cases)} 题；当前判断与书中结论一致：{matched} 题；不一致或无法裁决：{len(cases) - matched} 题。",
        "- 本报告不把书中结论强行当成当前引擎输出；每题均保留二者，便于另一位 AI 找到真正的规则分歧。",
        "",
    ])

    for case, outcome, decision, error, actions in results:
        source = case["source"]
        rows.extend([
            f"## {case['id'].rsplit('-', 1)[-1]} — 图 {source['diagram']}（第 {source['book_page']} 页）",
            "",
            f"- 分类：{source['section']}",
            f"- 书中结论：{VERDICT_LABEL[case['expected']]}。{case['verdict_text']}",
            f"- 当前判断：{VERDICT_LABEL[outcome]}。",
            f"- 当前责任方：{'红方' if outcome == 'red_must_change' else '黑方' if outcome == 'black_must_change' else '无（双方同级或未达到裁决）'}。",
            f"- 判定原因：{final_reason(outcome, decision, error)}",
            f"- 回放标签：{move_summary(actions)}",
            f"- 一致性：{'一致' if outcome == case['expected'] else '不一致'}。",
            "",
        ])

    output.write_text("\n".join(rows), encoding="utf-8")
    print(output.resolve())
    print(f"cases={len(cases)} matched={matched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
