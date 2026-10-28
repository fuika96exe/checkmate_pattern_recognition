"""Replay the external WXR chapter-5 corpus against the repetition core.

Usage:
  backend/.venv-workers/Scripts/python.exe backend/scripts/replay_wxr.py PATH_TO/ch5_cases.json

The corpus uses ranks 1--10 while this project uses UCCI ranks 0--9.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from app.board import (
    apply_move,
    build_piece_identity,
    move_piece_identity,
    side_to_move,
)
from app.repetition import adjudicate, assess_move, position_key


UCI_MOVE = re.compile(r"([a-i])(10|[1-9])")


def to_ucci(move: str) -> str:
    return UCI_MOVE.sub(lambda part: f"{part.group(1)}{int(part.group(2)) - 1}", move)


def _extension_cycle(case: dict) -> list[str]:
    """Return the final proven position cycle, if the fixture ends inside it."""
    final_state = len(case["moves_uci"])
    for group in reversed(case.get("repeats_at", [])):
        if group and group[-1] == final_state and len(group) >= 2:
            return case["moves_uci"][group[-2] : group[-1]]
    return []


def replay(case: dict) -> tuple[str, str | None]:
    fen = case["fen"]
    identities = build_piece_identity(fen)
    positions = [{"ply": 0, "key": position_key(fen)}]
    actions: list[dict] = []

    moves = list(case["moves_uci"])
    # The book often stops after demonstrating a cycle.  The product rule is
    # reached on occurrence three or four, so replay the proven final cycle
    # enough times to reach either result.
    cycle = _extension_cycle(case)
    moves.extend(cycle * 3)

    for ply, external_move in enumerate(moves, start=1):
        move = to_ucci(external_move)
        side = side_to_move(fen)
        try:
            next_fen = apply_move(fen, move)
        except Exception as exc:
            return "error", f"{external_move} -> {move}: {exc}"
        identities = move_piece_identity(identities, move[:2], move[2:])
        actions.append(assess_move(next_fen, identities, side).as_action(ply, side))
        fen = next_fen
        positions.append({"ply": ply, "key": position_key(fen)})
        decision = adjudicate(positions, actions)
        if decision["status"] in {"must_change", "draw"}:
            if decision["status"] == "draw":
                return "draw", None
            return f"{decision['restricted_side']}_must_change", None

    decision = adjudicate(positions, actions)
    if decision["status"] == "draw":
        return "draw", None
    if decision["status"] == "must_change":
        return f"{decision['restricted_side']}_must_change", None
    return decision["status"], None


def annotate_moves(case: dict) -> list[str]:
    """Return the baseline label for every supplied (not extended) WXF move."""
    fen = case["fen"]
    identities = build_piece_identity(fen)
    annotations: list[str] = []
    for external_move in case["moves_uci"]:
        move = to_ucci(external_move)
        side = side_to_move(fen)
        next_fen = apply_move(fen, move)
        identities = move_piece_identity(identities, move[:2], move[2:])
        assessment = assess_move(next_fen, identities, side)
        if assessment.is_check:
            label = "Check"
        elif assessment.pinned_rook_chase_target_ids:
            label = "PinnedRookChase"
        elif assessment.chase_target_ids:
            label = "Chase"
        else:
            label = "Idle"
        annotations.append(label)
        fen = next_fen
    return annotations


def main() -> int:
    if len(sys.argv) not in {2, 3, 5}:
        print("Usage: replay_wxr.py PATH_TO/ch5_cases.json [--review-first-30 | --review-range START END]", file=sys.stderr)
        return 2
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if len(sys.argv) in {3, 5}:
        if len(sys.argv) == 3 and sys.argv[2] == "--review-first-30":
            selected_cases = cases[:30]
        elif len(sys.argv) == 5 and sys.argv[2] == "--review-range":
            try:
                start, end = int(sys.argv[3]), int(sys.argv[4])
            except ValueError:
                print("Review range must use numeric case numbers.", file=sys.stderr)
                return 2
            selected_cases = cases[start - 1 : end]
        else:
            print(f"Unknown option: {sys.argv[2]}", file=sys.stderr)
            return 2
        labels = {
            "Check": "将",
            "PinnedRookChase": "捉被卧槽马牵制的车",
            "Chase": "捉（基础）",
            "Idle": "闲",
        }
        rows = [(case, replay(case)[0]) for case in selected_cases]
        for heading, matched in (("# 匹配", True), ("# 未匹配", False)):
            print(heading)
            for case, actual in rows:
                if (actual == case["expected"]) != matched:
                    continue
                expected = {"draw": "和棋", "red_must_change": "红方变着", "black_must_change": "黑方变着"}[case["expected"]]
                actual_text = {"draw": "和棋", "red_must_change": "红方变着", "black_must_change": "黑方变着", "none": "未达到重复阈值"}[actual]
                print(f"## {case['id'].rsplit('-', 1)[-1]} — 预期：{expected}；当前：{actual_text}")
                annotations = annotate_moves(case)
                for index in range(0, len(annotations), 2):
                    left = f"{case['moves_wxf'][index]}（{labels[annotations[index]]}）"
                    right = ""
                    if index + 1 < len(annotations):
                        right = f"　{case['moves_wxf'][index + 1]}（{labels[annotations[index + 1]]}）"
                    print(left + right)
                if matched:
                    print("原因：当前循环分类没有产生错误的唯一责任方。")
                elif case["expected"] == "draw":
                    print("原因：当前基础攻击格把本应降级的攻击误当成长捉。")
                else:
                    print("原因：当前基础攻击格未能识别语料所要求的有效长捉，或将双方误判为同级。")
        return 0
    outcomes: Counter[tuple[str, str]] = Counter()
    failures: list[tuple[dict, str, str | None]] = []
    for case in cases:
        actual, error = replay(case)
        outcomes[(case["expected"], actual)] += 1
        if actual != case["expected"]:
            failures.append((case, actual, error))

    print(f"cases={len(cases)} matched={len(cases) - len(failures)}")
    for (expected, actual), count in sorted(outcomes.items()):
        print(f"{count:3} expected={expected} actual={actual}")
    for case, actual, error in failures:
        print(
            f"FAIL {case['id']} | {case['source']['section']} | "
            f"expected={case['expected']} actual={actual}"
            + (f" | {error}" if error else "")
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
