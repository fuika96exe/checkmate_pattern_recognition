"use client";

import { useEffect, useRef, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { Spinner } from "@fluentui/react-spinner";
import { Textarea } from "@fluentui/react-textarea";
import { api } from "../lib/api";
import type {
  MemoryPreset,
  MoveRecord,
  PatternAnalysis,
  PatternId,
  PositionResponse,
  RecognitionState,
} from "../lib/types";
import { XiangqiBoard } from "./XiangqiBoard";

const SAMPLE_FEN = "4k4/3R1R3/4P4/9/9/9/9/9/9/4K4 b - - 0 1";
const EMPTY_MEMORY: MemoryPreset = {
  redChoicePath: [],
  blackChoicePath: [],
  blackComposite: null,
  redWing: null,
  blackWing: null,
};
const PATTERN_LABELS: Record<PatternId, string> = {
  CROWNED_CHECKMATE: "平顶冠",
  EUNUCHS_CHASING_EMPEROR_CHECKMATE: "太监追皇帝",
  CENTROID_PAWN_CHECKMATE: "花心兵",
  CANNONS_SANDWICHING_CHARIOT_CHECKMATE: "夹车炮",
  DOUBLE_CANNON_CHECKMATE: "重炮杀",
  DOUBLE_TOAST_CHECKMATE: "双杯献酒",
  SMOTHERED_CANNON_CHECKMATE: "闷宫杀",
  HEAVEN_AND_EARTH_CANNON_CHECKMATE: "天地炮",
  IRON_BOLT_CHECKMATE: "铁门栓",
  DRAWER_CHECKMATE: "进洞出洞",
  THROAT_CUTTING_CHECKMATE: "大胆穿心",
  THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE: "三车闹士",
  TWO_DEVILS_KNOCKING_CHECKMATE: "双鬼拍门",
  DOUBLE_CHARIOTS_CHECKMATE: "双车错",
  DISCOVERED_HORSE_CHECKMATE: "拔簧马",
  CENTROID_CHARIOT_CHECKMATE: "花心车",
  TIGER_SILHOUETTE_CHECKMATE: "侧面虎",
  HORSE_CANNON_CHECKMATE: "马后炮",
  DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE: "双马饮泉",
  DOUBLE_CHECK_CHECKMATE: "双将",
  ELBOW_HORSE_CHECKMATE: "卧槽马",
  PALCORNER_HORSE_CHECKMATE: "挂角马",
  ANGLER_HORSE_CHECKMATE: "钓鱼马",
  SMOTHERED_CHECKMATE: "闷杀",
  WHITE_FACE_GENERAL: "白脸将",
  STALEMATE: "困毙",
};

interface BoardSession {
  state: RecognitionState;
  legalMoves: string[];
}

export function WhiteFaceGeneralLab() {
  const [baseFen, setBaseFen] = useState(SAMPLE_FEN);
  const [moveText, setMoveText] = useState("");
  const [debugPatternId, setDebugPatternId] = useState<"" | PatternId>("");
  const [boardSession, setBoardSession] = useState<BoardSession | null>(null);
  const [lastMove, setLastMove] = useState<MoveRecord | undefined>(undefined);
  const [result, setResult] = useState<PatternAnalysis | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [boardBusy, setBoardBusy] = useState(true);
  const syncToken = useRef(0);

  useEffect(() => {
    const trimmedFen = baseFen.trim();
    if (!trimmedFen) {
      setBoardSession(null);
      setLastMove(undefined);
      return;
    }
    if (boardSession?.state.fen === trimmedFen && moveText.trim() === "") {
      return;
    }
    const token = ++syncToken.current;
    const timer = window.setTimeout(() => {
      setBoardBusy(true);
      api.inspect(trimmedFen, EMPTY_MEMORY)
        .then((response) => {
          if (syncToken.current !== token) return;
          setBoardSession({ state: response.state, legalMoves: response.legalMoves });
          setLastMove(undefined);
          setMoveText("");
          setResult(null);
        })
        .catch((reason: unknown) => {
          if (syncToken.current !== token) return;
          setBoardSession(null);
          setLastMove(undefined);
          setResult(null);
          setError(reason instanceof Error ? reason.message : "无法解析 FEN");
        })
        .finally(() => {
          if (syncToken.current === token) setBoardBusy(false);
        });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [baseFen]);

  function parseMoves(text: string): string[] {
    return text.trim() ? text.trim().split(/[,\s]+/).filter(Boolean) : [];
  }

  async function analyze() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await api.analyzePattern(
          baseFen.trim(),
          parseMoves(moveText),
          debugPatternId || undefined,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "分析失败");
    } finally {
      setBusy(false);
    }
  }

  async function replayMovesToBoard() {
    setBusy(true);
    setError("");
    try {
      let response: PositionResponse = await api.inspect(baseFen.trim(), EMPTY_MEMORY);
      let currentState = response.state;
      let currentLegalMoves = response.legalMoves;
      let currentMove: MoveRecord | undefined;
      for (const move of parseMoves(moveText)) {
        const advanced = await api.advance(currentState, move);
        currentState = advanced.state;
        currentLegalMoves = advanced.legalMoves;
        currentMove = advanced.move;
      }
      setBoardSession({ state: currentState, legalMoves: currentLegalMoves });
      setLastMove(currentMove);
    } catch (e) {
      setError(e instanceof Error ? e.message : "无法重播走法");
    } finally {
      setBusy(false);
    }
  }

  async function playOnBoard(move: string) {
    if (!boardSession) return;
    setBusy(true);
    setError("");
    try {
      const advanced = await api.advance(boardSession.state, move);
      const nextMoves = [...parseMoves(moveText), move];
      setBoardSession({ state: advanced.state, legalMoves: advanced.legalMoves });
      setLastMove(advanced.move);
      setMoveText(nextMoves.join(" "));
      setResult(
        await api.analyzePattern(
          baseFen.trim(),
          nextMoves,
          debugPatternId || undefined,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "走子失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pattern-lab">
      <section className="panel pattern-editor">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">CHECKMATE PATTERN LAB</span>
            <h2>杀法自动识别</h2>
          </div>
          <Badge appearance="outline">board-linked analysis</Badge>
        </div>
        <p className="support-copy">输入起始 FEN 会自动刷新棋盘；在棋盘上走子后，UCCI 着法序列会自动追加。也可以手改着法后再重播到棋盘。</p>
        {error && <div className="error-banner">{error}</div>}
        <label className="native-field">
          <span>调试模式</span>
          <select value={debugPatternId} onChange={(e) => setDebugPatternId(e.target.value as "" | PatternId)}>
            <option value="">自动识别全部杀法</option>
            <option value="CROWNED_CHECKMATE">仅平顶冠</option>
            <option value="EUNUCHS_CHASING_EMPEROR_CHECKMATE">仅太监追皇帝</option>
            <option value="CENTROID_PAWN_CHECKMATE">仅花心兵</option>
            <option value="CANNONS_SANDWICHING_CHARIOT_CHECKMATE">仅夹车炮</option>
            <option value="DOUBLE_CANNON_CHECKMATE">仅重炮杀</option>
            <option value="DOUBLE_TOAST_CHECKMATE">仅双杯献酒</option>
            <option value="SMOTHERED_CANNON_CHECKMATE">仅闷宫杀</option>
            <option value="HEAVEN_AND_EARTH_CANNON_CHECKMATE">仅天地炮</option>
            <option value="IRON_BOLT_CHECKMATE">仅铁门栓</option>
            <option value="DRAWER_CHECKMATE">仅进洞出洞</option>
            <option value="THROAT_CUTTING_CHECKMATE">仅大胆穿心</option>
            <option value="THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE">仅三车闹士</option>
            <option value="TWO_DEVILS_KNOCKING_CHECKMATE">仅双鬼拍门</option>
            <option value="DOUBLE_CHARIOTS_CHECKMATE">仅双车错</option>
            <option value="DISCOVERED_HORSE_CHECKMATE">仅拔簧马</option>
            <option value="CENTROID_CHARIOT_CHECKMATE">仅花心车</option>
            <option value="TIGER_SILHOUETTE_CHECKMATE">仅侧面虎</option>
            <option value="HORSE_CANNON_CHECKMATE">仅马后炮</option>
            <option value="DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE">仅双马饮泉</option>
            <option value="DOUBLE_CHECK_CHECKMATE">仅双将</option>
            <option value="ELBOW_HORSE_CHECKMATE">仅卧槽马</option>
            <option value="PALCORNER_HORSE_CHECKMATE">仅挂角马</option>
            <option value="ANGLER_HORSE_CHECKMATE">仅钓鱼马</option>
            <option value="SMOTHERED_CHECKMATE">仅闷杀</option>
            <option value="WHITE_FACE_GENERAL">仅白脸将</option>
            <option value="STALEMATE">仅困毙</option>
          </select>
        </label>
        <label className="native-field">
          <span>起始 FEN</span>
          <Textarea rows={3} value={baseFen} onChange={(_, d) => setBaseFen(d.value)} />
        </label>
        <label className="native-field">
          <span>走法序列</span>
          <Textarea
            rows={3}
            value={moveText}
            onChange={(_, d) => setMoveText(d.value)}
            placeholder="e6d6 或 e6d6 b7d7 d7d8"
          />
        </label>
        <div className="action-row">
          <Button appearance="outline" onClick={replayMovesToBoard} disabled={busy || boardBusy}>
            重播走法到棋盘
          </Button>
          <Button appearance="primary" onClick={analyze} disabled={busy || boardBusy}>
            自动识别杀法
          </Button>
        </div>
      </section>

      <section className="panel pattern-result">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">BOARD</span>
            <h2>棋盘联动</h2>
          </div>
          {boardSession && (
            <Badge appearance="outline">
              {boardSession.state.fen.split(" ")[1] === "w" ? "轮到红方" : "轮到黑方"}
            </Badge>
          )}
        </div>
        {boardBusy || !boardSession ? (
          <div className="loading-state">
            <Spinner label="正在同步棋盘" />
          </div>
        ) : (
          <>
            <XiangqiBoard
              fen={boardSession.state.fen}
              legalMoves={boardSession.legalMoves}
              lastMove={lastMove}
              disabled={busy}
              onMove={playOnBoard}
            />
            <div className="fen-strip">
              <span>当前 FEN</span>
              <code>{boardSession.state.fen}</code>
            </div>
          </>
        )}
      </section>

      <section className="panel pattern-result">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">RESULT</span>
            <h2>识别结果</h2>
          </div>
          {result && (
            <Badge color={result.bestMatch ? "success" : "danger"}>
              {result.bestMatch ? `命中 ${result.matches.length} 类` : "未命中已接入杀法"}
            </Badge>
          )}
        </div>
        {!result ? (
          <div className="empty-state">输入局面后点击自动识别，或先在棋盘上走子。</div>
        ) : (
          <>
            <div className="pattern-summary">
              <strong>
                {result.bestMatch
                  ? PATTERN_LABELS[result.bestMatch.patternId] ?? result.bestMatch.patternNameZh
                  : "未识别"}
              </strong>
              <span>
                {result.analysis.isCheckmate
                  ? "已将死"
                  : result.analysis.isStalemate
                    ? "已困毙"
                    : result.analysis.isCheck
                      ? "正在将军"
                      : "没有将军"}
              </span>
            </div>
            <div className="shape-row">
              <span>局面</span>
              <div>
                <code>合法着法：{result.analysis.legalMoves.length}</code>
                <code>将军：{result.analysis.isCheck ? "是" : "否"}</code>
                <code>困毙：{result.analysis.isStalemate ? "是" : "否"}</code>
              </div>
            </div>
            <div className="shape-row">
              <span>最佳命中</span>
              <div>
                {result.bestMatch ? (
                  <>
                    <code>
                      {PATTERN_LABELS[result.bestMatch.patternId] ?? result.bestMatch.patternNameZh}
                    </code>
                    <code>{result.bestMatch.patternId}</code>
                  </>
                ) : (
                  <em>当前未命中已接入杀法</em>
                )}
              </div>
            </div>
            <div className="shape-row">
              <span>命中列表</span>
              <div>
                {result.matches.length ? (
                  result.matches.map((match) => (
                    <code key={match.patternId}>
                      {PATTERN_LABELS[match.patternId]} · {match.patternId}
                    </code>
                  ))
                ) : (
                  <em>没有命中任何已接入 pattern</em>
                )}
              </div>
            </div>
            <div className="shape-row">
              <span>将军来源</span>
              <div>
                {result.analysis.checkingPieces.length ? (
                  result.analysis.checkingPieces.map((p) => (
                    <code key={`${p.square}-${p.reason}`}>{p.square} · {p.reason}</code>
                  ))
                ) : (
                  <em>没有找到将军棋子</em>
                )}
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
