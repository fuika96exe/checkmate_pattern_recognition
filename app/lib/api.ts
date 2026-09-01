import type { AdvanceResponse, MemoryPreset, PatternAnalysis, PatternId, PositionResponse, RecognitionState, RunAllResponse, TestCase } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`无法连接后端服务，请确认 ${API_BASE} 已启动`);
    }
    throw error;
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  initial: () => request<PositionResponse>("/api/state/initial", { method: "POST" }),
  advance: (state: RecognitionState, ucciMove: string) => request<AdvanceResponse>("/api/advance", { method: "POST", body: JSON.stringify({ state, ucciMove }) }),
  inspect: (fen: string, memoryPreset: MemoryPreset) => request<PositionResponse>("/api/inspect", { method: "POST", body: JSON.stringify({ fen, memoryPreset, inferFromFen: true }) }),
  cases: () => request<TestCase[]>("/api/test-cases"),
  saveCase: (testCase: TestCase) => request<TestCase>("/api/test-cases", { method: "POST", body: JSON.stringify(testCase) }),
  deleteCase: (id: string) => request<{ deleted: boolean }>(`/api/test-cases/${id}`, { method: "DELETE" }),
  runAll: () => request<RunAllResponse>("/api/test-cases/run-all", { method: "POST" }),
  analyzePattern: (fen: string, ucciMoves: string[], patternId?: PatternId) => request<PatternAnalysis>("/api/analyze-checkmate-pattern", { method: "POST", body: JSON.stringify({ patternId, fen, ucciMoves }) }),
};
