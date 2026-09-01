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
import type { MoveRecord, RecognitionState } from "../lib/types";
import { TestCaseLab } from "./TestCaseLab";
import { XiangqiBoard } from "./XiangqiBoard";
import { WhiteFaceGeneralLab } from "./WhiteFaceGeneralLab";

interface Snapshot {
  state: RecognitionState;
  legalMoves: string[];
  move?: MoveRecord;
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
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [language, setLanguage] = useState<"zh" | "en">("en");

  const current = snapshots[index];

  const reset = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const response = await api.initial();
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setIndex(0);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "無法連接辨認服務"); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => {
    let active = true;
    void api.initial().then((response) => {
      if (!active) return;
      setSnapshots([{ state: response.state, legalMoves: response.legalMoves }]);
      setIndex(0);
      setBusy(false);
    }).catch((reason: unknown) => {
      if (!active) return;
      setError(reason instanceof Error ? reason.message : "無法連接辨認服務");
      setBusy(false);
    });
    return () => { active = false; };
  }, []);

  async function play(move: string) {
    if (!current) return;
    setBusy(true); setError("");
    try {
      const result = await api.advance(current.state, move);
      const base = snapshots.slice(0, index + 1);
      const next = [...base, { state: result.state, legalMoves: result.legalMoves, move: result.move }];
      setSnapshots(next); setIndex(next.length - 1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "走子失敗"); }
    finally { setBusy(false); }
  }

  const moveHistory = snapshots.slice(1).map((item) => item.move).filter(Boolean) as MoveRecord[];
  const currentMove = index > 0 ? snapshots[index].move : undefined;

  return (
    <FluentProvider theme={webLightTheme} className="app-provider">
      <header className="app-header">
        <div className="brand-block"><div className="seal">局</div><div><span>XIANGQI OPENING LAB</span><h1>象棋開局辨認實驗室</h1></div></div>
        <div className="header-status"><span className={`status-light ${error ? "offline" : ""}`} />{error ? "後端未連接" : "規則引擎 mvp-0.1"}</div>
      </header>

      <nav className="app-tabs" aria-label="主要功能">
        <TabList selectedValue={tab} onTabSelect={(_, data) => setTab(String(data.value))}>
          <Tab value="game">棋局工作台</Tab><Tab value="patterns">殺法測試</Tab><Tab value="tests">案例測試</Tab>
        </TabList>
      </nav>

      <main className="app-main">
        {error && <div className="error-banner app-error" role="alert"><span>{error}</span><Button size="small" onClick={reset}>重新連接</Button></div>}
        {!current ? <div className="loading-state"><Spinner label="正在啟動辨認服務" /></div> : tab === "patterns" ? <WhiteFaceGeneralLab /> : tab === "tests" ? <TestCaseLab currentFen={current.state.fen} /> : (
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
              <XiangqiBoard fen={current.state.fen} legalMoves={current.legalMoves} lastMove={currentMove} disabled={busy} onMove={play} />
              <div className="fen-strip"><span>FEN</span><code>{current.state.fen}</code></div>
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
