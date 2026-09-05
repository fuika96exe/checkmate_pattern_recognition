"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import {
  ArrowPreviousRegular,
  ArrowNextRegular,
  PlayRegular,
  PauseRegular,
  DocumentCopyRegular,
  DeleteRegular,
} from "@fluentui/react-icons";
import { importXiangqiGame, applyMove, START_FEN } from "../lib/notation-import";
import type { GameBranch, ImportResult } from "../lib/notation-import/types";
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
  dpxq_branches: {
    label: "弈林新编 23变着与评注 (Case 15)",
    text: `[DhtmlXQ]
[DhtmlXQ_ver]www_dpxq_com[/DhtmlXQ_ver]
[DhtmlXQ_init]500,350[/DhtmlXQ_init]
[DhtmlXQ_binit]8979695949392919097717866646260600102030405060708012720323436383[/DhtmlXQ_binit]
[DhtmlXQ_pver]130606[/DhtmlXQ_pver]
[DhtmlXQ_adddate]2008-02-24 22:50:01[/DhtmlXQ_adddate]
[DhtmlXQ_editdate]2008-02-24 22:50:00[/DhtmlXQ_editdate]
[DhtmlXQ_title]中炮巡河炮对屏风马(一)[/DhtmlXQ_title]
[DhtmlXQ_movelist]774770627967102289798070262563641927204217157274666512117976116165646164675530412735001009191013594864655534232434222425223413143453742476701415707515192907656475654344354362435361403047374445654524214535213135331911614225354223111337676404334304074959[/DhtmlXQ_movelist]
[DhtmlXQ_move_0_48_1]24216535213135334362331325351319313761426042191030314837[/DhtmlXQ_move_0_48_1]
[DhtmlXQ_move_1_52_2]19116173[/DhtmlXQ_move_1_52_2]
[DhtmlXQ_move_0_43_3]47444030[/DhtmlXQ_move_0_43_3]
[DhtmlXQ_move_0_39_4]3527656475656082652524272527[/DhtmlXQ_move_0_39_4]
[DhtmlXQ_move_4_44_5]1929476724276947[/DhtmlXQ_move_4_44_5]
[DhtmlXQ_move_0_37_6]190962705361403047372434352734042715040915236564[/DhtmlXQ_move_0_37_6]
[DhtmlXQ_move_0_34_7]6564355670737674[/DhtmlXQ_move_0_34_7]
[DhtmlXQ_move_0_34_8]656335436343536140304737[/DhtmlXQ_move_0_34_8]
[DhtmlXQ_move_8_36_9]25154322[/DhtmlXQ_move_8_36_9]
[DhtmlXQ_move_0_31_10]354362432243651543627414[/DhtmlXQ_move_0_31_10]
[DhtmlXQ_move_0_26_11]43445574707476746274474464656947[/DhtmlXQ_move_0_26_11]
[DhtmlXQ_move_0_22_12]232425240030152530352522[/DhtmlXQ_move_0_22_12]
[DhtmlXQ_move_0_20_13]00100919101427357073252414241513643413113439493924253543224355436243474373437674[/DhtmlXQ_move_0_20_13]
[DhtmlXQ_move_13_32_14]73537675242539492535557435757453[/DhtmlXQ_move_13_32_14]
[DhtmlXQ_move_13_30_15]30412907[/DhtmlXQ_move_13_30_15]
[DhtmlXQ_move_13_27_16]15102210354324544362545519105535[/DhtmlXQ_move_13_27_16]
[DhtmlXQ_move_13_22_17]232425247424767062702735[/DhtmlXQ_move_13_22_17]
[DhtmlXQ_move_0_20_18]23242524422415252442091930412735747519127535767062701222642429077062474324542223[/DhtmlXQ_move_0_20_18]
[DhtmlXQ_move_18_27_19]19122234553474347670627047430020294720234344[/DhtmlXQ_move_18_27_19]
[DhtmlXQ_move_18_24_20]223455347434767062704743[/DhtmlXQ_move_18_24_20]
[DhtmlXQ_move_18_22_21]7424767062702735001009193041354322435543[/DhtmlXQ_move_18_22_21]
[DhtmlXQ_move_21_28_22]70621511[/DhtmlXQ_move_21_28_22]
[DhtmlXQ_move_0_15_23]656411717974[/DhtmlXQ_move_0_15_23]
[DhtmlXQ_firstnum]0[/DhtmlXQ_firstnum]
[DhtmlXQ_length]232[/DhtmlXQ_length]
[DhtmlXQ_type]全局[/DhtmlXQ_type]
[DhtmlXQ_gametype]慢棋[/DhtmlXQ_gametype]
[DhtmlXQ_other]中炮巡河炮对屏风马(一) [/DhtmlXQ_other]
[DhtmlXQ_open]C84 中炮巡河炮对屏风马 黑飞右象[/DhtmlXQ_open]
[DhtmlXQ_class]象棋谱大全-现代棋书专集[/DhtmlXQ_class]
[DhtmlXQ_event]弈林新编-杨官璘著[/DhtmlXQ_event]
[DhtmlXQ_round]4.布局研究[/DhtmlXQ_round]
[DhtmlXQ_date]0000-00-00[/DhtmlXQ_date]
[DhtmlXQ_result]红胜[/DhtmlXQ_result]
[DhtmlXQ_remark]杨官璘[/DhtmlXQ_remark]
[DhtmlXQ_hits]11782[/DhtmlXQ_hits]
[DhtmlXQ_sortid]695550[/DhtmlXQ_sortid]
[DhtmlXQ_owner]象棋谱大全[/DhtmlXQ_owner]
[DhtmlXQ_oldowner]象棋谱大全[/DhtmlXQ_oldowner]
[DhtmlXQ_comment0]《弈林新编》杨官璘编著||||||中炮巡河炮对屏风马||||中炮巡河炮又称为“五八炮巡河”，是常见的一种布局。这个布局的变化比较广泛，如中炮过河车对屏风马横车左相、及中炮直车对屏风马进炮封车等变化，也可以演变成中炮巡河炮的形势。||||现在，这里所介绍的形势，在先手方面主要是左炮先巡河，右车伺机进取的变化。在屏风马方面，大致有：左炮巡河、右炮巡河、兑三路兵、平右车等类型的应着。这些应着的变化，都是非常复杂的。||||它的特点是：当头炮方面较有稳健持久的先手攻势，但攻势比较缓慢。[/DhtmlXQ_comment0]
[DhtmlXQ_comment19]如图局势，黑方可走：(一)士4进5，(二)车1平2，(三)兵3进1，兹将三种着法，演变如下：[/DhtmlXQ_comment19]
[DhtmlXQ_comment25]巩固中路，并伏有伺机进取，是好的停着。[/DhtmlXQ_comment25]
[DhtmlXQ_comment63]红方稍占先手。[/DhtmlXQ_comment63]
[DhtmlXQ_comment1_61]红方优势。[/DhtmlXQ_comment1_61]
[DhtmlXQ_comment2_53]红方先手。[/DhtmlXQ_comment2_53]
[DhtmlXQ_comment3_44]局势比较平稳。[/DhtmlXQ_comment3_44]
[DhtmlXQ_comment4_45]红方略先。[/DhtmlXQ_comment4_45]
[DhtmlXQ_comment5_47]红方先手。[/DhtmlXQ_comment5_47]
[DhtmlXQ_comment6_48]局势平稳。[/DhtmlXQ_comment6_48]
[DhtmlXQ_comment7_37]兑子之后红方易走。[/DhtmlXQ_comment7_37]
[DhtmlXQ_comment8_39]红方优势。[/DhtmlXQ_comment8_39]
[DhtmlXQ_comment9_37]红方先手。[/DhtmlXQ_comment9_37]
[DhtmlXQ_comment10_36]兑子之后黑方先手。[/DhtmlXQ_comment10_36]
[DhtmlXQ_comment11_26]改走卒5进1比较平稳。[/DhtmlXQ_comment11_26]
[DhtmlXQ_comment11_33]红方较优。[/DhtmlXQ_comment11_33]
[DhtmlXQ_comment12_27]红方优势。[/DhtmlXQ_comment12_27]
[DhtmlXQ_comment13_28]如改走车3进1，则红方进马抢中兵，红方优势。[/DhtmlXQ_comment13_28]
[DhtmlXQ_comment13_39]红方优势。[/DhtmlXQ_comment13_39]
[DhtmlXQ_comment14_39]红方得子占优。[/DhtmlXQ_comment14_39]
[DhtmlXQ_comment15_31]避免黑车牵制，下一步红有车八进七捉马，红方先手。[/DhtmlXQ_comment15_31]
[DhtmlXQ_comment16_34]各有顾忌。[/DhtmlXQ_comment16_34]
[DhtmlXQ_comment17_27]红方先手。[/DhtmlXQ_comment17_27]
[DhtmlXQ_comment18_39]红方优势。[/DhtmlXQ_comment18_39]
[DhtmlXQ_comment19_37]红方稍占优。[/DhtmlXQ_comment19_37]
[DhtmlXQ_comment20_29]红方优势。[/DhtmlXQ_comment20_29]
[DhtmlXQ_comment21_31]红方优势。[/DhtmlXQ_comment21_31]
[DhtmlXQ_comment22_29]红方先手。[/DhtmlXQ_comment22_29]
[DhtmlXQ_comment23_17]演成“车换马炮局”，在中局研究栏里已有详载。[/DhtmlXQ_comment23_17]
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
  huaian: {
    label: "淮安机关赛 (Case 10: 布局含中炮进三兵)",
    text: `标题: 市邮政局 高智彬 负 市教育局 赵迎
分类: 其他赛事
赛事: 2006年淮安市第一届全民健身运动会机关部暨市级机关第十八届运动会象棋比赛
轮次: 第07轮
布局: D36 中炮进三兵对左炮封车转列炮 红两头蛇
红方: 市邮政局 高智彬
黑方: 市教育局 赵迎
结果: 黑方胜
日期: 2006.05.21
地点: 淮安市
记录: 赵迎
棋局类型: 全局
棋局性质: 慢棋
红方团体: 市邮政局
红方姓名: 高智彬
黑方团体: 市教育局
黑方姓名: 赵迎
棋谱主人: 东萍公司
棋谱价值: 1
浏览次数: 65
来源网站: 赵迎棋牌视界
 
  1.炮二平五      马８进７  
  2.马二进三      车９平８  
  3.车一平二      炮８进４  
  4.兵三进一      炮２平５  
  5.兵七进一      马２进３  
  6.马八进七      车１平２  
  7.车九平八      车２进４  
  8.炮八平九      车２平８  
  9.车八进六      炮８平７  
 10.车二平一      炮５平６  
 11.兵五进一      士６进５  
 12.马七进五      象７进５  
 13.兵五进一      卒５进１  
 14.车八平七      后车进２  
 15.兵七进一      卒７进１  
 16.兵七平六      后车进１  
 17.车七平二      车８退１  
 18.兵六平五      卒７进１  
 19.马五进三      车８平７  
 20.相三进一      炮７平２  
 21.车一平二      马７退９  
 22.后马进五      车７平３  
 23.车二进八      炮２退５  
 24.车二进一      士５退６  
 25.炮九平七      车３进３  
 26.车二退八      士４进５  
 27.车二平八      炮２进５  
 28.马五进六      马３进４  
 29.兵五平六      炮２退４  
 30.炮七平九      车３退３  
 31.马三进五      炮２平３  
 32.车八进二      炮３进７  
 33.仕六进五      马９进８  
 34.炮九平六      炮３平１  
 35.仕五进四      炮６平８  
 36.车八平六      车３进６  
 37.帅五进一      车３退１  
 38.帅五退一      车３退３  
 39.车六平八      车３平５  
 40.帅五进一      马８进６  
 41.车八平四      炮８进５  
 42.帅五平六      车５进２  
 43.仕四进五      马６进５  
 44.帅六退一      马５进３  
 45.帅六平五      马３进２  
 46.炮六退二      马２退４  
 
棋谱由 http://www.dpxq.com/ 生成`,
  },
};

export function NotationImportLab() {
  const [inputText, setInputText] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [activeBranchId, setActiveBranchId] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const playTimerRef = useRef<NodeJS.Timeout | null>(null);
  const activeMoveRowRef = useRef<HTMLTableRowElement | null>(null);

  // 自动滚动活动着法到可视区域
  useEffect(() => {
    if (activeMoveRowRef.current) {
      activeMoveRowRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [stepIndex, activeBranchId]);

  // 当前选中的活动分支 (若无多分支则默认为主线)
  const activeBranch = useMemo<GameBranch | null>(() => {
    if (!importResult || !importResult.branches || importResult.branches.length === 0) {
      return null;
    }
    return (
      importResult.branches.find((b) => b.branchId === activeBranchId) ||
      importResult.branches[0]
    );
  }, [importResult, activeBranchId]);

  // 当前分支的走法序列
  const activeMoves = useMemo(() => {
    if (activeBranch) {
      return activeBranch.moves;
    }
    return importResult?.moves || [];
  }, [activeBranch, importResult]);

  // 当前分支的中文着法列表
  const activeChineseMoves = useMemo(() => {
    if (activeBranch) {
      return activeBranch.chineseMoves;
    }
    return importResult?.chineseMoves || [];
  }, [activeBranch, importResult]);

  // 当前分支的评注字典
  const activeComments = useMemo<Record<number, string>>(() => {
    if (activeBranch) {
      return activeBranch.comments;
    }
    return importResult?.comments || {};
  }, [activeBranch, importResult]);

  // 计算当前分支每一步的历史局面 FEN 序列
  const positions = useMemo(() => {
    if (!importResult || !importResult.success || activeMoves.length === 0) {
      return [importResult?.initialFen || START_FEN];
    }
    const list = [importResult.initialFen];
    let cur = importResult.initialFen;
    for (const uci of activeMoves) {
      try {
        cur = applyMove(cur, uci);
        list.push(cur);
      } catch {
        break;
      }
    }
    return list;
  }, [importResult, activeMoves]);

  const currentFen = positions[stepIndex] || START_FEN;

  const currentMoveRecord = useMemo<MoveRecord | undefined>(() => {
    if (!importResult || stepIndex === 0 || !activeMoves[stepIndex - 1]) {
      return undefined;
    }
    const uci = activeMoves[stepIndex - 1];
    const prevFen = positions[stepIndex - 1];
    const side = prevFen ? (prevFen.split(" ")[1] === "b" ? "black" : "red") : "red";
    return {
      ply: stepIndex,
      side,
      ucci: uci,
      chineseNotation: activeChineseMoves[stepIndex - 1] || uci,
      fromSquare: uci.slice(0, 2),
      toSquare: uci.slice(2, 4),
    };
  }, [importResult, stepIndex, activeMoves, activeChineseMoves, positions]);

  const ALPHABETS = useMemo(() => ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M'], []);

  // 收集对局中所有存在分支变着的步骤序号 (1-based ply)
  const allDivergencePlies = useMemo(() => {
    if (!importResult?.branches || importResult.branches.length <= 1) return [];
    const pliesSet = new Set<number>();
    for (const b of importResult.branches) {
      if (b.branchPly > 0) {
        pliesSet.add(b.branchPly);
      }
    }
    return Array.from(pliesSet).sort((a, b) => a - b);
  }, [importResult]);

  // 根据当前活动分支与谱树血缘，计算指定步骤在当前线路上对应的变着代号 (A, B, C...)
  const getVariantLetter = useCallback(
    (ply: number): string | undefined => {
      if (!allDivergencePlies.includes(ply)) return undefined;
      if (!importResult?.branches) return undefined;

      let b: GameBranch | undefined = activeBranch || importResult.branches[0];
      while (b && b.branchId !== 0) {
        if (b.branchPly === ply) {
          const siblings = importResult.branches.filter(
            (item) => item.parentBranchId === b!.parentBranchId && item.branchPly === ply
          );
          const idx = siblings.findIndex((item) => item.branchId === b!.branchId);
          if (idx >= 0) {
            return ALPHABETS[idx + 1] || `${idx + 2}`;
          }
        }
        b = importResult.branches.find((item) => item.branchId === b!.parentBranchId);
      }
      return 'A';
    },
    [allDivergencePlies, importResult, activeBranch, ALPHABETS]
  );

  // 双列着法映射（完美支持红先/黑先，并标记变着代号与评注图标）
  const moveRows = useMemo(() => {
    if (!importResult || !importResult.success || activeMoves.length === 0) {
      return [];
    }
    const rows: {
      round: number;
      redStepIndex?: number;
      redNotation?: string;
      redVariant?: string;
      redHasComment?: boolean;
      blackStepIndex?: number;
      blackNotation?: string;
      blackVariant?: string;
      blackHasComment?: boolean;
    }[] = [];
    const isInitialBlack = (importResult.initialFen.split(" ")[1] || "w") === "b";

    let currentRound = 1;
    let i = 0;

    if (isInitialBlack && activeMoves.length > 0) {
      rows.push({
        round: currentRound++,
        blackStepIndex: 1,
        blackNotation: activeChineseMoves[0],
        blackVariant: getVariantLetter(1),
        blackHasComment: Boolean(activeComments[1]),
      });
      i = 1;
    }

    while (i < activeMoves.length) {
      const redStepIndex = i + 1;
      const redNotation = activeChineseMoves[i];
      const redVariant = getVariantLetter(redStepIndex);
      const redHasComment = Boolean(activeComments[redStepIndex]);
      i++;
      let blackStepIndex: number | undefined;
      let blackNotation: string | undefined;
      let blackVariant: string | undefined;
      let blackHasComment = false;
      if (i < activeMoves.length) {
        blackStepIndex = i + 1;
        blackNotation = activeChineseMoves[i];
        blackVariant = getVariantLetter(blackStepIndex);
        blackHasComment = Boolean(activeComments[blackStepIndex]);
        i++;
      }
      rows.push({
        round: currentRound++,
        redStepIndex,
        redNotation,
        redVariant,
        redHasComment,
        blackStepIndex,
        blackNotation,
        blackVariant,
        blackHasComment,
      });
    }

    return rows;
  }, [importResult, activeMoves, activeChineseMoves, activeComments, getVariantLetter]);

  // 当前步骤处的备选变着列表 (类似 xiangqi.com 的 VariationsList: A. 主线, B. 变着13, C. 变着18)
  const currentStepVariations = useMemo(() => {
    if (!importResult?.branches || importResult.branches.length <= 1) return [];

    const targetPly =
      stepIndex > 0
        ? allDivergencePlies.includes(stepIndex)
          ? stepIndex
          : allDivergencePlies.includes(stepIndex + 1)
          ? stepIndex + 1
          : null
        : allDivergencePlies.includes(1)
        ? 1
        : null;

    if (!targetPly) return [];

    const branches = importResult.branches;
    const currentB = activeBranch || branches[0];

    // 寻找在 targetPly 处的父基准分支
    let curr: GameBranch | undefined = currentB;
    while (curr && curr.branchId !== 0 && curr.branchPly > targetPly) {
      curr = branches.find((b) => b.branchId === curr!.parentBranchId);
    }
    if (!curr) curr = branches[0];

    let baseBranchId = curr.branchId;
    if (curr.branchPly === targetPly) {
      baseBranchId = curr.parentBranchId;
    }

    const baseBranch = branches.find((b) => b.branchId === baseBranchId);
    if (!baseBranch) return [];

    const diverging = branches.filter(
      (b) => b.parentBranchId === baseBranchId && b.branchPly === targetPly
    );
    if (diverging.length === 0) return [];

    function isDescendantOrSelf(targetId: number, checkId: number): boolean {
      if (targetId === checkId) return true;
      let c: GameBranch | undefined = branches.find((b) => b.branchId === checkId);
      while (c && c.branchId !== 0) {
        if (c.parentBranchId === targetId) return true;
        c = branches.find((b) => b.branchId === c!.parentBranchId);
      }
      return false;
    }

    const options: Array<{
      variantLetter: string;
      branchId: number;
      notation: string;
      label: string;
      isSelected: boolean;
      ply: number;
    }> = [];

    const baseMoveChinese = baseBranch.chineseMoves[targetPly - 1] || "...";
    options.push({
      variantLetter: "A",
      branchId: baseBranchId,
      notation: baseMoveChinese,
      label: baseBranchId === 0 ? "主线" : `变着 ${baseBranchId}`,
      isSelected:
        isDescendantOrSelf(baseBranchId, currentB.branchId) &&
        !diverging.some((d) => isDescendantOrSelf(d.branchId, currentB.branchId)),
      ply: targetPly,
    });

    diverging.forEach((d, idx) => {
      options.push({
        variantLetter: ALPHABETS[idx + 1] || `${idx + 2}`,
        branchId: d.branchId,
        notation: d.divergenceMoveChinese || d.chineseMoves[targetPly - 1] || "...",
        label: `变着 ${d.branchId}`,
        isSelected: isDescendantOrSelf(d.branchId, currentB.branchId),
        ply: targetPly,
      });
    });

    return options;
  }, [importResult, activeBranch, stepIndex, allDivergencePlies, ALPHABETS]);

  // 计算当前分支层级面包屑路径
  const branchBreadcrumbs = useMemo(() => {
    if (!activeBranch || activeBranch.branchId === 0) {
      return [{ branchId: 0, label: "主线" }];
    }
    const crumbs: Array<{ branchId: number; label: string }> = [];
    let curr: GameBranch | undefined = activeBranch;
    while (curr && curr.branchId !== 0) {
      crumbs.unshift({
        branchId: curr.branchId,
        label: `变着 ${curr.branchId}${curr.divergenceMoveChinese ? ` (${curr.divergenceMoveChinese})` : ""}`,
      });
      const parentId = curr.parentBranchId;
      curr = importResult?.branches?.find((b) => b.branchId === parentId);
    }
    crumbs.unshift({ branchId: 0, label: "主线" });
    return crumbs;
  }, [activeBranch, importResult]);

  // 当前步骤评注与开局总评
  const currentComment = activeComments[stepIndex];
  const openingComment = activeComments[0];

  // 执行导入解析
  function handleParse(textToParse = inputText) {
    setIsPlaying(false);
    setActiveBranchId(0);
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
              主线共 <strong>{importResult.moves.length}</strong> 步着法
            </span>
            {importResult.result && (
              <Badge color="informative">终局结果: {importResult.result}</Badge>
            )}
            {importResult.branches && importResult.branches.length > 1 && (
              <Badge color="informative">含 {importResult.branches.length - 1} 个变着分支</Badge>
            )}
            {importResult.comments && Object.keys(importResult.comments).length > 0 && (
              <Badge color="brand">含 {Object.keys(importResult.comments).length} 处评注</Badge>
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

      {/* 棋盘推演与走子列表双栏展示 (参考 xiangqi.com GameNote 布局设计) */}
      {importResult && importResult.success && activeMoves.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "20px", alignItems: "start" }}>
          {/* 左栏：棋盘与步数控制 (专注棋盘，消除多余弹窗与重复卡片) */}
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
                    第 {currentMoveRecord ? Math.ceil(currentMoveRecord.ply / 2) : Math.ceil(stepIndex / 2)} 步 ·{" "}
                    <strong style={{ color: currentMoveRecord?.side === "red" ? "#dc2626" : "#1e293b" }}>
                      {currentMoveRecord?.side === "red" ? "红方" : "黑方"}
                    </strong>{" "}
                    <strong>{activeChineseMoves[stepIndex - 1]}</strong>{" "}
                    <code style={{ fontSize: "12px", color: "#6b7280" }}>({activeMoves[stepIndex - 1]})</code>
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
            <div style={{ width: "100%", maxWidth: "440px" }}>
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

          {/* 右栏：侧边栏 (遵循 xiangqi.com GameNote 经典四段式布局) */}
          <section
            className="panel"
            style={{
              background: "var(--card-bg, #fff)",
              padding: "16px",
              borderRadius: "8px",
              border: "1px solid #e0e0e0",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              minWidth: "360px",
            }}
          >
            {/* 1. 评注区 (NotePreviewBox) */}
            <div
              style={{
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "8px 12px",
                  background: "#f1f5f9",
                  borderBottom: "1px solid #e2e8f0",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#334155",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>
                  {stepIndex === 0
                    ? "📖 棋谱开局总评 (Overview)"
                    : `📝 局面评注 · 第 ${Math.ceil(stepIndex / 2)} 步 ${currentMoveRecord?.side === "red" ? "红方" : "黑方"} ${activeChineseMoves[stepIndex - 1] || ""}`}
                </span>
                {((stepIndex === 0 && openingComment) || (stepIndex > 0 && currentComment)) && (
                  <span style={{ fontSize: "11px", color: "#166534", fontWeight: 600, background: "#dcfce7", padding: "1px 6px", borderRadius: "3px" }}>
                    含评注
                  </span>
                )}
              </div>
              <div
                style={{
                  padding: "10px 12px",
                  fontSize: "13px",
                  lineHeight: "1.6",
                  maxHeight: "130px",
                  overflowY: "auto",
                  color: (stepIndex === 0 ? openingComment : currentComment) ? "#1e293b" : "#94a3b8",
                  fontStyle: (stepIndex === 0 ? openingComment : currentComment) ? "normal" : "italic",
                  whiteSpace: "pre-wrap",
                }}
              >
                {(stepIndex === 0 ? openingComment : currentComment) ||
                  (stepIndex === 0 ? "（初始局面无总评）" : "（当前步骤无评注）")}
              </div>
            </div>

            {/* 2. 线路面包屑与切换 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                background: activeBranchId === 0 ? "#f8fafc" : "#eff6ff",
                border: `1px solid ${activeBranchId === 0 ? "#e2e8f0" : "#bfdbfe"}`,
                borderRadius: "6px",
                fontSize: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", overflow: "hidden" }}>
                <span style={{ color: "#64748b", flexShrink: 0 }}>线路:</span>
                <span
                  style={{
                    fontWeight: 600,
                    color: activeBranchId === 0 ? "#166534" : "#1d4ed8",
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                    overflow: "hidden",
                  }}
                >
                  {branchBreadcrumbs.map((crumb, idx) => (
                    <span key={crumb.branchId}>
                      {idx > 0 && <span style={{ color: "#94a3b8", margin: "0 4px" }}>&gt;</span>}
                      {crumb.branchId === activeBranchId ? (
                        <strong>{crumb.label}</strong>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setActiveBranchId(crumb.branchId)}
                          style={{
                            background: "none",
                            border: "none",
                            padding: 0,
                            color: "#2563eb",
                            cursor: "pointer",
                            textDecoration: "underline",
                            fontSize: "12px",
                          }}
                        >
                          {crumb.label}
                        </button>
                      )}
                    </span>
                  ))}
                </span>
              </div>
              {activeBranchId !== 0 && (
                <Button
                  size="small"
                  appearance="outline"
                  onClick={() => setActiveBranchId(0)}
                  style={{ fontSize: "11px", padding: "2px 8px", height: "24px", flexShrink: 0 }}
                >
                  返回主线
                </Button>
              )}
            </div>

            {/* 3. 对局着法列表 (Moves List Table) */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600, color: "#1e293b" }}>
                  着法记录
                </h3>
                <span style={{ fontSize: "12px", color: "#64748b" }}>
                  共 {activeMoves.length} 步
                </span>
              </div>
              <div
                style={{
                  maxHeight: currentStepVariations.length > 0 ? "240px" : "340px",
                  overflowY: "auto",
                  border: "1px solid #e2e8f0",
                  borderRadius: "6px",
                }}
              >
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ background: "#f1f5f9", borderBottom: "1px solid #cbd5e1", textAlign: "left", position: "sticky", top: 0, zIndex: 1 }}>
                      <th style={{ padding: "6px 8px", width: "40px", color: "#475569" }}>序号</th>
                      <th style={{ padding: "6px 8px", color: "#dc2626" }}>红方</th>
                      <th style={{ padding: "6px 8px", color: "#0f172a" }}>黑方</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moveRows.map((row) => {
                      const isRedActive = row.redStepIndex !== undefined && stepIndex === row.redStepIndex;
                      const isBlackActive = row.blackStepIndex !== undefined && stepIndex === row.blackStepIndex;

                      return (
                        <tr
                          key={row.round}
                          ref={isRedActive || isBlackActive ? (el) => { activeMoveRowRef.current = el; } : undefined}
                          style={{
                            borderBottom: "1px solid #f1f5f9",
                            background: row.round % 2 === 1 ? "#ffffff" : "#f8fafc",
                          }}
                        >
                          <td style={{ padding: "5px 8px", color: "#94a3b8", fontWeight: 500, fontSize: "12px" }}>
                            {row.round}.
                          </td>

                          {/* 红方走子 */}
                          <td
                            onClick={() => row.redStepIndex !== undefined && setStepIndex(row.redStepIndex)}
                            style={{
                              padding: "5px 8px",
                              cursor: row.redStepIndex !== undefined ? "pointer" : "default",
                              fontWeight: isRedActive ? 700 : 400,
                              background: isRedActive ? "#fee2e2" : "transparent",
                              color: isRedActive ? "#b91c1c" : row.redNotation ? "inherit" : "#94a3b8",
                              borderRadius: "4px",
                              border: isRedActive ? "1px solid #ef4444" : "1px solid transparent",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <span>
                                {row.redNotation || "..."}
                                {row.redVariant && (
                                  <span style={{ color: "#2563eb", fontWeight: 600, marginLeft: "4px", fontSize: "11px" }}>
                                    ({row.redVariant})
                                  </span>
                                )}
                              </span>
                              {row.redHasComment && (
                                <span title="包含局面评注" style={{ fontSize: "12px", marginLeft: "4px" }}>
                                  📝
                                </span>
                              )}
                            </div>
                          </td>

                          {/* 黑方走子 */}
                          <td
                            onClick={() => row.blackStepIndex !== undefined && setStepIndex(row.blackStepIndex)}
                            style={{
                              padding: "5px 8px",
                              cursor: row.blackStepIndex !== undefined ? "pointer" : "default",
                              fontWeight: isBlackActive ? 700 : 400,
                              background: isBlackActive ? "#e2e8f0" : "transparent",
                              color: isBlackActive ? "#0f172a" : "inherit",
                              borderRadius: "4px",
                              border: isBlackActive ? "1px solid #94a3b8" : "1px solid transparent",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <span>
                                {row.blackNotation || ""}
                                {row.blackVariant && (
                                  <span style={{ color: "#2563eb", fontWeight: 600, marginLeft: "4px", fontSize: "11px" }}>
                                    ({row.blackVariant})
                                  </span>
                                )}
                              </span>
                              {row.blackHasComment && (
                                <span title="包含局面评注" style={{ fontSize: "12px", marginLeft: "4px" }}>
                                  📝
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 4. 变着分支区 (VariantsContainer / VariationsList) */}
            <div
              style={{
                borderTop: "1px solid #e2e8f0",
                paddingTop: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ margin: 0, fontSize: "13px", fontWeight: 600, color: "#1e293b", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>🔀 变着 (Variations)</span>
                </h4>
                {currentStepVariations.length > 0 && (
                  <span style={{ fontSize: "11px", color: "#64748b" }}>
                    {currentStepVariations[0]?.ply === stepIndex
                      ? `第 ${Math.ceil(stepIndex / 2)} 步本着变着`
                      : `第 ${Math.ceil((stepIndex + 1) / 2)} 步下着分支`}
                  </span>
                )}
              </div>

              {currentStepVariations.length > 0 ? (
                <ul
                  className="sortable-list"
                  style={{
                    margin: 0,
                    padding: 0,
                    listStyle: "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                    maxHeight: "180px",
                    overflowY: "auto",
                  }}
                >
                  {currentStepVariations.map((v) => (
                    <li key={v.branchId} style={{ width: "100%" }}>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveBranchId(v.branchId);
                          setStepIndex(v.ply);
                        }}
                        style={{
                          width: "100%",
                          boxSizing: "border-box",
                          padding: "6px 10px",
                          borderRadius: "6px",
                          border: v.isSelected ? "1px solid #94a3b8" : "1px solid #e2e8f0",
                          background: v.isSelected ? "#e2e8f0" : "#ffffff",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          transition: "all 0.15s ease",
                          textAlign: "left",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              fontWeight: 700,
                              fontSize: "13px",
                              color: v.isSelected ? "#0f172a" : "#64748b",
                              minWidth: "18px",
                            }}
                          >
                            {v.variantLetter}.
                          </span>
                          <span
                            style={{
                              fontSize: "13px",
                              fontWeight: v.isSelected ? 700 : 500,
                              color: v.isSelected ? "#0f172a" : "#334155",
                            }}
                          >
                            {v.notation}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: "11px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: v.isSelected ? "#cbd5e1" : "#f1f5f9",
                            color: v.isSelected ? "#0f172a" : "#64748b",
                            fontWeight: 500,
                          }}
                        >
                          {v.label}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ fontSize: "12px", color: "#64748b", padding: "4px 0" }}>
                  {allDivergencePlies.length > 0 ? (
                    <div>
                      <div style={{ marginBottom: "6px", color: "#94a3b8" }}>
                        当前步无其他变着分支。对局分叉节点：
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {allDivergencePlies.map((ply) => (
                          <button
                            key={ply}
                            type="button"
                            onClick={() => {
                              if (ply > activeMoves.length) {
                                const targetB = importResult?.branches?.find((b) => b.branchPly === ply);
                                if (targetB) {
                                  setActiveBranchId(targetB.parentBranchId >= 0 ? targetB.parentBranchId : 0);
                                } else {
                                  setActiveBranchId(0);
                                }
                              }
                              setStepIndex(ply);
                            }}
                            style={{
                              padding: "2px 6px",
                              fontSize: "11px",
                              borderRadius: "4px",
                              border: "1px solid #cbd5e1",
                              background: "#f8fafc",
                              color: "#334155",
                              cursor: "pointer",
                            }}
                          >
                            第 {Math.ceil(ply / 2)} 步 ({ply % 2 === 1 ? "红" : "黑"})
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <span style={{ fontStyle: "italic", color: "#94a3b8" }}>（本对局无变着分支）</span>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
