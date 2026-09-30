"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { ArrowResetRegular, ChevronLeftRegular, ChevronRightRegular } from "@fluentui/react-icons";
import { Spinner } from "@fluentui/react-spinner";
import { api } from "../lib/api";
import type { MemoryPreset, MoveRecord, RecognitionState, TacticalCategoryAnalysis } from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

const RULES = [
  ["交换", "吃子后对方能立刻合法回吃，且双方子力价值相近。"],
  ["捉双", "同一枚刚走的棋子新同时安全攻击至少两个敌方非将目标。"],
  ["串打", "前子未受保护；它离线后，后方未受保护目标会受车／炮攻击。"],
  ["闪击", "移动一子后，另一枚己子新获得合法攻击线。"],
  ["消除保护", "直接吃掉指定守子，消除它对目标的合法回吃保护；直接吃目标属于交换。"],
  ["围困", "目标每个合法去处都会被安全吃掉，且已有己子直接捉住它。"],
  ["牵制", "仅车、马、炮参与：同线离开即失子，或吃子后会被车／炮合法回吃。"],
  ["炮兵突破", "兵的推进或吃子改变炮线／炮架，使己炮新取得合法攻击。"],
] as const;

interface Snapshot { state: RecognitionState; legalMoves: string[]; move?: MoveRecord; }
const EMPTY_MEMORY: MemoryPreset = { redChoicePath: [], blackChoicePath: [], blackComposite: null, redWing: null, blackWing: null };

export function TacticalCategoriesLab() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [index, setIndex] = useState(0);
  const [analysis, setAnalysis] = useState<TacticalCategoryAnalysis | null>(null);
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
      setFenDraft(response.state.fen); setIndex(0); setAnalysis(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "无法启动战术分类棋盘"); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void reset(); }, 0);
    return () => window.clearTimeout(timer);
  }, [reset]);

  useEffect(() => {
    if (!current) return;
    let active = true;
    api.analyzeTacticalCategories(snapshots[0].state.fen, moves.map((move) => move.ucci))
      .then((result) => { if (active) setAnalysis(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "无法识别战术分类"); });
    return () => { active = false; };
    // signature represents the complete currently selected move line.
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
    if (!fenDraft.trim()) { setError("请输入完整 FEN 后再载入。"); return; }
    setBusy(true); setError("");
    try {
      const response = await api.inspect(fenDraft.trim(), EMPTY_MEMORY);
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setFenDraft(response.state.fen); setIndex(0); setAnalysis(null);
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
      {!current ? <div className="loading-state"><Spinner label="正在准备战术分类棋盘" /></div> : <>
        <XiangqiBoard fen={current.state.fen} legalMoves={current.legalMoves} lastMove={current.move} disabled={busy} onMove={play} />
        <form className="fen-strip fen-editor" onSubmit={loadFen}>
          <label htmlFor="categories-fen">FEN</label><div className="fen-editor-field">
            <textarea id="categories-fen" value={fenDraft} onChange={(event) => setFenDraft(event.target.value)} rows={2} disabled={busy} spellCheck={false} />
            <div className="fen-editor-actions"><small>贴入 FEN 后载入，可从任意局面开始测试。</small><Button type="submit" appearance="primary" disabled={busy}>载入</Button></div>
          </div>
        </form>
      </>}
    </section>
    <aside className="tactics-side-panel">
      <section className="panel tactic-current-result">
        <div className="panel-heading"><div><span className="eyebrow">NINE TACTICAL CATEGORIES</span><h2>本步分类结果</h2></div><Badge appearance="outline">{index ? `ply ${index}` : "等待走子"}</Badge></div>
        {!currentAnnotation && index === 0 && <div className="empty-state">在左侧棋盘走一步，系统将按九类规则即时复算。</div>}
        {currentAnnotation && <>
          <div className="played-move"><strong>{moves[index - 1]?.chineseNotation ?? currentAnnotation.ucci}</strong><code>{currentAnnotation.ucci}</code></div>
          <div className="tactic-tags prominent">{currentAnnotation.occurrences.length ? currentAnnotation.occurrences.map((item, itemIndex) => <span key={`${item.id}-${itemIndex}`}>{item.labelZh}</span>) : <em>本步没有命中当前版本的九类严格规则。</em>}</div>
          {currentAnnotation.occurrences.map((item, itemIndex) => <p className="tactic-detail" key={`${item.id}-${itemIndex}`}><strong>{item.labelZh}</strong>{item.detail}<small>证据格：{item.squares.join(" · ")}</small></p>)}
        </>}
      </section>
      <section className="panel tactic-guide">
        <div className="panel-heading"><div><span className="eyebrow">AUDITABLE RULES</span><h2>九类当前定义</h2></div><Badge appearance="outline">草案 0.1</Badge></div>
        <div className="tactic-guide-grid">{RULES.map(([label, text]) => <div key={label}><strong>{label}</strong><span>{text}</span></div>)}</div>
      </section>
      {error && <div className="error-banner" role="alert">{error}</div>}
    </aside>
  </div>;
}
