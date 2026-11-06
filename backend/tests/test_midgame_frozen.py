"""Frozen, human-confirmed midgame regression gate.

The fixtures under ``fixtures/midgame_frozen/`` were confirmed label-by-label by a
human expert. They are NEVER edited by code agents and NEVER back-filled from
engine output. If a rule change makes any case here fail, the change is rejected
and must be returned to the user with the diff below; do not weaken this test.

Checked for every frozen case:
  * original puzzle on the native board (pyffish) and the pure-Python fallback;
  * colour-swapped, left-right mirrored and swapped+mirrored variants on the
    pure-Python fallback (set MIDGAME_FROZEN_FULL=1 to also run them natively).
When a later version re-rules a puzzle (``supersedes``), only its newest entry
is checked; the older file is kept unchanged as history.
Only the ``tactics`` set (restricted to the vocabulary at freeze time) and
``material.kind`` are frozen; evidence details are not. Evidence is only checked
for structural consistency (test_frozen_evidence_is_well_formed).
"""
import hashlib
import json
import os
import warnings
from pathlib import Path

import pytest

from backend.app import board as lab_board  # the lab's pyffish adapter, for the native runs
from xq_classify import board, classify_midgame, clear_caches
from xq_classify.midgame import replay

FROZEN_DIR = Path(__file__).parent / "fixtures" / "midgame_frozen"
MANIFEST = json.loads((FROZEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
FROZEN = {name: json.loads((FROZEN_DIR / name).read_text(encoding="utf-8")) for name in MANIFEST["frozen"]}
KNOWN_WRONG = json.loads((FROZEN_DIR / "known_wrong_v1.json").read_text(encoding="utf-8"))
FULL = os.environ.get("MIDGAME_FROZEN_FULL") == "1"


def _rot(square):
    return f"{chr(ord('i') - (ord(square[0]) - ord('a')))}{9 - int(square[1])}"


def _mirror(square):
    return f"{chr(ord('i') - (ord(square[0]) - ord('a')))}{square[1]}"


VARIANTS = {
    # name: (square transform, swap colours)
    "original": (lambda s: s, False),
    "color_swap": (_rot, True),
    "mirror": (_mirror, False),
    "color_swap_mirror": (lambda s: _rot(_mirror(s)), True),
}


def transform(case, variant):
    square, swap = VARIANTS[variant]
    if variant == "original":
        return case["initialFen"], case["blunderMove"], list(case["pv"]), case["solverSide"]
    pieces = {square(s): (p.swapcase() if swap else p) for s, p in board.parse_fen(case["initialFen"]).items()}
    side = board.side_to_move(case["initialFen"])
    solver = case["solverSide"]
    if swap:
        side = "black" if side == "red" else "red"
        solver = "black" if solver == "red" else "red"
    fen = f"{board.board_to_fen(pieces)} {'w' if side == 'red' else 'b'} - - 0 1"
    move = lambda m: square(m[:2]) + square(m[2:])
    return fen, move(case["blunderMove"]), [move(m) for m in case["pv"]], solver


@pytest.fixture(params=["native", "python"])
def board_backend(request):
    if request.param == "native" and lab_board.pyffish is None:
        pytest.skip("pyffish is unavailable")
    previous = board.use_backend(lab_board.NATIVE_BACKEND if request.param == "native" else board.PURE_BACKEND)
    clear_caches()
    yield request.param
    board.use_backend(previous)
    clear_caches()


def diff_report(case, variant, backend, vocabulary, result):
    want_tactics = set(case["expected"]["tactics"])
    got_tactics = set(result.get("tactics", [])) & set(vocabulary)
    lines = [
        "",
        "凍結回歸集差異：此改動不予通過，須交還用戶裁決（不得修改凍結 fixture）。",
        f"  題目    {case['id']}  row {case['sourceRow']}  {case['url']}",
        f"  變體    {variant} / {backend} board",
        f"  狀態    {result.get('status')}",
    ]
    if got_tactics != want_tactics:
        lines += [
            f"  凍結標籤 {sorted(want_tactics)}",
            f"  目前標籤 {sorted(got_tactics)}",
            f"  多出     {sorted(got_tactics - want_tactics)}",
            f"  缺少     {sorted(want_tactics - got_tactics)}",
        ]
    got_material = (result.get("material") or {}).get("kind")
    if got_material != case["expected"]["material"]:
        lines.append(f"  得子分類 凍結 {case['expected']['material']} → 目前 {got_material}")
    return "\n".join(lines)


def check(case, vocabulary, variant, backend):
    fen, blunder, pv, solver = transform(case, variant)
    result = classify_midgame(fen, blunder, pv, solver).to_dict()
    got = (set(result.get("tactics", [])) & set(vocabulary), (result.get("material") or {}).get("kind"))
    want = (set(case["expected"]["tactics"]), case["expected"]["material"])
    assert result.get("status") != "invalid" and got == want, diff_report(case, variant, backend, vocabulary, result)


def effective_cases():
    """Newest human-frozen expectation per puzzle.

    A later version may replace an earlier entry only when that version lists
    the puzzle under ``supersedes`` (a human re-ruling); any other repeat is an
    error. Earlier files stay byte-for-byte unchanged.
    """
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


@pytest.mark.parametrize("case,vocabulary", PARAMS)
def test_frozen_original(case, vocabulary, board_backend):
    check(case, vocabulary, "original", board_backend)


@pytest.mark.parametrize("variant", ["color_swap", "mirror", "color_swap_mirror"])
@pytest.mark.parametrize("case,vocabulary", PARAMS)
def test_frozen_variants(case, vocabulary, variant, board_backend):
    if board_backend == "native" and not FULL:
        pytest.skip("native variants run only with MIDGAME_FROZEN_FULL=1")
    check(case, vocabulary, variant, board_backend)


def evidence_problems(case, result):
    """Structural checks only: evidence must be internally consistent with the replayed
    line. These are not tactic judgements; a failure here is an engine bug."""
    problems = []
    positions, events = replay(case["initialFen"], case["blunderMove"], case["pv"], case["solverSide"])
    plies = result["plies"]
    last = len(events)
    if [p["ucci"] for p in plies] != [case["blunderMove"], *case["pv"]]:
        problems.append("plies 與輸入著法不一致")
    if result["fens"] != [p.fen for p in positions]:
        problems.append("fens 與重播局面不一致")
    if result["status"] != ("matched" if result["tactics"] else "unmatched"):
        problems.append(f"status {result['status']} 與標籤不符")
    keys, found = set(), set()

    def check_refs(label, ev):
        for ref in ev.get("actors", []) + ev.get("targets", []):
            if not (ref.get("id") and ref.get("square") and ref.get("piece")):
                problems.append(f"{label}: 棋子引用欠 id/square/piece {ref}")
            elif not any(pos.ids.get(ref["square"]) == ref["id"] for pos in positions):
                problems.append(f"{label}: {ref['id']} 從未在 {ref['square']} 出現")

    for ply, event in zip(plies, events, strict=True):
        if ply["solver"] != (event.ply > 1 and event.side == case["solverSide"]):
            problems.append(f"ply {ply['ply']} 的 solver 標記錯誤")
        for occurrence in ply["occurrences"]:
            ev, label = occurrence["evidence"], f"{occurrence['id']}@{ply['ply']}"
            if not ply["solver"]:
                problems.append(f"{label}: 標籤掛在非玩家手")
            if not ev["triggerPly"] == ply["ply"] <= ev["confirmedPly"] <= last:
                problems.append(f"{label}: triggerPly/confirmedPly 不合理 {ev['triggerPly']}/{ev['confirmedPly']}")
            if ev["key"] in keys:
                problems.append(f"{label}: 證據 key 重複")
            keys.add(ev["key"])
            found.add(occurrence["id"])
            check_refs(label, ev)
    if found != set(result["tactics"]):
        problems.append(f"逐手證據標籤 {sorted(found)} 與 tactics {sorted(result['tactics'])} 不一致")
    supporting = result.get("supportingEvidence", [])
    for occurrence in supporting:
        ev, label = occurrence["evidence"], f"support:{occurrence['id']}"
        if ev["key"] in keys:
            problems.append(f"{label}: 證據 key 重複")
        keys.add(ev["key"])
        if not 2 <= ev["triggerPly"] <= ev["confirmedPly"] <= last:
            problems.append(f"{label}: triggerPly/confirmedPly 不合理")
        if occurrence["id"] in found or not occurrence.get("suppressedBy"):
            problems.append(f"{label}: 支援證據應為被去重且註明 suppressedBy")
        check_refs(label, ev)
    for occurrence in [o for p in plies for o in p["occurrences"]] + supporting:
        parent = occurrence["evidence"].get("parentKey")
        if parent and parent not in keys:
            problems.append(f"{occurrence['id']}: parentKey {parent} 不存在")
    return problems


@pytest.mark.parametrize("case,vocabulary", PARAMS)
def test_frozen_evidence_is_well_formed(case, vocabulary):
    previous = board.use_backend(board.PURE_BACKEND)  # board-independent; parity is covered above
    clear_caches()
    try:
        result = classify_midgame(case["initialFen"], case["blunderMove"], case["pv"], case["solverSide"]).to_dict()
        problems = evidence_problems(case, result)
    finally:
        board.use_backend(previous)
        clear_caches()
    assert not problems, f"{case['id']} {case['url']} 證據結構錯誤：\n  " + "\n  ".join(problems)


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
            assert set(case["expected"]["tactics"]) <= set(data["vocabulary"])
            if case["id"] in data.get("supersedes", []):
                assert case.get("supersedes", {}).get("reason"), f"{case['id']} 取代舊版本須註明理由"


def test_frozen_and_known_wrong_are_disjoint():
    frozen_ids = set(EFFECTIVE)
    assert not frozen_ids & {c["id"] for c in KNOWN_WRONG["cases"]}


@pytest.mark.parametrize("case", KNOWN_WRONG["cases"], ids=[c["id"] for c in KNOWN_WRONG["cases"]])
def test_known_wrong_tracking(case):
    """Not a gate. XPASS means the engine now matches the expert correction:
    report it to the user, who decides whether to promote it to a new frozen version."""
    result = classify_midgame(case["initialFen"], case["blunderMove"], case["pv"], case["solverSide"]).to_dict()
    got = (sorted(set(result.get("tactics", [])) & set(KNOWN_WRONG["vocabulary"])), (result.get("material") or {}).get("kind"))
    if got != (case["expected"]["tactics"], case["expected"]["material"]):
        pytest.xfail(f"專家修正 {case['expected']['tactics']}，目前 {got[0]}：{case['note']}")
    warnings.warn(f"{case['id']} 已符合專家修正 {got[0]}；請交用戶決定是否升入新凍結版本", UserWarning)
