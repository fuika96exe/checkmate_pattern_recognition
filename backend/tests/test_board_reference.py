"""The split board geometry must behave exactly like the pre-split reference (board_reference.py).

Phase 0 step 2b split ``pseudo_legal_targets``, ``is_square_attacked`` and
``attacked_squares`` to cognitive complexity <= 15. Their results feed every
label and every piece of evidence, so they are compared with the verbatim
originals exactly:

* ``pseudo_legal_targets`` of every piece: the same list, in the same order;
* ``is_square_attacked`` for every square and both attackers;
* ``attacked_squares`` for both sides: the same targets in the same order, each
  with the same reasons in the same order.

Two kinds of board are compared. Random boards hold any number of pieces of any
kind on any square, so they reach corners real games never do: pieces outside
their palace or across the river, or an attacker already on the target square.
Real positions come from every 4th human-frozen puzzle line.
"""
import json
import random
from pathlib import Path

import board_reference as reference
import pytest

from xq_classify.board import (
    FILES,
    apply_move,
    attacked_squares,
    is_square_attacked,
    parse_fen,
    pseudo_legal_targets,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SQUARES = [f"{file}{rank}" for rank in range(10) for file in FILES]
PIECES = "RNBAKCPrnbakcp"
SEEDS = range(8)
BOARDS_PER_SEED = 250


def random_boards(seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    boards = []
    for _ in range(BOARDS_PER_SEED):
        squares = rng.sample(SQUARES, rng.randint(1, 45))
        boards.append({square: rng.choice(PIECES) for square in squares})
    return boards


def frozen_positions() -> list[dict[str, str]]:
    lines = []
    for directory in ("checkmate_frozen", "midgame_frozen"):
        manifest = json.loads((FIXTURES / directory / "MANIFEST.json").read_text(encoding="utf-8"))
        for name in manifest["frozen"]:
            for case in json.loads((FIXTURES / directory / name).read_text(encoding="utf-8"))["cases"]:
                lines.append((case["initialFen"], [case["blunderMove"], *case["pv"]]))
    boards = []
    for fen, moves in lines[::4]:
        boards.append(parse_fen(fen))
        for move in moves:
            fen = apply_move(fen, move)
            boards.append(parse_fen(fen))
    return boards


def differences(board: dict[str, str]) -> list[str]:
    found = []
    for source, piece in board.items():
        new, old = pseudo_legal_targets(board, source, piece), reference.pseudo_legal_targets(board, source, piece)
        if new != old:
            found.append(f"pseudo_legal_targets {piece}@{source}: {new} != reference {old}")
    for square in SQUARES:
        for by_red in (True, False):
            new, old = is_square_attacked(board, square, by_red), reference.is_square_attacked(board, square, by_red)
            if new != old:
                found.append(f"is_square_attacked {square} by_red={by_red}: {new} != reference {old}")
    for side in ("red", "black"):
        new, old = attacked_squares(board, side), reference.attacked_squares(board, side)
        if list(new.items()) != list(old.items()):
            found.append(f"attacked_squares {side}: {list(new.items())} != reference {list(old.items())}")
    return found


def check(boards: list[dict[str, str]]) -> None:
    for board in boards:
        found = differences(board)
        assert not found, f"board {board}:\n  " + "\n  ".join(found[:10])


@pytest.mark.parametrize("seed", SEEDS)
def test_random_boards_match_reference(seed):
    check(random_boards(seed))


def test_frozen_positions_match_reference():
    boards = frozen_positions()
    assert len(boards) > 400
    check(boards)
