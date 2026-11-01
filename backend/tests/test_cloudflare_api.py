import asyncio
import json
import threading

import pytest

from backend.app import main
from backend.app.board import START_FEN


async def _post(path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode()
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    await main.app(
        {
            "type": "http", "asgi": {"version": "3.0"},
            "http_version": "1.1", "method": "POST", "scheme": "http",
            "path": path, "raw_path": path.encode(), "query_string": b"",
            "root_path": "", "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 1234), "server": ("test", 80),
        },
        receive,
        send,
    )
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, json.loads(response)


@pytest.mark.parametrize("path", ["/api/analyze-tactics", "/api/analyze-live-report"])
def test_move_analysis_works_without_threads_on_cloudflare(monkeypatch, path: str) -> None:
    def no_threads(*args, **kwargs):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(main, "IS_CLOUDFLARE_WORKER", True)
    monkeypatch.setattr(threading.Thread, "start", no_threads)
    payload = (
        {"fen": START_FEN, "ucciMoves": ["h2e2"]}
        if path == "/api/analyze-tactics"
        else {"initialFen": START_FEN, "ucciMoves": ["h2e2"], "targetIndex": 1, "ply": 1}
    )
    status, response = asyncio.run(_post(path, payload))
    assert status == 200
    if path == "/api/analyze-tactics":
        assert response["annotations"][0]["ucci"] == "h2e2"
    else:
        assert response["legal"] is True
        assert response["ucci"] == "h2e2"
        assert response["ply"] == 1


def test_local_live_report_keeps_analysis_off_the_event_loop(monkeypatch) -> None:
    caller_thread = threading.get_ident()
    analysis_threads = []
    original_analyze = main.analyze_live_game_report

    def analyze(request):
        analysis_threads.append(threading.get_ident())
        return original_analyze(request)

    monkeypatch.setattr(main, "IS_CLOUDFLARE_WORKER", False)
    monkeypatch.setattr(main, "analyze_live_game_report", analyze)
    status, response = asyncio.run(_post("/api/analyze-live-report", {
        "initialFen": START_FEN, "ucciMoves": ["h2e2"], "targetIndex": 1, "ply": 1,
    }))
    assert status == 200
    assert response["ucci"] == "h2e2"
    assert len(analysis_threads) == 1
    assert analysis_threads[0] != caller_thread
