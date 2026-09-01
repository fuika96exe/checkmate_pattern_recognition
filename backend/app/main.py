from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .board import BoardError, position_analysis
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
)
from .service import advance, analyze, create_initial, inspect
from .patterns import analyze_patterns


ROOT = Path(__file__).resolve().parents[1]
BUILT_IN_DIR = ROOT / "tests" / "fixtures" / "built_in"
USER_DIR = ROOT / "tests" / "fixtures" / "user"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")

app = FastAPI(title="象棋開局辨認 MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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
    cases: list[TestCaseInput] = []
    for directory, source in ((BUILT_IN_DIR, "built_in"), (USER_DIR, "user")):
        directory.mkdir(parents=True, exist_ok=True)
        for path in sorted(directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["source"] = source
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
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/state/initial", response_model=InitialResponse)
def api_initial() -> InitialResponse:
    try:
        return create_initial()
    except Exception as exc:  # pragma: no cover
        raise _as_http_error(exc) from exc


@app.post("/api/advance", response_model=AdvanceResponse)
def api_advance(request: AdvanceRequest) -> AdvanceResponse:
    try:
        return advance(request.state, request.ucci_move)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
def api_analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return analyze(request.ucci_moves)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/inspect", response_model=InspectResponse)
def api_inspect(request: InspectRequest) -> InspectResponse:
    try:
        return inspect(request)
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze-position", response_model=PositionAnalysisResponse)
def api_analyze_position(request: PositionAnalysisRequest) -> PositionAnalysisResponse:
    try:
        return PositionAnalysisResponse.model_validate(position_analysis(request.fen))
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.post("/api/analyze-checkmate-pattern", response_model=PatternAnalysisResponse)
def api_analyze_checkmate_pattern(request: PatternAnalysisRequest) -> PatternAnalysisResponse:
    try:
        return PatternAnalysisResponse.model_validate(
            analyze_patterns(request.fen, request.ucci_moves, request.pattern_id)
        )
    except Exception as exc:
        raise _as_http_error(exc) from exc


@app.get("/api/test-cases", response_model=list[TestCaseInput])
def list_test_cases() -> list[TestCaseInput]:
    return _load_cases()


@app.post("/api/test-cases", response_model=TestCaseInput)
def save_test_case(case: TestCaseInput) -> TestCaseInput:
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
def delete_test_case(case_id: str) -> dict[str, bool]:
    path = _case_path(case_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="找不到使用者案例")
    path.unlink()
    return {"deleted": True}


@app.post("/api/test-cases/{case_id}/run", response_model=TestRunResult)
def run_test_case(case_id: str) -> TestRunResult:
    for case in _load_cases():
        if case.id == case_id:
            return _run_case(case)
    raise HTTPException(status_code=404, detail="找不到案例")


@app.post("/api/test-cases/run-all", response_model=TestRunAllResponse)
def run_all_test_cases() -> TestRunAllResponse:
    results = [_run_case(case) for case in _load_cases()]
    return TestRunAllResponse(
        total=len(results),
        passed=sum(result.passed for result in results),
        results=results,
    )
