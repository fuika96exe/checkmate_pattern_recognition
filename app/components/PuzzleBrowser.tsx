"use client";

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { Spinner } from "@fluentui/react-spinner";
import { api } from "../lib/api";
import { PATTERN_LABELS } from "../lib/patterns";
import type {
  PatternId,
  PuzzleDataset,
  PuzzleExpectations,
  PuzzleLineResponse,
  PuzzleRecognitionStatus,
  PuzzleRecognitionSummary,
  PuzzleRecord,
} from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

const PAGE_SIZE = 24;
const ANALYSIS_WORKERS = 3;
const CACHE_PREFIX = "xiangqi-puzzle-recognition:v1";

interface RecognitionCache {
  datasetVersion: string;
  rulesVersion: string;
  results: Record<string, PuzzleRecognitionSummary>;
}

interface BatchState {
  running: boolean;
  completed: number;
  total: number;
}

function parseFen(fen: string): Record<string, string> {
  const board: Record<string, string> = {};
  const placement = fen.trim().split(/\s+/)[0] ?? "";
  placement.split("/").forEach((rank, row) => {
    let file = 0;
    for (const character of rank) {
      if (/\d/.test(character)) file += Number(character);
      else {
        board[`${String.fromCharCode(97 + file)}${9 - row}`] = character;
        file += 1;
      }
    }
  });
  return board;
}

const MiniBoard = memo(function MiniBoard({ fen }: { fen: string }) {
  const board = useMemo(() => parseFen(fen), [fen]);
  return (
    <div className="mini-board" aria-label="棋题局面缩图">
      {Array.from({ length: 90 }, (_, index) => {
        const row = Math.floor(index / 9);
        const file = index % 9;
        const square = `${String.fromCharCode(97 + file)}${9 - row}`;
        const piece = board[square];
        return (
          <span className="mini-square" key={square}>
            {piece && <i className={piece === piece.toUpperCase() ? "red" : "black"} />}
          </span>
        );
      })}
    </div>
  );
});

function responseSummary(response: PuzzleLineResponse): PuzzleRecognitionSummary {
  if (!response.valid || !response.analysis) {
    return { status: "invalid", patternIds: [], error: response.error ?? "无法分析棋题" };
  }
  const patternIds = response.analysis.matches.map((match) => match.patternId);
  return {
    status: patternIds.length ? "matched" : "unmatched",
    patternIds,
  };
}

function statusLabel(status: PuzzleRecognitionStatus): string {
  return {
    unanalyzed: "未分析",
    analyzing: "分析中",
    matched: "已匹配",
    unmatched: "未匹配",
    invalid: "无效",
  }[status];
}

function statusFor(
  puzzle: PuzzleRecord,
  summaries: Record<string, PuzzleRecognitionSummary>,
  analyzing: Set<string>,
): PuzzleRecognitionStatus {
  if (puzzle.importStatus === "invalid") return "invalid";
  if (analyzing.has(puzzle.key)) return "analyzing";
  return summaries[puzzle.key]?.status ?? "unanalyzed";
}

function samePatterns(left: PatternId[], right: PatternId[]): boolean {
  return left.length === right.length && [...left].sort().every((item, index) => item === [...right].sort()[index]);
}

export function PuzzleBrowser() {
  const [dataset, setDataset] = useState<PuzzleDataset | null>(null);
  const [expectations, setExpectations] = useState<Record<string, PatternId[]>>({});
  const [rulesVersion, setRulesVersion] = useState("");
  const [summaries, setSummaries] = useState<Record<string, PuzzleRecognitionSummary>>({});
  const [analyzing, setAnalyzing] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<PuzzleRecord | null>(null);
  const [selectedResult, setSelectedResult] = useState<PuzzleLineResponse | null>(null);
  const [selectedBusy, setSelectedBusy] = useState(false);
  const [timelineIndex, setTimelineIndex] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [playbackDelay, setPlaybackDelay] = useState(800);
  const [loadError, setLoadError] = useState("");
  const [ratingMin, setRatingMin] = useState("");
  const [ratingMax, setRatingMax] = useState("");
  const [movesMin, setMovesMin] = useState("");
  const [movesMax, setMovesMax] = useState("");
  const [patternFilter, setPatternFilter] = useState<"" | PatternId>("");
  const [statusFilter, setStatusFilter] = useState<"all" | "matched" | "unmatched" | "invalid">("all");
  const [filtersExpanded, setFiltersExpanded] = useState(true);
  const [listExpanded, setListExpanded] = useState(true);
  const [page, setPage] = useState(1);
  const [batch, setBatch] = useState<BatchState>({ running: false, completed: 0, total: 0 });
  const selectionToken = useRef(0);
  const batchController = useRef<AbortController | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetch("/data/checkmate-puzzles.json").then((response) => {
        if (!response.ok) throw new Error(`无法载入棋题资料：HTTP ${response.status}`);
        return response.json() as Promise<PuzzleDataset>;
      }),
      fetch("/data/checkmate-puzzle-expectations.json").then((response) => {
        if (!response.ok) return { schemaVersion: "1.0", expectations: {} } as PuzzleExpectations;
        return response.json() as Promise<PuzzleExpectations>;
      }),
      api.health(),
    ]).then(([nextDataset, nextExpectations, health]) => {
      if (!active) return;
      setDataset(nextDataset);
      setExpectations(nextExpectations.expectations);
      setRulesVersion(health.rulesVersion);
      try {
        const raw = window.localStorage.getItem(`${CACHE_PREFIX}:${nextDataset.datasetVersion}`);
        if (raw) {
          const cache = JSON.parse(raw) as RecognitionCache;
          if (cache.datasetVersion === nextDataset.datasetVersion && cache.rulesVersion === health.rulesVersion) {
            setSummaries(cache.results);
          }
        }
      } catch {
        try { window.localStorage.removeItem(`${CACHE_PREFIX}:${nextDataset.datasetVersion}`); } catch { /* storage is unavailable */ }
      }
    }).catch((reason: unknown) => {
      if (active) setLoadError(reason instanceof Error ? reason.message : "无法载入棋题浏览器");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!dataset || !rulesVersion) return;
    const timer = window.setTimeout(() => {
      const cache: RecognitionCache = {
        datasetVersion: dataset.datasetVersion,
        rulesVersion,
        results: summaries,
      };
      try {
        window.localStorage.setItem(`${CACHE_PREFIX}:${dataset.datasetVersion}`, JSON.stringify(cache));
      } catch {
        // Private browsing or a full quota must not block human review.
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [dataset, rulesVersion, summaries]);

  useEffect(() => {
    if (!playing || !selectedResult || timelineIndex >= selectedResult.timeline.length - 1) return;
    const timer = window.setTimeout(() => {
      setTimelineIndex((current) => Math.min(current + 1, selectedResult.timeline.length - 1));
    }, playbackDelay);
    return () => window.clearTimeout(timer);
  }, [playing, playbackDelay, selectedResult, timelineIndex]);

  const filteredPuzzles = useMemo(() => {
    if (!dataset) return [];
    const minRating = ratingMin === "" ? null : Number(ratingMin);
    const maxRating = ratingMax === "" ? null : Number(ratingMax);
    const minMoves = movesMin === "" ? null : Number(movesMin);
    const maxMoves = movesMax === "" ? null : Number(movesMax);
    return dataset.puzzles.filter((puzzle) => {
      const status = statusFor(puzzle, summaries, analyzing);
      if (minRating !== null && (puzzle.rating === null || puzzle.rating < minRating)) return false;
      if (maxRating !== null && (puzzle.rating === null || puzzle.rating > maxRating)) return false;
      if (minMoves !== null && puzzle.moveCount < minMoves) return false;
      if (maxMoves !== null && puzzle.moveCount > maxMoves) return false;
      if (patternFilter && !summaries[puzzle.key]?.patternIds.includes(patternFilter)) return false;
      if (statusFilter !== "all" && status !== statusFilter) return false;
      return true;
    });
  }, [analyzing, dataset, movesMax, movesMin, patternFilter, ratingMax, ratingMin, statusFilter, summaries]);

  const totalPages = Math.max(1, Math.ceil(filteredPuzzles.length / PAGE_SIZE));
  const visiblePuzzles = filteredPuzzles.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const counts = useMemo(() => {
    if (!dataset) return { matched: 0, unmatched: 0, invalid: 0, unanalyzed: 0 };
    return dataset.puzzles.reduce((accumulator, puzzle) => {
      const status = statusFor(puzzle, summaries, analyzing);
      if (status === "analyzing") accumulator.unanalyzed += 1;
      else accumulator[status] += 1;
      return accumulator;
    }, { matched: 0, unmatched: 0, invalid: 0, unanalyzed: 0 });
  }, [analyzing, dataset, summaries]);
  const activeFilterCount = [
    ratingMin,
    ratingMax,
    movesMin,
    movesMax,
    patternFilter,
    statusFilter === "all" ? "" : statusFilter,
  ].filter(Boolean).length;

  function recordResponse(puzzle: PuzzleRecord, response: PuzzleLineResponse) {
    if (rulesVersion && response.rulesVersion !== rulesVersion) {
      setRulesVersion(response.rulesVersion);
      setSummaries({ [puzzle.key]: responseSummary(response) });
      return;
    }
    setSummaries((current) => ({ ...current, [puzzle.key]: responseSummary(response) }));
  }

  async function openPuzzle(puzzle: PuzzleRecord) {
    const token = ++selectionToken.current;
    setSelected(puzzle);
    setSelectedResult(null);
    setPlaying(false);
    setTimelineIndex(1);
    if (puzzle.importStatus === "invalid") return;
    setSelectedBusy(true);
    setAnalyzing((current) => new Set(current).add(puzzle.key));
    try {
      const response = await api.analyzePuzzle(puzzle);
      recordResponse(puzzle, response);
      if (selectionToken.current === token) {
        setSelectedResult(response);
        setTimelineIndex(response.timeline.length > 1 ? 1 : 0);
      }
    } catch (reason) {
      const error = reason instanceof Error ? reason.message : "棋题分析失败";
      const summary: PuzzleRecognitionSummary = { status: "invalid", patternIds: [], error };
      setSummaries((current) => ({ ...current, [puzzle.key]: summary }));
      if (selectionToken.current === token) {
        setSelectedResult({ rulesVersion, valid: false, error, failedMoveIndex: null, timeline: [], analysis: null });
      }
    } finally {
      setAnalyzing((current) => {
        const next = new Set(current);
        next.delete(puzzle.key);
        return next;
      });
      if (selectionToken.current === token) setSelectedBusy(false);
    }
  }

  async function runAllPuzzles() {
    if (!dataset || batch.running) return;
    const puzzles = dataset.puzzles.filter((puzzle) => puzzle.importStatus === "ready");
    const controller = new AbortController();
    batchController.current = controller;
    setBatch({ running: true, completed: 0, total: puzzles.length });
    let cursor = 0;

    async function worker() {
      while (!controller.signal.aborted) {
        const puzzle = puzzles[cursor];
        cursor += 1;
        if (!puzzle) return;
        setAnalyzing((current) => new Set(current).add(puzzle.key));
        try {
          const response = await api.analyzePuzzle(puzzle, controller.signal);
          recordResponse(puzzle, response);
        } catch (reason) {
          if (!controller.signal.aborted) {
            const error = reason instanceof Error ? reason.message : "棋题分析失败";
            setSummaries((current) => ({
              ...current,
              [puzzle.key]: { status: "invalid", patternIds: [], error },
            }));
          }
        } finally {
          setAnalyzing((current) => {
            const next = new Set(current);
            next.delete(puzzle.key);
            return next;
          });
          if (!controller.signal.aborted) {
            setBatch((current) => ({ ...current, completed: current.completed + 1 }));
          }
        }
      }
    }

    await Promise.all(Array.from({ length: ANALYSIS_WORKERS }, () => worker()));
    setBatch((current) => ({ ...current, running: false }));
    batchController.current = null;
  }

  function stopBatch() {
    batchController.current?.abort();
    setBatch((current) => ({ ...current, running: false }));
  }

  if (loadError) return <div className="error-banner">{loadError}</div>;
  if (!dataset) return <div className="loading-state"><Spinner label="正在载入棋题资料" /></div>;

  const selectedStatus = selected ? statusFor(selected, summaries, analyzing) : "unanalyzed";
  const timeline = selectedResult?.timeline ?? [];
  const currentFrame = timeline[timelineIndex];
  const currentPatterns = selectedResult?.analysis?.matches.map((match) => match.patternId) ?? [];
  const reviewedPatterns = selected ? expectations[selected.key] ?? [] : [];
  const playbackActive = playing && timelineIndex < timeline.length - 1;

  return (
    <div className="puzzle-browser">
      <section className="panel puzzle-catalog">
        <div className="panel-heading puzzle-heading">
          <div>
            <span className="eyebrow">PUZZLE CORPUS</span>
            <h2>棋题浏览器</h2>
          </div>
          <Badge appearance="outline">{dataset.puzzleCount} 题</Badge>
        </div>

        <div className="puzzle-metrics">
          <span><strong>{counts.matched}</strong> 已匹配</span>
          <span><strong>{counts.unmatched}</strong> 未匹配</span>
          <span><strong>{counts.invalid}</strong> 无效</span>
          <span><strong>{counts.unanalyzed}</strong> 未分析</span>
        </div>

        <button
          type="button"
          className="puzzle-section-toggle"
          aria-expanded={filtersExpanded}
          aria-controls="puzzle-filter-panel"
          onClick={() => setFiltersExpanded((expanded) => !expanded)}
        >
          <span><strong>筛选器</strong><small>{activeFilterCount ? `${activeFilterCount} 项条件生效` : "显示全部棋题"}</small></span>
          <span className="puzzle-toggle-action">{filtersExpanded ? "收起" : "展开"}<i aria-hidden="true">{filtersExpanded ? "⌃" : "⌄"}</i></span>
        </button>

        {filtersExpanded && (
          <div className="puzzle-filter-grid" id="puzzle-filter-panel">
            <label><span>评分下限</span><input type="number" value={ratingMin} onChange={(event) => { setRatingMin(event.target.value); setPage(1); }} placeholder="不限" /></label>
            <label><span>评分上限</span><input type="number" value={ratingMax} onChange={(event) => { setRatingMax(event.target.value); setPage(1); }} placeholder="不限" /></label>
            <label><span>着数下限</span><input type="number" value={movesMin} onChange={(event) => { setMovesMin(event.target.value); setPage(1); }} placeholder="不限" /></label>
            <label><span>着数上限</span><input type="number" value={movesMax} onChange={(event) => { setMovesMax(event.target.value); setPage(1); }} placeholder="不限" /></label>
            <label className="wide"><span>杀法</span><select value={patternFilter} onChange={(event) => { setPatternFilter(event.target.value as "" | PatternId); setPage(1); }}><option value="">全部杀法</option>{Object.entries(PATTERN_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
            <label><span>状态</span><select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value as typeof statusFilter); setPage(1); }}><option value="all">全部</option><option value="matched">已匹配</option><option value="unmatched">未匹配</option><option value="invalid">无效</option></select></label>
          </div>
        )}

        <div className="batch-bar">
          <div>
            <strong>{batch.running ? `正在分析 ${batch.completed} / ${batch.total}` : "全量人工复核准备"}</strong>
            <small>每题实时运行全部杀法规则，结果仅作人工检查。</small>
          </div>
          {batch.running ? <Button onClick={stopBatch}>停止</Button> : <Button appearance="primary" onClick={() => void runAllPuzzles()}>分析全部 {dataset.puzzleCount} 题</Button>}
        </div>
        {batch.total > 0 && <progress className="batch-progress" max={batch.total} value={batch.completed} />}

        <button
          type="button"
          className="puzzle-section-toggle puzzle-list-toggle"
          aria-expanded={listExpanded}
          aria-controls="puzzle-list-panel"
          onClick={() => setListExpanded((expanded) => !expanded)}
        >
          <span><strong>题目列表</strong><small>{filteredPuzzles.length} 题 · 第 {page} / {totalPages} 页</small></span>
          <span className="puzzle-toggle-action">{listExpanded ? "收起" : "展开"}<i aria-hidden="true">{listExpanded ? "⌃" : "⌄"}</i></span>
        </button>

        {listExpanded && (
          <div id="puzzle-list-panel">
            <div className="puzzle-list" aria-label="棋题列表">
              {visiblePuzzles.map((puzzle) => {
                const status = statusFor(puzzle, summaries, analyzing);
                const patternIds = summaries[puzzle.key]?.patternIds ?? [];
                return (
                  <button type="button" className={`puzzle-row${selected?.key === puzzle.key ? " selected" : ""}`} key={puzzle.key} onClick={() => void openPuzzle(puzzle)}>
                    <MiniBoard fen={puzzle.initialFen} />
                    <span className="puzzle-row-main">
                      <span className="puzzle-patterns">
                        {patternIds.length ? patternIds.map((id) => <i key={id}>{PATTERN_LABELS[id]}</i>) : <em>{status === "analyzing" ? "正在识别…" : status === "unmatched" ? "未识别到杀法" : status === "invalid" ? "无法识别杀法" : "待识别杀法"}</em>}
                      </span>
                      <span className="puzzle-row-meta">
                        <strong>{puzzle.solverSide === "red" ? "红方解题" : puzzle.solverSide === "black" ? "黑方解题" : "行棋方不明"}</strong>
                        <small>{puzzle.moveCount} 着</small>
                        <span className={`puzzle-row-status ${status}`}>{statusLabel(status)}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
              {visiblePuzzles.length === 0 && <div className="empty-state">没有符合筛选条件的棋题。</div>}
            </div>

            <div className="puzzle-pagination">
              <Button size="small" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>上一页</Button>
              <span>{page} / {totalPages} · {filteredPuzzles.length} 题</span>
              <Button size="small" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>下一页</Button>
            </div>
          </div>
        )}
      </section>

      <section className="puzzle-viewer">
        {!selected ? (
          <div className="panel puzzle-placeholder">
            <span className="eyebrow">HUMAN REVIEW</span>
            <h2>选择一道棋题开始检查</h2>
            <p>打开棋题时会实时重播失着与 PV，并以整条解答线的终局运行全部杀法规则。</p>
          </div>
        ) : selected.importStatus === "invalid" ? (
          <div className="panel">
            <div className="panel-heading"><div><span className="eyebrow">INVALID PUZZLE</span><h2>棋题资料无效</h2></div><Badge appearance="outline">无效</Badge></div>
            <div className="error-banner">{selected.importErrors.join("；")}</div>
          </div>
        ) : selectedBusy && !selectedResult ? (
          <div className="panel loading-state"><Spinner label="正在实时分析棋题" /></div>
        ) : (
          <>
            <section className="panel puzzle-board-panel">
              <div className="panel-heading">
                <div><span className="eyebrow">SOLUTION REPLAY</span><h2>{selected.solverSide === "red" ? "红方" : "黑方"}解题 · {selected.moveCount} 着</h2></div>
                <Badge appearance="outline">{statusLabel(selectedStatus)}</Badge>
              </div>
              {currentFrame ? (
                <>
                  <XiangqiBoard fen={currentFrame.fen} legalMoves={[]} disabled onMove={() => undefined} />
                  <div className="puzzle-replay-controls">
                    <Button disabled={timelineIndex <= 0} onClick={() => { setPlaying(false); setTimelineIndex((current) => current - 1); }}>上一步</Button>
                    <span>{timelineIndex} / {timeline.length - 1}</span>
                    <Button disabled={timelineIndex >= timeline.length - 1} onClick={() => { setPlaying(false); setTimelineIndex((current) => current + 1); }}>下一步</Button>
                    <Button onClick={() => { if (timelineIndex >= timeline.length - 1) setTimelineIndex(Math.min(1, timeline.length - 1)); setPlaying(!playbackActive); }}>{playbackActive ? "暂停" : "自动播放"}</Button>
                    <Button onClick={() => { setPlaying(false); setTimelineIndex(Math.min(1, timeline.length - 1)); }}>回到解题起点</Button>
                    <label>速度<select value={playbackDelay} onChange={(event) => setPlaybackDelay(Number(event.target.value))}><option value={1200}>慢</option><option value={800}>正常</option><option value={450}>快</option></select></label>
                  </div>
                  <div className="fen-strip"><span>FEN</span><code>{currentFrame.fen}</code></div>
                  <div className="puzzle-moves">
                    {timeline.slice(1).map((frame) => <button type="button" className={frame.index === timelineIndex ? "active" : ""} key={frame.index} onClick={() => { setPlaying(false); setTimelineIndex(frame.index); }}><span>{frame.index}</span><code>{frame.move}</code></button>)}
                  </div>
                </>
              ) : <div className="error-banner">{selectedResult?.error ?? "无法建立棋题时间线"}</div>}
            </section>

            <section className="panel puzzle-recognition-panel">
              <div className="panel-heading">
                <div><span className="eyebrow">RECOGNITION RESULT</span><h2>整条解答线的杀法</h2></div>
                <Badge appearance="outline">{currentPatterns.length} 项匹配</Badge>
              </div>
              {selectedResult?.error && <div className="error-banner">{selectedResult.error}</div>}
              {selectedResult?.valid && selectedResult.analysis ? (
                <>
                  <div className="recognition-state">
                    <strong>{selectedResult.analysis.analysis.isCheckmate ? "终局已将死" : "终局不是将死"}</strong>
                    <span>合法着法 {selectedResult.analysis.analysis.legalMoves.length} · 规则 {selectedResult.rulesVersion}</span>
                  </div>
                  <div className="recognized-pattern-list">
                    {currentPatterns.length ? currentPatterns.map((patternId) => (
                      <div key={patternId}><strong>{PATTERN_LABELS[patternId]}</strong><code>{patternId}</code></div>
                    )) : <div className="empty-state">这是有效的将死局面，但没有命中任何已接入杀法。</div>}
                  </div>
                  {reviewedPatterns.length > 0 && (
                    <div className={`reviewed-result${samePatterns(reviewedPatterns, currentPatterns) ? " match" : " mismatch"}`}>
                      <strong>{samePatterns(reviewedPatterns, currentPatterns) ? "符合人工复核标签" : "与人工复核标签不同"}</strong>
                      <span>{reviewedPatterns.map((id) => PATTERN_LABELS[id]).join("、")}</span>
                    </div>
                  )}
                </>
              ) : !selectedResult?.error && <div className="empty-state">等待识别结果。</div>}
            </section>
          </>
        )}
      </section>
    </div>
  );
}
