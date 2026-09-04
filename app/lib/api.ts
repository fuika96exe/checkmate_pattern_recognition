import type { AdvanceResponse, HealthResponse, MemoryPreset, PatternAnalysis, PatternId, PositionResponse, PuzzleLineResponse, PuzzleRecord, RecognitionState, RunAllResponse, TestCase } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE
  ?? (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000");

const PUZZLE_ANALYSIS_ATTEMPTS = 4;

class ApiRequestError extends Error {
  constructor(message: string, readonly status: number | null) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiRequestError(`无法连接后端服务，请确认 ${API_BASE} 已启动`, null);
    }
    throw error;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiRequestError(payload.detail ?? `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

function abortableDelay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason ?? new DOMException("请求已取消", "AbortError"));
      return;
    }
    const finish = () => {
      signal?.removeEventListener("abort", cancel);
      resolve();
    };
    const cancel = () => {
      window.clearTimeout(timer);
      reject(signal.reason ?? new DOMException("请求已取消", "AbortError"));
    };
    const timer = window.setTimeout(finish, milliseconds);
    signal?.addEventListener("abort", cancel, { once: true });
  });
}

async function requestWithRetry<T>(path: string, init?: RequestInit): Promise<T> {
  for (let attempt = 1; attempt <= PUZZLE_ANALYSIS_ATTEMPTS; attempt += 1) {
    try {
      return await request<T>(path, init);
    } catch (error) {
      const retryable = error instanceof ApiRequestError
        && (error.status === null || error.status >= 500);
      if (!retryable || attempt === PUZZLE_ANALYSIS_ATTEMPTS || init?.signal?.aborted) throw error;
      await abortableDelay(500 * (2 ** (attempt - 1)), init?.signal ?? undefined);
    }
  }
  throw new Error("棋题分析重试失败");
}

let puzzleAnalysisQueue: Promise<void> = Promise.resolve();

function enqueuePuzzleAnalysis<T>(task: () => Promise<T>): Promise<T> {
  const result = puzzleAnalysisQueue.then(task, task);
  puzzleAnalysisQueue = result.then(() => undefined, () => undefined);
  return result;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  initial: () => request<PositionResponse>("/api/state/initial", { method: "POST" }),
  advance: (state: RecognitionState, ucciMove: string) => request<AdvanceResponse>("/api/advance", { method: "POST", body: JSON.stringify({ state, ucciMove }) }),
  inspect: (fen: string, memoryPreset: MemoryPreset) => request<PositionResponse>("/api/inspect", { method: "POST", body: JSON.stringify({ fen, memoryPreset, inferFromFen: true }) }),
  cases: () => request<TestCase[]>("/api/test-cases"),
  saveCase: (testCase: TestCase) => request<TestCase>("/api/test-cases", { method: "POST", body: JSON.stringify(testCase) }),
  deleteCase: (id: string) => request<{ deleted: boolean }>(`/api/test-cases/${id}`, { method: "DELETE" }),
  runAll: () => request<RunAllResponse>("/api/test-cases/run-all", { method: "POST" }),
  analyzePattern: (fen: string, ucciMoves: string[], patternId?: PatternId) => request<PatternAnalysis>("/api/analyze-checkmate-pattern", { method: "POST", body: JSON.stringify({ patternId, fen, ucciMoves }) }),
  analyzePuzzle: (puzzle: PuzzleRecord, signal?: AbortSignal) => enqueuePuzzleAnalysis(() =>
    requestWithRetry<PuzzleLineResponse>("/api/analyze-puzzle-line", {
      method: "POST",
      body: JSON.stringify({ fen: puzzle.initialFen, blunderMove: puzzle.blunderMove, pv: puzzle.pv }),
      signal,
    })),
};
