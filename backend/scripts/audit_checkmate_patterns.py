"""Read-only structural and symmetry audit of the checkmate corpus and examples.

Writes evidence for review; diagnostic flags are not automatic replacement labels.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))  # xq_classify, imported by backend.app.board
from backend.app import board  # noqa: E402
from xq_classify.checkmate import geometry, recognition as patterns  # noqa: E402

RECOGNIZER_SOURCE = ROOT / "backend/xq_classify/checkmate/recognition.py"


def encode(pieces: dict[str, str], side: str) -> str:
    return f"{board.board_to_fen(pieces)} {side} - - 0 1"


def transform(fen: str, moves: list[str], rotate: bool = False) -> tuple[str, list[str]]:
    def square(value: str) -> str:
        return f"{chr(ord('i') - (ord(value[0]) - ord('a')))}{9-int(value[1]) if rotate else value[1]}"
    pieces = {square(s): p.swapcase() if rotate else p for s, p in board.parse_fen(fen).items()}
    side = fen.split()[1]
    if rotate:
        side = "b" if side == "w" else "w"
    return encode(pieces, side), [square(move[:2]) + square(move[2:]) for move in moves]


def corpus_row(task: tuple[dict, dict]) -> dict:
    puzzle, recognition = task
    moves = [puzzle["blunderMove"], *puzzle["pv"]]
    # The imported lines have already been replayed and validated. One native
    # call reconstructs the final board without re-running all recognizers.
    final = board.pyffish.get_fen(board.VARIANT, puzzle["initialFen"], [board.ucci_to_engine(m) for m in moves])
    pieces = board.parse_fen(final)
    analysis = board.position_analysis(final)
    defender = analysis["side_to_move"]
    attacker = "red" if defender == "black" else "black"
    king = analysis["king_square"]
    targets = {king, *geometry.orthogonal_palace_neighbors(king, defender)}
    attacks = analysis["attacked_squares"]
    labels = recognition["patternIds"]
    flags: list[str] = []

    def own(piece: str) -> bool:
        return piece.isupper() if attacker == "red" else piece.islower()

    def contribution(source: str) -> bool:
        return any(any(e["square"] == source for e in attacks.get(t, [])) for t in targets)

    horses = [s for s, p in pieces.items() if own(p) and p.upper() == "N"]
    tiger = {"c6", "g6"} if attacker == "red" else {"c3", "g3"}
    elbow = {"c8", "g8"} if attacker == "red" else {"c1", "g1"}
    if "TIGER_SILHOUETTE_CHECKMATE" in labels and not any(contribution(s) for s in horses if s in tiger):
        flags.append("tiger_without_real_palace_control")
    if "ELBOW_HORSE_CHECKMATE" in labels and not any(contribution(s) for s in horses if s in elbow):
        flags.append("elbow_without_real_palace_control")

    if "IRON_BOLT_CHECKMATE" in labels:
        meaningful_lock = False
        for source, piece in pieces.items():
            if not own(piece) or piece.upper() not in {"C", "R", "K"} or source[0] != "e":
                continue
            for guard, candidate in pieces.items():
                if own(candidate) or candidate.upper() != "A" or guard[0] != "e":
                    continue
                trial = dict(pieces)
                del trial[guard]
                if any(e["square"] == source for e in board.attacked_squares(trial, attacker).get(king, [])):
                    meaningful_lock = True
        if not meaningful_lock:
            flags.append("iron_bolt_without_central_check_or_advisor_pin")

    if analysis["is_checkmate"]:
        checker_types = {pieces[e["square"]].upper() for e in analysis["checking_pieces"]}
        neighbors = geometry.orthogonal_palace_neighbors(king, defender)
        if checker_types == {"N"} and all(s in pieces and not own(pieces[s]) for s in neighbors):
            if "SMOTHERED_CHECKMATE" not in labels:
                flags.append("fully_self_blocked_horse_mate_not_smothered")

        own_king = next(s for s, p in pieces.items() if own(p) and p.upper() == "K")
        if own_king[0] != "e" and "WHITE_FACE_GENERAL" not in labels:
            for target in neighbors:
                if target in pieces or target[0] != own_king[0]:
                    continue
                if not any(s in pieces for s in board.squares_between(own_king, target)) and not attacks.get(target):
                    flags.append("off_center_general_closes_unique_escape_but_no_white_face")
                    break

        corner_targets = {"d7", "d9", "f7", "f9"} if defender == "black" else {"d0", "d2", "f0", "f2"}
        opposite = {"d7":"f9", "f9":"d7", "f7":"d9", "d9":"f7", "d2":"f0", "f0":"d2", "f2":"d0", "d0":"f2"}
        if "OCTAGON_HORSE_CHECKMATE" not in labels:
            for source in horses:
                if source in corner_targets and opposite[source] == king:
                    controlled = [t for t in targets if any(e["square"] == source for e in attacks.get(t, []))]
                    if len(controlled) >= 2:
                        flags.append("octagon_geometry_present_but_missing_label")
                        break
        if "PALCORNER_HORSE_CHECKMATE" not in labels and any(
            s in corner_targets and sum(any(e["square"] == s for e in attacks.get(t, [])) for t in targets) == 1
            for s in horses
        ):
            flags.append("palcorner_unlabeled_sequence_review_candidate")
        if "HORSE_CANNON_CHECKMATE" not in labels:
            for checker in analysis["checking_pieces"]:
                if checker["reason"] != "cannon_screen":
                    continue
                screen = [s for s in board.squares_between(checker["square"], king) if s in pieces]
                if len(screen) == 1 and screen[0] in horses:
                    flags.append("horse_cannon_geometry_unlabeled_candidate")
                    break

    # Trace pieces without invoking the native engine for intermediate FENs.
    trial = board.parse_fen(puzzle["initialFen"])
    trace = []
    for ply, move in enumerate(moves, 1):
        piece = trial.pop(move[:2])
        trace.append({"ply": ply, "piece": piece, "move": move, "captured": trial.get(move[2:])})
        trial[move[2:]] = piece

    if "THROAT_CUTTING_CHECKMATE" in labels:
        central = "e8" if defender == "black" else "e1"
        penetrations = [e for e in trace[1::2] if e["piece"].upper() in {"R", "P"} and e["move"][2:] == central and e["captured"] and e["captured"].upper() == "A"]
        if penetrations and not any(trace[e["ply"]]["move"][2:] == central for e in penetrations if e["ply"] < len(trace)):
            # Declining an offered sacrifice is allowed by existing examples;
            # absence of a recapture is not itself a false positive.
            flags.append("throat_cutting_without_immediate_recapture_review_only")

    native_check = board.pyffish.gives_check(board.VARIANT, final, [])
    return {"id": puzzle["id"], "finalFen": final, "labels": labels,
            "isCheckmate": analysis["is_checkmate"], "isStalemate": analysis["is_stalemate"],
            "isCheck": analysis["is_check"], "nativeIsCheck": native_check, "flags": flags}


def literal_examples() -> list[dict]:
    tree = ast.parse((ROOT/"backend/tests/test_position_analysis.py").read_text(encoding="utf-8"))
    source = ast.parse(RECOGNIZER_SOURCE.read_text(encoding="utf-8"))
    dispatch = {}
    for f in source.body:
        if isinstance(f, ast.FunctionDef):
            for ret in f.body:
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Dict):
                    for key, value in zip(ret.value.keys, ret.value.values):
                        if isinstance(key, ast.Constant) and key.value == "pattern_id" and isinstance(value, ast.Constant):
                            dispatch[f.name] = value.value
    examples = {}

    def collect(call, test, bindings):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            return
        try:
            args = [bindings[arg.id] if isinstance(arg, ast.Name) and arg.id in bindings else ast.literal_eval(arg) for arg in call.args]
        except (ValueError, TypeError):
            return
        if call.func.id == "recognize_pattern" and len(args) >= 2:
            pattern, fen, *tail = args
        elif call.func.id in dispatch and args:
            pattern = dispatch[call.func.id]
            fen, *tail = args
        else:
            return
        moves = tail[0] if tail else []
        key = (pattern, fen, tuple(moves))
        examples[key] = {"pattern": pattern, "fen": fen, "moves": moves, "test": test.name, "line": call.lineno}

    for test in tree.body:
        if not isinstance(test, ast.FunctionDef):
            continue
        bindings = {}
        for call in ast.walk(test):
            collect(call, test, {})
            if isinstance(call, ast.Assign) and len(call.targets) == 1 and isinstance(call.targets[0], ast.Name):
                try:
                    bindings[call.targets[0].id] = ast.literal_eval(call.value)
                except (ValueError, TypeError):
                    pass
        for loop in (n for n in ast.walk(test) if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)):
            values = bindings.get(loop.iter.id, []) if isinstance(loop.iter, ast.Name) else []
            names = [n.id for n in loop.target.elts if isinstance(n, ast.Name)]
            for value in values:
                if not isinstance(value, (tuple, list)) or len(value) != len(names):
                    continue
                for call in ast.walk(loop):
                    collect(call, test, dict(zip(names, value)))
    return list(examples.values())


def audit_example(example: dict) -> dict:
    pattern, fen, moves = example["pattern"], example["fen"], example["moves"]
    result = patterns.recognize_pattern(pattern, fen, moves)
    output = {**example, "detected": result["detected"], "finalFen": result["fen"], "variants": {}}
    for name, rotate in (("horizontal_mirror", False), ("rotate_swap_colors", True)):
        f, m = transform(fen, moves, rotate)
        v = patterns.recognize_pattern(pattern, f, m)
        output["variants"][name] = {"detected": v["detected"], "isCheckmate": v["analysis"]["is_checkmate"], "fen": f, "moves": m}
    if result["detected"]:
        final = patterns.recognize_pattern(pattern, result["fen"], [])
        output["variants"]["final_fen_only"] = {"detected": final["detected"]}
    return output


def sequence_recheck(task: tuple[dict, str]) -> dict:
    puzzle, pattern = task
    fen, moves = puzzle["initialFen"], [puzzle["blunderMove"], *puzzle["pv"]]
    full = patterns.recognize_pattern(pattern, fen, moves)
    solver_fen = board.apply_move(fen, moves[0])
    suffix = patterns.recognize_pattern(pattern, solver_fen, moves[1:])
    return {"id": puzzle["id"], "pattern": pattern, "fullDetected": full["detected"],
            "solverLineDetected": suffix["detected"], "fullFeatures": full["features"],
            "solverLineFeatures": suffix["features"],
            "fenOnlyDetected": patterns.recognize_pattern(pattern, full["fen"], [])["detected"]}


def focused_probes() -> list[dict]:
    cases = [
        ("drawer_original", "DRAWER_CHECKMATE", "3akab1C/9/4b4/5R3/9/9/9/9/9/5K3 w - - 0 1", ["f6f9", "e9e8", "f9f8"], True),
        ("drawer_with_legal_blunder_prefix", "DRAWER_CHECKMATE", "2bakab1C/9/9/5R3/9/9/9/9/9/5K3 b - - 0 1", ["c9e7", "f6f9", "e9e8", "f9f8"], True),
        ("heaven_earth_quiet_finish", "HEAVEN_AND_EARTH_CANNON_CHECKMATE", "1Cbak4/4a4/4b1N2/4CR3/9/9/9/9/9/3K5 w - - 0 1", ["f6f9"], True),
        ("horse_cannon_rook_unblocks_screen", "HORSE_CANNON_CHECKMATE", "3a1k3/9/3a1N3/9/5R3/5C3/9/9/9/4K4 w - - 0 1", ["f5h5"], True),
        ("three_chariots_remote_pawns", "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE", "4k4/4aR3/6N2/P7P/9/9/9/9/9/4K4 w - - 0 1", ["f8f9"], False),
        ("elbow_blocked_leg_no_palace_control", "ELBOW_HORSE_CHECKMATE", "5k3/2NPR4/7R1/9/9/9/9/9/9/3K5 w - - 0 1", ["h7h9"], False),
        ("octagon_two_corner_horses", "OCTAGON_HORSE_CHECKMATE", "3k5/1R7/3N1N3/9/9/9/9/9/9/4K4 w - - 0 1", ["b8b9"], True),
        ("eunuch_pawn_supported_by_general", "EUNUCHS_CHASING_EMPEROR_CHECKMATE", "4r4/9/5k3/9/5P3/9/9/9/9/5K3 w - - 0 1", ["f5f6", "f7f8", "f6f7", "f8f9", "f7f8"], True),
        ("white_face_off_center_general", "WHITE_FACE_GENERAL", "4kr3/9/9/4R4/9/9/9/9/9/3K5 b - - 0 1", [], True),
        ("smothered_horse_existing_test", "SMOTHERED_CHECKMATE", "3aka3/4n4/9/5N3/9/9/9/9/9/3K5 w - - 0 1", ["f6g8"], True),
        ("double_rooks_guarding_occupied_capture_square", "DOUBLE_CHARIOTS_CHECKMATE", "3ak4/4aR3/9/9/5R3/9/9/9/9/4K4 w - - 0 1", ["f8f9"], True),
        ("angler_guards_checking_rook_capture_square", "ANGLER_HORSE_CHECKMATE", "3ak4/4aR3/6N2/9/9/9/9/9/9/4K4 w - - 0 1", ["f8f9"], True),
        ("sandwich_uninvolved_home_half_cannons", "CANNONS_SANDWICHING_CHARIOT_CHECKMATE", "3ak4/4aR3/6N2/9/9/9/R8/9/C1C6/4K4 w - - 0 1", ["f8f9"], False),
    ]
    output = []
    removals = {
        "three_chariots_remote_pawns": ["a6", "i6"],
        "elbow_blocked_leg_no_palace_control": ["c8"],
        "octagon_two_corner_horses": ["d7"],
        "double_rooks_guarding_occupied_capture_square": ["f5"],
        "angler_guards_checking_rook_capture_square": ["g7"],
        "sandwich_uninvolved_home_half_cannons": ["a3", "a1", "c1"],
    }
    for name, pattern, fen, moves, expected in cases:
        r = patterns.recognize_pattern(pattern, fen, moves)
        record = {"name": name, "pattern": pattern, "fen": fen, "moves": moves,
                  "expected": expected, "detected": r["detected"], "isCheckmate": r["analysis"]["is_checkmate"],
                  "finalFen": r["fen"], "features": r["features"]}
        if name in removals:
            pieces = board.parse_fen(r["fen"])
            for square in removals[name]:
                del pieces[square]
            counterfactual = encode(pieces, r["fen"].split()[1])
            state = board.position_analysis(counterfactual)
            record["counterfactual"] = {"removed": removals[name], "fen": counterfactual,
                                        "isCheckmate": state["is_checkmate"], "legalMoves": state["legal_moves"]}
        output.append(record)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=ROOT/"docs/checkmate-audit-evidence.json")
    args = parser.parse_args()
    data = json.loads((ROOT/"public/data/checkmate-puzzles.json").read_text(encoding="utf-8"))
    recognition = json.loads((ROOT/"public/data/checkmate-puzzle-recognition.json").read_text(encoding="utf-8"))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(corpus_row, [(p, recognition["results"][p["key"]]) for p in data["puzzles"]], chunksize=16))
        examples = list(pool.map(audit_example, literal_examples(), chunksize=4))
        puzzles = {p["id"]: p for p in data["puzzles"]}
        rechecks = []
        for row in rows:
            for flag, pattern in (("palcorner_unlabeled_sequence_review_candidate", "PALCORNER_HORSE_CHECKMATE"),
                                  ("elbow_without_real_palace_control", "ELBOW_HORSE_CHECKMATE"),
                                  ("horse_cannon_geometry_unlabeled_candidate", "HORSE_CANNON_CHECKMATE")):
                if flag in row["flags"] and row["isCheckmate"]:
                    rechecks.append((puzzles[row["id"]], pattern))
        sequence_checks = list(pool.map(sequence_recheck, rechecks, chunksize=4))
    flags = defaultdict(list)
    for row in rows:
        for flag in row["flags"]:
            flags[flag].append(row["id"])
    result = {"datasetVersion": data["datasetVersion"], "rulesVersion": patterns.CHECKMATE_RULES_VERSION,
              "recognizerSha256": hashlib.sha256(RECOGNIZER_SOURCE.read_bytes()).hexdigest(),
              "patternCounts": dict(Counter(k for row in rows for k in row["labels"])),
              "flagCounts": {k: len(v) for k, v in flags.items()}, "flagIds": dict(flags),
              "examples": examples, "sequenceChecks": sequence_checks, "focusedProbes": focused_probes(), "corpus": rows}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result["flagCounts"], indent=2), flush=True)
    print(f"Audited {len(rows)} puzzles and {len(examples)} literal example calls", flush=True)


if __name__ == "__main__":
    main()
