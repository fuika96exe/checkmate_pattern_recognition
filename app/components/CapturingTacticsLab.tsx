"use client";

import { memo, useEffect, useMemo, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { Spinner } from "@fluentui/react-spinner";
import type { MoveRecord, Side, TacticalCategoryId } from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

const PAGE_SIZE = 24;

interface PlyOccurrence { id: TacticalCategoryId; label_zh: string; squares: string[]; detail: string; }
interface PlyAnnotation { ply: number; ucci: string; solver: boolean; occurrences: PlyOccurrence[]; }
type GainKind = "big" | "small" | "none";
interface MaterialGain { kind: GainKind; gain: number; mainGain: number; captures: { move: string; piece: string; value: number; by: "solver" | "opponent" }[]; }
const PIECE_ZH: Record<string, string> = { R: "车", C: "炮", N: "马", B: "相", A: "仕", P: "兵" };
interface CapturingPuzzle {
  id: string; rating: number | null; initialFen: string; blunderMove: string; solverSide: Side | null;
  pv: string[]; url: string; status: "matched" | "unmatched" | "invalid"; error?: string;
  material: MaterialGain | null; tactics: TacticalCategoryId[]; fens: string[]; plies: PlyAnnotation[];
}
interface CapturingDataset {
  rulesVersion: string; source: string; seed: number; eligibleRows: number; generatedAt: string;
  puzzleCount: number; gainLabels: Record<GainKind, string>; labels: Record<TacticalCategoryId, string>; summary: Record<string, number>; puzzles: CapturingPuzzle[];
}

function parseFen(fen: string): Record<string, string> {
  const board: Record<string, string> = {};
  (fen.trim().split(/\s+/)[0] ?? "").split("/").forEach((rank, row) => {
    let file = 0;
    for (const character of rank) {
      if (/\d/.test(character)) file += Number(character);
      else { board[`${String.fromCharCode(97 + file)}${9 - row}`] = character; file += 1; }
    }
  });
  return board;
}

const MiniBoard = memo(function MiniBoard({ fen }: { fen: string }) {
  const board = useMemo(() => parseFen(fen), [fen]);
  return (
    <div className="mini-board" aria-label="棋题局面缩图">
      {Array.from({ length: 90 }, (_, index) => {
        const square = `${String.fromCharCode(97 + (index % 9))}${9 - Math.floor(index / 9)}`;
        const piece = board[square];
        return <span className="mini-square" key={square}>{piece && <i className={piece === piece.toUpperCase() ? "red" : "black"} />}</span>;
      })}
    </div>
  );
});

export function CapturingTacticsLab() {
  const [dataset, setDataset] = useState<CapturingDataset | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<CapturingPuzzle | null>(null);
  const [frame, setFrame] = useState(1);
  const [tacticFilter, setTacticFilter] = useState<"" | TacticalCategoryId | "none">("");
  const [gainFilter, setGainFilter] = useState<"" | GainKind>("");
  const [movesMin, setMovesMin] = useState("");
  const [movesMax, setMovesMax] = useState("");
  const [idQuery, setIdQuery] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let active = true;
    fetch("/data/capturing-tactics.json")
      .then((response) => { if (!response.ok) throw new Error(`无法载入吃子战术资料：HTTP ${response.status}`); return response.json() as Promise<CapturingDataset>; })
      .then((data) => { if (active) setDataset(data); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "无法载入吃子战术资料"); });
    return () => { active = false; };
  }, []);

  const visible = useMemo(() => (dataset?.puzzles ?? []).filter((puzzle) => {
    if (idQuery && !puzzle.id.toLowerCase().includes(idQuery.trim().toLowerCase())) return false;
    if (movesMin !== "" && puzzle.pv.length < Number(movesMin)) return false;
    if (movesMax !== "" && puzzle.pv.length > Number(movesMax)) return false;
    if (gainFilter && puzzle.material?.kind !== gainFilter) return false;
    if (tacticFilter === "none") return puzzle.tactics.length === 0;
    return !tacticFilter || puzzle.tactics.includes(tacticFilter);
  }), [dataset, tacticFilter, gainFilter, movesMin, movesMax, idQuery]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!dataset) return <div className="loading-state"><Spinner label="正在载入吃子战术资料" /></div>;

  const pages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const pageRows = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const labels = dataset.labels;
  const last = selected ? selected.fens.length - 1 : 0;
  const annotation = selected && frame > 0 ? selected.plies[frame - 1] : undefined;
  const open = (puzzle: CapturingPuzzle) => { setSelected(puzzle); setFrame(1); };
  const lastMove = annotation ? ({ ply: annotation.ply, side: "red", ucci: annotation.ucci, chineseNotation: "", fromSquare: annotation.ucci.slice(0, 2), toSquare: annotation.ucci.slice(2, 4) } satisfies MoveRecord) : undefined;

  return (
    <div className="puzzle-browser">
      <section className="panel puzzle-catalog">
        <div className="panel-heading puzzle-heading">
          <div><span className="eyebrow">CAPTURING TACTICS SAMPLE</span><h2>吃子棋题战术标注</h2></div>
          <Badge appearance="outline">{dataset.rulesVersion}</Badge>
        </div>
        <div className="puzzle-metrics">
          <span>抽样<strong>{dataset.puzzleCount}</strong></span>
          <span>已标注<strong>{dataset.puzzles.filter((p) => p.tactics.length).length}</strong></span>
          <span>未识别<strong>{dataset.summary.unmatched ?? 0}</strong></span>
          <span>无效<strong>{dataset.summary.invalid ?? 0}</strong></span>
        </div>
        <div className="puzzle-filter-grid">
          <label className="wide"><span>题目 ID</span><input value={idQuery} onChange={(event) => { setIdQuery(event.target.value); setPage(1); }} placeholder="例如 RZ8Qlq" /></label>
          <label className="wide"><span>战术</span>
            <select value={tacticFilter} onChange={(event) => { setTacticFilter(event.target.value as typeof tacticFilter); setPage(1); }}>
              <option value="">全部（{dataset.puzzleCount}）</option>
              {(Object.keys(labels) as TacticalCategoryId[]).map((id) => <option key={id} value={id}>{labels[id]}（{dataset.summary[id] ?? 0}）</option>)}
              <option value="none">未识别</option>
            </select>
          </label>
          <label><span>最少步数</span><input type="number" min={1} value={movesMin} onChange={(event) => { setMovesMin(event.target.value); setPage(1); }} placeholder="1" /></label>
          <label><span>最多步数</span><input type="number" min={1} value={movesMax} onChange={(event) => { setMovesMax(event.target.value); setPage(1); }} placeholder="∞" /></label>
          <label className="wide"><span>得子</span>
            <select value={gainFilter} onChange={(event) => { setGainFilter(event.target.value as typeof gainFilter); setPage(1); }}>
              <option value="">全部</option>
              {(["big", "small", "none"] as GainKind[]).map((kind) => <option key={kind} value={kind}>{dataset.gainLabels[kind]}（{dataset.summary[`gain_${kind}`] ?? 0}）</option>)}
            </select>
          </label>
        </div>
        <p className="support-copy" style={{ padding: "0 14px" }}>数据来源 {dataset.source}（CAPTURING 已发布 {dataset.eligibleRows} 题中随机抽样，seed {dataset.seed}）。标注取解题方每一手的战术分类结果。</p>
        <div className="puzzle-list" aria-label="吃子棋题列表">
          {pageRows.map((puzzle) => (
            <button type="button" className={`puzzle-row${selected?.id === puzzle.id ? " selected" : ""}`} key={puzzle.id} onClick={() => open(puzzle)}>
              <MiniBoard fen={puzzle.fens[1] ?? puzzle.initialFen} />
              <span className="puzzle-row-main">
                <span className="puzzle-patterns">
                  {puzzle.tactics.length ? puzzle.tactics.map((id) => <i key={id}>{labels[id]}</i>) : <em>{puzzle.status === "invalid" ? "无法识别" : "未识别到战术"}</em>}
                </span>
                <span className="puzzle-row-meta">
                  <strong>{puzzle.solverSide === "red" ? "红方解题" : "黑方解题"}</strong>
                  <small>{puzzle.id} · {puzzle.rating ?? "—"} · {puzzle.pv.length} 着</small>
                  <span className={`puzzle-row-status ${puzzle.status}`}>{puzzle.material ? dataset.gainLabels[puzzle.material.kind] : "无效"}</span>
                </span>
              </span>
            </button>
          ))}
          {pageRows.length === 0 && <div className="empty-state">没有符合筛选条件的棋题。</div>}
        </div>
        <div className="puzzle-pagination">
          <Button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
          <span>{page} / {pages} · {visible.length} 题</span>
          <Button disabled={page >= pages} onClick={() => setPage(page + 1)}>下一页</Button>
        </div>
      </section>

      <section className="puzzle-viewer">
        {!selected ? (
          <div className="panel puzzle-placeholder"><span className="eyebrow">HUMAN REVIEW</span><h2>选择一道吃子棋题</h2><p>左侧每题都标出解题线用到的战术；点开后可逐手回放，并查看每一手的识别依据。</p></div>
        ) : (
          <>
            <section className="panel puzzle-board-panel">
              <div className="panel-heading">
                <div><span className="eyebrow">SOLUTION REPLAY</span><h2>{selected.solverSide === "red" ? "红方" : "黑方"}解题 · {selected.pv.length} 着</h2></div>
                <Badge appearance="outline"><a href={selected.url} target="_blank" rel="noreferrer">{selected.id}</a></Badge>
              </div>
              <XiangqiBoard fen={selected.fens[frame]} legalMoves={[]} lastMove={lastMove} disabled onMove={() => undefined} />
              <div className="puzzle-replay-controls">
                <Button disabled={frame <= 0} onClick={() => setFrame(frame - 1)}>上一步</Button>
                <span>{frame} / {last}</span>
                <Button disabled={frame >= last} onClick={() => setFrame(frame + 1)}>下一步</Button>
                <Button onClick={() => setFrame(1)}>回到失误后局面</Button>
              </div>
              <div className="fen-strip"><span>FEN</span><code>{selected.fens[frame]}</code></div>
              <div className="puzzle-moves">
                {selected.plies.map((ply) => (
                  <button type="button" className={ply.ply === frame ? "active" : ""} key={ply.ply} onClick={() => setFrame(ply.ply)}>
                    <span>{ply.ply}{ply.ply === 1 ? "失" : ""}</span><code>{ply.ucci}</code>
                  </button>
                ))}
              </div>
            </section>
            <section className="panel puzzle-recognition-panel">
              <div className="panel-heading">
                <div><span className="eyebrow">TACTIC LABELS</span><h2>解题线战术</h2></div>
                <Badge color={selected.tactics.length ? "success" : "danger"}>{selected.tactics.length ? `命中 ${selected.tactics.length} 类` : "未识别"}</Badge>
              </div>
              {selected.error && <div className="error-banner">{selected.error}</div>}
              {selected.material && (
                <div className="shape-row"><span>得子判断</span>
                  <div>
                    <code>{dataset.gainLabels[selected.material.kind]}</code>
                    <code>整体 {selected.material.gain >= 0 ? "+" : ""}{selected.material.gain}</code>
                    <code>大子 {selected.material.mainGain >= 0 ? "+" : ""}{selected.material.mainGain}</code>
                    {selected.material.captures.map((capture, index) => (
                      <code key={index}>{capture.by === "solver" ? "得" : "失"} {PIECE_ZH[capture.piece.toUpperCase()] ?? capture.piece}（{capture.value}）· {capture.move}</code>
                    ))}
                  </div>
                </div>
              )}
              <div className="recognized-pattern-list">
                {selected.tactics.length ? selected.tactics.map((id) => <strong key={id}>{labels[id]}</strong>) : <div className="empty-state">解题方没有任何一手命中八类战术规则。</div>}
              </div>
              <div className="shape-row"><span>{frame === 0 ? "起始局面" : frame === 1 ? "对方失误（第 1 手）" : `第 ${frame} 手${annotation?.solver ? "（解题方）" : "（应着）"}`}</span>
                <div>
                  {annotation?.occurrences.length ? annotation.occurrences.map((item, index) => (
                    <code key={`${item.id}-${index}`} title={item.detail}>{labels[item.id]} · {item.squares.join(" ")}</code>
                  )) : <em>这一手没有命中战术规则</em>}
                </div>
              </div>
              {annotation?.occurrences.map((item, index) => <p className="support-copy" key={index}>{item.detail}</p>)}
            </section>
          </>
        )}
      </section>
    </div>
  );
}
