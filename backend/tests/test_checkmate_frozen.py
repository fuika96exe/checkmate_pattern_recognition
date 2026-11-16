"""Frozen, human-confirmed checkmate-pattern regression gate.

The fixtures under ``fixtures/checkmate_frozen/`` were confirmed puzzle by puzzle
by a human expert. They are NEVER edited by code agents and NEVER back-filled
from engine output. If a rule change makes any case here fail, the change is
rejected and must be returned to the user with the diff below; do not weaken
this test.

Checked for every frozen case:
  * the original puzzle on the native board (pyffish) and the pure-Python
    fallback;
  * colour-swapped, left-right mirrored and swapped+mirrored variants on the
    pure-Python fallback (set CHECKMATE_FROZEN_FULL=1 to also run them natively).
Frozen are the exact set of checkmate pattern IDs (restricted to the vocabulary
at freeze time) and the material fallback code (子力歸類), which is only present
when no named pattern matched. When a later version re-rules a puzzle
(``supersedes``), only its newest entry is checked.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from app import board as lab_board  # the lab's pyffish adapter, for the native runs
from xq_classify import board, classify_checkmate, clear_caches

FROZEN_DIR = Path(__file__).parent / "fixtures" / "checkmate_frozen"
MANIFEST = json.loads((FROZEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
FROZEN = {name: json.loads((FROZEN_DIR / name).read_text(encoding="utf-8")) for name in MANIFEST["frozen"]}
FULL = os.environ.get("CHECKMATE_FROZEN_FULL") == "1"


def effective_cases():
    """Newest human-frozen expectation per puzzle (see test_midgame_frozen)."""
    effective = {}
    for data in sorted(FROZEN.values(), key=lambda d: d["version"]):
        allowed = set(data.get("supersedes", []))
        for case in data["cases"]:
            if case["id"] in effective and case["id"] not in allowed:
                raise AssertionError(f"v{data['version']} 重複凍結 {case['id']} 但未聲明 supersedes")
            if case["id"] in allowed and case["id"] not in effective:
                raise AssertionError(f"v{data['version']} 聲明取代 {case['id']}，但較早版本沒有此題")
            effective[case["id"]] = (case, data)
    return effective


EFFECTIVE = effective_cases()
PARAMS = [pytest.param(case, data["vocabulary"], id=f"v{data['version']}-{case['id']}")
          for case, data in EFFECTIVE.values()]


def _rot(square):
    return f"{chr(ord('i') - (ord(square[0]) - ord('a')))}{9 - int(square[1])}"


def _mirror(square):
    return f"{chr(ord('i') - (ord(square[0]) - ord('a')))}{square[1]}"


VARIANTS = {
    "original": (lambda s: s, False),
    "color_swap": (_rot, True),
    "mirror": (_mirror, False),
    "color_swap_mirror": (lambda s: _rot(_mirror(s)), True),
}


def transform(case, variant):
    if variant == "original":
        return case["initialFen"], case["blunderMove"], list(case["pv"])
    square, swap = VARIANTS[variant]
    pieces = {square(s): (p.swapcase() if swap else p) for s, p in board.parse_fen(case["initialFen"]).items()}
    side = board.side_to_move(case["initialFen"])
    if swap:
        side = "black" if side == "red" else "red"
    fen = f"{board.board_to_fen(pieces)} {'w' if side == 'red' else 'b'} - - 0 1"
    move = lambda m: square(m[:2]) + square(m[2:])
    return fen, move(case["blunderMove"]), [move(m) for m in case["pv"]]


@pytest.fixture(params=["native", "python"])
def board_backend(request):
    if request.param == "native" and lab_board.pyffish is None:
        pytest.skip("pyffish is unavailable")
    previous = board.use_backend(lab_board.NATIVE_BACKEND if request.param == "native" else board.PURE_BACKEND)
    clear_caches()
    yield request.param
    board.use_backend(previous)
    clear_caches()


def check(case, vocabulary, variant, backend):
    fen, blunder, pv = transform(case, variant)
    result = classify_checkmate(fen, blunder, pv).to_dict()
    got = (set(result.get("patternIds", [])) & set(vocabulary), result.get("materialId"))
    want = (set(case["expected"]["patterns"]), case["expected"]["material"])
    if result.get("status") != "invalid" and got == want:
        return
    lines = [
        "",
        "殺法凍結回歸集差異：此改動不予通過，須交還用戶裁決（不得修改凍結 fixture）。",
        f"  題目    {case['id']}  第 {case['puzzleNumber']} 題  {case['url']}",
        f"  變體    {variant} / {backend} board",
        f"  狀態    {result.get('status')} {result.get('error') or ''}",
        f"  凍結殺法 {sorted(want[0])}   目前 {sorted(got[0])}",
        f"  多出     {sorted(got[0] - want[0])}   缺少 {sorted(want[0] - got[0])}",
        f"  子力歸類 凍結 {want[1]} → 目前 {got[1]}",
    ]
    pytest.fail("\n".join(lines))


@pytest.mark.parametrize("case,vocabulary", PARAMS)
def test_frozen_original(case, vocabulary, board_backend):
    check(case, vocabulary, "original", board_backend)


@pytest.mark.parametrize("variant", ["color_swap", "mirror", "color_swap_mirror"])
@pytest.mark.parametrize("case,vocabulary", PARAMS)
def test_frozen_variants(case, vocabulary, variant, board_backend):
    if board_backend == "native" and not FULL:
        pytest.skip("native variants run only with CHECKMATE_FROZEN_FULL=1")
    check(case, vocabulary, variant, board_backend)


def test_frozen_files_are_unchanged():
    """Frozen files may only be appended as new versions by a human."""
    for name, digest in MANIFEST["frozen"].items():
        actual = hashlib.sha256((FROZEN_DIR / name).read_bytes()).hexdigest()
        assert actual == digest, f"{name} 已被改動；凍結檔不可修改，只能由人工追加新版本"
    for name, data in FROZEN.items():
        assert data["status"] == "frozen"
        ids = [c["id"] for c in data["cases"]]
        assert len(ids) == len(set(ids)), f"{name} 有重複題目"
        for case in data["cases"]:
            assert set(case["expected"]["patterns"]) <= set(data["vocabulary"])
            assert not (case["expected"]["patterns"] and case["expected"]["material"]), \
                f"{case['id']}：子力歸類只在沒有殺法名時出現"
            if case["id"] in data.get("supersedes", []):
                assert case.get("supersedes", {}).get("reason"), f"{case['id']} 取代舊版本須註明理由"
