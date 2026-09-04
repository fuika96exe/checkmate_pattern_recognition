"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import {
  ArrowPreviousRegular,
  ArrowNextRegular,
  PlayRegular,
  PauseRegular,
  TopSpeedRegular,
  DocumentCopyRegular,
  DeleteRegular,
} from "@fluentui/react-icons";
import { importXiangqiGame, applyMove, START_FEN, parseFen } from "../lib/notation-import";
import type { ImportResult } from "../lib/notation-import/types";
import { XiangqiBoard } from "./XiangqiBoard";
import type { MoveRecord } from "../lib/types";

// 预设测试用例样例库
const PRESET_EXAMPLES: Record<string, { label: string; text: string }> = {
  dpxq_text: {
    label: "东萍纯文本 (Case 1)",
    text: `标题: 北京 刘永富 负 北京 张永生
分类: 其他赛事
赛事: 2026年第137届龙马鹏程大兴月赛
轮次: 第07轮
布局: B00 中炮局
红方: 北京 刘永富
黑方: 北京 张永生
结果: 黑方胜
日期: 2026.08.31
地点: 北京市大兴区大悦春风里1层
记时规则: 15分＋5秒
棋局类型: 全局
棋局性质: 慢棋
红方团体: 北京
红方姓名: 刘永富
黑方团体: 北京
黑方姓名: 张永生
棋谱主人: ryueifu
来源网站: http://www.dpxq.com/
 
  1.炮二平五      士６进５  
  2.马二进三      炮８平４  
  3.车一平二      马８进７  
  4.兵三进一      象７进５  
  5.马八进九      车９平６  
  6.炮八平七      马２进１  
  7.车九平八      车１平２  
  8.车八进四      卒１进１  
  9.马三进四      炮２进２  
 10.仕四进五      炮２平３  
 11.车八进五      马１退２  
 12.炮七进三      车６进５  
 13.炮七平二      车６退５  
 14.炮二平八      马２进１  
 15.炮八进二      车６进４  
 16.炮八退五      马１进２  
 17.炮五平三      马２进３  
 18.炮八平七      马３退４  
 19.车二进三      马４进２  
 20.炮七平六      车６进４  
 21.炮六退一      车６退３  
 22.相三进五      炮４进４  
 23.车二进四      炮４退４  
 24.炮六平七      车６进１  
 25.炮七进八      象５退３  
 26.车二平三      车６平５  
 27.车三进二      士５退６  
 28.车三退三      马２退４  
 29.炮三平二      车５平８  
 30.车三平五      炮４平５  
 31.炮二平四      马４进６  
 32.车五退二      马６进７  
 33.兵三进一      士４进５  
 34.兵一进一      卒３进１  
 35.相五退三      车８进３  
 36.相七进五      卒３进１  
 37.炮四退二      车８退４  
 38.车五平二      马７退８  
 39.炮四进四      马８进６  
 40.兵三平四      卒３平４  
 41.马九进七      炮５平９  
 42.兵九进一      卒１进１  
 43.炮四平九      马６进７  
 44.帅五平四      炮９平６  
 45.兵四平五      马７退６  
 46.兵五平四      马６进７  
 47.兵四平五      卒４进１  
 48.马七进六      马７退６  
 49.兵五平四      马６退４  
 50.兵四平五      卒４平５  
 51.相五进七      马４进６  
 52.兵五平四      马６进７  
 53.兵四平五      卒５平６  
 54.兵五平四  
 
棋谱由 http://www.dpxq.com/ 生成`,
  },
  dpxq_ubb: {
    label: "东萍 UBB 代码 (Case 2)",
    text: `[DhtmlXQ]
[DhtmlXQ_ver]www_dpxq_com[/DhtmlXQ_ver]
[DhtmlXQ_init]500,350[/DhtmlXQ_init]
[DhtmlXQ_binit]8979695949392919097717866646260600102030405060708012720323436383[/DhtmlXQ_binit]
[DhtmlXQ_title]北京 刘永富 负 北京 张永生[/DhtmlXQ_title]
[DhtmlXQ_movelist]77475041796772328979706266656042190780501727100209190010191503046755121459481424151002102724505524745550741410021412505412170214476714261727263479763415273754583738585569473236767236323828555628204220726256466260415060631534677746766343324277573455434555676564304186852324476976792947242557597975457567755955755664542535072642820605040555055668495982525444685644545668544435362634685644545635544436464725355644545668544446564454[/DhtmlXQ_movelist]
[DhtmlXQ_event]2026年第137届龙马鹏程大兴月赛[/DhtmlXQ_event]
[DhtmlXQ_red]北京 刘永富[/DhtmlXQ_red]
[DhtmlXQ_black]北京 张永生[/DhtmlXQ_black]
[DhtmlXQ_result]黑胜[/DhtmlXQ_result]
[/DhtmlXQ]`,
  },
  pgn_handicap: {
    label: "让九子残局 PGN (Case 3)",
    text: `[Game "Chinese Chess"]
[Event "许银川让九子对聂棋圣"]
[Site "广州"]
[Date "1999.12.09"]
[Red "许银川"]
[Black "聂卫平"]
[Result "1-0"]
[FEN "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/9/1C5C1/9/RN2K2NR r - - 0 1"]
{评注：许银川让去５只兵和双士双相，执红先行。}

1. 炮八平五 炮８平５
{红方首着架中炮必走之着，聂棋圣还架中炮拼兑子力，战术对头。}
2. 炮五进五 象７进５ 3. 炮二平五
马８进７ 4. 马二进三 车９平８ 5. 马八进七 马２进１ 6. 车九平六 车１平２
7. 车六进八 炮２进７ 8. 车一进四 炮２平１ 9. 马七进八 炮１退４ 10. 马八退七 炮１进４ 11. 马七进八 车２进２
12. 炮五平八 炮１退４ 13. 炮八进五 炮１平９ 14. 炮八平三 车８进２ 15. 炮三进一 车８进２ 16. 马八进六 炮９平５
17. 炮三平一 士６进５ 18. 马六进四 车８平５ 19. 帅五平六 车５平６ 20. 马四进三 将５平６ 21. 车六退四 卒５进１
22. 车六进二 炮５平７ 23. 前马退二 象５进７ 24. 马二退三 卒５进１ 25. 车六平三 卒５平６ 26. 车三进三 将６进１
27. 后马进二 士５进６ 28. 马二进三 将６平５ 29. 前马进二 将５进１ 30. 车三平六 士６退５ 31. 马二退三 车６退１
32. 车六退三 车６平７ 33. 车六平三 卒６平７ 34. 车三平五 将５平６ 35. 帅六平五 将６退１ 36. 车五进二 将６退１
37. 车五进一 将６进１ 38. 车五平七
1-0`,
  },
  iccs: {
    label: "台湾棋王赛 ICCS (Case 4)",
    text: `[Game "Chinese Chess"]
[Title "謝承宇先負陳國興3"]
[Event "啟泰趣笑第四屆臺灣象棋棋王賽-四強賽"]
[Red "謝承宇"]
[Black "陳國興"]
[Opening "过宫炮局"]
[Format "ICCS"]
1. H2-D2 G6-G5
2. H0-G2 H9-G7
3. I0-H0 I9-H9
4. H0-H4 H7-I7
5. H4-F4 B7-D7
6. B0-A2 B9-C7
7. C3-C4 A9-B9
8. A0-B0 B9-B5
9. B2-C2 B5-D5
10. D2-D7 D5-D7
11. C0-E2 H9-H3
12. G3-G4 H3-G3
13. G4-G5 G3-G5
14. D0-E1 C9-E7
15. B0-B6 G7-H5
16. G2-H4 D9-E8
17. B6-C6 G5-B5
18. F4-F5 B5-B2
19. C6-C7 D7-D1
20. C7-C6 B2-C2
21. E1-D0 H5-G7
22. H4-G6 I7-I3
23. F0-E1 C2-A2
24. F5-F8 D1-D7
25. C6-B6 I3-I0
26. G0-I2 A2-E2
27. B6-B9 E8-D9
 *`,
  },
  wxf: {
    label: "PlayOK WXF 格式 (Case 5)",
    text: `FORMAT  WXF
RED     tmt6838g ; 1137 ;;
BLACK   computerhuang ; 1177 ;;
RESULT  1-0
DATE    2026-09-03 16:20:58
EVENT   PlayOK Game ; 10m+0s
START{
 1. C8.5 c2.5   2. H8+7 h2+3   3. R9.8 r1+1
 4. P5+1 r1.6   5. H2+3 p3+1   6. R8+4 r6+3
 7. P3+1 h8+7   8. H7+5 r6+2   9. C2+2 h3+4
10. R8.6 h4-6  11. P5+1 p5+1  12. H5+6 h6+4
13. R6+1 a6+5  14. R6.5 r6.7  15. R1+2 r7.3
16. H3+4 r3.8  17. H4+3 p9+1  18. C2+1 r9+3
19. P3+1 e7+9  20. R1.3 p9+1  21. P1+1 r9+2
22. C2.1 r8-3  23. C1.2 c8+2  24. P3.2 r8+1
25. C5+5 e3+5  26. R5.2 r9.5  27. R3.5 r5+2
28. E3+5 }END`,
  },
  same_bishop: {
    label: "同列相消歧 PGN (Case 6)",
    text: `[Game "Chinese Chess"]
1. 兵三进一 卒３进１
2. 马二进三 马２进３
3. 车一进一 象３进５
4. 相七进五 马８进９
5. 车一平七 卒９进１
6. 兵七进一 炮８平７
7. 兵七进一 车９平８
8. 炮二进二 卒７进１
9. 兵七进一 马３退５
10. 车七进三 卒９进１
11. 兵一进一 车１平３
12. 炮八退一 马９进７
13. 炮八平二 车８平９
14. 兵三进一 象５进７
15. 前炮平三 马７进５
16. 车七平五 后马进６
17. 车五平四 炮７进３
18. 车四进二 士４进５
19. 相五进三 马５进４
20. 马八进六 炮２平４
21. 车九进一 车９进５
22. 相三进五 车３进３
23. 炮二进五 炮４退２
24. 炮二平五 士５进６
25. 马三进四 车９进３
26. 仕四进五 车９平６
27. 车九平八 炮４平３
28. 车八进六 车３平４
29. 车八平七 炮３平２
30. 车七进二 将５进１
31. 车七平八 马４退３
32. 车八退一 车４退２
33. 车八平六 将５平４
34. 炮五退一 马３退４
35. 马四进五 将４退１
36. 车四退五 马４进５
37. 车四进六 将４平５
38. 兵五进一 马５退７
39. 车四平三 马７退９
40. 车三进二 马９进８
41. 马五退三 马８退９
42. 马三进四 将５进１
43. 兵五进一 将５平６
44. 马四退六 士６进５
45. 兵五进一 马９进７
46. 车三退三 将６退１
47. 车三进三 将６进１
48. 兵五进一 士５进４
49. 兵五平四 将６平５
50. 兵四平五 将５平６
51. 后马进五 卒１进１
52. 马五进四 卒１进１
53. 马四进三 卒１平２
54. 车三平四 1-0`,
  },
  compact: {
    label: "紧凑无空格纯文本 (Case 7)",
    text: `1.兵七进一炮2平32.兵三进一炮8平53.马二进三马8进74.马八进七车9平85.车一平二马2进16.车九平八车8进47.炮二平一车8进58.马三退二车1平29.马二进三车2进410.炮八平九车2平811.马七进六卒7进112.兵三进一车8平713.相七进五卒1进114.车八进四车7平415.兵七进一卒3进116.炮一退一马1进317.马三进四卒3进118.马四进六卒3平219.马六进五马3进420.马五进七将5进121.炮九进三将5平622.仕六进五马7进623.炮一平四马6进524.仕五进四马5退625.炮九进一士6进526.炮九平一士5进627.马七进五马6退828.马五退六象3进529.炮一退二马8进930.兵一进一将6退1`,
  },
};

export function NotationImportLab() {
  const [inputText, setInputText] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const playTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 计算每一步的历史局面 FEN 序列
  const positions = useMemo(() => {
    if (!importResult || !importResult.success || importResult.moves.length === 0) {
      return [importResult?.initialFen || START_FEN];
    }
    const list = [importResult.initialFen];
    let cur = importResult.initialFen;
    for (const uci of importResult.moves) {
      try {
        cur = applyMove(cur, uci);
        list.push(cur);
      } catch {
        break;
      }
    }
    return list;
  }, [importResult]);

  const currentFen = positions[stepIndex] || START_FEN;

  const currentMoveRecord = useMemo<MoveRecord | undefined>(() => {
    if (!importResult || stepIndex === 0 || !importResult.moves[stepIndex - 1]) {
      return undefined;
    }
    const uci = importResult.moves[stepIndex - 1];
    const prevFen = positions[stepIndex - 1];
    const side = prevFen ? (prevFen.split(" ")[1] === "b" ? "black" : "red") : "red";
    return {
      ply: stepIndex,
      side,
      ucci: uci,
      chineseNotation: importResult.chineseMoves[stepIndex - 1] || uci,
      fromSquare: uci.slice(0, 2),
      toSquare: uci.slice(2, 4),
    };
  }, [importResult, stepIndex, positions]);

  // 执行导入解析
  function handleParse(textToParse = inputText) {
    setIsPlaying(false);
    if (!textToParse.trim()) {
      setImportResult(null);
      return;
    }
    const res = importXiangqiGame(textToParse);
    setImportResult(res);
    setStepIndex(0);
  }

  // 加载预设用例
  function loadPreset(key: string) {
    const preset = PRESET_EXAMPLES[key];
    if (preset) {
      setInputText(preset.text);
      handleParse(preset.text);
    }
  }

  // 自动播放推演
  useEffect(() => {
    if (isPlaying) {
      playTimerRef.current = setTimeout(() => {
        if (stepIndex < positions.length - 1) {
          setStepIndex((prev) => prev + 1);
        } else {
          setIsPlaying(false);
        }
      }, 700);
    }
    return () => {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
    };
  }, [isPlaying, stepIndex, positions.length]);

  return (
    <div className="importer-lab-container" style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "12px" }}>
      {/* 顶部标题与说明 */}
      <section className="panel" style={{ background: "var(--card-bg, #fff)", padding: "16px", borderRadius: "8px", border: "1px solid #e0e0e0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "18px", fontWeight: 600 }}>棋譜導入測試工作台 (Xiangqi Notation Import Lab)</h2>
          <span style={{ fontSize: "12px", color: "#666" }}>支持 PGN / 东萍纯文本 / 东萍 UBB / ICCS / PlayOK WXF / 紧凑排版</span>
        </div>
        
        {/* 预设快捷测试按钮 */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "12px" }}>
          <span style={{ fontSize: "13px", fontWeight: 600, alignSelf: "center", color: "#555" }}>预设真实用例：</span>
          {Object.entries(PRESET_EXAMPLES).map(([key, item]) => (
            <Button
              key={key}
              size="small"
              appearance="secondary"
              onClick={() => loadPreset(key)}
            >
              {item.label}
            </Button>
          ))}
        </div>
      </section>

      {/* 文本输入与操作栏 */}
      <section className="panel" style={{ background: "var(--card-bg, #fff)", padding: "16px", borderRadius: "8px", border: "1px solid #e0e0e0" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label style={{ fontSize: "14px", fontWeight: 600 }}>棋谱原始文本 (输入或直接粘贴)：</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <Button
                size="small"
                icon={<DeleteRegular />}
                onClick={() => {
                  setInputText("");
                  setImportResult(null);
                  setStepIndex(0);
                }}
              >
                清空
              </Button>
              <Button
                size="small"
                appearance="primary"
                icon={<DocumentCopyRegular />}
                onClick={() => handleParse()}
              >
                解析并导入
              </Button>
            </div>
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={6}
            placeholder="在此粘贴任意格式的象棋棋谱文本 (如广东象棋网 PGN、东萍文本/UBB、天天象棋对局、ICCS、PlayOK WXF、无空格紧凑文本等)..."
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px",
              fontFamily: "monospace",
              fontSize: "13px",
              borderRadius: "6px",
              border: "1px solid #ccc",
              resize: "vertical",
            }}
          />
        </div>
      </section>

      {/* 解析结果状态栏 */}
      {importResult && (
        <section
          style={{
            background: importResult.success ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${importResult.success ? "#86efac" : "#fca5a5"}`,
            padding: "14px 18px",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <Badge color={importResult.success ? "success" : "danger"} size="large">
              {importResult.success ? "解析成功 (SUCCESS)" : "解析失败 (FAILED)"}
            </Badge>
            <Badge appearance="outline">识别格式: {importResult.format.toUpperCase()}</Badge>
            <strong>{importResult.title}</strong>
            <span style={{ fontSize: "13px", color: "#666" }}>
              共识别 <strong>{importResult.moves.length}</strong> 步着法
            </span>
            {importResult.result && (
              <Badge color="informative">终局结果: {importResult.result}</Badge>
            )}
          </div>

          {importResult.error && (
            <div style={{ color: "#b91c1c", fontSize: "13px", marginTop: "4px" }}>
              <strong>错误详情:</strong> {importResult.error}
            </div>
          )}

          {/* 元数据展示 */}
          {Object.keys(importResult.headers).length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", fontSize: "12px", color: "#555", marginTop: "4px" }}>
              {importResult.headers.Event && <span>赛事: {importResult.headers.Event}</span>}
              {importResult.headers.Date && <span>日期: {importResult.headers.Date}</span>}
              {importResult.headers.Red && <span>红方: {importResult.headers.Red}</span>}
              {importResult.headers.Black && <span>黑方: {importResult.headers.Black}</span>}
            </div>
          )}
        </section>
      )}

      {/* 棋盘推演与走子列表双栏展示 */}
      {importResult && importResult.success && importResult.moves.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "20px", alignItems: "start" }}>
          {/* 左栏：棋盘与步数控制 */}
          <section
            style={{
              background: "var(--card-bg, #fff)",
              padding: "16px",
              borderRadius: "8px",
              border: "1px solid #e0e0e0",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
            }}
          >
            {/* 推演操作栏 */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px", width: "100%", justifyContent: "space-between" }}>
              <div>
                <span style={{ fontSize: "13px", color: "#666" }}>步数: </span>
                <strong>{stepIndex}</strong> / {positions.length - 1}
              </div>
              <div style={{ display: "flex", gap: "4px" }}>
                <Button
                  size="small"
                  aria-label="回到开局"
                  icon={<ArrowPreviousRegular />}
                  disabled={stepIndex === 0}
                  onClick={() => setStepIndex(0)}
                />
                <Button
                  size="small"
                  aria-label="上一步"
                  disabled={stepIndex === 0}
                  onClick={() => setStepIndex((prev) => Math.max(0, prev - 1))}
                >
                  ◀
                </Button>
                <Button
                  size="small"
                  appearance="primary"
                  icon={isPlaying ? <PauseRegular /> : <PlayRegular />}
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? "暂停" : "播放"}
                </Button>
                <Button
                  size="small"
                  aria-label="下一步"
                  disabled={stepIndex >= positions.length - 1}
                  onClick={() => setStepIndex((prev) => Math.min(positions.length - 1, prev + 1))}
                >
                  ▶
                </Button>
                <Button
                  size="small"
                  aria-label="终局"
                  icon={<ArrowNextRegular />}
                  disabled={stepIndex >= positions.length - 1}
                  onClick={() => setStepIndex(positions.length - 1)}
                />
              </div>
            </div>

            {/* 当前着法高亮提示 */}
            <div
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "8px 12px",
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                borderRadius: "6px",
                fontSize: "14px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span style={{ color: "#64748b" }}>当前回合：</span>
                {stepIndex === 0 ? (
                  <em>初始局面</em>
                ) : (
                  <span>
                    第 {Math.ceil(stepIndex / 2)} 回合 ·{" "}
                    <strong style={{ color: stepIndex % 2 === 1 ? "#dc2626" : "#1e293b" }}>
                      {stepIndex % 2 === 1 ? "红方" : "黑方"}
                    </strong>{" "}
                    <strong>{importResult.chineseMoves[stepIndex - 1]}</strong>{" "}
                    <code style={{ fontSize: "12px", color: "#6b7280" }}>({importResult.moves[stepIndex - 1]})</code>
                  </span>
                )}
              </div>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                轮到: <strong style={{ color: currentFen.split(" ")[1] === "w" ? "#dc2626" : "#1e293b" }}>
                  {currentFen.split(" ")[1] === "w" ? "红方" : "黑方"}
                </strong>
              </span>
            </div>

            {/* 棋盘渲染 */}
            <div style={{ width: "380px" }}>
              <XiangqiBoard
                fen={currentFen}
                legalMoves={[]}
                lastMove={currentMoveRecord}
                disabled={true}
                onMove={() => {}}
              />
            </div>

            {/* FEN 串 */}
            <div style={{ width: "100%", fontSize: "11px", color: "#666", overflowX: "auto" }}>
              <span>FEN: </span>
              <code style={{ background: "#eee", padding: "2px 4px", borderRadius: "3px" }}>{currentFen}</code>
            </div>
          </section>

          {/* 右栏：双列着法记录表，支持任意步骤点击跳转 */}
          <section
            className="panel"
            style={{
              background: "var(--card-bg, #fff)",
              padding: "16px",
              borderRadius: "8px",
              border: "1px solid #e0e0e0",
              maxHeight: "680px",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h3 style={{ margin: "0 0 12px 0", fontSize: "15px", fontWeight: 600 }}>对局着法列表 (点击任意步跳转)</h3>
            <div style={{ overflowY: "auto", flex: 1, paddingRight: "4px" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                <thead>
                  <tr style={{ background: "#f1f5f9", borderBottom: "1px solid #cbd5e1", textAlign: "left" }}>
                    <th style={{ padding: "6px 8px", width: "45px" }}>序号</th>
                    <th style={{ padding: "6px 8px" }}>红方</th>
                    <th style={{ padding: "6px 8px" }}>黑方</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: Math.ceil(importResult.moves.length / 2) }).map((_, roundIdx) => {
                    const redIdx = roundIdx * 2;
                    const blackIdx = roundIdx * 2 + 1;
                    const isRedActive = stepIndex === redIdx + 1;
                    const isBlackActive = stepIndex === blackIdx + 1;

                    return (
                      <tr key={roundIdx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "6px 8px", color: "#94a3b8", fontWeight: 500 }}>{roundIdx + 1}.</td>
                        
                        {/* 红方走子 */}
                        <td
                          onClick={() => setStepIndex(redIdx + 1)}
                          style={{
                            padding: "6px 8px",
                            cursor: "pointer",
                            fontWeight: isRedActive ? 700 : 400,
                            background: isRedActive ? "#fee2e2" : "transparent",
                            color: isRedActive ? "#b91c1c" : "inherit",
                            borderRadius: "4px",
                          }}
                        >
                          {importResult.chineseMoves[redIdx]}
                        </td>

                        {/* 黑方走子 */}
                        <td
                          onClick={() => blackIdx < importResult.moves.length && setStepIndex(blackIdx + 1)}
                          style={{
                            padding: "6px 8px",
                            cursor: blackIdx < importResult.moves.length ? "pointer" : "default",
                            fontWeight: isBlackActive ? 700 : 400,
                            background: isBlackActive ? "#e2e8f0" : "transparent",
                            color: isBlackActive ? "#0f172a" : "inherit",
                            borderRadius: "4px",
                          }}
                        >
                          {blackIdx < importResult.moves.length ? importResult.chineseMoves[blackIdx] : ""}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
