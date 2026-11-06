"""xq_classify.exchange must compute the same values as xiangqi-server (phase 0 step 3).

``fixtures/server_exchange_reference.json`` holds 10,000 moves (8,000 captures,
2,000 quiet moves) sampled from the lab's puzzle and game positions, each with
the value the server's ``api/util/exchange.py`` computed. Like
``fake_human_exchange.json``, these are upstream outputs, not human labels. A
mismatch means the two implementations have diverged; the fixture is never
regenerated from the package. The package runs on its default pure board, as the
server's vendored copy will.
"""
import json
from collections import Counter
from pathlib import Path

import pytest

from xq_classify import board, exchange

REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "server_exchange_reference.json").read_text(encoding="utf-8")
)


@pytest.fixture
def pure_board():
    """The lab installs pyffish as the package backend when it loads; the server runs the pure board."""
    previous = board.use_backend(board.PURE_BACKEND)
    yield
    board.use_backend(previous)


def test_reference_fixture_shape():
    assert REFERENCE["fields"] == ["fen", "move", "kind", "server"]
    assert Counter(kind for _, _, kind, _ in REFERENCE["cases"]) == {"capture": 8000, "quiet": 2000}


def test_package_exchange_matches_server(pure_board):
    assert board.current_backend() is board.PURE_BACKEND
    mismatches = [
        (fen, move, kind, server, got)
        for fen, move, kind, server in REFERENCE["cases"]
        if (got := exchange.evaluate_exchange(fen, move)) != server
    ]
    report = "\n  ".join(f"{fen} {move} ({kind}): server {server}, package {got}"
                         for fen, move, kind, server, got in mismatches[:20])
    assert not mismatches, f"{len(mismatches)} of {len(REFERENCE['cases'])} differ from the server:\n  {report}"
