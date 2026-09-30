"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { ArrowResetRegular, ChevronLeftRegular, ChevronRightRegular } from "@fluentui/react-icons";
import { Spinner } from "@fluentui/react-spinner";
import { api } from "../lib/api";
import type { MemoryPreset, MoveRecord, RecognitionState, TacticAnalysis } from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

const TACTIC_HELP = [
  ["逃", "走前被抓，走后脱离直接攻击"], ["保", "建立可合法回吃的保护关系"],
  ["弃", "主动送子，或放弃刚受攻击的棋子"], ["挡", "其他棋子进入车路，截断原本可到达格"],
  ["封锁", "原有封锁子向车逼近，继续压缩车路"], ["困", "所有合法走法都会立刻失子"],
  ["牵", "仅车、马、炮：车线上的两枚敌子彼此受约束"],
];

interface Snapshot { state: RecognitionState; legalMoves: string[]; move?: MoveRecord; }
const EMPTY_MEMORY: MemoryPreset = { redChoicePath: [], blackChoicePath: [], blackComposite: null, redWing: null, blackWing: null };

export function TacticsLab() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [index, setIndex] = useState(0);
  const [analysis, setAnalysis] = useState<TacticAnalysis | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [fenDraft, setFenDraft] = useState("");
  const current = snapshots[index];
  const moves = snapshots.slice(1).map((snapshot) => snapshot.move).filter(Boolean) as MoveRecord[];
  const signature = current ? `${snapshots[0].state.fen}|${moves.map((move) => move.ucci).join(",")}` : "";

  const reset = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const response = await api.initial();
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setFenDraft(response.state.fen);
      setIndex(0); setAnalysis(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "无法启动战术棋盘"); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void reset(); }, 0);
    return () => window.clearTimeout(timer);
  }, [reset]);

  useEffect(() => {
    if (!current) return;
    let active = true;
    api.analyzeTactics(snapshots[0].state.fen, moves.map((move) => move.ucci))
      .then((result) => { if (active) setAnalysis(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "无法识别战术手法"); });
    return () => { active = false; };
  // The signature represents the immutable current line and prevents stale requests.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  async function play(move: string) {
    if (!current) return;
    setBusy(true); setError("");
    try {
      const response = await api.advance(current.state, move);
      const next = [...snapshots.slice(0, index + 1), { state: response.state, legalMoves: response.legalMoves, move: response.move }];
      setSnapshots(next); setIndex(next.length - 1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "走子失败"); }
    finally { setBusy(false); }
  }

  async function loadFen(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fen = fenDraft.trim();
    if (!fen) { setError("请输入完整 FEN 后再载入。"); return; }
    setBusy(true); setError("");
    try {
      const response = await api.inspect(fen, EMPTY_MEMORY);
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setIndex(0); setAnalysis(null); setFenDraft(response.state.fen);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "FEN 无法载入，请检查格式。"); }
    finally { setBusy(false); }
  }

  const currentAnnotation = index > 0 ? analysis?.annotations[index - 1] : null;
  return <div className="tactics-board-lab">
    <section className="panel tactics-board-panel">
      <div className="board-toolbar">
        <div><span className="turn-label">轮到</span><strong className={current?.state.fen.split(" ")[1] === "w" ? "red-text" : ""}>{current?.state.fen.split(" ")[1] === "w" ? "红方" : "黑方"}</strong></div>
        <div className="navigation-controls">
          <Button aria-label="上一步" icon={<ChevronLeftRegular />} disabled={index === 0 || busy} onClick={() => setIndex(index - 1)} />
          <span>{index} / {Math.max(snapshots.length - 1, 0)}</span>
          <Button aria-label="下一步" icon={<ChevronRightRegular />} disabled={index === snapshots.length - 1 || busy} onClick={() => setIndex(index + 1)} />
          <Button icon={<ArrowResetRegular />} disabled={busy} onClick={reset}>重设棋盘</Button>
        </div>
      </div>
      {!current ? <div className="loading-state"><Spinner label="正在准备战术棋盘" /></div> : <>
        <XiangqiBoard fen={current.state.fen} legalMoves={current.legalMoves} lastMove={current.move} disabled={busy} onMove={play} />
        <form className="fen-strip fen-editor" onSubmit={loadFen}>
          <label htmlFor="tactics-fen">FEN</label>
          <div className="fen-editor-field">
            <textarea id="tactics-fen" value={fenDraft} onChange={(event) => setFenDraft(event.target.value)} rows={2} disabled={busy} spellCheck={false} aria-describedby="tactics-fen-help" />
            <div className="fen-editor-actions"><small id="tactics-fen-help">修改后点击载入，棋盘会立即切换到该局面。</small><Button type="submit" appearance="primary" disabled={busy}>载入</Button></div>
          </div>
        </form>
      </>}
    </section>
    <aside className="tactics-side-panel">
      <section className="panel tactic-current-result">
        <div className="panel-heading"><div><span className="eyebrow">JUST PLAYED</span><h2>这一步是什么手法？</h2></div><Badge appearance="outline">{index ? `ply ${index}` : "等待走子"}</Badge></div>
        {!currentAnnotation && index === 0 && <div className="empty-state">在左侧棋盘走一步，这里会立刻显示判定。</div>}
        {currentAnnotation && <>
          <div className="played-move"><strong>{moves[index - 1]?.chineseNotation ?? currentAnnotation.ucci}</strong><code>{currentAnnotation.ucci}</code></div>
          <div className="tactic-tags prominent">{currentAnnotation.occurrences.length ? currentAnnotation.occurrences.map((item, itemIndex) => <span key={`${item.id}-${itemIndex}`} title={`${item.detail} (${item.squares.join(", ")})`}>{item.labelZh}</span>) : <em>这一步暂未命中已定义的战术手法。</em>}</div>
          {currentAnnotation.occurrences.map((item, itemIndex) => <p className="tactic-detail" key={`${item.id}-detail-${itemIndex}`}><strong>{item.labelZh}</strong>{item.detail}<small>涉及格：{item.squares.join(" · ")}</small></p>)}
        </>}
      </section>
      <section className="panel tactic-guide">
        <div className="panel-heading"><div><span className="eyebrow">TACTICAL DEFINITIONS</span><h2>当前识别定义</h2></div><Badge appearance="outline">草案规则</Badge></div>
        <div className="tactic-guide-grid">{TACTIC_HELP.map(([label, text]) => <div key={label}><strong>{label}</strong><span>{text}</span></div>)}</div>
      </section>
      {error && <div className="error-banner" role="alert">{error}</div>}
    </aside>
  </div>;
}
