from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .board import BoardError, apply_move, position_analysis
from .builtin_cases import BUILT_IN_CASES
from .models import (
    AdvanceRequest,
    AdvanceResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    InitialResponse,
    InspectRequest,
    InspectResponse,
    TestCaseInput,
    TestRunAllResponse,
    TestRunResult,
    PositionAnalysisRequest,
    PositionAnalysisResponse,
    PatternAnalysisRequest,
    PatternAnalysisResponse,
    PuzzleLineRequest,
    PuzzleLineResponse,
    PuzzleTimelineEntry,
)
from .service import advance, analyze, create_initial, inspect
from .patterns import CHECKMATE_RULES_VERSION, analyze_patterns


ROOT = Path(os.environ.get("XIANGQI_DATA_DIR", Path(__file__).resolve().parents[1]))
BUILT_IN_DIR = ROOT / "tests" / "fixtures" / "built_in"
USER_DIR = ROOT / "tests" / "fixtures" / "user"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
IS_CLOUDFLARE_WORKER = sys.platform == "emscripten"

app = FastAPI(title="象棋開局辨認 MVP", version="0.1.0")
configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if IS_CLOUDFLARE_WORKER:
    configured_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins
    or [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _as_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BoardError | ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="辨認服務發生未預期錯誤")


def _case_path(case_id: str, *, user: bool = True) -> Path:
    if not SAFE_ID.fullmatch(case_id):
        raise HTTPException(status_code=422, detail="案例 ID 只可使用小寫字母、數字及連字號")
    return (USER_DIR if user else BUILT_IN_DIR) / f"{case_id}.json"


def _load_cases() -> list[TestCaseInput]:
    cases = [TestCaseInput.model_validate(payload) for payload in BUILT_IN_CASES]
    if USER_DIR.exists():
        for path in sorted(USER_DIR.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["source"] = "user"
            cases.append(TestCaseInput.model_validate(payload))
    return cases


def _run_case(case: TestCaseInput) -> TestRunResult:
    response = inspect(
        InspectRequest(
            fen=case.fen,
            memory_preset=case.memory_preset,
            infer_from_fen=True,
        )
    )
    actual = response.state.classification.display_name
    return TestRunResult(
        id=case.id,
        passed=actual == case.expected_name,
        expected_name=case.expected_name,
        actual_name=actual,
        diagnostics=response.state.classification.diagnostics,
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "rulesVersion": CHECKMATE_RULES_VERSION}


@app.post("/api/state/initial", response_model=InitialResponse)
async def api_initial() -> InitialResponse:
    try:
        return create_initial()
    except Exception as exc:  # pragma: no cover
        raise _as_http_error(exc) from exc


@app.post("/api/advance", response_model=AdvanceResponse)
async def api_advance(request: AdvanceRequest) -> AdvanceResponse:
    try:
        return advance(request.state, request.ucci_move)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def api_analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return analyze(request.ucci_moves)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/inspect", response_model=InspectResponse)
async def api_inspect(request: InspectRequest) -> InspectResponse:
    try:
        return inspect(request)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze-position", response_model=PositionAnalysisResponse)
async def api_analyze_position(request: PositionAnalysisRequest) -> PositionAnalysisResponse:
    try:
        return PositionAnalysisResponse.model_validate(position_analysis(request.fen))
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze-checkmate-pattern", response_model=PatternAnalysisResponse)
async def api_analyze_checkmate_pattern(request: PatternAnalysisRequest) -> PatternAnalysisResponse:
    try:
        return PatternAnalysisResponse.model_validate(
            analyze_patterns(request.fen, request.ucci_moves, request.pattern_id)
        )
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze-puzzle-line", response_model=PuzzleLineResponse)
async def api_analyze_puzzle_line(request: PuzzleLineRequest) -> PuzzleLineResponse:
    moves = [request.blunder_move, *request.pv]
    timeline = [PuzzleTimelineEntry(index=0, fen=request.fen)]
    current_fen = request.fen

    for index, move in enumerate(moves, start=1):
        try:
            current_fen = apply_move(current_fen, move)
        except Exception as exc:
            return PuzzleLineResponse(
                rules_version=CHECKMATE_RULES_VERSION,
                valid=False,
                error=f"第 {index} 手 {move} 無法套用：{exc}",
                failed_move_index=index,
                timeline=timeline,
            )
        timeline.append(PuzzleTimelineEntry(index=index, fen=current_fen, move=move))

    try:
        analysis = PatternAnalysisResponse.model_validate(
            analyze_patterns(request.fen, moves)
        )
    except Exception as exc:
        return PuzzleLineResponse(
            rules_version=CHECKMATE_RULES_VERSION,
            valid=False,
            error=f"殺法分析失敗：{exc}",
            timeline=timeline,
        )

    if not analysis.analysis.is_checkmate:
        return PuzzleLineResponse(
            rules_version=CHECKMATE_RULES_VERSION,
            valid=False,
            error="解答線終局不是將死局面",
            timeline=timeline,
            analysis=analysis,
        )

    return PuzzleLineResponse(
        rules_version=CHECKMATE_RULES_VERSION,
        valid=True,
        timeline=timeline,
        analysis=analysis,
    )


@app.get("/api/test-cases", response_model=list[TestCaseInput])
async def list_test_cases() -> list[TestCaseInput]:
    return _load_cases()


@app.post("/api/test-cases", response_model=TestCaseInput)
async def save_test_case(case: TestCaseInput) -> TestCaseInput:
    if IS_CLOUDFLARE_WORKER or os.getenv("READ_ONLY_TEST_CASES") == "1":
        raise HTTPException(
            status_code=503,
            detail="Saving fixtures is disabled on this logic-only deployment.",
        )
    case.source = "user"
    path = _case_path(case.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(case.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
    return case


@app.delete("/api/test-cases/{case_id}")
async def delete_test_case(case_id: str) -> dict[str, bool]:
    if IS_CLOUDFLARE_WORKER or os.getenv("READ_ONLY_TEST_CASES") == "1":
        raise HTTPException(
            status_code=503,
            detail="Deleting fixtures is disabled on this logic-only deployment.",
        )
    path = _case_path(case_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="找不到使用者案例")
    path.unlink()
    return {"deleted": True}


@app.post("/api/test-cases/{case_id}/run", response_model=TestRunResult)
async def run_test_case(case_id: str) -> TestRunResult:
    for case in _load_cases():
        if case.id == case_id:
            return _run_case(case)
    raise HTTPException(status_code=404, detail="找不到案例")


@app.post("/api/test-cases/run-all", response_model=TestRunAllResponse)
async def run_all_test_cases() -> TestRunAllResponse:
    results = [_run_case(case) for case in _load_cases()]
    return TestRunAllResponse(
        total=len(results),
        passed=sum(result.passed for result in results),
        results=results,
    )
