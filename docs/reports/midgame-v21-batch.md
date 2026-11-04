# 中局題 v2.1 批次報告

規則 `midgame-tactics-2.1`，資料 `2.1`。

基準 SHA：`ee36518e806bada0e3b4e9d2a73d01d1215a17c3`。既有未提交的將殺／開局相關修改保留。

CSV SHA256：`29f714b8b6f6ed0bab3997587e0404610269030d595b3d5628c5b32fbdd81e90`。

舊索引 SHA256：`5a1a96279bcf98448cd1b1bf05098ba25e9e9c8c7ac31bc9a3282dc284da84c5`。

新索引 SHA256：`68aa84c6d1e86eca97cb15c6def8f307de0487e088ca9038d85da97f633b3e04`。

生成時間：2026-11-03T04:59:07.001345+00:00；分類批次耗時 273.522 秒。

輸入 3135 列；有效 3135，無效 0；得子 2281，並非得子 854。
有標籤 1861 題；無標籤 1274 題。全部逐列核對來源列號、ID、原 FEN、PV、合法時間線、身份證據及 summary。

## 與 v2.0 的分類交叉表

全部由原棋譜重新分析；每題 material 與凍結的 v2.0 基準逐項一致。

| 舊分類 | gain | no_gain | invalid |
| --- | ---: | ---: | ---: |
| gain | 2281 | 0 | 0 |
| no_gain | 0 | 854 | 0 |

## 逐標籤差異（按題去重）

| ID | 新增 | 移除 | 保留 | 命中 |
| --- | ---: | ---: | ---: | ---: |
| fork | 2 | 316 | 614 | 616 |
| discovered_attack | 0 | 6 | 438 | 438 |
| skewer | 0 | 65 | 112 | 112 |
| pin | 368 | 0 | 150 | 518 |
| check_fork | 1 | 195 | 349 | 350 |
| trap | 78 | 79 | 120 | 198 |
| remove_defender | 29 | 18 | 73 | 102 |
| overload | 10 | 0 | 0 | 10 |
| exchange | 0 | 476 | 619 | 619 |
| clearance | 9 | 0 | 0 | 9 |

## 使用者覆核題

| ID | 分類 | 最終標籤 |
| --- | --- | --- |
| ogm3Jr | gain | 捉雙、抽將、圍困 |
| q5YwNm | gain | 過載 |
| qGK2kX | gain | 閃擊、串打 |
| Lmpvzn | gain | 消除阻隔 |
| Ll62Gb | gain | 牽制 |
| LxN1pw | no_gain | 捉雙、串打、牽制 |
| oM0beE | gain | 牽制 |
| R6jDez | no_gain | 牽制 |
| o9WMlO | gain | 牽制 |
| LzPwnV | gain | 捉雙、牽制 |
| oyMnv4 | gain | 交換 |
| ovMw1a | gain | 交換 |
| oX0nE1 | gain | 交換 |
| RdpMdl | gain | 捉雙、牽制、抽將、消除保護 |

## 覆核與抽樣

尚未經人工核對，已審數為 0；正確數、precision、recall 不提供。上述僅為命中分布，不是準確率。

固定 seed 20261103：每標籤最多 30 題，另抽無標籤及 delta 3/4/5 交界各最多 30 題，去重後 303 題。
[盲審檔](midgame-v21-blind-review.json) 隱藏機器結果；人審欄位保持 null。[機讀批次報告](midgame-v21-batch.json) 另含各抽樣組的 ID。禁止把生成結果寫回人工期望。

待裁決涉及 858 題，詳見 [FEN、步數及完整候選證據](midgame-v21-review-candidates.json)。

| 標籤 | 覆核原因 | 候選數 |
| --- | --- | ---: |
| pin | horse_leg_value_boundary | 66 |
| remove_defender | no_prior_legal_attack | 87 |
| remove_defender | release_not_proven_forced | 66 |
| skewer | no_profitable_two_stage_confirmation | 63 |
| threat | nonpositive_mover_recaptured_next_ply | 481 |
| trap | defender_in_check | 469 |

## 本輪規則與驗證

加入 indirect suicide 逃路代價、真實應將後驗證第二威脅、立即被吃且交換收益 ≤0 的攻擊者過濾。串打兩段皆須有利。取消過載／迫走守子的唯一合法應法門檻，保留實際 PV 因果與兌現檢查。

牽制承接對手應着、識別利用既有牽制、逐一檢查炮線兩個阻擋子；士相兵卒須有促成實際吃車馬炮的功能證據。純由牽制造成的無逃路放入牽制證據。新增 clearance 消除阻隔。

得子題的閃擊＋抽將會抑制捉雙；有其他標籤時抑制交換。被抑制的有效證據放 supportingEvidence，父證據鍵保持可追溯；統計與篩選只計最終標籤。

[驗證明細](midgame-v21-validation.json) 記錄本輪測試與限制。原 v2.0 的既有失敗清單見 [前輪驗證](midgame-v2-validation.json)。機器回歸通過不代表人工精確率。

重建：

```bash
python backend/scripts/generate_capturing_tactics.py --csv data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv --output public/data/capturing-tactics.json
python backend/scripts/audit_midgame_tactics.py
python -m pytest backend/tests -q
npm run lint
npm run build
```
