# 無失著入口差分報告

package `0.2.0`，中局規則 `midgame-tactics-3.1`，殺法規則 `checkmate-patterns-2026.11.05-v15`，棋盤 `python`。

做法：每題先走失著，再以 `blunder=None` 和原 PV 分類，與凍結標籤比較（限該版本詞彙，與關卡相同）。差異只報告，不改規則；由專家裁定無失著路徑應有的標籤。

另一種棋盤（`native`）的逐題結論：完全相同。

## 中局

有效凍結題 160 題：與凍結標籤相同 153 題，不同 7 題（其中重播錯誤 0 題）。

### R20geZ（v5，CSV 第 13 列）

- 題目：https://play.xiangqi.com/puzzle/R20geZ/P
- 起始局面（已走失著 `h0h9`）：`4kabR1/4a4/6n2/p3p3p/2r3b2/2C2R3/Pc2P3P/c5N2/4A4/1N1AK1B2 b - - 1 22`
- 解答：`a2b2 b0d1 b2c2 d1b2 g7h9 c4b4`，解題方 black
- 凍結標籤：—；得子 no_gain
- 無失著標籤：—
- 得子：有失著 no_gain（start 0，end 0，delta 0） → 無失著 gain（start -9，end 0，delta 9）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 9 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### LkMzG9（v5，CSV 第 15 列）

- 題目：https://play.xiangqi.com/puzzle/LkMzG9/P
- 起始局面（已走失著 `g7h5`）：`2bakr3/4a4/4b4/p3p2Rp/2p3pn1/4Pn3/P1c3c1P/B1N2CN1B/4A4/3AK4 w - - 7 17`
- 解答：`f2f9 e8f9`，解題方 red
- 凍結標籤：交換（exchange）；得子 no_gain
- 無失著標籤：交換（exchange）
- 得子：有失著 no_gain（start 0，end 1，delta 1） → 無失著 gain（start -4，end 1，delta 5）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### RV5w9b（v5，CSV 第 127 列）

- 題目：https://play.xiangqi.com/puzzle/RV5w9b/P
- 起始局面（已走失著 `b5d5`）：`2bak4/4a4/4b4/p3C1r1p/3rR4/2R6/P5pcP/9/5Cn2/2BAKABN1 w - - 3 26`
- 解答：`e5d5 g6e6`，解題方 red
- 凍結標籤：交換（exchange）；得子 no_gain
- 無失著標籤：交換（exchange）
- 得子：有失著 no_gain（start 8，end 9，delta 1） → 無失著 gain（start 4，end 9，delta 5）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### RdpMPr（v5，CSV 第 128 列）

- 題目：https://play.xiangqi.com/puzzle/RdpMPr/P
- 起始局面（已走失著 `e3e4`）：`3akab2/4n4/b8/3Rn3p/p4rp2/1R2P4/P1P3P1P/N3B1N2/4A4/2c1K4 b - - 1 23`
- 解答：`e8d6 e2c0`，解題方 black
- 凍結標籤：交換（exchange）；得子 no_gain
- 無失著標籤：交換（exchange）
- 得子：有失著 no_gain（start -1，end 0，delta 1） → 無失著 gain（start -5，end 0，delta 5）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### RdpMGl（v5，CSV 第 132 列）

- 題目：https://play.xiangqi.com/puzzle/RdpMGl/P
- 起始局面（已走失著 `c2c7`）：`2bakabr1/9/2C1c4/p1p1p3p/1N7/6R2/P2rn1PcP/R3B1N2/2C6/3AKAB2 b - - 1 16`
- 解答：`e3g4 g3g4`，解題方 black
- 凍結標籤：交換（exchange）；得子 no_gain
- 無失著標籤：交換（exchange）
- 得子：有失著 no_gain（start 0，end 1，delta 1） → 無失著 gain（start -4，end 1，delta 5）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### ovMw2z（v5，CSV 第 241 列）

- 題目：https://play.xiangqi.com/puzzle/ovMw2z/P
- 起始局面（已走失著 `e3e2`）：`r1bakab2/9/2N6/p3n1p1p/9/3p2P2/P1P5P/C3r4/R3A3R/2c1KAB2 w - - 1 16`
- 解答：`g0e2 c0c7`，解題方 red
- 凍結標籤：交換（exchange）；得子 no_gain
- 無失著標籤：交換（exchange）
- 得子：有失著 no_gain（start 4，end 5，delta 1） → 無失著 gain（start 0，end 5，delta 5）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### oM2jKq（v5，CSV 第 501 列）

- 題目：https://play.xiangqi.com/puzzle/oM2jKq/P
- 起始局面（已走失著 `d5e3`）：`r3kabr1/4aR3/4b1n2/p3c3p/2p1C1p2/9/P3n1c1P/4C1N1B/5R3/2BAKA3 w - - 3 18`
- 解答：`e5e7 e9d9 e7e3 a9a8`，解題方 red
- 凍結標籤：抽將（check_fork）、閃擊（discovered_attack）、捉雙（fork）；得子 no_gain
- 無失著標籤：捉雙（fork）、閃擊（discovered_attack）、抽將（check_fork）
- 得子：有失著 no_gain（start 0，end 0，delta 0） → 無失著 gain（start -4，end 0，delta 4）
- 消失的出現：—
- 新增的出現：—
- 原因：戰術出現完全相同，只有得子分類改變。有失著時從失著前計算，失著吃掉解題方 4 分，回吃只算扯平；無失著時從失著後計算，回吃算作得子。

### 凍結比對相同、但引擎輸出有變的題目

- R20gdZ：消失 —；新增 —；得子 gain（start -1，end 4，delta 5） → gain（start -5，end 4，delta 9）
- RV5wdg：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）
- RZgpN6：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）
- o99pJo：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）
- oM0b9E：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）
- o9WMdE：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）
- oM0b9b：消失 —；新增 —；得子 no_gain（start 0，end -4，delta -4） → no_gain（start -4，end -4，delta 0）
- o74wm2：消失 —；新增 —；得子 gain（start 0，end 5，delta 5） → gain（start -4，end 5，delta 9）

## 殺法

有效凍結題 125 題：與凍結標籤相同 124 題，不同 1 題。

### R0g4pn（v1，第 466 題）

- 題目：https://play.xiangqi.com/puzzle/R0g4pn/P
- 起始局面（已走失著 `d8d7`）：`R4a3/4a4/3k5/2N6/2p1p3p/9/2r6/9/4A4/2BAK4 w - - 4 34`
- 解答：`a9a7`
- 凍結：側面虎（TIGER_SILHOUETTE_CHECKMATE）；子力 —
- 有失著：matched：側面虎（TIGER_SILHOUETTE_CHECKMATE）
- 無失著：matched：—；子力 車馬（RN）
