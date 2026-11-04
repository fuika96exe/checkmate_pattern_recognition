"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Spinner } from "@fluentui/react-spinner";
import type { MoveRecord, Side, MidgameTacticId, MidgameGainKind, MidgameOccurrence, MidgamePieceRef } from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

type GainKind = MidgameGainKind;
interface PlyAnnotation { ply: number; ucci: string; chinese?: string; solver: boolean; occurrences: MidgameOccurrence[]; }
interface MaterialGain { kind: GainKind; start: number; end: number; delta: number; }
type SupportingOccurrence = MidgameOccurrence & { suppressedBy: string };
interface ReviewReason { label: string; ply: number; reason: string; fen: string; evidence: unknown; }
interface CapturingPuzzle {
  id: string; rating: number | null; initialFen: string; blunderMove: string; solverSide: Side | null;
  pv: string[]; url: string; sourceRow?: number | null; status: "matched" | "unmatched" | "invalid"; error?: string;
  errorPly?: number; errorFen?: string;
  reviewReasons: ReviewReason[]; supportingEvidence: SupportingOccurrence[];
  material: MaterialGain | null; tactics: MidgameTacticId[]; fens: string[]; plies: PlyAnnotation[];
}
interface CapturingDataset {
  schemaVersion: string; rulesVersion: string; source: string; seed: number; eligibleRows: number; generatedAt: string;
  puzzleCount: number; gainLabels: Record<GainKind, string>; labels: Record<MidgameTacticId, string>; summary: Record<string, number>; puzzles: CapturingPuzzle[];
}

const ORDER: MidgameTacticId[] = ["fork", "discovered_attack", "skewer", "pin", "check_fork", "trap", "remove_defender", "overload", "exchange", "clearance"];
// Display wording follows the 中局标签审查台, so a puzzle reads the same in both places.
const TACTIC_ZH: Record<string, string> = {
  fork: "捉双", discovered_attack: "闪击", skewer: "串打", pin: "牵制", check_fork: "抽将", trap: "围困",
  remove_defender: "消除保护", overload: "过载", exchange: "交换", clearance: "消除阻隔", threat: "威胁",
};
const GLYPH: Record<string, string> = { K: "帥", A: "仕", B: "相", N: "傌", R: "俥", C: "炮", P: "兵", k: "將", a: "士", b: "象", n: "馬", r: "車", c: "砲", p: "卒" };
const KIND_ZH: Record<string, string> = {
  new_target_pair: "同一子新增两个目标", two_new_threats: "走子后出现两个新的有效威胁",
  friendly_cannon_screen_check: "炮将军，己方炮架同时攻子", vacated_blocker: "让开阻挡格", ray: "车炮直线",
  horse_leg: "马腿", elephant_eye: "象眼", flying_general: "将帅对面", all_legal_escapes: "所有逃着均失子",
  profitable_release: "守子被消除后有利吃取", actual_guard_response: "守子实际应着后另一目标失守",
  bilateral_major_captures: "双方都吃掉大子", blunder_trade_recaptured: "失着兑子，第 2 手吃回",
  checking_parent: "由含将军的父战术推导", forced_blocker_departure: "阻隔子被迫离开",
  illegal_recapture: "对方不能合法吃回", recapture_costs_rear: "吃回会失去后方较大子",
};
const REASON_ZH: Record<string, string> = {
  nonpositive_mover_recaptured_next_ply: "走子无利且下一手被吃，不计其威胁", defender_in_check: "对方正被将军，不判围困",
  defensible: "对手可不亏地吃掉攻击子，不判捉双", no_prior_legal_attack: "此前没有合法攻击，消除保护只送覆核",
  release_not_proven_forced: "未证明守子是被迫离开", no_profitable_two_stage_confirmation: "串打前后两段未都有利",
  absolute_pin_without_proven_gain: "绝对牵制没有实际得子证据", horse_leg_value_boundary: "马腿牵制的子力边界",
  missing_actual_check_response: "将军后 PV 没有实际应着", revealed_attack_not_profitable: "闪出的攻击交换收益不大于 0",
  target_explained_by_line_tactic: "目标已由直线战术解释", target_is_pinned_front: "目标是被牵制的前子",
  skewer_not_realized: "串打没有兑现", no_profitable_capture_after_check: "应将后没有有利的吃大子",
  check_with_preexisting_attack: "将军前已有该攻击，不算抽将", target_not_confirmed_after_check: "应将后目标未确认失守",
};
const SUPPRESSED_ZH: Record<string, string> = { gain_has_other_tactic: "得子题已有其他战术，不另计交换" };
const MATERIAL_ZH: Record<GainKind, string> = { gain: "得子", no_gain: "并非得子" };

interface Filters { query: string; tactics: MidgameTacticId[]; none: boolean; material: "" | GainKind | "invalid"; steps: string; }
const NO_FILTERS: Filters = { query: "", tactics: [], none: false, material: "", steps: "" };
const NO_MOVES: string[] = [];
const noop = () => undefined;

// The tab unmounts whenever another tab opens. Keep the data and the reviewer's place until the page reloads.
let datasetRequest: Promise<CapturingDataset> | null = null;
const remembered: { filters: Filters; puzzleId: string | null; frame: number } = { filters: NO_FILTERS, puzzleId: null, frame: 1 };

function loadDataset(): Promise<CapturingDataset> {
  if (!datasetRequest) {
    datasetRequest = fetch("/data/capturing-tactics.json")
      .then((response) => { if (!response.ok) throw new Error(`无法载入吃子战术资料：HTTP ${response.status}`); return response.json() as Promise<CapturingDataset>; })
      .then((data) => { if (data.schemaVersion !== "2.1") throw new Error("中局题资料版本不兼容，请重建 v2.1 索引"); return data; });
    datasetRequest.catch(() => { datasetRequest = null; });
  }
  return datasetRequest;
}

const tacticName = (id: string, labels: Record<string, string>) => TACTIC_ZH[id] ?? labels[id] ?? id;
const squaresOf = (refs: MidgamePieceRef[]) => refs.map((ref) => ref.square).filter((square): square is string => Boolean(square));
const stepKey = (puzzle: CapturingPuzzle) => (puzzle.pv.length >= 10 ? "10+" : String(puzzle.pv.length));
const isTyping = (target: EventTarget | null) => target instanceof HTMLElement && Boolean(target.closest("input, textarea, select"));
const sameFilters = (a: Filters, b: Filters) => JSON.stringify(a) === JSON.stringify(b);

function matches(puzzle: CapturingPuzzle, filters: Filters): boolean {
  const query = filters.query.trim().toLowerCase();
  if (query && !puzzle.id.toLowerCase().includes(query) && String(puzzle.sourceRow ?? "") !== query) return false;
  if (filters.none && puzzle.status !== "unmatched") return false;
  if (filters.tactics.some((id) => !puzzle.tactics.includes(id))) return false;
  if (filters.material === "invalid" ? puzzle.status !== "invalid" : filters.material && puzzle.material?.kind !== filters.material) return false;
  if (filters.steps && stepKey(puzzle) !== filters.steps) return false;
  return true;
}

function Refs({ refs }: { refs: MidgamePieceRef[] }) {
  if (!refs.length) return <>—</>;
  return <>{refs.map((ref, index) => <span key={`${ref.id}-${index}`}>{index ? "、" : ""}{GLYPH[ref.piece] ?? ref.piece}<code>{ref.square ?? "?"}</code></span>)}</>;
}

function OccurrenceCard({ item, labels, pressed, onToggle, onGo }: {
  item: MidgameOccurrence | SupportingOccurrence; labels: Record<string, string>; pressed: boolean; onToggle: () => void; onGo: (ply: number) => void;
}) {
  const { triggerPly, confirmedPly, actors, targets, relationKind } = item.evidence;
  const suppressedBy = "suppressedBy" in item ? item.suppressedBy : "";
  return (
    <div className={`cap-occ${pressed ? " pressed" : ""}`}>
      <div className="h">
        <button type="button" className="title" aria-pressed={pressed} onClick={onToggle} title="在棋盘标出行动子和目标">
          <span className="lab">{tacticName(item.id, labels)}</span> <span className="lid">{item.id}</span>
        </button>
        <span className="plies">
          <button type="button" onClick={() => onGo(triggerPly)}>触发 第{triggerPly}手</button>
          {confirmedPly !== triggerPly && <button type="button" onClick={() => onGo(confirmedPly)}>确认 第{confirmedPly}手</button>}
        </span>
      </div>
      <div className="who"><span className="a">行动：<Refs refs={actors} /></span><span className="g">目标：<Refs refs={targets} /></span></div>
      <div className="kind" title={relationKind}>
        {KIND_ZH[relationKind] ?? relationKind}{suppressedBy ? ` · 已被去重：${SUPPRESSED_ZH[suppressedBy] ?? suppressedBy}` : ""}
      </div>
      <details><summary>原始证据</summary><pre>{JSON.stringify(item.evidence, null, 2)}</pre></details>
    </div>
  );
}

export function CapturingTacticsLab() {
  const [dataset, setDataset] = useState<CapturingDataset | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<Filters>(remembered.filters);
  const [puzzleId, setPuzzleId] = useState<string | null>(remembered.puzzleId);
  const [frame, setFrame] = useState(remembered.frame);
  const [flipped, setFlipped] = useState<boolean | null>(null);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    let active = true;
    loadDataset()
      .then((data) => { if (active) setDataset(data); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "无法载入吃子战术资料"); });
    return () => { active = false; };
  }, []);

  useEffect(() => { remembered.filters = filters; remembered.puzzleId = puzzleId; remembered.frame = frame; }, [filters, puzzleId, frame]);

  const puzzles = dataset?.puzzles;
  const visible = useMemo(() => (puzzles ?? []).filter((puzzle) => matches(puzzle, filters)), [puzzles, filters]);
  const byId = useMemo(() => new Map((puzzles ?? []).map((puzzle) => [puzzle.id, puzzle])), [puzzles]);
  const stepOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const puzzle of puzzles ?? []) counts.set(stepKey(puzzle), (counts.get(stepKey(puzzle)) ?? 0) + 1);
    const order = (key: string) => (key === "10+" ? 10 : Number(key));
    return [...counts.entries()].sort((a, b) => order(a[0]) - order(b[0]));
  }, [puzzles]);

  // A puzzle stays open after a filter hides it; with nothing chosen, the first visible puzzle opens.
  const current = (puzzleId ? byId.get(puzzleId) : undefined) ?? visible[0] ?? null;
  const last = current ? Math.max(0, current.fens.length - 1) : 0;
  const ply = Math.min(Math.max(0, frame), last);
  const isFlipped = flipped ?? current?.solverSide === "black";

  const open = (puzzle: CapturingPuzzle) => {
    setPuzzleId(puzzle.id); setFrame(puzzle.fens.length > 1 ? 1 : 0); setFocusKey(null); setFlipped(null);
  };
  const goPuzzle = (direction: number) => {
    const index = visible.findIndex((puzzle) => puzzle.id === current?.id);
    const next = index === -1 ? visible[0] : visible[Math.min(visible.length - 1, Math.max(0, index + direction))];
    if (next && next.id !== current?.id) open(next);
  };
  const goPly = (target: number) => setFrame(Math.min(Math.max(0, target), last));

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (!current || event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return;
      const key = event.key.toLowerCase();
      if (event.key === "ArrowLeft") { event.preventDefault(); goPly(ply - 1); }
      else if (event.key === "ArrowRight") { event.preventDefault(); goPly(ply + 1); }
      else if (key === "n") goPuzzle(1);
      else if (key === "p") goPuzzle(-1);
      else if (key === "f") setFlipped(!isFlipped);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const currentId = current?.id;
  useEffect(() => {
    listRef.current?.querySelector('[aria-current="true"]')?.scrollIntoView({ block: "nearest" });
  }, [currentId]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!dataset) return <div className="loading-state"><Spinner label="正在载入吃子战术资料" /></div>;

  const labels = dataset.labels as Record<string, string>;
  const summary = dataset.summary;
  // CSV row 2 is source puzzle 1; a contiguous slice is shown as its puzzle range.
  const sourceRows = dataset.puzzles.map((puzzle) => puzzle.sourceRow).filter((row): row is number => typeof row === "number");
  const firstRow = Math.min(...sourceRows);
  const lastRow = Math.max(...sourceRows);
  const coverage = dataset.puzzleCount === dataset.eligibleRows ? `全量导入 ${dataset.puzzleCount} 题`
    : sourceRows.length === dataset.puzzleCount && lastRow - firstRow + 1 === dataset.puzzleCount
      ? `${dataset.eligibleRows} 题中第 ${firstRow - 1}–${lastRow - 1} 题`
      : `${dataset.eligibleRows} 题中抽样 ${dataset.puzzleCount} 题`;

  const annotation = current && ply > 0 ? current.plies[ply - 1] : undefined;
  const occurrences = current ? current.plies.flatMap((entry) => entry.occurrences) : [];
  const supporting = current?.supportingEvidence ?? [];
  const focused = [...occurrences, ...supporting].find((item) => item.evidence.key === focusKey);
  // A chosen card stays marked; otherwise mark whatever the shown move triggers.
  const marked = focused ? [focused] : annotation?.occurrences ?? [];
  const marks = { actors: marked.flatMap((item) => squaresOf(item.evidence.actors)), targets: marked.flatMap((item) => squaresOf(item.evidence.targets)) };
  const lastMove = annotation ? ({ ply: annotation.ply, side: "red", ucci: annotation.ucci, chineseNotation: annotation.chinese ?? "", fromSquare: annotation.ucci.slice(0, 2), toSquare: annotation.ucci.slice(2, 4) } satisfies MoveRecord) : undefined;
  const where = ply === 0 ? "B0 失着前" : ply === 1 ? "第 1 手（失着）后：解题开始局面" : `第 ${ply} 手后`;
  const fen = current ? current.fens[ply] ?? current.initialFen : "";
  const update = (patch: Partial<Filters>) => setFilters((previous) => ({ ...previous, ...patch }));
  const toggleTactic = (id: MidgameTacticId) => update({ none: false, tactics: filters.tactics.includes(id) ? filters.tactics.filter((t) => t !== id) : [...filters.tactics, id] });
  const toggleFocus = (item: MidgameOccurrence) => {
    if (focusKey === item.evidence.key) { setFocusKey(null); return; }
    setFocusKey(item.evidence.key); goPly(item.evidence.triggerPly);
  };

  return (
    <div className="cap-lab">
      <header className="cap-top">
        <div>
          <span className="eyebrow">CAPTURING TACTICS</span>
          <h2>吃子棋题战术标注</h2>
          <div className="cap-sub">
            {dataset.source}（{coverage}）· 规则 <span className="mono">{dataset.rulesVersion}</span> · 生成于 {new Date(dataset.generatedAt).toLocaleString()}
          </div>
        </div>
        <div className="cap-stats">
          <div className="cap-stat"><b>{dataset.puzzleCount}</b><span>题目</span></div>
          <div className="cap-stat tagged"><b>{dataset.puzzles.filter((puzzle) => puzzle.tactics.length).length}</b><span>有标签</span></div>
          <div className="cap-stat"><b>{summary.unmatched ?? 0}</b><span>无标签</span></div>
          <div className="cap-stat gain"><b>{summary.gain_gain ?? 0}</b><span>得子</span></div>
          {(summary.invalid ?? 0) > 0 && <div className="cap-stat invalid"><b>{summary.invalid}</b><span>无效</span></div>}
        </div>
      </header>

      <div className="cap-grid">
        <aside className="cap-pane cap-queue" aria-label="题目列表">
          <div className="cap-filters">
            <input type="search" id="cap-query" value={filters.query} onChange={(event) => update({ query: event.target.value })} placeholder="搜索题目 ID 或 CSV 行号" aria-label="搜索题目" />
            <div className="cap-row2">
              <select id="cap-material" value={filters.material} onChange={(event) => update({ material: event.target.value as Filters["material"] })} aria-label="得子判定">
                <option value="">得子：全部</option>
                <option value="gain">得子（{summary.gain_gain ?? 0}）</option>
                <option value="no_gain">并非得子（{summary.gain_no_gain ?? 0}）</option>
                {(summary.invalid ?? 0) > 0 && <option value="invalid">无效（{summary.invalid}）</option>}
              </select>
              <select id="cap-steps" value={filters.steps} onChange={(event) => update({ steps: event.target.value })} aria-label="PV 步数">
                <option value="">步数：全部</option>
                {stepOptions.map(([key, count]) => <option key={key} value={key}>{key === "10+" ? "10 步或以上" : `${key} 步`}（{count}）</option>)}
              </select>
            </div>
            <div className="cap-chips" aria-label="按标签筛选（须同时含有所选标签）">
              {ORDER.map((id) => (
                <button type="button" key={id} className="cap-chip" aria-pressed={filters.tactics.includes(id)} onClick={() => toggleTactic(id)}>
                  {tacticName(id, labels)}<small>{summary[id] ?? 0}</small>
                </button>
              ))}
              <button type="button" className="cap-chip" aria-pressed={filters.none} onClick={() => update({ none: !filters.none, tactics: [] })}>
                无标签<small>{summary.unmatched ?? 0}</small>
              </button>
            </div>
            <div className="cap-count">
              <span>显示 {visible.length} / {dataset.puzzleCount} 题</span>
              <button type="button" className="cap-btn small" disabled={sameFilters(filters, NO_FILTERS)} onClick={() => setFilters(NO_FILTERS)}>清除筛选</button>
            </div>
          </div>
          <ul className="cap-list" ref={listRef}>
            {visible.map((puzzle) => {
              const kind = puzzle.status === "invalid" || !puzzle.material ? "invalid" : puzzle.material.kind;
              return (
                <li key={puzzle.id}>
                  <button type="button" className="cap-item" aria-current={puzzle.id === current?.id} onClick={() => open(puzzle)}>
                    <span className="id">{puzzle.id}</span>
                    <span className={`cap-pill ${kind}`}>{kind === "invalid" ? "无效" : kind === "gain" ? "得子" : "非得子"}</span>
                    <span className="meta">
                      {puzzle.sourceRow != null && <span>#{puzzle.sourceRow}</span>}
                      <span>{puzzle.pv.length} 步</span>
                      {puzzle.tactics.length ? puzzle.tactics.map((id) => <span className="t" key={id}>{tacticName(id, labels)}</span>) : <span>无标签</span>}
                    </span>
                  </button>
                </li>
              );
            })}
            {visible.length === 0 && <li className="cap-empty">没有符合筛选的题目。</li>}
          </ul>
        </aside>

        <section className="cap-pane cap-stage" aria-label="棋局">
          {!current ? <p className="cap-empty">没有符合筛选的题目。</p> : (
            <>
              <div className="cap-phead">
                <span className="cap-pid">{current.id}</span>
                <span className={`cap-tag${current.solverSide === "red" ? " red" : ""}`}>{current.solverSide === "red" ? "红方解题" : "黑方解题"}</span>
                {current.material ? (
                  <span className={`cap-tag ${current.material.kind}`}>
                    {MATERIAL_ZH[current.material.kind]} · Δ {current.material.delta >= 0 ? "+" : ""}{current.material.delta}（{current.material.start} → {current.material.end}）
                  </span>
                ) : <span className="cap-tag invalid">无效</span>}
                {current.rating != null && <span className="cap-tag mono">{current.rating}</span>}
                {current.sourceRow != null && <span className="cap-tag mono">CSV 第 {current.sourceRow} 行</span>}
                {current.url && <a href={current.url} target="_blank" rel="noreferrer">在 xiangqi.com 打开 ↗</a>}
              </div>
              <div className="cap-board-row">
                <div className="cap-board-box">
                  <XiangqiBoard fen={fen} legalMoves={NO_MOVES} lastMove={lastMove} disabled onMove={noop} flipped={isFlipped} marks={marks} coordinates />
                  <div className="cap-plybar">
                    <button type="button" className="cap-btn" onClick={() => goPly(0)} disabled={ply === 0} aria-label="失着前">⏮</button>
                    <button type="button" className="cap-btn" onClick={() => goPly(ply - 1)} disabled={ply === 0} aria-label="上一手">◀</button>
                    <button type="button" className="cap-btn" onClick={() => goPly(ply + 1)} disabled={ply === last} aria-label="下一手">▶</button>
                    <button type="button" className="cap-btn" onClick={() => goPly(last)} disabled={ply === last} aria-label="终局">⏭</button>
                    <button type="button" className="cap-btn" onClick={() => setFlipped(!isFlipped)}>翻转</button>
                    <span className="cap-where">{where}</span>
                  </div>
                  <div className="cap-legend">
                    <span><i className="move" />上一手</span><span><i className="actor" />攻击/行动子</span><span><i className="target" />目标</span>
                  </div>
                  <details className="cap-fen"><summary>FEN</summary><code>{fen}</code></details>
                </div>
                <ol className="cap-moves" aria-label="着法">
                  <li>
                    <button type="button" className="cap-mv start" aria-current={ply === 0} onClick={() => goPly(0)}>
                      <span className="n">0</span><span className="txt"><span className="who">B0 失着前局面</span></span>
                    </button>
                  </li>
                  {current.plies.map((entry) => (
                    <li key={entry.ply}>
                      <button type="button" className="cap-mv" aria-current={ply === entry.ply} onClick={() => goPly(entry.ply)}>
                        <span className="n">{entry.ply}</span>
                        <span className={`who${entry.ply === 1 ? " blunder" : entry.solver ? " solver" : ""}`}>{entry.ply === 1 ? "失着" : entry.solver ? "解题方" : "应着"}</span>
                        <span className="txt">
                          <span className="zh">{entry.chinese ?? entry.ucci}</span>
                          {entry.chinese && <span className="uc">{entry.ucci}</span>}
                          {entry.occurrences.map((item) => <span className="ot" key={item.evidence.key}>{tacticName(item.id, labels)}</span>)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              </div>
            </>
          )}
        </section>

        <div className="cap-side">
          <section className="cap-pane" aria-label="程序标签">
            <h3>程序给出的标签（{current?.tactics.length ?? 0}）</h3>
            {current?.error && <div className="error-banner">第 {current.errorPly ?? 0} 手：{current.error}<pre>{current.errorFen}</pre></div>}
            {occurrences.length ? occurrences.map((item) => (
              <OccurrenceCard key={item.evidence.key} item={item} labels={labels} pressed={focusKey === item.evidence.key} onToggle={() => toggleFocus(item)} onGo={goPly} />
            )) : current && current.status !== "invalid" && <p className="cap-empty">程序没有给出任何标签（unmatched）。请确认这题确实没有十类战术中的任何一种。</p>}
            {supporting.length > 0 && (
              <details className="cap-more">
                <summary>被去重的支援证据（{supporting.length}）</summary>
                {supporting.map((item) => (
                  <OccurrenceCard key={item.evidence.key} item={item} labels={labels} pressed={focusKey === item.evidence.key} onToggle={() => toggleFocus(item)} onGo={goPly} />
                ))}
              </details>
            )}
            {current && current.reviewReasons.length > 0 && (
              <details className="cap-more">
                <summary>程序放弃标注的候选（{current.reviewReasons.length}）</summary>
                <ul>
                  {current.reviewReasons.map((reason, index) => (
                    <li key={`${reason.label}-${reason.ply}-${index}`}>
                      <button type="button" className="cap-link" onClick={() => goPly(reason.ply)}>第 {reason.ply} 手</button>
                      {" · "}{tacticName(reason.label, labels)} · {REASON_ZH[reason.reason] ?? reason.reason} <code>{reason.reason}</code>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
          <section className="cap-pane" aria-label="说明">
            <h3>说明</h3>
            <p className="cap-note">得子按失着前至 PV 终点的车马炮净差计算（车 9、马炮 4，增加至少 4 为得子）。战术从第 2 手起计；延后确认的证据挂在解题方触发的一手。</p>
            <div className="cap-keys">
              快捷键：<kbd>←</kbd><kbd>→</kbd> 前后一手 · <kbd>N</kbd><kbd>P</kbd> 下/上一题 · <kbd>F</kbd> 翻转棋盘
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
