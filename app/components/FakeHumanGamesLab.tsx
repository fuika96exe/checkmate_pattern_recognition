"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { api } from "../lib/api";
import type { MoveRecord, RecognitionState } from "../lib/types";
import { ChoicePath } from "./ChoicePath";
import { XiangqiBoard } from "./XiangqiBoard";

interface Game { id: string; botSide: "red" | "black"; moves: string[] }
interface Snapshot { state: RecognitionState; legalMoves: string[]; move?: MoveRecord }
type Result = { status: "done"; name: string; certainty: string } | { status: "error"; message: string };
interface OpeningIndex { rulesVersion: string; generatedAt: string; results: Record<string, Result> }
type IndexStatus = { kind: "loading" } | { kind: "stored"; rulesVersion: string; generatedAt: string } | { kind: "missing" } | { kind: "live" };
const emptyMemory = { redChoicePath: [], blackChoicePath: [], blackComposite: null, redWing: null, blackWing: null };
const REPLAY_CHUNK_SIZE = 10;

export function FakeHumanGamesLab() {
  const [games, setGames] = useState<Game[]>([]);
  const [results, setResults] = useState<Record<string, Result>>({});
  const [selected, setSelected] = useState<Game | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [index, setIndex] = useState(0);
  const [query, setQuery] = useState("");
  const [side, setSide] = useState("all");
  const [status, setStatus] = useState("all");
  const [opening, setOpening] = useState("all");
  const [busy, setBusy] = useState(false);
  const [loadingLine, setLoadingLine] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [fenDraft, setFenDraft] = useState("");
  const [language, setLanguage] = useState<"zh" | "en">("zh");
  const [standalone, setStandalone] = useState(false);
  const [indexStatus, setIndexStatus] = useState<IndexStatus>({ kind: "loading" });
  const generation = useRef(0);
  const batchGeneration = useRef(0);
  const current = snapshots[index];

  useEffect(() => {
    let active = true;
    const gameRequests = generation;
    const batchRequests = batchGeneration;
    fetch("/data/fake-human-games.json").then((response) => {
      if (!response.ok) throw new Error(`棋譜資料載入失敗 (${response.status})`);
      return response.json() as Promise<{ games: Game[] }>;
    }).then((data) => { if (active) setGames(data.games); }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "棋譜資料載入失敗");
    });
    // Opening results are pre-computed by backend/scripts/generate_fake_human_openings.py,
    // so opening the tab never replays all games.
    fetch("/data/fake-human-openings.json").then((response) => {
      if (!response.ok) throw new Error(`開局分析索引載入失敗 (${response.status})`);
      return response.json() as Promise<OpeningIndex>;
    }).then((data) => {
      if (!active) return;
      // Results already produced live in this session (a loaded game or a re-run) take precedence.
      setResults((old) => ({ ...data.results, ...old }));
      setIndexStatus((old) => old.kind === "live" ? old : { kind: "stored", rulesVersion: data.rulesVersion, generatedAt: data.generatedAt });
    }).catch(() => { if (active) setIndexStatus((old) => old.kind === "loading" ? { kind: "missing" } : old); });
    return () => { active = false; gameRequests.current++; batchRequests.current++; };
  }, []);

  const loadGame = useCallback(async (game: Game) => {
    const requestId = ++generation.current;
    setSelected(game); setBusy(true); setLoadingLine(true); setError(""); setStandalone(false); setSnapshots([]); setIndex(0);
    let completed = 0;
    try {
      const initial = await api.initial();
      if (generation.current !== requestId) return;
      setSnapshots([{ state: initial.state, legalMoves: initial.legalMoves }]);
      setFenDraft(initial.state.fen);
      setBusy(false);
      let state = initial.state;
      while (completed < game.moves.length) {
        const replay = await api.replayOpeningSample(game.moves.slice(completed, completed + REPLAY_CHUNK_SIZE), state);
        if (generation.current !== requestId) return;
        if (!replay.length) throw new Error("棋譜回放未返回走法");
        state = replay[replay.length - 1].state;
        completed += replay.length;
        setSnapshots((old) => generation.current === requestId ? [...old, ...replay] : old);
        if (completed === Math.min(20, game.moves.length)) {
          const classification = state.classification;
          setResults((old) => ({ ...old, [game.id]: { status: "done", name: classification.displayName, certainty: classification.certainty } }));
        }
      }
    } catch (reason) {
      if (generation.current !== requestId) return;
      const message = reason instanceof Error ? reason.message : "棋譜分析失敗";
      setError(`${game.id}：${message}`);
      if (completed < Math.min(20, game.moves.length)) {
        setResults((old) => ({ ...old, [game.id]: { status: "error", message } }));
      }
    } finally { if (generation.current === requestId) { setBusy(false); setLoadingLine(false); } }
  }, []);

  async function runAll() {
    const runId = ++batchGeneration.current;
    setRunning(true); setProgress(0); setIndexStatus({ kind: "live" });
    for (let i = 0; i < games.length; i++) {
      const game = games[i];
      try {
        const line = await api.replayOpeningSample(game.moves.slice(0, 20));
        const classification = line.at(-1)?.state.classification;
        if (!classification) throw new Error("棋譜沒有走法");
        if (batchGeneration.current !== runId) return;
        setResults((old) => ({ ...old, [game.id]: { status: "done", name: classification.displayName, certainty: classification.certainty } }));
      } catch (reason) {
        if (batchGeneration.current !== runId) return;
        setResults((old) => ({ ...old, [game.id]: { status: "error", message: reason instanceof Error ? reason.message : "分析失敗" } }));
      }
      setProgress(i + 1);
    }
    if (batchGeneration.current === runId) setRunning(false);
  }

  function navigate(next: number) {
    setIndex(next); setFenDraft(snapshots[next].state.fen);
  }

  async function play(move: string) {
    if (!current) return;
    generation.current++; setLoadingLine(false);
    setBusy(true); setError("");
    try {
      const response = await api.advanceOpeningSample(current.state, move);
      const line = [...snapshots.slice(0, index + 1), response];
      setSnapshots(line); setIndex(line.length - 1); setFenDraft(response.state.fen);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "走子失敗"); }
    finally { setBusy(false); }
  }

  async function loadFen(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!current) return;
    generation.current++; setLoadingLine(false);
    setBusy(true); setError("");
    try {
      const position = await api.inspect(fenDraft.trim(), emptyMemory);
      if (current.state.ply >= 20) {
        position.state.classification = current.state.classification;
        position.state.openingMemory = { ...current.state.openingMemory, moves: [], baseMatchupId: current.state.openingMemory.baseMatchupId };
        position.state.ply = current.state.ply;
        position.state.sideMoves = current.state.sideMoves;
      }
      setSnapshots([position]); setIndex(0); setFenDraft(position.state.fen); setStandalone(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "FEN 載入失敗"); }
    finally { setBusy(false); }
  }

  const names = [...new Set(Object.values(results).filter((r): r is Extract<Result, { status: "done" }> => r.status === "done").map((r) => r.name))].sort();
  const visible = games.filter((game) => {
    const result = results[game.id];
    const state = !result ? "unanalysed" : result.status === "error" ? "error" : result.certainty;
    return game.id.toLowerCase().includes(query.toLowerCase()) && (side === "all" || side === game.botSide)
      && (status === "all" || status === state) && (opening === "all" || (result?.status === "done" && result.name === opening));
  });
  const history = snapshots.slice(1).map((snapshot) => snapshot.move).filter((move): move is MoveRecord => Boolean(move));
  const classification = current?.state.classification;

  return <div className="fake-human-lab">
    <section className="panel fake-human-intro">
      <div><span className="eyebrow">FAKE HUMAN OPENING REVIEW</span><h2>假人對局／開局測試</h2>
        <p>198 局經核實的假人對局。開局只分析前十回合（20 個半手），後續走法不改變判斷；此樣本沒有開局標準答案。</p>
        <p className="fake-human-index-status">{indexStatus.kind === "stored" ? `開局判斷已預先分析並儲存（規則 ${indexStatus.rulesVersion}，生成於 ${new Date(indexStatus.generatedAt).toLocaleString()}）。`
          : indexStatus.kind === "missing" ? "找不到預先分析結果；可按「重新分析全部」即時分析。"
          : indexStatus.kind === "live" ? "目前顯示本次即時重新分析的結果。" : "載入預先分析結果…"}</p></div>
      <div className="fake-human-actions"><Button disabled={running || !games.length} onClick={() => void runAll()}>重新分析全部</Button>
        {running && <span role="status">分析中 {progress} / {games.length}</span>}</div>
    </section>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <section className="panel fake-human-list">
      <div className="fake-human-filters">
        <label>對局 ID <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜尋對局" /></label>
        <label>假人顏色 <select value={side} onChange={(e) => setSide(e.target.value)}><option value="all">全部</option><option value="red">紅方</option><option value="black">黑方</option></select></label>
        <label>狀態 <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">全部</option><option value="unanalysed">未分析</option><option value="pending">pending</option><option value="confirmed">confirmed</option><option value="provisional">provisional</option><option value="error">失敗</option></select></label>
        <label>開局 <select value={opening} onChange={(e) => setOpening(e.target.value)}><option value="all">全部</option>{names.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      </div>
      <p>顯示 {visible.length} / {games.length} 局；已處理 {Object.keys(results).length} 局。點選棋局查看完整棋譜。</p>
      <div className="fake-human-table-wrap"><table><thead><tr><th>對局 ID</th><th>假人</th><th>半手</th><th>第十回合開局判斷</th><th>狀態</th></tr></thead><tbody>
        {visible.map((game) => { const result = results[game.id]; return <tr key={game.id} className={selected?.id === game.id ? "selected-game" : ""}>
          <td><button type="button" disabled={busy} onClick={() => void loadGame(game)}>{game.id}</button></td><td>{game.botSide === "red" ? "紅" : "黑"}</td><td>{game.moves.length}</td>
          <td>{result?.status === "done" ? result.name : result?.status === "error" ? result.message : "—"}</td><td>{result?.status === "done" ? result.certainty : result?.status === "error" ? "失敗" : "未分析"}</td>
        </tr>; })}
      </tbody></table></div>
    </section>
    {selected && <div className="fake-human-selected"><strong>對局 {selected.id}</strong> · 假人{selected.botSide === "red" ? "紅方" : "黑方"} {busy && "· 載入中…"}{loadingLine && !busy && ` · 棋譜載入 ${snapshots.length - 1} / ${selected.moves.length} 半手`}{standalone && " · 已載入獨立 FEN；重設可返回原棋譜"}</div>}
    {current && classification && <div className="workbench-grid">
      <section className="board-column">
        <div className="board-toolbar"><div><span className="turn-label">輪到</span><strong className={current.state.fen.split(" ")[1] === "w" ? "red-text" : ""}>{current.state.fen.split(" ")[1] === "w" ? "紅方" : "黑方"}</strong></div>
          <div className="navigation-controls"><Button aria-label="上一步" disabled={busy || index === 0} onClick={() => navigate(index - 1)}>‹</Button><span>{index} / {snapshots.length - 1}</span><Button aria-label="下一步" disabled={busy || index === snapshots.length - 1} onClick={() => navigate(index + 1)}>›</Button><Button disabled={busy} onClick={() => selected && void loadGame(selected)}>重設</Button></div></div>
        <XiangqiBoard fen={current.state.fen} legalMoves={current.legalMoves} lastMove={current.move} disabled={busy} onMove={(move) => void play(move)} />
        <form className="fen-strip fen-editor" onSubmit={(e) => void loadFen(e)}><label htmlFor="sample-fen">FEN</label><div className="fen-editor-field"><textarea id="sample-fen" value={fenDraft} onChange={(e) => setFenDraft(e.target.value)} rows={2} disabled={busy} spellCheck={false} /><div className="fen-editor-actions"><small>載入 FEN 會建立獨立局面；沒有原棋譜歷史。</small><Button type="submit" appearance="primary" disabled={busy}>載入局面</Button></div></div></form>
      </section>
      <aside className="analysis-column">
        <section className="panel classification-card"><div className="panel-heading"><div><span className="eyebrow">LIVE CLASSIFICATION</span><h2>目前判斷 <Button size="small" onClick={() => setLanguage((old) => old === "zh" ? "en" : "zh")}>{language === "zh" ? "EN" : "中"}</Button></h2></div><Badge color={classification.certainty === "confirmed" ? "success" : "warning"}>{classification.certainty}</Badge></div>
          <div className="opening-name">{language === "en" ? classification.displayNameEn || classification.displayName : classification.displayName}</div><div className="matchup-id">{classification.baseMatchupId ?? "等待雙方主選擇形成"}</div>
          <p className="sample-cutoff">{current.state.ply >= 20 ? "開局判斷已固定於第 20 個半手" : `開局判斷：第 ${current.state.ply} / 20 個半手`}{standalone && " · 獨立 FEN"}</p>
          <div className="choice-columns"><ChoicePath side="red" state={current.state} /><ChoicePath side="black" state={current.state} /></div>
        </section>
        <section className="panel shape-card"><div className="panel-heading compact"><div><span className="eyebrow">FEN OBSERVATION</span><h2>目前棋形</h2></div><Badge appearance="outline">ply {current.state.ply}</Badge></div>{(["red", "black"] as const).map((s) => <div className="shape-row" key={s}><span>{s === "red" ? "紅" : "黑"}</span><div>{current.state.currentShapes[s].length ? current.state.currentShapes[s].map((shape) => <code key={shape}>{shape}</code>) : <em>無已知棋形</em>}</div></div>)}</section>
        <section className="panel history-card"><div className="panel-heading compact"><div><span className="eyebrow">MOVE HISTORY</span><h2>中文着法</h2></div><Badge appearance="outline">{history.length} ply</Badge></div><div className="move-list">
          {history.length === 0 && <div className="empty-state">目前沒有走法。</div>}
          {history.map((move, i) => <button type="button" className={`sample-move${index === i + 1 ? " active" : ""}`} key={i} onClick={() => navigate(i + 1)}><span>{Math.ceil(move.ply / 2)}. {move.side === "red" ? "紅" : "黑"}</span><strong>{move.chineseNotation}</strong><small>{move.ucci}</small></button>)}
        </div></section>
      </aside>
    </div>}
  </div>;
}
