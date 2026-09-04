import assert from 'node:assert/strict';
import test from 'node:test';
import { importXiangqiGame } from '../app/lib/notation-import/index.ts';

// Case 1: 东萍象棋网纯文本
const CASE_1_DPXQ_TEXT = `
标题: 北京 刘永富 负 北京 张永生
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
棋谱价值: 1
浏览次数: 170
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
 
棋谱由 http://www.dpxq.com/ 生成
`;

// Case 2: 东萍象棋网 UBB
const CASE_2_DPXQ_UBB = `
[DhtmlXQ]
[DhtmlXQ_ver]www_dpxq_com[/DhtmlXQ_ver]
[DhtmlXQ_init]500,350[/DhtmlXQ_init]
[DhtmlXQ_binit]8979695949392919097717866646260600102030405060708012720323436383[/DhtmlXQ_binit]
[DhtmlXQ_pver]130606[/DhtmlXQ_pver]
[DhtmlXQ_adddate]2026-08-31 10:25:15[/DhtmlXQ_adddate]
[DhtmlXQ_editdate]2026-08-31 10:25:15[/DhtmlXQ_editdate]
[DhtmlXQ_title]北京 刘永富 负 北京 张永生[/DhtmlXQ_title]
[DhtmlXQ_movelist]77475041796772328979706266656042190780501727100209190010191503046755121459481424151002102724505524745550741410021412505412170214476714261727263479763415273754583738585569473236767236323828555628204220726256466260415060631534677746766343324277573455434555676564304186852324476976792947242557597975457567755955755664542535072642820605040555055668495982525444685644545668544435362634685644545635544436464725355644545668544446564454[/DhtmlXQ_movelist]
[DhtmlXQ_firstnum]0[/DhtmlXQ_firstnum]
[DhtmlXQ_length]107[/DhtmlXQ_length]
[DhtmlXQ_type]全局[/DhtmlXQ_type]
[DhtmlXQ_gametype]慢棋[/DhtmlXQ_gametype]
[DhtmlXQ_open]B00 中炮局[/DhtmlXQ_open]
[DhtmlXQ_class]其他赛事[/DhtmlXQ_class]
[DhtmlXQ_event]2026年第137届龙马鹏程大兴月赛[/DhtmlXQ_event]
[DhtmlXQ_place]北京市大兴区大悦春风里1层[/DhtmlXQ_place]
[DhtmlXQ_timerule]15分＋5秒[/DhtmlXQ_timerule]
[DhtmlXQ_round]第07轮[/DhtmlXQ_round]
[DhtmlXQ_date]2026-08-31[/DhtmlXQ_date]
[DhtmlXQ_result]黑胜[/DhtmlXQ_result]
[DhtmlXQ_red]北京 刘永富[/DhtmlXQ_red]
[DhtmlXQ_redteam]北京[/DhtmlXQ_redteam]
[DhtmlXQ_redname]刘永富[/DhtmlXQ_redname]
[DhtmlXQ_black]北京 张永生[/DhtmlXQ_black]
[DhtmlXQ_blackteam]北京[/DhtmlXQ_blackteam]
[DhtmlXQ_blackname]张永生[/DhtmlXQ_blackname]
[DhtmlXQ_hits]170[/DhtmlXQ_hits]
[DhtmlXQ_sortid]1426100[/DhtmlXQ_sortid]
[DhtmlXQ_owner]ryueifu[/DhtmlXQ_owner]
[DhtmlXQ_oldowner]ryueifu[/DhtmlXQ_oldowner]
[DhtmlXQ_refer]http%3A//www.dpxq.com/%0D%0Ahttp%3A//www.dpxq.com/hldcg/search/view_m_142610.html[/DhtmlXQ_refer]
[DhtmlXQ_generator][/DhtmlXQ_generator]
[/DhtmlXQ]
`;

// Case 3: PGN 许银川让九子对聂棋圣 (带让子 FEN、海量多行中文注释、前马/后马、1-0)
const CASE_3_PGN_HANDICAP = `
[Game "Chinese Chess"]
[Event "许银川让九子对聂棋圣"]
[Site "广州"]
[Date "1999.12.09"]
[Red "许银川"]
[Black "聂卫平"]
[Result "1-0"]
[FEN "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/9/1C5C1/9/RN2K2NR r - - 0 1"]
{　　评注：许银川
　　象棋让九子原属茶余饭后的娱乐，不意今日却被摆上赛桌，更为离奇的是：我的对手竟是在围棋棋坛上叱咤风云的聂大帅。赛前我并不了解对手的实力，但相信以聂棋圣在围棋上所体现出来的过人智慧，必能在棋理上触类旁通。因此我在赛前也作了一些准备，在对局中更是小心翼翼，不敢掉以轻心。
　　许银川让去５只兵和双士双相，执红先行。棋盘如右图所示。当然，PGN文件里是无法嵌入图片的。}

1. 炮八平五 炮８平５
{　　红方首着架中炮必走之着，聂棋圣还架中炮拼兑子力，战术对头。}
2. 炮五进五 象７进５ 3. 炮二平五
{　　再架中炮也属正着，如改走马八进七，则象５退７，红方帅府受攻，当然若红方仍再架中炮拼兑，那么失去双炮就难有作用了。}
马８进７ 4. 马二进三 车９平８ 5. 马八进七 马２进１ 6. 车九平六 车１平２
{　　聂棋圣仍按常规战法出动主力，却忽略了红方车塞象眼的凶着，应走车１进１。}
7. 车六进八
{　　红车疾点象眼，局势霎时有剑拔弩张之感。这种对弈不能以常理揣度，红方只能像程咬金的三板斧一般猛攻一轮，若黑方防守得法则胜负立判。}
炮２进７
{　　却说聂棋圣见我来势汹汹，神色顿时颇为凝重，一番思索之后沉下底炮以攻为守，果是身手不凡。此着如改走炮２平３，则帅五平六，炮３进５，车六进一，将５进１，炮五退二，黑方不易驾驭局面。}
8. 车一进四 炮２平１ 9. 马七进八 炮１退４ 10. 马八退七 炮１进４ 11. 马七进八 车２进２
{　　其实黑方仍可走炮１退４，红方若续走马八退七，则仍炮１进４不变作和，因黑右车叫将红可车六退九，故不算犯规。}
12. 炮五平八 炮１退４
{　　劣着，导致失子，应走车２平３，红方如马八进六，则车３退１，红方无从着手。但有一点必须注意，黑车躲进暗道似与棋理相悖，故聂棋圣弃子以求局势缓和情有可原。}
13. 炮八进五 炮１平９ 14. 炮八平三 车８进２ 15. 炮三进一 车８进２ 16. 马八进六 炮９平５
17. 炮三平一 士６进５ 18. 马六进四 车８平５ 19. 帅五平六
{　　可直接走马四进三叫将再踩中象。}
车５平６ 20. 马四进三 将５平６ 21. 车六退四 卒５进１ 22. 车六进二 炮５平７
23. 前马退二 象５进７ 24. 马二退三 卒５进１ 25. 车六平三 卒５平６ 26. 车三进三 将６进１
27. 后马进二 士５进６ 28. 马二进三 将６平５ 29. 前马进二
{　　红方有些拖沓，应直接走车三平六立成绝杀。}
将５进１ 30. 车三平六 士６退５ 31. 马二退三 车６退１ 32. 车六退三
{　　再擒一车，以下着法仅是聊尽人事而已。}
车６平７ 33. 车六平三 卒６平７ 34. 车三平五 将５平６ 35. 帅六平五 将６退１
36. 车五进二 将６退１ 37. 车五进一 将６进１ 38. 车五平七
{　　至此，聂棋圣认负。与此同时，另一盘围棋对弈我被屠去一条大龙，已无力再战，遂平分秋色，皆大欢喜。}
1-0
`;

// Case 4: xqipu.com ICCS
const CASE_4_ICCS = `
[Game "Chinese Chess"]
[Title "謝承宇先負陳國興3"]
[Event "啟泰趣笑第四屆臺灣象棋棋王賽-四強賽"]
[Red "謝承宇"]
[RedTeam ""]
[Black "陳國興"]
[BlackName ""]
[Opening "过宫炮局"]
[Date ""]
[Site ""]
[Round "第三局"]
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
 *
`;

// Case 5: playok.com WXF
const CASE_5_PLAYOK_WXF = `
FORMAT  WXF
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
28. E3+5 }END
`;

// Case 6: 用户初始样例 1 (标准 PGN、全角数字、同列相消歧 相三进五、1-0)
const CASE_6_USER_EXAMPLE_1 = `
[Game "Chinese Chess"]
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
54. 车三平四 1-0
`;

// Case 7: 用户初始样例 2 (无标头、无空格无换行粘连)
const CASE_7_USER_EXAMPLE_2 = `
1.兵七进一炮2平32.兵三进一炮8平53.马二进三马8进74.马八进七车9平85.车一平二马2进16.车九平八车8进47.炮二平一车8进58.马三退二车1平29.马二进三车2进410.炮八平九车2平811.马七进六卒7进112.兵三进一车8平713.相七进五卒1进114.车八进四车7平415.兵七进一卒3进116.炮一退一马1进317.马三进四卒3进118.马四进六卒3平219.马六进五马3进420.马五进七将5进121.炮九进三将5平622.仕六进五马7进623.炮一平四马6进524.仕五进四马5退625.炮九进一士6进526.炮九平一士5进627.马七进五马6退828.马五退六象3进529.炮一退二马8进930.兵一进一将6退1
`;

test('Case 1: 东萍象棋网纯文本 (dpxq 文本)', () => {
  const result = importXiangqiGame(CASE_1_DPXQ_TEXT);
  assert.equal(result.success, true, result.error);
  assert.equal(result.moves.length, 107, 'Should parse all 107 moves');
  assert.equal(result.headers.Red, '刘永富');
  assert.equal(result.headers.Black, '张永生');
  assert.equal(result.chineseMoves[0], '炮二平五');
  assert.equal(result.chineseMoves[result.chineseMoves.length - 1], '兵五平四');
});

test('Case 2: 东萍象棋网 UBB (dpxq UBB) - Cross validation with Case 1', () => {
  const resUbb = importXiangqiGame(CASE_2_DPXQ_UBB);
  const resText = importXiangqiGame(CASE_1_DPXQ_TEXT);

  assert.equal(resUbb.success, true, resUbb.error);
  assert.equal(resUbb.format, 'dpxq_ubb');
  assert.equal(resUbb.moves.length, 107, 'Should parse all 107 moves from UBB movelist');

  // Verify that DhtmlXQ UBB coordinates match the plain text moves 100%
  assert.deepEqual(
    resUbb.moves,
    resText.moves,
    'DhtmlXQ UBB moves must match plain text moves exactly',
  );
  assert.deepEqual(
    resUbb.chineseMoves,
    resText.chineseMoves,
    'DhtmlXQ UBB chineseMoves must match plain text moves exactly',
  );
});

test('Case 3: 许银川让九子对聂棋圣 (PGN with FEN, long comments, 1-0)', () => {
  const result = importXiangqiGame(CASE_3_PGN_HANDICAP);
  assert.equal(result.success, true, result.error);
  assert.equal(
    result.initialFen,
    'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/9/1C5C1/9/RN2K2NR r - - 0 1',
    'Must preserve handicap FEN',
  );
  assert.equal(result.moves.length, 75, 'Should parse all 75 moves');
  assert.equal(result.chineseMoves[0], '炮八平五');
  assert.equal(result.chineseMoves[result.chineseMoves.length - 1], '车五平七');
  assert.equal(result.result, '1-0');
});

test('Case 4: 台湾棋王赛四强赛 (xqipu.com ICCS)', () => {
  const result = importXiangqiGame(CASE_4_ICCS);
  assert.equal(result.success, true, result.error);
  assert.equal(result.format, 'iccs');
  assert.equal(result.moves.length, 54, 'Should parse all 54 moves (27 rounds)');
  assert.equal(result.moves[0], 'h2d2');
  assert.equal(result.moves[1], 'g6g5');
  assert.equal(result.chineseMoves[0], '炮二平六');
  assert.equal(result.chineseMoves[1], '卒7进1');
  assert.equal(result.headers.Red, '謝承宇');
  assert.equal(result.headers.Black, '陳國興');
});

test('Case 5: PlayOK 对局 (playok.com WXF)', () => {
  const result = importXiangqiGame(CASE_5_PLAYOK_WXF);
  assert.equal(result.success, true, result.error);
  assert.equal(result.format, 'wxf');
  assert.equal(result.moves.length, 55, 'Should parse all 55 moves');
  assert.equal(result.chineseMoves[0], '炮八平五');
  assert.equal(result.chineseMoves[1], '炮2平5');
  assert.equal(result.chineseMoves[2], '马八进七');
  assert.equal(result.chineseMoves[3], '马2进3');
  assert.equal(result.result, '1-0');
});

test('Case 6: 用户初始样例 1 (PGN with same-column bishops 相三进五, fullwidth digits, 1-0)', () => {
  const result = importXiangqiGame(CASE_6_USER_EXAMPLE_1);
  assert.equal(result.success, true, result.error);
  assert.equal(result.moves.length, 107, 'Should parse all 107 moves');
  assert.equal(result.chineseMoves[0], '兵三进一');
  // Verify move 43 (round 22 move 1: 相三进五 / 后相进五) was correctly resolved to g0e2
  assert.equal(result.moves[42], 'g0e2', 'Move 43 must be resolved to g0e2');
  assert.equal(result.chineseMoves[106], '车三平四');
});

test('Case 7: 用户初始样例 2 (完全紧凑无空格 1.兵七进一炮2平32.兵三进一...)', () => {
  const result = importXiangqiGame(CASE_7_USER_EXAMPLE_2);
  assert.equal(result.success, true, result.error);
  assert.equal(result.moves.length, 60, 'Should parse all 60 moves');
  assert.equal(result.chineseMoves[0], '兵七进一');
  assert.equal(result.chineseMoves[1], '炮2平3');
  assert.equal(result.chineseMoves[result.chineseMoves.length - 1], '将6退1');
});

test('Case 8: 繁体字与异形字 (俥一進一 傌二進三 砲二平五 象７進５)', () => {
  const traditionalNotation = `
[Game "Chinese Chess"]
1. 俥一進一 象７進５
2. 砲二平五 傌８進７
3. 傌二進三 車９平８
`;
  const result = importXiangqiGame(traditionalNotation);
  assert.equal(result.success, true, result.error);
  assert.equal(result.moves.length, 6);
  assert.equal(result.chineseMoves[0], '车一进一');
  assert.equal(result.chineseMoves[2], '炮二平五');
});

test('Case 9: 纯 UCI 坐标流导入 (h2e2 h9g7 b0c2 i9h9)', () => {
  const uciStream = `1. h2e2 h9g7 2. b0c2 i9h9`;
  const result = importXiangqiGame(uciStream);
  assert.equal(result.success, true, result.error);
  assert.equal(result.format, 'uci');
  assert.equal(result.moves.length, 4);
  assert.equal(result.chineseMoves[0], '炮二平五');
  assert.equal(result.chineseMoves[1], '马8进7');
  assert.equal(result.chineseMoves[2], '马八进七');
  assert.equal(result.chineseMoves[3], '车9平8');
});

test('Case 10: 布局头信息含着法字样 (中炮进三兵) 与后车/后马 (淮安市机关赛)', () => {
  const case10Text = `
标题: 市邮政局 高智彬 负 市教育局 赵迎
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
 
棋谱由 http://www.dpxq.com/ 生成
`;
  const result = importXiangqiGame(case10Text);
  assert.equal(result.success, true, result.error);
  assert.equal(result.moves.length, 92, 'Should parse all 92 moves');
  assert.equal(result.headers?.Red, '高智彬');
  assert.equal(result.headers?.Black, '赵迎');
  assert.equal(result.chineseMoves[0], '炮二平五');
  assert.equal(result.chineseMoves[1], '马8进7');
  assert.equal(result.chineseMoves[27], '后车进2');
  assert.equal(result.chineseMoves[42], '后马进五');
  assert.equal(result.chineseMoves[60], '马三进五');
  assert.equal(result.chineseMoves[91], '马2退4');
});

test('Case 11: ICCS 与 WXF 评注内包含走法字符串不应被当做实战走法', () => {
  const iccsWithComment = `
[Format "ICCS"]
1. H2-E2 { H9-G7 is natural but here we test comment stripping } H9-G7
2. B0-C2
`;
  const res1 = importXiangqiGame(iccsWithComment);
  assert.equal(res1.success, true, res1.error);
  assert.equal(res1.moves.length, 3, 'Should parse 3 moves, not 4');
  assert.equal(res1.moves[0], 'h2e2');
  assert.equal(res1.moves[1], 'h9g7');
  assert.equal(res1.moves[2], 'b0c2');

  const wxfWithComment = `
[Event "WXF Comment Test"]
[Format "WXF"]
1. C8.5 { c2.5 is also playable } c2.5
2. H8+7
`;
  const res2 = importXiangqiGame(wxfWithComment);
  assert.equal(res2.success, true, res2.error);
  assert.equal(res2.moves.length, 3, 'Should parse 3 moves, not 4');
  assert.equal(res2.moves[0], 'b2e2');
  assert.equal(res2.moves[1], 'b7e7');
  assert.equal(res2.moves[2], 'b0c2');
});

test('Case 12: 无效/无着法输入严格返回失败（如 hello world）', () => {
  const garbage = 'hello world this is not a chess game';
  const res1 = importXiangqiGame(garbage);
  assert.equal(res1.success, false, 'Garbage text must not succeed');
  assert.equal(res1.moves.length, 0);

  const emptyIccs = '[Format "ICCS"]\n[Red "A"]\n[Black "B"]\n';
  const res2 = importXiangqiGame(emptyIccs);
  assert.equal(res2.success, false, 'ICCS without moves must not succeed');

  const emptyWxf = '[Format "WXF"]\n[Event "Empty"]\n';
  const res3 = importXiangqiGame(emptyWxf);
  assert.equal(res3.success, false, 'WXF without moves must not succeed');
});

test('Case 13: 黑方先走 (Black to move) 自定义 FEN 开局解析', () => {
  // Black to move initial FEN (side = 'b')
  const blackFirstFen = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 0 1';
  const notation = `
[FEN "${blackFirstFen}"]
1. ... 炮8平5
2. 炮二平五 马8进7
`;
  const res = importXiangqiGame(notation);
  assert.equal(res.success, true, res.error);
  assert.equal(res.moves.length, 3);
  assert.equal(res.chineseMoves[0], '炮8平5');
  assert.equal(res.chineseMoves[1], '炮二平五');
  assert.equal(res.chineseMoves[2], '马8进7');
});

test('Case 14: 中文棋谱注释内含 ICCS/WXF 坐标时不误判格式 (Reviewer finding)', () => {
  const chineseWithIccsComment = `
[Game "Chinese Chess"]
{alternative H2-E2}
1. 炮二平五 炮8平5
`;
  const res1 = importXiangqiGame(chineseWithIccsComment);
  assert.equal(res1.success, true, res1.error);
  assert.equal(res1.format, 'plain_chinese');
  assert.equal(res1.moves.length, 2);
  assert.equal(res1.chineseMoves[0], '炮二平五');
  assert.equal(res1.chineseMoves[1], '炮8平5');

  const chineseWithWxfComment = `
[Game "Chinese Chess"]
{note: C8.5 or h2+3 were considered}
1. 马二进三 马8进7
`;
  const res2 = importXiangqiGame(chineseWithWxfComment);
  assert.equal(res2.success, true, res2.error);
  assert.equal(res2.format, 'plain_chinese');
  assert.equal(res2.moves.length, 2);
  assert.equal(res2.chineseMoves[0], '马二进三');
  assert.equal(res2.chineseMoves[1], '马8进7');
});


