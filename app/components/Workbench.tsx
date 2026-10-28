"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { FluentProvider } from "@fluentui/react-provider";
import { Spinner } from "@fluentui/react-spinner";
import { Tab, TabList } from "@fluentui/react-tabs";
import { webLightTheme } from "@fluentui/react-theme";
import { ArrowResetRegular, ChevronLeftRegular, ChevronRightRegular } from "@fluentui/react-icons";
import { api } from "../lib/api";
import type { LiveGameReport, MemoryPreset, MoveRecord, RecognitionState } from "../lib/types";
import { TestCaseLab } from "./TestCaseLab";
import { PuzzleBrowser } from "./PuzzleBrowser";
import { XiangqiBoard } from "./XiangqiBoard";
import { WhiteFaceGeneralLab } from "./WhiteFaceGeneralLab";
import { NotationImportLab } from "./NotationImportLab";
import { TacticsLab } from "./TacticsLab";
import { TacticalCategoriesLab } from "./TacticalCategoriesLab";
import { CapturingTacticsLab } from "./CapturingTacticsLab";

interface Snapshot {
  state: RecognitionState;
  legalMoves: string[];
  move?: MoveRecord;
  liveReport?: LiveGameReport | null;
  reportStatus?: "pending" | "ready" | "failed";
}

const SYSTEM_LABELS: Record<string, string> = {
  central_cannon: "中炮", fly_elephant: "飛相／象", proper_horse_opening: "起馬",
  palcorner_cannon: "仕角炮", cross_palace_cannon: "過宮炮", angle_pawn: "仙人指路／挺卒",
  pawn_bottom_cannon: "卒底炮", screen_horse: "屏風馬", reverse_palace_horse: "反宮馬",
  single_horse: "單提馬", left_three_step_tiger: "左三步虎", right_three_step_tiger: "右三步虎",
  left_cannon_blockade: "左炮封車",
  five_six_cannon: "五六炮",
  five_seven_cannon: "五七炮",
  five_eight_cannon: "五八炮",
  five_nine_cannon: "五九炮",
  seven_route_horse: "七路馬",
  edge_horse_left: "邊馬",
  edge_horse_right: "邊馬",
  horizontal_rook: "橫車",
  straight_rook: "直車",
  double_horizontal_rooks: "雙橫車",
  river_cannon: "巡河炮",
  river_rook: "巡河車",
  riding_river_rook: "騎河車",
  cross_river_rook: "過河車",
  flat_cannon_exchange: "平炮兌車",
  advance_three_pawn: "進三兵",
  advance_seven_pawn: "進七兵",
  advance_three_soldier: "挺三卒",
  advance_seven_soldier: "挺七卒",
  two_headed_snake: "兩頭蛇",
  double_proper_horses: "雙正馬",
};

const EMPTY_MEMORY: MemoryPreset = {
  redChoicePath: [], blackChoicePath: [], blackComposite: null, redWing: null, blackWing: null,
};

type RepetitionLanguage = "en" | "zh-CN" | "zh-TW" | "vi";

const REPETITION_COPY: Record<RepetitionLanguage, {
  languageLabel: string;
  labels: Record<RecognitionState["repetitionDecision"]["status"], string>;
  warningTitle: string;
  warningBody: string;
  blockedTitle: string;
  blockedBody: string;
  drawTitle: string;
  drawBody: string;
  restart: string;
}> = {
  en: {
    languageLabel: "Language",
    labels: { none: "No repetition", watch: "Repeated position", warning: "Repetition warning", must_change: "Different move required", draw: "Draw" },
    warningTitle: "Repeated position detected",
    warningBody: "This position has occurred three times. Repeating it once more will result in a draw.",
    blockedTitle: "A different move is required",
    blockedBody: "This move would repeat the position. Please make a different move.",
    drawTitle: "Draw by repetition",
    drawBody: "The same position has occurred four times.",
    restart: "New game",
  },
  "zh-CN": {
    languageLabel: "语言",
    labels: { none: "未重复", watch: "发现重复", warning: "重复警告", must_change: "需要变着", draw: "和棋" },
    warningTitle: "检测到重复局面",
    warningBody: "该局面已出现三次。若再次出现相同局面，本局将判和。",
    blockedTitle: "需要变着",
    blockedBody: "此着会再次形成重复局面，请选择其他走法。",
    drawTitle: "重复和棋",
    drawBody: "相同局面已出现四次。",
    restart: "重新开始",
  },
  "zh-TW": {
    languageLabel: "語言",
    labels: { none: "未重複", watch: "發現重複", warning: "重複警告", must_change: "需要變著", draw: "和棋" },
    warningTitle: "偵測到重複局面",
    warningBody: "此局面已出現三次。若再次出現相同局面，本局將判和。",
    blockedTitle: "需要變著",
    blockedBody: "此著會再次形成重複局面，請選擇其他走法。",
    drawTitle: "重複和棋",
    drawBody: "相同局面已出現四次。",
    restart: "重新開始",
  },
  vi: {
    languageLabel: "Ngôn ngữ",
    labels: { none: "Không lặp lại", watch: "Phát hiện lặp lại", warning: "Cảnh báo lặp lại", must_change: "Cần đi nước khác", draw: "Hòa" },
    warningTitle: "Đã phát hiện thế cờ lặp lại",
    warningBody: "Thế cờ này đã xuất hiện ba lần. Nếu lặp lại thêm một lần nữa, ván đấu sẽ được xử hòa.",
    blockedTitle: "Bạn cần đi nước khác",
    blockedBody: "Nước đi này sẽ lặp lại thế cờ. Vui lòng chọn một nước đi khác.",
    drawTitle: "Hòa do lặp lại thế cờ",
    drawBody: "Cùng một thế cờ đã xuất hiện bốn lần.",
    restart: "Ván mới",
  },
};

function ChoicePath({ side, state }: { side: "red" | "black"; state: RecognitionState }) {
  const memory = state.openingMemory[side];
  const items = [...memory.choicePath, ...memory.compositeSystems, ...memory.formedShapes];
  return (
    <div className="choice-column">
      <div className="choice-label"><span className={`side-dot ${side}`} />{side === "red" ? "紅方" : "黑方"}</div>
      {items.length ? <div className="choice-path">{items.map((item, index) => {
        const wingText = item.id === "palcorner_cannon"
          ? ""
          : item.wing
            ? ` · ${item.wing === "left" ? "左" : "右"}`
            : "";
        return <span key={`${item.id}-${index}`}><strong>{SYSTEM_LABELS[item.id] ?? item.id}</strong><small>{item.source} · ply {item.formedAtPly}{wingText}</small></span>;
      })}</div> : <div className="choice-empty">尚未形成主選擇</div>}
    </div>
  );
}

export function Workbench() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [index, setIndex] = useState(0);
  const [tab, setTab] = useState("game");
  const [hydrated, setHydrated] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [ruleNotice, setRuleNotice] = useState<"blocked" | null>(null);
  const [language, setLanguage] = useState<"zh" | "en">("en");
  const [repetitionLanguage, setRepetitionLanguage] = useState<RepetitionLanguage>("zh-CN");
  const [fenDraft, setFenDraft] = useState("");

  const current = snapshots[index];
  const currentFen = current?.state.fen;

  // Keep the debug FEN in sync with the board being viewed.  This also makes
  // stepping backward and forward through the move list a quick way to copy
  // the exact position that triggered a label.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (currentFen) setFenDraft(currentFen);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [currentFen]);

  const reset = useCallback(async () => {
    setBusy(true); setError(""); setRuleNotice(null);
    try {
      const response = await api.initial();
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setFenDraft(response.state.fen);
      setIndex(0);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "無法連接辨認服務"); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    let active = true;
    const hydrationTimer = window.setTimeout(() => {
      if (active) setHydrated(true);
    }, 0);
    void api.initial().then((response) => {
      if (!active) return;
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setFenDraft(response.state.fen);
      setIndex(0);
      setBusy(false);
    }).catch((reason: unknown) => {
      if (!active) return;
      setError(reason instanceof Error ? reason.message : "無法連接辨認服務");
      setBusy(false);
    });
    return () => { active = false; window.clearTimeout(hydrationTimer); };
  }, []);

  async function play(move: string) {
    if (!current) return;
    setBusy(true); setError(""); setRuleNotice(null);
    try {
      const result = await api.advance(current.state, move);
      const base = snapshots.slice(0, index + 1);
      const reportKey = `${result.state.ply}:${result.state.fen}`;
      const next = [...base, { state: result.state, legalMoves: result.legalMoves, move: result.move, liveReport: null, reportStatus: "pending" as const }];
      setSnapshots(next); setIndex(next.length - 1);
      // Deliberately do not await tactical analysis: the legal move, updated
      // board, and repetition decision should remain responsive even when a
      // dense position needs more time to inspect.
      void api.analyzeLiveReport(
        base[0].state.fen,
        next.slice(1).map((item) => item.move?.ucci).filter((ucci): ucci is string => Boolean(ucci)),
        next.length - 1,
        result.state.ply,
        result.state.repetitionDecision,
      ).then((report) => {
        setSnapshots((existing) => existing.map((snapshot) => (
          `${snapshot.state.ply}:${snapshot.state.fen}` === reportKey
            ? { ...snapshot, liveReport: report, reportStatus: "ready" as const }
            : snapshot
        )));
      }).catch(() => {
        setSnapshots((existing) => existing.map((snapshot) => (
          `${snapshot.state.ply}:${snapshot.state.fen}` === reportKey
            ? { ...snapshot, reportStatus: "failed" as const }
            : snapshot
        )));
      });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "走子失敗";
      if (message === "此着会形成长将／长捉重复，请选择其他着法") {
        setRuleNotice("blocked");
      } else {
        setError(message);
      }
    }
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
      setFenDraft(response.state.fen);
      setIndex(0);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "FEN 无法载入，请检查格式。");
    } finally { setBusy(false); }
  }

  const moveHistory = snapshots.slice(1).map((item) => item.move).filter(Boolean) as MoveRecord[];
  const currentMove = index > 0 ? snapshots[index].move : undefined;
  const liveReport = index > 0 ? snapshots[index].liveReport : null;
  const repetition = current?.state.repetitionDecision;
  const repetitionCopy = REPETITION_COPY[repetitionLanguage];
  const repetitionLabel = repetitionCopy.labels[repetition?.status ?? "none"];
  const isDraw = repetition?.status === "draw";

  return (
    <FluentProvider theme={webLightTheme} className="app-provider">
      <header className="app-header">
        <div className="brand-block"><div className="seal">局</div><div><span>XIANGQI OPENING LAB</span><h1>象棋開局辨認實驗室</h1></div></div>
        <div className="header-status"><span className={`status-light ${error ? "offline" : ""}`} />{error ? "後端未連接" : "規則引擎 mvp-0.1"}</div>
      </header>

      <nav className="app-tabs" aria-label="主要功能">
        {hydrated ? (
          <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(String(data.value))}>
            <Tab value="game">棋局工作台</Tab><Tab value="categories">战术分类</Tab><Tab value="tactics">手法识别</Tab><Tab value="patterns">殺法測試</Tab><Tab value="puzzles">棋题浏览器</Tab><Tab value="capturing">吃子战术标注</Tab><Tab value="tests">案例測試</Tab><Tab value="importer">棋譜導入測試</Tab>
          </TabList>
        ) : <div className="app-tabs-placeholder" aria-hidden="true" />}
      </nav>

      <main className="app-main">
        {error && <div className="error-banner app-error" role="alert"><span>{error}</span><Button size="small" onClick={reset}>重新連接</Button></div>}
        {tab === "importer" ? (
          <NotationImportLab />
        ) : !current ? (
          <div className="loading-state"><Spinner label="正在啟動辨認服務" /></div>
        ) : tab === "categories" ? (
          <TacticalCategoriesLab />
        ) : tab === "tactics" ? (
          <TacticsLab />
        ) : tab === "patterns" ? (
          <WhiteFaceGeneralLab />
        ) : tab === "puzzles" ? (
          <PuzzleBrowser />
        ) : tab === "capturing" ? (
          <CapturingTacticsLab />
        ) : tab === "tests" ? (
          <TestCaseLab currentFen={current.state.fen} />
        ) : (
          <div className="workbench-grid">
            <section className="board-column">
              <div className="board-toolbar">
                <div><span className="turn-label">輪到</span><strong className={current.state.fen.split(" ")[1] === "w" ? "red-text" : ""}>{current.state.fen.split(" ")[1] === "w" ? "紅方" : "黑方"}</strong></div>
                <div className="navigation-controls">
                  <Button aria-label="上一步" icon={<ChevronLeftRegular />} disabled={index === 0 || busy} onClick={() => setIndex(index - 1)} />
                  <span>{index} / {snapshots.length - 1}</span>
                  <Button aria-label="下一步" icon={<ChevronRightRegular />} disabled={index === snapshots.length - 1 || busy} onClick={() => setIndex(index + 1)} />
                  <Button icon={<ArrowResetRegular />} disabled={busy} onClick={reset}>重設</Button>
                </div>
              </div>
              <XiangqiBoard fen={current.state.fen} legalMoves={current.legalMoves} lastMove={currentMove} disabled={busy || isDraw} onMove={play} />
              {isDraw && <section className="game-result" role="status">
                <span>GAME OVER</span><strong>{repetitionCopy.drawTitle}</strong><p>{repetitionCopy.drawBody}</p>
                <Button appearance="primary" onClick={reset}>{repetitionCopy.restart}</Button>
              </section>}
              <form className="fen-strip fen-editor" onSubmit={loadFen}>
                <label htmlFor="workbench-fen">FEN</label>
                <div className="fen-editor-field">
                  <textarea
                    id="workbench-fen"
                    value={fenDraft}
                    onChange={(event) => setFenDraft(event.target.value)}
                    rows={2}
                    disabled={busy}
                    spellCheck={false}
                    aria-label="输入 FEN 局面"
                  />
                  <div className="fen-editor-actions">
                    <small>贴入完整 FEN 后载入，即可从该局面继续走子。</small>
                    <Button type="submit" appearance="primary" disabled={busy}>载入局面</Button>
                  </div>
                </div>
              </form>
            </section>

            <aside className="analysis-column">
              <section className="panel classification-card">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">LIVE CLASSIFICATION</span>
                    <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      目前判斷
                      <Button size="small" style={{ minWidth: '40px', padding: '2px 6px', height: '20px', fontSize: '11px' }} onClick={() => setLanguage(l => l === "zh" ? "en" : "zh")}>
                        {language === "zh" ? "EN" : "中"}
                      </Button>
                    </h2>
                  </div>
                  <Badge color={current.state.classification.certainty === "confirmed" ? "success" : "warning"}>{current.state.classification.certainty}</Badge>
                </div>
                <div className="opening-name">
                  {language === "en"
                    ? (current.state.classification.displayNameEn || current.state.classification.displayName)
                    : current.state.classification.displayName}
                </div>
                <div className="matchup-id">{current.state.classification.baseMatchupId ?? "等待雙方主選擇形成"}</div>
                <div className="choice-columns"><ChoicePath side="red" state={current.state} /><ChoicePath side="black" state={current.state} /></div>
              </section>

              <section className="panel shape-card">
                <div className="panel-heading compact"><div><span className="eyebrow">FEN OBSERVATION</span><h2>目前棋形</h2></div><Badge appearance="outline">ply {current.state.ply}</Badge></div>
                <div className="shape-row"><span>紅</span><div>{current.state.currentShapes.red.length ? current.state.currentShapes.red.map((shape) => <code key={shape}>{shape}</code>) : <em>無已知棋形</em>}</div></div>
                <div className="shape-row"><span>黑</span><div>{current.state.currentShapes.black.length ? current.state.currentShapes.black.map((shape) => <code key={shape}>{shape}</code>) : <em>無已知棋形</em>}</div></div>
              </section>

              <section className="panel repetition-card">
                <div className="panel-heading compact"><div><span className="eyebrow">REPETITION ADJUDICATION</span><h2>重复局面／长将长捉</h2></div><Badge appearance="outline">{repetitionLabel}</Badge></div>
                <label className="native-field repetition-language"><span>{repetitionCopy.languageLabel}</span><select value={repetitionLanguage} onChange={(event) => setRepetitionLanguage(event.target.value as RepetitionLanguage)}><option value="zh-CN">简体中文</option><option value="zh-TW">繁體中文</option><option value="en">English</option><option value="vi">Tiếng Việt</option></select></label>
                <div className="shape-row"><span>出现</span><div>{repetition?.occurrenceCount ?? 1} 次同局面</div></div>
                {current.state.repetitionActions.at(-1) && <div className="shape-row"><span>本手</span><div>{current.state.repetitionActions.at(-1)!.isCheck ? "将军" : current.state.repetitionActions.at(-1)!.chaseTargetIds.length ? `捉 ${current.state.repetitionActions.at(-1)!.chaseTargetIds.length} 子` : "闲着"}</div></div>}
                <div className="shape-row"><span>红方</span><div>{repetition?.redClassification ?? "idle"}</div></div>
                <div className="shape-row"><span>黑方</span><div>{repetition?.blackClassification ?? "idle"}</div></div>
                {repetition?.restrictedSide && <div className="shape-row"><span>责任方</span><div>{repetition.restrictedSide === "red" ? "红方必须变着" : "黑方必须变着"}</div></div>}
                {repetition?.status === "warning" && <div className="rule-notice warning" role="status"><strong>{repetitionCopy.warningTitle}</strong><p>{repetitionCopy.warningBody}</p></div>}
                {repetition?.status === "must_change" && <div className="rule-notice blocked" role="alert"><strong>{repetitionCopy.blockedTitle}</strong><p>{repetitionCopy.blockedBody}</p></div>}
                {ruleNotice === "blocked" && <div className="rule-notice blocked" role="alert"><strong>{repetitionCopy.blockedTitle}</strong><p>{repetitionCopy.blockedBody}</p></div>}
              </section>

              <section className="panel live-report-card">
                <div className="panel-heading compact">
                  <div><span className="eyebrow">LIVE REFEREE REPORT</span><h2>本手对局报告</h2></div>
                  <Badge appearance="outline">{liveReport ? `ply ${liveReport.ply}` : "等待落子"}</Badge>
                </div>
                {!liveReport && snapshots[index]?.reportStatus === "pending" ? <div className="empty-state"><Spinner size="tiny" /> 正在后台分析本手的战术与走子目的…</div>
                  : !liveReport && snapshots[index]?.reportStatus === "failed" ? <div className="empty-state">本手已走完，但报告分析失败；不影响棋局继续进行。</div>
                  : !liveReport ? <div className="empty-state">每次合法落子后，会在这里汇总棋规、战术与走子目的。</div>
                  : liveReport.events.length === 0 ? <div className="empty-state">本手合法，未触发目前已定义的棋规、战术或走子目的标签。</div>
                    : <div className="move-list live-report-list">
                      {liveReport.events.map((event, eventIndex) => (
                        <div className="shape-row" key={`${event.source}-${event.id}-${eventIndex}`}>
                          <span>{event.source === "rule" ? "棋规" : event.source === "tactical_category" ? "战术" : "目的"}</span>
                          <div>
                            <strong>{event.labelZh}</strong>
                            <small>{event.detail}</small>
                            {event.squares.length > 0 && <code>{event.squares.join(" · ")}</code>}
                          </div>
                        </div>
                      ))}
                    </div>}
              </section>

              <section className="panel history-card">
                <div className="panel-heading compact"><div><span className="eyebrow">MOVE HISTORY</span><h2>中文着法</h2></div><Badge appearance="outline">{moveHistory.length} ply</Badge></div>
                <div className="move-list">
                  {moveHistory.length === 0 && <div className="empty-state">在棋盤點擊棋子，再點擊合法落點。</div>}
                  {Array.from({ length: Math.ceil(moveHistory.length / 2) }, (_, row) => {
                    const red = moveHistory[row * 2]; const black = moveHistory[row * 2 + 1];
                    return <button type="button" className="move-row" key={row} onClick={() => setIndex(Math.min(row * 2 + (black ? 2 : 1), snapshots.length - 1))}><span>{row + 1}.</span><strong>{red?.chineseNotation}</strong><small>{red?.ucci}</small><strong>{black?.chineseNotation ?? ""}</strong><small>{black?.ucci ?? ""}</small></button>;
                  })}
                </div>
              </section>
            </aside>
          </div>
        )}
      </main>
    </FluentProvider>
  );
}
