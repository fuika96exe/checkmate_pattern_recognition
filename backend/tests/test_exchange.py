import json
from pathlib import Path

import pytest

from backend.app import board, exchange


CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "fake_human_exchange.json").read_text(encoding="utf-8")
)["cases"]


@pytest.fixture(params=["native", "python"])
def exchange_backend(request):
    """Run the same reference cases locally and with Cloudflare's board engine."""
    if request.param == "native" and board.NATIVE_BACKEND is None:
        pytest.skip("pyffish is unavailable")
    previous = board.use_backend(board.NATIVE_BACKEND if request.param == "native" else board.PURE_BACKEND)
    yield
    board.use_backend(previous)  # also clears the board caches and the exchange caches


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_fake_human_reference_exchange(case, exchange_backend):
    assert exchange.evaluate_exchange(case["fen"], case["move"]) == case["gain"], case.get("line", "")


def test_invalid_capture_does_not_evaluate_as_a_gain(exchange_backend):
    assert exchange.evaluate_exchange(board.START_FEN, "a0a9") == 0


def test_exchange_does_not_mutate_the_position(exchange_backend):
    fen = CASES[0]["fen"]
    snapshot = board.parse_fen(fen)
    exchange.evaluate_exchange(fen, CASES[0]["move"])
    assert board.parse_fen(fen) == snapshot
