"""Print a shareable, per-case rule explanation for all WXR CH5 fixtures.

Run from ``backend``:
  ./.venv-workers/Scripts/python.exe scripts/print_wxr_cycle_rule_reference.py PATH_TO/ch5_cases.json

The script deliberately uses the isolated evaluator and ``assume_cycle=True``.
It therefore explains the chess-rule nature of abbreviated book examples,
rather than requiring each JSON fragment to contain three/four occurrences.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cycle_rules import CycleRuleResult, evaluate_cycle


UCI_MOVE = re.compile(r"([a-i])(10|[1-9])")
KIND = {
    "check": "长将",
    "pinned_rook_chase": "捉被卧槽马牵制的车",
    "chase": "有效捉",
    "idle": "闲",
}
VERDICT = {
    "red_must_change": "红方必须变着",
    "black_must_change": "黑方必须变着",
    "draw": "和棋",
    "watch": "继续观察",
    "none": "未形成循环",
}


def to_ucci(move: str) -> str:
    return UCI_MOVE.sub(lambda hit: f"{hit.group(1)}{int(hit.group(2)) - 1}", move)


def reason(result: CycleRuleResult) -> str:
    red, black = KIND[result.red_kind], KIND[result.black_kind]
    if result.verdict == "red_must_change":
        return f"红方循环类别为{red}，高于黑方的{black}，故红方承担变着责任。"
    if result.verdict == "black_must_change":
        return f"黑方循环类别为{black}，高于红方的{red}，故黑方承担变着责任。"
    return f"红方为{red}、黑方为{black}，两方同级或均未构成连续违规捉，故和棋。"


def move_line(wxf: str, move) -> str:
    pairs = ", ".join(f"{attacker}→{victim}" for attacker, victim in move.chase_pairs) or "无"
    side = "红" if move.side == "red" else "黑"
    return f"{move.ply}. {side}{wxf}：{KIND[move.kind]}；有效关系：{pairs}。"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: print_wxr_cycle_rule_reference.py PATH_TO/ch5_cases.json", file=sys.stderr)
        return 2
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    matched = 0
    print("# WXR CH5：110 题逐题棋规判别依据")
    print()
    print("口径：使用独立纯函数 `evaluate_cycle(..., assume_cycle=True)`；题面线路视作待裁定循环。")
    print("等级：长将 > 捉被卧槽马牵制的车 > 有效捉 > 闲。")
    for case in cases:
        result = evaluate_cycle(case["fen"], [to_ucci(move) for move in case["moves_uci"]], assume_cycle=True)
        matched += result.verdict == case["expected"]
        code = case["id"].rsplit("-", 1)[-1]
        print()
        print(f"## {code}")
        print()
        print(f"- 题目分类：{case['source']['section']}")
        print(f"- 本函数判定：{VERDICT[result.verdict]}")
        print(f"- JSON 参考：{VERDICT[case['expected']]}（{'一致' if result.verdict == case['expected'] else '不一致'}）")
        print(f"- 循环分类：红方 {KIND[result.red_kind]}；黑方 {KIND[result.black_kind]}。")
        print(f"- 判别依据：{reason(result)}")
        print("- 逐手依据：")
        for wxf, move in zip(case["moves_wxf"], result.moves):
            print(f"  - {move_line(wxf, move)}")
    print()
    print(f"## 汇总\n\n- 命中：{matched}/{len(cases)}（{matched / len(cases):.1%}）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
