# 中局題 v2 批次報告

規則 `midgame-tactics-2.0`，資料 `2.0`。

基準 SHA：`ee36518e806bada0e3b4e9d2a73d01d1215a17c3`。既有未提交的將殺／開局相關修改保留。

CSV SHA256：`29f714b8b6f6ed0bab3997587e0404610269030d595b3d5628c5b32fbdd81e90`。

舊索引 SHA256：`43617e4a9111fc09075b48c943566a992788094d39862e3404345547a837de6c`。

新索引 SHA256：`5a1a96279bcf98448cd1b1bf05098ba25e9e9c8c7ac31bc9a3282dc284da84c5`。

生成時間：2026-11-02T15:59:25.125455+00:00；分類批次耗時 463.309 秒。

輸入 3135 列；有效 3135，無效 0；得子 2281，並非得子 854。
有標籤 1814 題；無標籤 1321 題。全部逐列核對來源列號、ID、原 FEN、PV、合法時間線、身份證據及 summary。

## 新舊分類交叉表

舊分類不能直接映射；以下均由原棋譜重新計算。

| 舊分類 | gain | no_gain | invalid |
| --- | ---: | ---: | ---: |
| big | 2270 | 210 | 0 |
| small | 0 | 226 | 0 |
| none | 11 | 418 | 0 |

## 逐標籤差異（按題去重）

| ID | 新增 | 移除 | 保留 | 命中 |
| --- | ---: | ---: | ---: | ---: |
| fork | 470 | 3 | 460 | 930 |
| discovered_attack | 229 | 41 | 215 | 444 |
| skewer | 133 | 36 | 44 | 177 |
| pin | 57 | 61 | 93 | 150 |
| check_fork | 544 | 0 | 0 | 544 |
| trap | 102 | 62 | 97 | 199 |
| remove_defender | 69 | 189 | 22 | 91 |
| overload | 0 | 0 | 0 | 0 |
| exchange | 632 | 98 | 463 | 1095 |
| cannon_pawn_breakthrough | 0 | 12 | 0 | 0 |

## 覆核與抽樣

尚未經人工核對，已審數為 0；正確數、precision、recall 不提供。上述僅為命中分布，不是準確率。

固定 seed 20261102：每標籤最多 30 題，另抽無標籤及 delta 3/4/5 交界各最多 30 題，去重後 291 題。
[盲審檔](midgame-v2-blind-review.json) 隱藏機器結果；人審欄位保持 null。[機讀批次報告](midgame-v2-batch.json) 另含各抽樣組的 ID。禁止把生成結果寫回人工期望。

待裁決涉及 658 題，詳見 [FEN、步數及完整候選證據](midgame-v2-review-candidates.json)。

| 標籤 | 覆核原因 | 候選數 |
| --- | --- | ---: |
| overload | alternative_responses_not_proven | 10 |
| pin | horse_leg_value_boundary | 9 |
| remove_defender | no_prior_legal_attack | 87 |
| remove_defender | release_not_proven_forced | 77 |
| skewer | no_legal_rear_confirmation | 25 |
| trap | defender_in_check | 736 |

過載初版只自動接受唯一合法回應的實際回吃鏈，本批命中 0 題。其他替代應法、馬腿價值交界、被將時的圍困及尚無先前合法攻擊的消除保護候選均保守處理。守護恢復即中止、圍困只標新狀態；盲審應另查這些取捨造成的漏標。

## 驗證與限制

五道使用者代表題全部合法並符合指定標籤；串打 B 的 c3 炮架、c6 前子、c7 後子身份分離；抽將 B 由兩炮捉雙派生，沒有誤標新增炮架為閃擊。

[驗證明細](midgame-v2-validation.json) 記錄新增測試、交換 parity、全套測試及隔離基準的失敗清單。全套已有 36 項失敗，未新增失敗；未改寫這些開局／將殺／通用分類語義。lint、build 通過。額外 tsc 檢查仍有其他未修改檔案的既有錯誤。

瀏覽器連線 host 不可用，原生 Chrome 應用存取核准逾時，故兩類／九標籤／無標篩選與證據跳轉的互動式驗收尚未完成。開發伺服器與首頁 HTTP 200 已確認；不可把這項檢查視為互動測試通過。

重建：

```bash
python backend/scripts/generate_capturing_tactics.py --csv data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv --output public/data/capturing-tactics.json
python backend/scripts/audit_midgame_tactics.py
python -m pytest backend/tests -q
npm run lint
npm run build
```
