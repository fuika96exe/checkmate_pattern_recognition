"""The pure-Python move generator must agree with pyffish (phase 0 step 2).

xq_classify always classifies with its own pure generator; pyffish is only the
reference. For every position along the puzzle lines below, both must give:

* the same set of legal moves (the order differs by design, and evidence
  follows the pure order);
* the same check status, from pyffish ``gives_check`` and from both pure checks:
  the targeted ``is_square_attacked`` used by move generation and the attack map
  behind ``position_analysis``;
* the same checkmate and stalemate;
* the same position after each move of the line: board, side to move and move
  number. The halfmove clock is a known difference.

Positions without both generals are skipped, because they must never reach pyffish.

Default: every 4th line of the human-frozen midgame and checkmate sets (~500
positions; pyffish costs about 30 ms a position).
BOARD_PARITY_FULL=1: every line of both upload CSVs (7,864 puzzles, 54,880
positions, about 30 minutes).
"""
import ast
import csv
import json
import os
from pathlib import Path

import pytest

from app import board as lab_board
from xq_classify.board import (
    apply_legal_move,
    attacked_squares,
    generate_legal_moves,
    has_both_generals,
    is_square_attacked,
    parse_fen,
    side_to_move,
)

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests" / "fixtures"
SOURCES = BACKEND.parent / "data" / "puzzle-sources"
CSV_FILES = ("Puzzles_2026-10-22_08-12-00_tactic_upload.csv", "Puzzles_2026-10-22_08-12-00_checkmate_upload.csv")
FULL = os.environ.get("BOARD_PARITY_FULL") == "1"
MAX_REPORTED = 20
DEFAULT_STRIDE = 4

pytestmark = pytest.mark.skipif(lab_board.pyffish is None, reason="pyffish is unavailable")


def frozen_lines() -> dict[str, tuple[str, list[str]]]:
    lines = {}
    for directory in ("checkmate_frozen", "midgame_frozen"):
        manifest = json.loads((FIXTURES / directory / "MANIFEST.json").read_text(encoding="utf-8"))
        for name in manifest["frozen"]:
            for case in json.loads((FIXTURES / directory / name).read_text(encoding="utf-8"))["cases"]:
                lines[f"{directory}:{case['id']}"] = (case["initialFen"], [case["blunderMove"], *case["pv"]])
    return lines


def csv_lines() -> dict[str, tuple[str, list[str]]]:
    lines = {}
    for name in CSV_FILES:
        with (SOURCES / name).open(encoding="utf-8-sig", newline="") as handle:
            for row_number, row in enumerate(csv.DictReader(handle), 2):
                moves = [row["blunder_move"].strip(), *ast.literal_eval(row["pv"])]
                lines[f"{name}:{row_number}"] = (row["fen_before"].strip(), moves)
    return lines


def compare_position(fen: str) -> list[str]:
    """Differences between the two generators for one position (empty when they agree)."""
    board = parse_fen(fen)
    moving = side_to_move(fen)
    opponent = "black" if moving == "red" else "red"
    king = next(square for square, piece in board.items() if piece == ("K" if moving == "red" else "k"))
    pure_moves = generate_legal_moves(fen)
    native_moves = lab_board.NATIVE_BACKEND.legal_moves(fen)
    pure_check = is_square_attacked(board, king, opponent == "red")
    map_check = bool(attacked_squares(board, opponent).get(king))
    native_check = bool(lab_board.pyffish.gives_check(lab_board.VARIANT, fen, []))
    found = []
    if len(set(pure_moves)) != len(pure_moves):
        found.append(f"pure lists a move twice: {sorted(pure_moves)}")
    if set(pure_moves) != set(native_moves):
        found.append(f"moves pure-only {sorted(set(pure_moves) - set(native_moves))} "
                     f"native-only {sorted(set(native_moves) - set(pure_moves))}")
    if not pure_check == map_check == native_check:
        found.append(f"check: is_square_attacked {pure_check}, attack map {map_check}, pyffish {native_check}")
    if (pure_check and not pure_moves) != (native_check and not native_moves):
        found.append("checkmate differs")
    if (not pure_check and not pure_moves) != (not native_check and not native_moves):
        found.append("stalemate differs")
    return found


def compare_move(fen: str, move: str) -> tuple[str, list[str]]:
    pure_after = apply_legal_move(fen, move)
    native_after = lab_board.NATIVE_BACKEND.apply_move(fen, move)
    pure_fields, native_fields = pure_after.split(), native_after.split()
    keep = (0, 1, 5)  # board, side to move, move number; not the halfmove clock (index 4)
    if [pure_fields[i] for i in keep] != [native_fields[i] for i in keep]:
        return pure_after, [f"after {move}: pure {pure_after} / pyffish {native_after}"]
    return pure_after, []


def test_pure_generator_matches_pyffish():
    lines = csv_lines() if FULL else dict(list(frozen_lines().items())[::DEFAULT_STRIDE])
    compared = skipped = 0
    mismatches = []
    for key, (fen, moves) in lines.items():
        for ply, move in enumerate([*moves, None]):
            if not has_both_generals(parse_fen(fen)):
                skipped += 1
                break
            problems = compare_position(fen)
            compared += 1
            if move is not None:
                if move not in generate_legal_moves(fen):
                    problems.append(f"line move {move} is not legal")
                    mismatches.append((key, ply, fen, problems))
                    break
                fen, move_problems = compare_move(fen, move)
                problems += move_problems
            if problems:
                mismatches.append((key, ply, fen, problems))
    report = [f"{key} ply {ply} {fen}\n      " + "\n      ".join(problems)
              for key, ply, fen, problems in mismatches[:MAX_REPORTED]]
    assert not mismatches, f"{len(mismatches)} mismatches in {compared} positions:\n  " + "\n  ".join(report)
    assert compared >= (50_000 if FULL else 400), (compared, skipped)
