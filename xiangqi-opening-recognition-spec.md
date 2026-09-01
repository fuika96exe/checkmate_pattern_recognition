# 中國象棋開局辨認引擎與測試前端規格

- 文件版本：0.4
- 狀態：MVP 實作規格
- 文件語言：繁體中文
- 前端技術：React、TypeScript、Vite
- 後端技術：Python 3.12、FastAPI、Pydantic、pytest
- 着法內部格式：UCCI 座標着法
- 顯示棋譜：標準中國象棋中文記譜

## 1. 項目目標

建立一套可解釋、可擴充、以行棋歷史為核心的中國象棋開局辨認系統，以及一個供開發者和象棋使用者測試判斷邏輯的網頁前端。

系統不以硬編碼完整着法序列辨認開局，而是：

1. 將每一步棋轉換成中性的原子事實；
2. 使用紅黑共用的原子及幾何棋形 detector，再按角色政策建立雙方的開局記憶；
3. 保存雙方曾作出的主選擇、已形成棋形、選擇轉換和具體變例；
4. 由雙方累積資料組合出開局名稱；
5. 顯示每一個判斷所依據的着法及規則。

本項目的核心用途不是完全重製 ECCO A00–E99，而是建立一套比完整 ECCO 更容易維護、可逐步增加規則、又能保留中國象棋開局命名邏輯的辨認框架。

## 2. 已確認的產品決策

### 2.1 技術決策

- 使用 React + TypeScript + Vite 建立獨立網頁應用；
- 棋盤合法性、UCCI 着法、標準中文記譜、開局辨認及測試執行全部由 Python backend 負責；
- backend 使用 FastAPI 提供無 server session 的增量 JSON API；client 每次提交上一個 `RecognitionState` 和新一步 UCCI；
- frontend 不複製任何開局或合法着法判斷邏輯；
- 規則以 YAML 或 JSON 儲存，由 Python backend 載入及校驗；
- 使用 Pydantic 定義 API contract，使用 pytest 執行引擎及使用者建立的 test cases；
- MVP 不設使用者帳戶或正式資料庫；
- UI 建立的 test cases 由 backend 儲存為可納入版本控制的 JSON fixture；
- UI 設定和自訂分析回合上限可以存入 `localStorage`。

### 2.2 輸入方式

MVP 支援：

- 在互動棋盤上點擊棋子行棋；
- 上一步、下一步及跳到任意 ply；
- 修改較早着法後，自動刪除其後分支，從該 ply 保存的 `RecognitionState` 增量建立新線；snapshot 不可用時才從頭重播。

MVP 不提供文字着法輸入。Frontend 將棋盤點擊轉成起點／終點，由 backend 驗證後保存為 UCCI 着法；着法列表顯示 backend 生成的標準中國象棋中文記譜。

### 2.3 分類政策

- 紅黑雙方共用同一套原子特徵和幾何棋形 detector；
- 主選擇另有角色資格：同一棋形可以紅黑都偵測到，但只容許指定一方升格為主選擇；
- 角色限制寫在同一條規則的 `main_choice_roles`，不可為紅黑複製兩套幾何判斷；
- 目前棋形每步由 FEN 重新辨認；開局主選擇、形成時間及鎖定由上一個 `OpeningMemory` 延續；
- 完整着法歷史不是增量分類必要輸入，只用於 UI 棋譜、fixture 重現、設定變更後重算及 snapshot 復原；
- 開局記憶只增不減；
- 已確認的主選擇不會因棋子後來離開原位置而失效；
- 選擇轉換屬於路徑延伸，不是新選擇取代舊選擇；
- 互斥棋形採首次確認後鎖定；
- 主對局分類一經確認，不會被其後局面改判；
- 之後只可以加入轉型、子棋形和具體變例；
- 使用自訂穩定 ID，可附上相關 ECCO code 作參考，但不承諾完全兼容 ECCO。

合資格的複合主體系亦可成為一方的主體系。以 `中炮對屏風馬` 為例：

- 紅方主體系是 `central_cannon`；
- 黑方主體系是 `screen_horse`；
- `screen_horse` 並非一步棋產生的原子選擇，而是由雙正馬及中間炮狀態推導、首次成立後鎖定的複合主體系。

`screen_horse`、`reverse_palace_horse`、`single_horse` 在 MVP 只容許黑方成為複合主體系。紅方出現相同幾何棋形時，只記錄原子事實或後續棋形，不新增同名主選擇。

## 3. 核心不變量

以下規則是實作時不得破壞的系統不變量。

### 3.1 棋盤狀態可變，開局記憶不可回收

`PositionState` 表示目前棋盤，會隨每一步棋改變。`OpeningMemory` 表示在此棋局歷史中已確認的開局事實，只可以追加。

例如一方第一步選擇中炮，其後中炮離開中路：

- 目前棋盤可以已經沒有中炮；
- `central_cannon` 選擇仍永久保留；
- 其後出齊雙正馬不會將該方主開局改成屏風馬。

### 3.2 選擇使用有序路徑保存

「起馬轉中炮」保存為：

```text
proper_horse_opening → central_cannon
```

「仙人指路轉中炮」保存為：

```text
angle_pawn → central_cannon
```

第二個選擇不會刪除第一個選擇；名稱生成器根據完整路徑輸出「轉」。

### 3.3 互斥棋形首次確認後鎖定

同一個互斥棋形軸，例如 `defensive_system`，只可以鎖定一次。

例子：

- 黑方先形成雙正馬、中間無炮：鎖定屏風馬；其後走仕角炮不改判成反宮馬；
- 黑方先有仕角炮，再形成雙正馬：鎖定反宮馬；
- 黑方先選擇中炮，其後中炮離開，再形成雙正馬：仍屬中炮開局，不鎖定屏風馬；
- 紅方相同雙馬幾何不會鎖定屏風馬／反宮馬，仍按起馬、飛相、仕角炮等選擇路徑命名。

### 3.4 主分類穩定，名稱可逐步細化

以下演進是允許的：

```text
中炮局
→ 中炮對屏風馬
→ 五七炮對屏風馬
→ 五七炮對屏風馬進七卒
```

當「中炮對屏風馬」確認後，`baseMatchupId` 保持不變；後兩步只增加 modifier 和更新展示名稱。

### 3.5 左右鏡像結果一致

左右完全鏡像的棋局必須得到相同分類 ID。原始炮、馬、車來自哪一翼可以作為內部資料保留，但不可因整盤左右鏡像而產生不同主分類。

### 3.6 FEN 只足以辨認當前棋形

標準 FEN 保存棋子位置、行棋方等局面資料，但不保存着法次序、選擇路徑、形成時間或已鎖定主體系。因此 FEN-only 不足以產生本規格要求的權威開局分類。

以下不同歷史可以到達相同 FEN，但分類不同：

- 紅方先起馬後中炮，與先中炮後進馬：棋子終點可以相同，但前者有 `proper_horse_opening → central_cannon`，後者只有中炮主選擇；
- 黑方先形成屏風馬再走仕角炮，與先走仕角炮再完成雙正馬：最終棋子位置可以相同，前者仍鎖定屏風馬，後者鎖定反宮馬；
- 一方先選中炮、中炮離位後形成雙正馬，與未選過中炮而直接形成雙正馬：當前雙馬形狀可以相同，但歷史排除結果不同。

系統提供三種處理層級：

1. **權威增量模式（MVP 主流程）**：提交上一個 backend 產生的 `RecognitionState` 加新一步 UCCI。`position_fen` 用來辨認目前棋形，`opening_memory` 保存此前已確認主選擇、形成時點及鎖定；不需要每次提交完整 move history；
2. **重播模式（測試／復原）**：提交由初始局面開始的 UCCI move history，backend 逐步呼叫同一個增量函式重建 state；用於 fixture、完整性校驗及遺失 snapshot 後復原；
3. **FEN-only 診斷模式（可選）**：沒有 `opening_memory` 時，只輸出目前可見 atomic facts、derived formations 和可能候選，固定標示 `history_unknown`，不可輸出 confirmed `choice_path`、鎖定主體系或穩定 `baseMatchupId`。

不可從 FEN 猜測缺失歷史後當作 confirmed 結果。權威 runtime state 是 `position_fen + piece_identity + opening_memory + ply + rules_version`，並非完整着法歷史。Fixture 仍建議保存 `ucciMoves` 以便人類閱讀和重現，但 classification domain API 不以完整 history 為必要參數。

## 4. 名詞定義

| 名詞 | 定義 |
|---|---|
| Ply | 一方行一步棋；一個完整回合等於兩個 ply |
| 原子事實 | 可直接由一步棋或棋盤判斷的中性事實，例如「左正馬已發展」 |
| 主選擇 | 一方明確採用的開局方向，例如中炮、飛相、起馬、挺兵 |
| 複合主體系 | 由多個原子事實推導並按角色資格鎖定、可作為 Matchup 一方主體系的棋形，例如黑方屏風馬、反宮馬、單提馬 |
| 選擇路徑 | 依時間排列的主選擇，例如起馬 → 中炮 |
| 棋形 | 由多個事實構成並有開局意義的結構，例如屏風馬、五七炮 |
| 棋形軸 | 一組互斥棋形，例如屏風馬／反宮馬／中炮雙馬結構 |
| Modifier | 不改變主分類、只令名稱更具體的特徵，例如過河車、進七卒 |
| Matchup | 由紅黑雙方選擇和棋形組合出的主對局分類 |
| Evidence | 支持某個判斷的着法、棋盤格和規則條件 |
| Pending | 尚未有足夠資料 |
| Provisional | 可展示暫定描述，但未鎖定主分類 |
| Confirmed | 主選擇、棋形或 Matchup 已確認並鎖定 |

## 5. 系統架構

```text
React 棋盤點擊
      ↓ from/to
FastAPI /api/advance（previous RecognitionState + UCCI move）
      ↓
Python UCCI 合法性驗證 → next FEN
      ↓
標準中文記譜生成
      ↓
從 next FEN 偵測目前原子事實／棋形
      ↓
合併 previous OpeningMemory（append-only）
      ↓
棋形鎖定器 + 選擇路徑偵測器
      ↓
Matchup Resolver
      ↓
名稱生成器 + Evidence
      ↓
Next RecognitionState + legalMoves
      ↓
React 棋盤、歷史及測試介面
```

建議程式結構：

```text
backend/
  app/
    api/
    domain/
      board/
      ucci/
      notation/
      facts/
      formations/
      classification/
      naming/
    rules/
    schemas/
  tests/
    fixtures/
      built_in/
      user/

frontend/
  src/
    api/
    board/
    move-history/
    analysis/
    rule-inspector/
    test-case-editor/
```

Python domain layer不得依賴 FastAPI 或 React，並應可直接由 pytest 呼叫。FastAPI 只負責 request／response、輸入校驗及 fixture 儲存。

## 6. UCCI 着法與標準中文記譜

### 6.1 UCCI 為權威內部格式

Frontend 每次棋盤操作只提交起點與終點。Backend 將合法着法表示成 UCCI 四字元座標，例如 `h2e2`。UCCI 是「一步棋」的權威格式；分類的權威累積狀態是 `RecognitionState`。重播 adapter、move history、fixture 和 pytest 仍使用 UCCI move list，但增量分類 API 不要求每次重傳整條 list。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CanonicalMove:
    ply: int
    side: str
    ucci: str
    piece_id: str
    piece_type: str
    from_square: str
    to_square: str
    captured_piece_id: str | None = None
    chinese_notation: str | None = None
```

規則使用「行棋方視角」描述左右和路線，避免紅黑各寫一套座標邏輯。所有主要 fixture 亦提供左右鏡像版本。

### 6.2 標準中文記譜只作顯示

Backend 必須根據走子前局面將每個合法 UCCI move 轉成標準中國象棋中文記譜，包括：

- 紅方中文數字及黑方阿拉伯數字；
- `進／退／平`；
- 同一路有同類棋子時使用 `前／後／中` 消歧；
- 棋子名稱使用繁體中文；
- 吃子不使用額外 `x` 符號，按中國象棋標準記譜顯示。

中文記譜不是辨認引擎輸入，不可反向用展示字串作規則條件。

## 7. 合法性檢查

互動棋盤所有走子均由 Python backend 的同一合法性引擎處理。MVP 必須處理：

- 將、士活動範圍；
- 象不能過河及塞象眼；
- 馬腿；
- 車直線阻擋；
- 炮架及吃子；
- 兵卒過河前後走法；
- 將帥照面；
- 不得走完後令己方將帥被將軍。

MVP 不處理：

- 長將、長捉裁決；
- 三次重複或自然限着；
- 勝負判決的完整競賽規則；
- 讓子棋或非標準初始局面。

## 8. 開局資料模型

### 8.1 可變棋盤狀態

```python
@dataclass
class PositionState:
    board: Board
    side_to_move: str
    ply: int
```

### 8.2 事實與證據

```python
@dataclass(frozen=True)
class EvidenceRef:
    ply: int
    message_key: str
    move: CanonicalMove | None = None
    squares: tuple[str, ...] = ()

@dataclass(frozen=True)
class FeatureOccurrence:
    id: str
    side: str
    kind: str  # choice | composite_system | formation | modifier | atomic
    formed_at_ply: int
    evidence: tuple[EvidenceRef, ...]
    related_ecco_codes: tuple[str, ...] = ()
```

`FeatureOccurrence` 一旦進入 `OpeningMemory`，沿同一棋局路線不可移除。

### 8.3 棋形鎖定

```python
@dataclass(frozen=True)
class FormationLock:
    axis: str
    feature: FeatureOccurrence
```

### 8.4 單方開局記憶

```python
@dataclass
class SideOpeningMemory:
    choice_path: list[FeatureOccurrence]
    composite_systems: list[FeatureOccurrence]
    locked_formations: dict[str, FormationLock]
    modifiers: list[FeatureOccurrence]
    atomic_history: list[FeatureOccurrence]
```

`choice_path` 只保存該角色合資格的直接選擇；`composite_systems` 只保存通過 `main_choice_roles` 後由多步推導並鎖定的主體系。兩者都可以成為 Matchup 的一方主體系。只偵測到但不具主選擇資格的紅方兵底炮、雙馬或左炮封車結構，必須放入 `modifiers`／`atomic_history`，不可混入以上兩個欄位。

### 8.5 雙方分類結果

```python
@dataclass(frozen=True)
class SideSystemRef:
    id: str
    source: str  # choice | composite_system
    formed_at_ply: int

@dataclass(frozen=True)
class MatchupResult:
    id: str
    red_system: SideSystemRef
    black_system: SideSystemRef
    confirmed_at_ply: int
    evidence: tuple[EvidenceRef, ...]
    related_ecco_codes: tuple[str, ...] = ()

@dataclass(frozen=True)
class Diagnostic:
    level: str  # info | warning | error
    code: str
    message_key: str
    ply: int | None = None
    rule_id: str | None = None

@dataclass
class ClassificationSnapshot:
    ply: int
    red: SideOpeningMemory
    black: SideOpeningMemory
    base_matchup: MatchupResult | None
    display_name: str
    certainty: str  # pending | provisional | confirmed
    has_choice_extension: bool
    has_refinements: bool
    diagnostics: list[Diagnostic]
```

使用 `certainty` 與兩個獨立旗標，而不是以單一狀態混合「確認」、「轉型」和「細化」。

### 8.6 增量辨認狀態

```python
@dataclass(frozen=True)
class SideCurrentShapes:
    atomic_ids: frozenset[str]
    formation_ids: frozenset[str]

@dataclass(frozen=True)
class CurrentShapeSnapshot:
    red: SideCurrentShapes
    black: SideCurrentShapes

@dataclass
class OpeningMemory:
    red: SideOpeningMemory
    black: SideOpeningMemory
    base_matchup: MatchupResult | None

@dataclass
class RecognitionState:
    schema_version: str
    rules_version: str
    classifier_config: ClassifierConfig
    ply: int
    position_fen: str
    piece_identity: dict[str, str]  # current square -> stable initial piece_id
    current_shapes: CurrentShapeSnapshot
    opening_memory: OpeningMemory
    current_classification: ClassificationSnapshot
```

`current_shapes` 每步由 `position_fen` 重新計算，可以隨棋子移動而出現或消失；`piece_identity` 補足標準 FEN 不保存原始棋子身份的限制；`opening_memory` 是此前主選擇及鎖定歷史，只增不減。三者合起來足以處理下一步，不需要完整 move history。

Backend 接收 client 回傳的 state 時必須驗證：

- schema／rules version 相容；
- FEN、ply、side-to-move 與新 UCCI 一致；
- `piece_identity` 與 FEN 棋種及數量一致；
- append-only memory 沒有重複 ID、非法角色主選擇或互斥 axis 衝突。

MVP 是本機測試工具，可直接傳結構化 state。若日後 state 會由不可信 client 提交，應改用 backend 簽署的 opaque token，或把 state 放入 server-side／database storage。

## 9. 原子事實、直接選擇、複合主體系與棋形

### 9.1 Side-neutral 原則

原子事實及幾何 detector 預設 `detect_for: [red, black]`。例如 `advance_flank_pawn`、雙正馬和兩馬中間炮狀態的座標邏輯對紅黑完全相同。

「偵測到棋形」不等於「升格為主選擇」。每條 choice／composite rule 必須另外宣告：

```yaml
main_choice_roles: [red, black]  # 或只寫 [black]
```

當行棋方不在 `main_choice_roles`：

- detector 仍可產生 atomic evidence 或中性 derived formation；
- 不可加入該方 `choice_path` 或 `composite_systems`；
- 不可用該 ID 建立該方 `SideSystemRef`；
- 該方既有主選擇不變，展示名稱按既有路徑決定。

因此共用的是偵測邏輯，不是所有主選擇的紅黑命名資格。「仙人指路／挺卒」可由同一動作按角色命名；「屏風馬」則是黑方主體系名稱，紅方相同雙馬結構不使用此主體系 ID。

### 9.1.1 Observation source

每條規則必須明確宣告資料來源，不要求所有主選擇使用同一種辨認方式：

| `observe_from` | 用途 |
|---|---|
| `fen` | 只看 next FEN 的目前棋子位置，例如中炮、飛相、首步正馬、首步挺三／七兵卒及複合棋形 |
| `move` | 必須知道上一手由哪格到哪格及原始 `piece_id`，例如仕角炮、過宮炮 |
| `fen_and_memory` | FEN 提供目前棋形，OpeningMemory 決定是否已選過、誰先形成及是否可升格 |
| `move_and_memory` | move 證明特定來源動作，OpeningMemory 再檢查 root／transition allowlist 和衝突 |

所有 FEN detector 產生的 `current_shapes` 可以消失；只有通過 memory policy 後加入的 choice／lock 才永久保留。`RecognitionState` 是混合規則之間處理形成次序、互斥、provisional 升格和 transition 衝突的唯一權威。

### 9.2 MVP 原子事實

第一版至少包括：

#### 炮

- 左炮／右炮平中；
- 仕角炮；
- 過宮炮；
- 卒底炮／兵底炮；
- 巡河炮；
- 過河炮；
- 平炮兌車；
- 炮原始翼別。

#### 馬

- 左正馬；
- 右正馬；
- 雙正馬；
- 左邊馬；
- 右邊馬；
- 盤河馬；
- 外盤河馬。

#### 車

- 左直車；
- 右直車；
- 左橫車；
- 右橫車；
- 巡河車；
- 過河車；
- 雙直車；
- 雙橫車。

#### 兵卒、相象與士

- 挺三路兵卒；
- 挺七路兵卒；
- 兩頭蛇；
- 飛左相象；
- 飛右相象；
- 上左士；
- 上右士。

### 9.3 MVP 直接選擇

- `central_cannon`：中炮；
- `fly_elephant`：飛相；
- `proper_horse_opening`：起馬；
- `palcorner_cannon`：仕角炮；
- `cross_palace_cannon`：過宮炮；
- `angle_pawn`：挺三／七兵作為首個開局選擇；
- `pawn_bottom_cannon`：在對方三／七線兵卒下形成的兵底炮／卒底炮。

同一方可以依次追加多個選擇，形成 `choice_path`。未符合任何已定義選擇的行棋顯示為「未定型」，但不建立任何永久 fallback choice，避免日後真正選擇中炮等體系時被阻擋。

以上七個直接選擇 ID 及下節六個複合主體系 ID，是 MVP 的 exhaustive list；部分 ID 只有黑方有主選擇資格。邊馬局、邊炮局、上仕局、河口炮、金鈎炮、挺邊兵等較少見 A0 類型暫時只記錄 atomic facts 並顯示「未定型」，不推測為最接近的已知體系；日後必須以新增 rule ID 及 fixtures 的方式擴充。

### 9.4 MVP 複合主體系

以下主體系由多個原子事實推導，不要求玩家以單一步棋直接「選擇」：

- `screen_horse`：屏風馬；
- `reverse_palace_horse`：反宮馬；
- `single_horse`：單提馬；
- `left_three_step_tiger`：左三步虎；
- `right_three_step_tiger`：右三步虎；
- `left_cannon_blockade`：左炮封車。

一經形成，先檢查 `main_choice_roles`。角色合資格才加入該方 `composite_systems` 並鎖定主體系 axis；不合資格只記錄中性棋形 evidence。Matchup Resolver 只把已升格的 composite system 視為與中炮等直接選擇同級的「一方主體系」。

因此：

```text
中炮對屏風馬
red_system  = central_cannon       # direct choice
black_system = screen_horse        # composite system

中炮對反宮馬
red_system  = central_cannon
black_system = reverse_palace_horse

中炮對單提馬
red_system  = central_cannon
black_system = single_horse
```

### 9.5 MVP 派生棋形及 modifier

- 五六炮；
- 五七炮；
- 五八炮；
- 五九炮；
- 中炮七路馬；
- 中炮右橫車；
- 中炮巡河炮；
- 中炮巡河車；
- 中炮過河車；
- 仙人指路兩頭蛇；
- 對兵互進正馬；
- 對兵轉兵底炮。

### 9.6 主選擇識別共通規則

以下定義是 MVP 主選擇的完整清單。紅黑共用 detector，但每次命中後必須再通過角色資格；不可把「共用 detector」理解成紅黑一定產生相同主選擇。

座標及棋子身份規則：

- `own_file` 使用行棋方標準記譜視角的 1–9 路；
- 所有「原始炮／馬／相／兵」都以開局時的穩定 `piece_id` 判斷，不只看目前格上的棋種；
- 規則先將原始 UCCI 歷史與完整左右鏡像比較並選出 canonical orientation；下表的標準記譜例子均指 canonical orientation；
- 左右鏡像條件寫成同一規則的 alternatives，原局與鏡像局必須輸出同一分類 ID；
- 未特別註明時，中間可以插入其他合法着法；
- 規則只在 `analysis_max_ply` 內產生新的開局選擇；
- `root_only` 只在該方 `choice_path` 尚未有已確認選擇時加入；之後相同動作只作 atomic fact 或 modifier；
- `root_or_transition` 無論是否已有選擇都可加入一次；已有選擇時形成 path extension；
- `contextual` 必須同時命中本方動作、對手已確認的上下文及 `main_choice_roles`；如本方已有選擇則形成 path extension，且確認後即使相關棋子離位也不移除；
- 每個選擇 ID 對同一方最多加入一次。

#### 9.6.1 主選擇角色資格矩陣

| ID | 紅方可作主選擇 | 黑方可作主選擇 | 紅方相同幾何的處理 |
|---|---:|---:|---|
| `central_cannon` | 是 | 是 | 正常加入中炮或選擇轉換 |
| `fly_elephant` | 是 | 是 | 正常加入飛相 |
| `proper_horse_opening` | 是 | 是 | 正常加入起馬；如已有飛相等 root choice，正馬只作棋形證據 |
| `palcorner_cannon` | 是 | 是 | 正常加入仕角炮或「起馬轉仕角炮」等選擇路徑 |
| `cross_palace_cannon` | 是 | 是 | 正常加入過宮炮 |
| `angle_pawn` | 是 | 是 | 紅方命名仙人指路；黑方按 Matchup 語境命名挺卒 |
| `pawn_bottom_cannon` | **否** | **是** | 只記 `pawn_bottom_cannon_shape`／modifier，不加入 `choice_path` |
| `screen_horse` | **否** | **是** | 只記雙正馬及中間無炮；主選擇仍按起馬、飛相等既有路徑 |
| `reverse_palace_horse` | **否** | **是** | 只記雙正馬和仕角炮結構；主選擇使用仕角炮或起馬轉仕角炮等既有路徑 |
| `single_horse` | **否** | **是** | 只記單正馬承諾棋形；主選擇仍按起馬、飛相或日後邊馬規則 |
| `left_three_step_tiger` | 是 | 是 | 按第 9.8 節形成複合主體系 |
| `right_three_step_tiger` | 是 | 是 | 按第 9.8 節形成複合主體系 |
| `left_cannon_blockade` | **否** | **是** | 只記 `left_cannon_blockade_shape`／modifier，不建立同名主體系 |

此矩陣是 MVP 的權威角色政策。新增主選擇時必須明確選擇 `[red, black]`、`[red]` 或 `[black]`，不可依靠名稱模板暗中推斷。

### 9.7 所有直接選擇的精確定義

| ID | 模式 | 主選擇角色 | Side-neutral 識別條件 | 紅方結果 | 黑方結果 |
|---|---|---|---|---|---|
| `central_cannon` | `root_or_transition` | 紅、黑 | 原始 2 路炮平至 5 路，或原始 8 路炮平至 5 路；炮必須仍在原始炮線上 | 中炮 | 中炮 |
| `fly_elephant` | `root_only` | 紅、黑 | 原始 3 路相象進至 5 路中心相位，或原始 7 路相象進至 5 路中心相位，即 `相三進五／相七進五` 的 side-neutral 等價 | 飛相局 | 飛象 |
| `proper_horse_opening` | `root_only` | 紅、黑 | 原始 2 路馬內進至 3 路正馬位，或原始 8 路馬內進至 7 路正馬位；atomic `proper_horse_left/right` 無論是否 root 都要記錄 | 起馬局 | 進正馬；複合體系形成前只作暫定描述 |
| `palcorner_cannon` | `root_or_transition` | 紅、黑 | 原始 2 路炮平至同翼 4 路，或原始 8 路炮平至同翼 6 路，即 `炮二平四／炮八平六` 的 side-neutral 等價 | 仕角炮／起馬轉仕角炮等 | 仕角炮；可成為反宮馬形成條件 |
| `cross_palace_cannon` | `root_only` | 紅、黑 | 原始 2 路炮越過中線平至 6 路，或原始 8 路炮越過中線平至 4 路，即 `炮二平六／炮八平四` 的 side-neutral 等價 | 過宮炮 | 過宮炮 |
| `angle_pawn` | `root_only` | 紅、黑 | 原始 3 路或 7 路兵卒向前一步；只有在 `choice_path` 為空時是主選擇 | 仙人指路 | 挺三／七卒；按對手體系可顯示「起馬對挺卒」等名稱 |
| `pawn_bottom_cannon` | `contextual` | **只限黑** | 對方已確認 3／7 路 `angle_pawn`，本方相應原始炮平至該三／七線炮位；炮、兵卒必須屬同一鏡像關係，不接受任意炮平三／七路 | 不產生主選擇；只記後續兵底炮棋形 | 卒底炮主選擇 |

`central_cannon` 和 `palcorner_cannon` 可形成選擇轉換；其餘 `root_only` 動作若在另一主選擇之後出現，不會新增 choice，但仍可成為 modifier 或複合主體系證據。

`pawn_bottom_cannon` 的 canonical 黑方例子是：

```text
兵三進一　炮８平７
```

完整左右鏡像是：

```text
兵七進一　炮２平３
```

紅方作為回應方時可以偵測完全相同的幾何關係，但只加入 `pawn_bottom_cannon_shape`／modifier；不可把 `pawn_bottom_cannon` 加入紅方 `choice_path`，亦不可建立紅方兵底炮 `SideSystemRef`。

### 9.8 所有複合主體系的精確定義

所有複合主體系 detector 都可讀取紅黑幾何事實；只有角色在 `main_choice_roles` 內，才使用 `axis: defensive_system` 首次確認後鎖定並加入 `composite_systems`。不合資格一方只記錄中性 atomic／derived formation，不鎖定同名主體系。以下「左／右」是 canonical orientation 下的開局分類名稱，不是螢幕上的固定物理方向；整盤左右鏡像後仍輸出同一分類 ID。

#### `screen_horse`

- 兩隻原始馬均已到正馬位；
- 雙正馬首次完成當刻，中間無本方炮；
- 此前 `choice_path` 無 `central_cannon` 或 `palcorner_cannon`；
- `defensive_system` 未鎖定；
- `main_choice_roles: [black]`；只有黑方成立後可作主體系，對手為中炮時 Matchup 是「中炮對屏風馬」；
- 紅方相同結構只保留 `double_proper_horses` 及 `inter_horse_cannon_none`，主選擇按此前的起馬、飛相等路徑決定。

#### `reverse_palace_horse`

- 兩隻原始馬均已到正馬位；
- 雙正馬首次完成當刻，中間為本方仕角炮；
- 此前無 `central_cannon`；
- `defensive_system` 未鎖定；
- `main_choice_roles: [black]`；只有黑方成立後可作主體系，對手為中炮時 Matchup 是「中炮對反宮馬」；
- 紅方相同結構不命名反宮馬，主選擇按歷史為仕角炮、起馬轉仕角炮等。

#### `single_horse`

- 恰好一隻原始馬在正馬位；
- 另一翼作出明確非雙正馬承諾，符合以下其中之一：
  - 另一隻原始馬走到邊馬位；
  - 另一翼原始車進一，形成單提馬橫車起點；
- 本方此前無 `central_cannon`；
- `defensive_system` 未鎖定；
- 不可因「暫時只有一隻正馬」而鎖定，必須有上述第二項正面證據；
- `main_choice_roles: [black]`；仕角炮可以先出現，形成黑方「仕角炮轉單提馬」路徑，但不可已有屏風馬或反宮馬鎖定；
- 紅方相同結構只記單正馬承諾棋形，主選擇維持起馬、飛相，或日後新增的邊馬選擇。

#### `left_three_step_tiger`

本方完成以下三個核心事件，次序可以交換，中間可插入三／七線挺卒：

```text
左正馬：馬８進７
左車移位：車９平８
左炮歸邊：炮８平９
```

以上着法按行棋方視角解讀，鏡像局由同一 rule alternative 處理。`main_choice_roles: [red, black]`。此前不可有中炮、仕角炮或已鎖定 `defensive_system`。

#### `right_three_step_tiger`

MVP 採用較早可確認的結構：

```text
右正馬：馬２進３
右炮歸邊：炮２平１
```

`main_choice_roles: [red, black]`。兩項完成後鎖定；不可只有右正馬。此前不可有中炮、仕角炮或已鎖定 `defensive_system`。如日後需要更嚴格版本，可以新增車發展條件，但不得靜默改變既有 fixture。

#### `left_cannon_blockade`

本方完成：

```text
左正馬：馬８進７
左車移位：車９平８
左炮封車：炮８進４
```

三項次序可按規則容許交換，中間可插入三／七線挺卒。`main_choice_roles: [black]`：黑方成立後鎖定 `left_cannon_blockade`；如其後另一門炮平中，追加「左炮封車轉列炮」transition／refinement，但不刪除已鎖定體系。紅方相同結構只記 `left_cannon_blockade_shape`／modifier，不建立同名主體系或 transition 起點。

### 9.9 一方有效主體系的選擇

`choice_path` 和 `composite_systems` 都保存歷史；Matchup Resolver 另行產生 `SideSystemRef`：

1. 已按角色資格鎖定複合主體系時，複合主體系優先於其前置 atomic／起馬選擇，例如黑方由一隻正馬發展成屏風馬後，`black_system = screen_horse`；紅方相同棋形因不具資格，不會走此分支；
2. 無複合主體系時，使用 `choice_path` 最後一個適用選擇；
3. 「起馬 → 中炮」使用 `central_cannon` 作有效主體系，但名稱保留「起馬轉中炮」；
4. base Matchup 已確認後不再更換，只可加入 transition 或 modifier；
5. 未有符合條件的主體系時，狀態為 provisional／未定型，不寫入永久 fallback choice。

### 9.10 特殊 Matchup 並非單方主選擇

- `順炮`、`列炮` 是雙方均為 `central_cannon` 後，根據兩門原始炮翼關係生成的 Matchup alias；
- `對兵局` 是雙方均為 `angle_pawn`，而且是 `兵三進一、卒３進１` 或其完整左右鏡像時生成的 Matchup alias；
- 所以單方唔會有 `same_direction_cannon`、`opposite_direction_cannon` 或 `opposing_pawns` 主選擇 ID。

### 9.11 紅黑着法與 UCCI 對照矩陣

這一節是實作及 fixture 的座標真值表。`A | B` 表示左右鏡像 alternatives；兩者命中同一 ID。中文着法只用作閱讀及驗收，recognizer 仍以 UCCI、`piece_id` 和事件歷史判斷。

#### 直接選擇

| ID | 紅方着法／UCCI 及結果 | 黑方着法／UCCI 及結果 |
|---|---|---|
| `central_cannon` | 炮二平五 `h2e2` \| 炮八平五 `b2e2` | 炮２平５ `b7e7` \| 炮８平５ `h7e7` |
| `fly_elephant` | 相三進五 `g0e2` \| 相七進五 `c0e2` | 象３進５ `c9e7` \| 象７進５ `g9e7` |
| `proper_horse_opening` | 馬二進三 `h0g2` \| 馬八進七 `b0c2` | 馬２進３ `b9c7` \| 馬８進７ `h9g7` |
| `palcorner_cannon` | 炮二平四 `h2f2` \| 炮八平六 `b2d2` | 炮２平４ `b7d7` \| 炮８平６ `h7f7` |
| `cross_palace_cannon` | 炮二平六 `h2d2` \| 炮八平四 `b2f2` | 炮２平６ `b7f7` \| 炮８平４ `h7d7` |
| `angle_pawn` | 兵三進一 `g3g4` \| 兵七進一 `c3c4` | 卒３進１ `c6c5` \| 卒７進１ `g6g5` |
| `pawn_bottom_cannon` | 對 `c6c5`：炮八平七 `b2c2`；鏡像對 `g6g5`：炮二平三 `h2g2`；**只產生後續棋形，不觸發主選擇** | 對 `g3g4`：炮８平７ `h7g7`；鏡像對 `c3c4`：炮２平３ `b7c7`；觸發卒底炮主選擇 |

#### 複合主體系

| ID | 主選擇角色 | 紅方相同幾何／UCCI 及結果 | 黑方 positive evidence／UCCI 及結果 |
|---|---|---|---|
| `screen_horse` | **只限黑** | `b0c2` + `h0g2` 且兩馬之間無炮；只記雙正馬棋形，**不產生 `screen_horse`** | `b9c7` + `h9g7` 且兩馬之間無炮；觸發屏風馬 |
| `reverse_palace_horse` | **只限黑** | `b0c2` + `h0g2` + (`h2f2` \| `b2d2`)；保留仕角炮／起馬轉仕角炮，**不產生 `reverse_palace_horse`** | `b9c7` + `h9g7` + (`b7d7` \| `h7f7`)；觸發反宮馬 |
| `single_horse` | **只限黑** | 恰一正馬加另一翼邊馬／橫車承諾；保留起馬、飛相或日後邊馬選擇，**不產生 `single_horse`** | 恰一項 `b9c7`／`h9g7`；另一翼原始馬走邊 `b9a7`／`h9i7`，或同翼原始車進一 `a9a8`／`i9i8`；按翼別配對後觸發單提馬 |
| `left_three_step_tiger` | 紅、黑 | 馬八進七 `b0c2` + 車九平八 `a0b0` + 炮八平九 `b2a2`；觸發主體系 | 馬８進７ `h9g7` + 車９平８ `i9h9` + 炮８平９ `h7i7`；觸發主體系 |
| `right_three_step_tiger` | 紅、黑 | 馬二進三 `h0g2` + 炮二平一 `h2i2`；觸發主體系 | 馬２進３ `b9c7` + 炮２平１ `b7a7`；觸發主體系 |
| `left_cannon_blockade` | **只限黑** | 馬八進七 `b0c2` + 車九平八 `a0b0` + 炮八進四 `b2b6`；只記後續棋形，**不產生 `left_cannon_blockade`** | 馬８進７ `h9g7` + 車９平８ `i9h9` + 炮８進４ `h7h3`；觸發左炮封車 |

對複合主體系而言，上表只列 positive geometry；第 9.8 節的排除條件、首次確認時點、角色資格及 `defensive_system` 鎖定仍然全部適用。`main_choice_roles: [black]` 的規則必須以「黑方形成＝正例、紅方形成＝同名主選擇反例」測試；所有規則另需鏡像和只差一項條件的 near-miss。

## 10. 屏風馬、反宮馬與中炮歷史

這是 MVP 最重要的歷史敏感規則。中間炮狀態 detector 對紅黑共用，但 `screen_horse`、`reverse_palace_horse` 和 `single_horse` 的主體系升格只適用於黑方。

### 10.1 中間炮狀態

當任一方首次完成雙正馬時都計算下列中性狀態；只有黑方會把結果送入屏風馬／反宮馬主體系 resolver：

```python
from enum import StrEnum

class InterHorseCannonState(StrEnum):
    NONE = "none"
    CENTRAL_CANNON = "central_cannon"
    PALCORNER_CANNON = "palcorner_cannon"
    OTHER = "other"
```

### 10.2 屏風馬

黑方屏風馬成立條件：

1. 該方首次形成雙正馬；
2. 形成當刻正馬中間無炮；
3. 在形成當刻之前，`choice_path` 不包含中炮或仕角炮；
4. `defensive_system` 尚未鎖定。

成立後鎖定：

```text
defensive_system = screen_horse
```

紅方符合相同四項幾何及歷史條件時，不執行上述鎖定；只留下雙正馬及無中間炮 evidence，紅方主選擇維持起馬、飛相或其他既有路徑。

### 10.3 反宮馬

黑方反宮馬成立條件：

1. 該方首次形成雙正馬；
2. 形成當刻正馬中間為仕角炮，或此前已選擇仕角炮而該炮仍構成相應結構；
3. 此前沒有中炮主選擇；
4. `defensive_system` 尚未鎖定。

紅方符合相同結構時，不鎖定反宮馬；以其 `choice_path` 顯示仕角炮、起馬轉仕角炮等名稱。

### 10.4 中炮歷史優先

如黑方已在 `choice_path` 選擇中炮，後來即使：

- 中炮離開；
- 再形成雙正馬；
- 當前正馬中間無炮；

仍不可新增屏風馬主棋形。雙正馬只記錄為原子事實或 modifier。紅方無論有否中炮歷史，本來就不會升格為屏風馬；紅方中炮歷史仍按 append-only 原則保留。

### 10.5 形成後不可改判

若黑方雙正馬、中間無炮已首先鎖定屏風馬，其後走仕角炮：

- 屏風馬鎖定保持；
- 仕角炮可以成為新選擇、轉型或 modifier；
- 不會改判反宮馬。

## 11. 選擇轉換

一般轉換 detector 對紅黑共用，但 transition 仍須繼承來源主選擇的角色資格；黑方限定的 `left_cannon_blockade` 不可在紅方成為 transition 起點。

MVP 至少支援：

- 起馬 → 中炮；
- 仙人指路／挺卒 → 中炮；
- 左炮封車 → 列炮；
- 三步虎 → 列炮。

轉換事件：

```python
@dataclass(frozen=True)
class TransitionEvent:
    id: str
    side: str
    from_choice_id: str
    to_choice_id: str
    at_ply: int
    evidence: tuple[EvidenceRef, ...]
```

名稱例子：

```text
起馬轉中炮
仙人指路轉中炮
中炮對左炮封車轉列炮
```

## 12. 規則資料格式

建議規則目錄：

```text
rules/
  atomic-features.yaml
  choices.yaml
  composite-systems.yaml
  derived-formations.yaml
  transitions.yaml
  matchup-names.yaml
  variation-templates.yaml
  locales/
    zh-Hant.yaml
```

### 12.1 屏風馬示例

```yaml
id: screen_horse
kind: composite_system
axis: defensive_system
detect_for: [red, black]
main_choice_roles: [black]
lock_policy: first_confirmed

trigger:
  all:
    - atomic: double_proper_horses
    - position:
        inter_horse_cannon: none

history:
  none_before_trigger:
    - choice: central_cannon
    - choice: palcorner_cannon

evidence:
  include:
    - proper_horse_left
    - proper_horse_right
```

### 12.2 選擇轉換示例

```yaml
id: proper_horse_to_central_cannon
kind: transition
detect_for: [red, black]
main_choice_roles: [red, black]

path:
  ordered:
    - proper_horse_opening
    - central_cannon

name_key: transition.proper_horse_to_central_cannon
```

### 12.3 Matchup 示例

```yaml
id: central_vs_screen_horse
kind: matchup

when:
  red:
    choice_path_contains: central_cannon
  black:
    composite_system_contains: screen_horse

name_key: matchup.central_vs_screen_horse
related_ecco_codes:
  - C00-C99
```

### 12.4 規則校驗

建置時必須檢查：

- ID 不重複；
- 引用的 feature、axis 和 name key 存在；
- 每條 choice／composite／transition 規則均明確宣告 `detect_for` 及 `main_choice_roles`，而後者必須是前者的子集；
- 同一 axis 的規則都有明確 lock policy；
- Matchup 不可在某角色引用該角色不具 `main_choice_roles` 資格的 ID，例如不可建立 `red_system = screen_horse`；
- Matchup 的紅黑主體系只可引用已定義的直接選擇或複合主體系；
- 規則循環依賴必須報錯；
- 每條正式規則至少有一個正例和一個反例 fixture。

## 13. 辨認演算法

### 13.1 單步處理

```text
1. 接收 frontend 提交的 from/to，轉成候選 UCCI 着法並驗證
2. 由 previous RecognitionState 驗證着法，產生 next FEN 及更新 piece_identity
3. 根據走子前局面生成標準中文記譜
4. 從 next FEN 偵測目前棋形，並為行棋方產生新原子事實
5. 偵測直接選擇幾何；角色在 main_choice_roles 才追加 choice_path，否則只記中性棋形
6. 對尚未鎖定的棋形軸檢查形成條件
7. 首次符合時先檢查角色資格；合資格才鎖定主體系並加入 composite_systems，不合資格只追加 derived formation／modifier
8. 只從角色合資格的來源主選擇追加 transition；再追加 modifier
9. 如 baseMatchup 尚未確認，嘗試確認
10. 根據更新後 OpeningMemory 生成展示名稱
11. 產生 next RecognitionState、ClassificationSnapshot、標準記譜及下一手 legalMoves
```

預設只有擁有該棋形的一方自行行棋後，才可觸發新的主選擇或棋形鎖定。對手吃掉一隻阻擋棋子，不應憑空令另一方獲得新開局選擇。個別規則如需要例外，必須明確宣告。

### 13.2 偽代碼

```python
def advance_state(
    previous: RecognitionState,
    ucci: str,
) -> AdvanceResult:
    validate_recognition_state(previous)
    position = position_from_state(previous)
    memory = deepcopy(previous.opening_memory)

    move = validate_ucci_move(position, ucci)
    move = with_chinese_notation(move, position)
    next_position = apply_legal_move(position, move)
    side = move.side
    observations = inspect_fen(
        next_position.fen,
        next_position.piece_identity,
        move,
        side,
    )

    append_atomic_facts(memory[side], observations)
    append_role_eligible_choices(memory[side], observations, side)
    formation_hits = detect_formations(memory[side], observations, next_position)
    promote_role_eligible_composites(memory[side], formation_hits, side)
    append_non_primary_shapes(memory[side], formation_hits, side)
    append_role_eligible_transitions(memory[side], side)
    append_modifiers(memory[side], observations)
    confirm_base_matchup_once(memory)

    next_state = build_recognition_state(next_position, memory, previous.classifier_config)
    return AdvanceResult(
        move=move,
        state=next_state,
        legal_moves=generate_legal_ucci_moves(next_position),
    )


def classify_game(ucci_moves: list[str], config: ClassifierConfig) -> ClassificationTimeline:
    """Replay／fixture adapter；不是增量 classifier 的必要輸入形式。"""
    state = create_initial_recognition_state(config)
    results: list[AdvanceResult] = []
    for ucci in ucci_moves[: config.analysis_max_ply]:
        result = advance_state(state, ucci)
        results.append(result)
        state = result.state
    return timeline_from_results(results)
```

### 13.3 Undo、跳步及修改舊着法

OpeningMemory 對單一路線是 append-only。UI timeline 每個 ply 保存 backend 回傳的 immutable `RecognitionState` snapshot；回到較早 ply 時直接選取該 snapshot，不在最新 state 上刪除記憶。

```text
查看 ply 8
→ 使用 timeline.states[8]

在 ply 5 修改着法
→ 刪除原 ply 6 之後着法
→ 以 timeline.states[5] + 新 UCCI 呼叫 advanceState
→ 建立新分支的下一個 immutable state
```

如果 snapshot 遺失、rules version 改變或完整性校驗失敗，才以保存的 UCCI history 從初始 state 重播復原。這可避免 undo 邏輯破壞歷史不變量，同時不要求正常操作每次重播全局。

## 14. Matchup Resolver 與名稱生成

### 14.1 命名順序

1. 特殊公認名稱；
2. 已知標準 Matchup；
3. 選擇轉換模板；
4. 紅方子棋形 + 對 + 黑方主棋形 + 黑方 modifier；
5. 無正式名稱時，顯示雙方描述，不創造正式分類 ID。

### 14.2 特殊名稱

#### 順炮／列炮

雙方都選擇中炮時，根據兩門中炮的原始炮翼及雙方相對方向，使用規則資料表決定順炮或列炮。方向映射必須集中定義，不可散落在 UI 或 UCCI／notation module。

#### 對兵

「對兵局」只適用於三、七線相應兵卒互進，不是任意兩枚兵卒都可以形成對兵。

接受的標準記譜關係為：

```text
兵三進一　卒３進１
```

以及整盤左右鏡像：

```text
兵七進一　卒７進１
```

規則必須以雙方行棋方視角及明確 file mapping 判斷，不可只檢查「雙方都曾挺一隻兵卒」。中兵、邊兵或不相應的三七線組合均不得輸出對兵局。

如只有紅方首步挺三／七兵，按語境命名為「仙人指路」；如黑方以挺三／七卒回應其他開局，顯示「挺卒」。

### 14.3 一般模板

```yaml
- id: five_seven_vs_screen_horse_with_7th_pawn
  base_matchup: central_vs_screen_horse
  requires:
    red:
      modifier: five_seven_cannons
    black:
      modifier: advanced_7th_pawn
  template: "{redFormation}對{blackFormation}{blackModifier}"
```

結果：

```text
五七炮對屏風馬進七卒
```

### 14.4 名稱與分類 ID 分離

以下 ID 保持穩定：

```text
central_vs_screen_horse
```

展示名稱可由：

```text
中炮對屏風馬
```

逐步細化成：

```text
五七炮左直車對屏風馬進七卒
```

不得以展示字串作為程式判斷依據。

## 15. 分析回合設定

### 15.1 全局設定

```python
@dataclass(frozen=True)
class ClassifierConfig:
    analysis_max_ply: int = 20
    include_provisional: bool = True
    mirror_validation: bool = False
```

- 預設 `analysisMaxPly = 20`；
- UI 可設定 2–60 ply；
- config 是 `RecognitionState` 一部分；正常 `/api/advance` 不可中途靜默改 config；
- 調高或調低上限後，UI 使用已保存 UCCI history 呼叫 `/api/analyze` 由初始 state 重算一次，並替換整條 timeline snapshots；
- 規則可以另設 `eligibleUntilPly`，限制某個主選擇最遲何時仍算開局選擇；
- 超過上限後 `/api/advance` 仍更新 FEN、piece identity、中文記譜和 legal moves，但不再新增開局 choice／composite system；
- 已在期限內確認的歷史不會因其後 ply 超過期限而消失。

### 15.2 暫定判斷

未足以鎖定主分類時，可以顯示：

```text
紅：中炮
黑：已進一隻正馬
暫定：中炮對進馬
```

此時：

- `certainty = provisional`；
- 不設 `baseMatchupId`；
- 後來形成屏風馬、反宮馬或單提馬時才正式確認。

## 16. MVP 開局覆蓋範圍

### 16.1 主選擇與基礎體系

- 飛相；
- 起馬；
- 仕角炮；
- 過宮炮；
- 中炮；
- 仙人指路／挺卒；
- 兵底炮／卒底炮；
- 屏風馬；
- 反宮馬；
- 單提馬；
- 左／右三步虎；
- 左炮封車；
- 未定型（只作畫面 fallback，不寫入歷史）。

### 16.2 主要 Matchup

- 中炮對屏風馬；
- 中炮對反宮馬；
- 中炮對單提馬；
- 中炮對左／右三步虎；
- 順炮；
- 列炮；
- 後補列炮；
- 仙人指路對卒底炮；
- 對兵局；
- 起馬對挺卒；
- 飛相對進馬；
- 飛相對中炮；
- 過宮炮對中炮；
- 仕角炮對中炮。

### 16.3 具體變例層

- 五六炮；
- 五七炮；
- 五八炮；
- 五九炮；
- 中炮七路馬；
- 中炮右橫車；
- 中炮巡河炮；
- 中炮巡河車；
- 中炮過河車；
- 互進七兵；
- 平炮兌車；
- 進三／七兵卒；
- 左／右直車；
- 左／右橫車；
- 兩頭蛇。

### 16.4 ECCO 參考

每條 Matchup 或 variation 可附上 `relatedEccoCodes`，例如：

```json
{
  "id": "central_vs_screen_horse",
  "relatedEccoCodes": ["C00-C99"]
}
```

此欄只表示概念來源或涵蓋範圍，不表示輸出等同該 ECCO code。

參考資料：

- [ECCO 目錄](https://www.xqbase.com/ecco/ecco_contents.htm)
- [ECCO 說明](https://www.xqbase.com/ecco/ecco_intro.htm)
- [ECCO 常見問題](https://www.xqbase.com/ecco/ecco_faq.htm)

## 17. 前端功能規格

### 17.1 整體版面

桌面版採三欄：

```text
┌────────────┬─────────────┬──────────────────────┐
│ 象棋棋盤   │ 着法與時間線 │ 判斷結果／證據／規則 │
└────────────┴─────────────┴──────────────────────┘
```

窄螢幕改為：棋盤、着法、分析三個可切換頁籤。

### 17.2 操作控制

- 新棋局；
- 清除；
- 棋盤翻轉；
- 左右鏡像測試；
- 分析 ply 上限；
- 顯示／隱藏 provisional 判斷。

MVP 不提供匯入 UCCI／ICCS、匯入中文着法、複製 UCCI 或複製分析 JSON。所有着法只可以透過棋盤點擊產生。

### 17.3 互動棋盤

- 9×10 中國象棋棋盤；
- 點擊棋子後顯示所有合法落點；
- 最近一步以起點／終點標示；
- 點擊 Evidence 時高亮相關棋子和格；
- 可選紅方或黑方視角；
- 非法操作顯示原因；
- 不加入 AI、自動走棋或局面評分。

### 17.4 着法與分類時間線

每個 ply 顯示：

- backend 生成的標準中國象棋中文着法；
- 該步產生的新原子事實；
- 新增主選擇；
- 新增複合主體系；
- 新鎖定棋形；
- 新 modifier；
- 名稱是否更新。

分類事件使用不同圖示：

```text
● 主選擇
◆ 棋形鎖定
→ 選擇延伸
+ 變例細化
```

點擊任意 ply，棋盤和右方分析均顯示該歷史前綴的結果。

### 17.5 判斷結果頁籤

顯示：

- 目前展示名稱；
- certainty；
- 穩定 `baseMatchupId`；
- 首次確認 ply；
- 相關 ECCO 範圍；
- 由目前 FEN 即時計算、可以消失的 `current_shapes`；
- 由此前判斷累積、不可因棋子離位而消失的 `opening_memory`；
- 紅方 `choice_path`；
- 黑方 `choice_path`；
- 雙方已鎖定棋形；
- 雙方 modifier；
- 未有正式名稱時的描述性結果。

### 17.6 紅方／黑方 Profile 頁籤

兩方 UI 結構完全相同，只以顏色和角色區分。每個項目顯示：

- 中性 feature ID；
- 語境化中文名稱；
- `detect_for` 與 `main_choice_roles`；
- 本次是「只偵測到棋形」還是「已升格為主選擇」；
- formedAtPly；
- 所屬 axis；
- 是否已鎖定；
- Evidence 着法；
- 原始規則 ID。

### 17.7 規則證據頁籤

對已命中的每條規則顯示：

- 規則名稱及 ID；
- 所有必要條件及命中結果；
- 歷史排除條件；
- 用作證據的着法；
- 鎖定時間；
- 為何未被另一規則取代。

對 provisional 候選顯示尚欠條件，例如：

```text
屏風馬候選
✓ 已有左正馬
✗ 尚未形成右正馬
? 中間炮狀態待確認
```

### 17.8 規則瀏覽器

測試前端提供只讀規則瀏覽：

- 按 feature／formation／matchup／variation 分組；
- 以 ID 或中文名稱搜尋；
- 查看 YAML/JSON 等價內容；
- 查看正例／反例 fixture；
- 顯示規則依賴關係；
- 顯示角色資格；黑方限定規則要明示「紅方同形只作後續棋形」；
- MVP 不提供在瀏覽器直接修改和保存規則。

### 17.9 開局 test case 編輯器

完成基本棋盤 UI 後，必須加入「儲存為測試案例」區域，讓使用者將目前棋局變成正式 recognition fixture。

Test case 支援兩種模式：

- `game_line`：保存完整 UCCI move list，由初始 state 重播，最適合整盤行棋及命名測試；
- `state_transition`：保存某 ply 的 previous `RecognitionState` 加下一步 UCCI，直接測試 FEN + 既有主選擇歷史如何產生 next state，不需要保存此前全部着法。

不可只保存裸 FEN 後期望 confirmed 主選擇。每個案例必須保存其 mode 所需輸入，並包括：

- `game_line` 的完整 UCCI move list及每步標準中文記譜快照；或 `state_transition` 的 previous RecognitionState、下一步 UCCI 和預期 next state；
- 最終／next FEN，作棋形輸入及肉眼核對；
- 分析截止 ply；
- 預期紅方直接選擇及 `choice_path`；
- 預期紅方複合主體系；
- 預期黑方直接選擇及 `choice_path`；
- 預期黑方複合主體系；
- 預期 baseMatchupId；
- 預期展示名稱；
- 可選的預期 `current_shapes`，用來單獨驗證 FEN 棋形 detector；
- 可選的預期 modifier；
- 可選的預期非主體系 derived formation，例如紅方 `pawn_bottom_cannon_shape`；
- 可選的「不得出現」主體系、棋形、modifier 或 Matchup；
- 測試名稱、備註及建立時間。

主體系、棋形及 Matchup 以規則 ID 下拉選擇，避免輸入拼錯 ID；展示名稱可以文字輸入，亦可以選擇「不比較展示名稱」。

操作流程：

```text
在棋盤行棋
→ 停在要測試的 ply
→ 點擊「儲存為測試案例」
→ 選擇 game_line 或 state_transition
→ UI 預填目前實際偵測結果
→ 使用者修改成正確期望值
→ backend 校驗並保存 JSON fixture
→ 可立即執行此案例
```

UI 必須提供：

- 新增、修改及刪除 test case；
- 以棋盤重新開啟案例；
- 執行單一案例；
- 執行全部使用者案例；
- 顯示 pass／fail；
- fail 時顯示 expected vs actual 差異；
- 點擊差異跳到首次偏離的 ply；
- 顯示 backend／rules 版本或 git commit（如可取得）。

案例由 backend 保存到：

```text
backend/tests/fixtures/user/<case-id>.json
```

pytest 必須讀取同一批 JSON，而不是另抄一份測試資料。使用者在 UI 保存的新案例，下一次執行 pytest 時即可用來測試 recognition logic。

### 17.10 非法操作及 API 錯誤

- Frontend 只容許選擇 backend 回傳的 legalMoves；
- Backend 仍必須重新驗證每一步，不可信任 frontend；
- 非法走子顯示原因及相關棋盤格；
- API 或規則載入失敗時保留目前着法歷史，並清楚顯示錯誤；
- 不可在 backend 拒絕某步後仍將該步加入前端歷史。

## 18. Python service 與 FastAPI contract

### 18.1 Domain service

```python
def validate_ucci_move(position: PositionState, ucci: str) -> CanonicalMove: ...

def generate_legal_ucci_moves(position: PositionState) -> list[str]: ...

def to_standard_chinese_notation(
    position_before_move: PositionState,
    move: CanonicalMove,
) -> str: ...

def create_initial_recognition_state(config: ClassifierConfig) -> RecognitionState: ...

def advance_state(
    previous: RecognitionState,
    ucci: str,
) -> AdvanceResult: ...

def classify_game(
    ucci_moves: list[str],
    config: ClassifierConfig,
) -> ClassificationTimeline: ...

def classify_at_ply(
    ucci_moves: list[str],
    ply: int,
    config: ClassifierConfig,
) -> ClassificationSnapshot: ...

def mirror_game(ucci_moves: list[str]) -> list[str]: ...

def explain_rule(
    rule_id: str,
    snapshot: ClassificationSnapshot,
) -> RuleExplanation: ...
```

Domain service 不可 import FastAPI，方便 pytest 直接測試。

### 18.2 增量 State API（MVP 主流程）

```http
POST /api/state/initial
POST /api/advance
```

`/api/state/initial` 接收 classifier config，回傳初始 `RecognitionState` 和 legal moves。

`/api/advance` Request：

```json
{
  "state": {
    "schemaVersion": "1",
    "rulesVersion": "mvp-1",
    "classifierConfig": {
      "analysisMaxPly": 20,
      "includeProvisional": true,
      "mirrorValidation": false
    },
    "ply": 0,
    "positionFen": "...",
    "pieceIdentity": {},
    "currentShapes": {},
    "openingMemory": {},
    "currentClassification": {}
  },
  "ucciMove": "h2e2"
}
```

Response 至少包括：

```json
{
  "move": {
    "ply": 1,
    "ucci": "h2e2",
    "chineseNotation": "炮二平五"
  },
  "state": {
    "schemaVersion": "1",
    "rulesVersion": "mvp-1",
    "classifierConfig": {
      "analysisMaxPly": 20,
      "includeProvisional": true,
      "mirrorValidation": false
    },
    "ply": 1,
    "positionFen": "...",
    "pieceIdentity": {},
    "currentShapes": {},
    "openingMemory": {},
    "currentClassification": {}
  },
  "legalMoves": ["..."]
}
```

以上 JSON 內的空 object 只為縮短示例；正式 Pydantic schema 必須完整。Backend 不保存 session；每次 response 的 `state` 是下一次 request 的輸入。Frontend 每個 ply 保存該 immutable state snapshot。

### 18.3 重播分析 API（測試／復原）

```http
POST /api/analyze
```

Request：

```json
{
  "ucciMoves": ["h2e2"],
  "analysisMaxPly": 20,
  "includeProvisional": true
}
```

Response 至少包括：

```json
{
  "moves": [
    {
      "ply": 1,
      "ucci": "h2e2",
      "chineseNotation": "炮二平五"
    }
  ],
  "positionFen": "...",
  "legalMoves": ["..."],
  "snapshots": [],
  "currentClassification": {}
}
```

`/api/analyze` 逐步呼叫 `advance_state()`，只用於 fixture runner、snapshot 遺失後復原、rules version 更新後重算及一致性檢查。正常棋盤行棋、undo、跳步或修改舊着法不需要每次提交完整 UCCI 前綴。

### 18.4 Test case API

```http
GET    /api/test-cases
POST   /api/test-cases
GET    /api/test-cases/{id}
PUT    /api/test-cases/{id}
DELETE /api/test-cases/{id}
POST   /api/test-cases/{id}/run
POST   /api/test-cases/run-all
```

Backend 必須防止 path traversal，case ID 只容許安全 slug，並以原子寫入方式保存 JSON fixture。

## 19. 測試規格

### 19.1 單元測試

#### 棋盤與着法

- 每種棋子合法着法；
- 馬腿、象眼、炮架；
- 將帥照面和自將檢查；
- UCCI 座標驗證及重播；
- UCCI 至標準中文記譜；
- 前／後／中同類棋子消歧；
- 左右鏡像後着法仍合法。

#### 歷史不變量

- 已加入 `choice_path` 的選擇不可消失；
- formation lock 不可被第二條同 axis 規則覆蓋；
- modifier 只追加一次；
- baseMatchupId 確認後保持不變；
- 對同一前綴，逐步 `advance_state`、保存 snapshot 後直接讀取，以及 `/api/analyze` 重播所得結果完全相同；
- `RecognitionState` 經 Pydantic serialize／deserialize round-trip 後結果不變；
- rules version 不相容或 FEN／piece identity 不一致的 state 必須被拒絕。

### 19.2 必須存在的核心 fixture

1. 一方先選中炮，中炮後來離開，再出齊雙正馬：仍為中炮開局，不得判為屏風馬；
2. 先起馬，後行中炮：`choice_path` 為起馬 → 中炮，名稱含「起馬轉中炮」；
3. 先仙人指路，後行中炮：保留仙人指路，名稱含「仙人指路轉中炮」；
4. 雙正馬形成當刻中間無炮，且此前無中炮／仕角炮：鎖定屏風馬；
5. 仕角炮在先，雙正馬在後：鎖定反宮馬；
6. 屏風馬已鎖定後再行仕角炮：保持屏風馬，不改判反宮馬；
7. 雙方選中炮：按炮方向正確輸出順炮或列炮；
8. 紅方首步挺兵：顯示仙人指路；同一動作作為黑方應法：顯示挺卒；
9. `兵三進一、卒３進１` 及其左右鏡像輸出對兵局；中兵、邊兵或不相應三七線兵卒不得輸出對兵局；
10. 中炮對屏風馬後形成五七炮、黑進七卒：baseMatchup 不變，名稱細化；
11. 在關鍵着法之間插入規則未提及的合法着法，只要不超出期限及不觸犯排除條件，結果不變；
12. 所有主要 fixture 左右鏡像後，分類 ID 與原局一致；
13. 紅方形成兵底炮幾何：可有 `pawn_bottom_cannon_shape`，但紅方 `choice_path` 不得出現 `pawn_bottom_cannon`；
14. 紅方形成雙正馬中間無炮：不得出現 `screen_horse`，原有起馬或飛相主選擇保持；
15. 紅方雙正馬配仕角炮：不得出現 `reverse_palace_horse`，名稱按仕角炮或起馬轉仕角炮處理；
16. 紅方形成單提馬幾何：不得出現 `single_horse`，原有起馬／飛相主選擇保持；
17. 紅方形成左炮封車幾何：可記後續棋形，但不得出現 `left_cannon_blockade` 主體系或以它作 transition 起點。

每個 fixture 為 JSON，至少包含：

```json
{
  "type": "game_line",
  "id": "central-vs-screen-horse-basic",
  "name": "中炮對屏風馬基本型",
  "ucciMoves": ["..."],
  "analysisPly": 8,
  "finalFen": "...",
  "expected": {
    "redChoicePath": ["central_cannon"],
    "redCompositeSystems": [],
    "blackChoicePath": [],
    "blackCompositeSystems": ["screen_horse"],
    "baseMatchupId": "central_vs_screen_horse",
    "displayName": "中炮對屏風馬"
  },
  "forbidden": {
    "blackCompositeSystems": ["reverse_palace_horse"],
    "baseMatchupIds": ["central_vs_reverse_palace_horse"]
  },
  "mirroredSameClassification": true,
  "notes": ""
}
```

`game_line` fixture 的 `finalFen` 用於核對重播結果；pytest 以 `ucciMoves` 逐步呼叫 `advance_state()`。`state_transition` fixture 則以 `previousState + ucciMove` 呼叫一次 `advance_state()`。兩者均禁止以裸 FEN 作 confirmed 主選擇的唯一輸入。

### 19.3 規則測試最低要求

每條正式規則至少具備：

- 標準正例；
- 允許插入無關着法的正例；
- 一個只欠關鍵條件的近似反例；
- 一個被歷史排除的反例；
- 如適用，一個左右鏡像正例；
- 如適用，一個鎖定後不可改判的例子。

每個第 9.7 節直接選擇及第 9.8 節複合主體系，額外必須按第 9.6.1 節角色矩陣測試：

- 如 `main_choice_roles` 包含紅方，加入紅方主選擇正例；否則加入「紅方相同幾何只成棋形、同名主選擇不得出現」反例；
- 如 `main_choice_roles` 包含黑方，加入黑方主選擇正例；否則加入對稱的角色反例；
- 完整左右鏡像正例；
- 相似但不應形成主選擇的反例；
- 如屬 `root_only`，一個「已有其他 choice 後只成為 modifier」的反例；
- 如屬 composite system，一個被更早中炮／仕角炮歷史排除或被 axis lock 阻擋的反例。

### 19.4 UI 建立案例與 pytest 共用

- `/api/test-cases` 保存的每個 fixture 必須通過 Pydantic schema；
- pytest 參數化讀取 `backend/tests/fixtures/built_in/*.json` 及 `backend/tests/fixtures/user/*.json`；
- UI 執行單一案例與 pytest 必須呼叫同一個 Python `classify_game()`；
- UI 顯示的 pass／fail 不得另寫一套 JavaScript comparison logic；
- expected 欄位可以只指定需要斷言的部分，未指定欄位不作比較；
- 保存案例時如 expected 完全等於目前 actual，UI 要提醒使用者確認，避免無意中將錯誤結果當作正確答案。

## 20. 非功能要求

### 20.1 性能

- Python domain `advance_state()` 單步更新應低於 20 ms，重播及分析 60 ply 應低於 100 ms；
- 本機 FastAPI `/api/advance` 端到端回應應低於 100 ms；`/api/analyze` 60 ply 應低於 200 ms；
- 點擊上一步／下一步後 UI 應在 API 回應後一個 animation frame 內更新；
- 規則數增至 500 條時仍不應長時間阻塞 backend worker；
- 可按 atomic feature 建立索引，避免每步掃描所有規則。

### 20.2 可解釋性

任何 confirmed 結果必須有 Evidence。不可只有名稱而無法指出：

- 哪一步形成主選擇；
- 哪一步鎖定棋形；
- 哪些條件成立；
- 哪些歷史排除條件被檢查；
- 名稱由哪個模板生成。

### 20.3 可維護性

- 規則與程式碼分離；
- 中文名稱與判斷 ID 分離；
- 不以展示名稱作條件；
- 不在 React component 或 frontend utility 內實作合法着法、中文記譜或分類邏輯；
- FastAPI route 不直接實作 domain logic；
- 所有規則經 schema 驗證；
- 規則加入後必須同時加入 fixture。

### 20.4 無障礙與基本 UX

- 棋盤格和控制按鈕支援鍵盤操作；
- 不只以紅／黑顏色表示狀態；
- Evidence 高亮同時提供文字；
- 錯誤訊息可由螢幕閱讀器讀取。

## 21. MVP 非目標

- 完整兼容 ECCO A00–E99；
- 象棋引擎評分或最佳着推薦；
- 聯機對弈；
- 帳戶、雲端同步、分享連結；
- 任意 FEN 起始局面；
- 多分支棋譜樹；
- 以文字匯入 UCCI／ICCS 或中文着法；
- 從 UI 複製 UCCI 或分析 JSON；
- 在 UI 直接編輯規則；
- 自動由棋譜資料集學習新分類；
- 完整競賽裁決。

## 22. 驗收標準

MVP 完成需同時符合：

1. 可在棋盤完成一條合法行棋線並即時看到分類；
2. 所有棋盤點擊由 Python backend 驗證並保存為 UCCI，着法歷史顯示標準中文記譜；
3. 可在 2–60 ply 之間調整分析上限；
4. 紅黑使用同一套 detector 和規則引擎，但嚴格執行 `main_choice_roles`；
5. 主選擇和棋形歷史只增不減；
6. 起馬轉中炮、仙人指路轉中炮均保留完整 `choice_path`；
7. 中炮離開後再形成雙正馬不會錯判屏風馬；
8. 屏風馬／反宮馬按形成當刻及此前歷史鎖定；
9. 順炮、列炮、對兵能透過雙方關係產生特殊名稱，而對兵只接受三七線相應兵卒互進；
10. 已確認 baseMatchup 不會被後續 modifier 改寫；
11. 每個判斷可顯示 Evidence；
12. 跳步和 undo 直接使用保存的 immutable state snapshot；修改舊着法從該 ply snapshot 增量開新線，結果與完整重播一致；
13. 主要 fixture 左右鏡像後 ID 一致；
14. 所有正式規則均有正反測試；
15. Python domain engine 可獨立於 FastAPI 和 React 被 pytest 呼叫；
16. `中炮對屏風馬／反宮馬／單提馬` 的黑方 `SideSystemRef` 分別為 `screen_horse／reverse_palace_horse／single_horse`；
17. UI 可把案例保存為完整 UCCI `game_line` fixture，或 previous state + 一步 UCCI 的 `state_transition` fixture；
18. UI 可執行單一或全部使用者 fixture，並顯示首次 expected／actual 差異；
19. pytest 會讀取並執行 UI 保存的同一批 fixture；
20. 第 9.7、9.8 節每個主選擇／複合主體系均有合資格角色正例、不合資格角色同形反例、鏡像及 near-miss fixture；
21. 新 frontend 重用參考專案棋盤、UCCI、History 及跳步模式，但不重用其 `isValidMove` 作權威判斷；
22. 紅方形成兵底炮、屏風馬、反宮馬、單提馬或左炮封車的相同幾何時，不得產生該黑方限定主選擇；
23. 標準 FEN 不可單獨產生 confirmed 歷史分類；MVP 以 `FEN + piece_identity + OpeningMemory` 的 RecognitionState 增量分類，FEN-only 結果必須標記 `history_unknown`。

## 23. 建議實作階段

### 階段 1：棋盤、Notation 與增量 State

- Python UCCI Canonical Move；
- Python 合法着法；
- UCCI 至標準中文記譜；
- FastAPI `/api/state/initial`、`/api/advance` 及復原用 `/api/analyze`；
- 棋盤 UI；
- immutable state 時間線和重播校驗。

### 階段 2：Append-only 開局記憶

- 原子事實；
- 主選擇；
- 複合主體系；
- `choice_path`；
- `main_choice_roles` 角色升格檢查；
- formation axis 鎖定；
- Evidence。

先只用核心 fixture 驗證中炮、屏風馬、反宮馬、起馬轉中炮和仙人指路轉中炮。

### 階段 3：Matchup 與名稱生成

- 順炮／列炮；
- 對兵；
- 中炮對屏風馬／反宮馬／單提馬；
- 通用名稱模板；
- modifier 細化。

### 階段 4：分析與規則前端

- Profile 面板；
- Evidence；
- provisional 候選；
- 規則瀏覽器；
- test case 編輯器；
- 單一／批量 fixture runner；
- pytest 共用 user fixture。

### 階段 5：擴大 MVP 規則

- 五六／五七／五八／五九炮；
- 過河車、巡河炮、平炮兌車；
- 單提馬、三步虎、轉列炮；
- 飛相、仕角炮、過宮炮及仙人指路相關 Matchup；
- 完整鏡像及插入無關着法測試。

## 24. 參考前端 `xiangqi-project` 重用方案

參考專案：

```text
C:\Coding\Fake Human Test\xiangqi-project
```

該專案使用 React 18、Vite 5、Tailwind CSS，已有可工作的中國象棋棋盤、UCCI 歷史和跳步互動。新項目可重用視覺及互動程式，但 Python backend 仍是合法着法與開局辨認的唯一權威。

### 24.1 建議直接移植並轉成 TypeScript

| 參考檔案 | 可重用內容 | 新項目調整 |
|---|---|---|
| `src/components/Board.jsx` | SVG 9×10 棋盤、楚河漢界、九宮線、棋子樣式、選取、最後一步及可走位置高亮 | 轉成 `Board.tsx`；刪除 `isValidMove` import；可走位置完全使用 backend `legalMoves` |
| `src/utils/uciUtils.js` | board row/column 與 UCCI `a0–i9` 轉換、`toUcciMove`、`uciToCoords` | 轉成有嚴格型別的 `ucci.ts`；加入格式校驗；只負責座標轉換，不判斷合法性 |
| `src/components/History.jsx` | 紅黑雙欄回合表格、自動捲到底、點擊跳到 ply | 改為接收 `{ ucci, chineseNotation }`；畫面只顯示標準中文着法 |
| `src/App.jsx` 的 `moveHistory`、`viewIndex`、左右鍵及 `jumpToMove` 模式 | 線性 UCCI 歷史、ply 導航、較早位置行棋後截斷後續歷史 | 抽成 `useGameTimeline.ts`；每個 ply 同時保存 UCCI、中文記譜及 backend `RecognitionState` snapshot；新一步提交 `/api/advance` |
| `src/constants.js` | 棋盤尺寸、紅黑、棋種及棋子顯示字 | 轉成 TypeScript constants；統一 UTF-8 繁體字串 |

### 24.2 只作行為參考，不直接作權威邏輯

| 參考檔案 | 可參考內容 | 不可直接重用原因 |
|---|---|---|
| `src/logic/NotationLogic.js` | 路線編號、進退平、前後中棋子消歧嘅基本做法 | 新規格要求中文記譜由 Python backend 產生；需補齊所有歧義情況及 pytest fixture |
| `src/utils/boardUtils.js` | 初始棋盤、基本棋子走法、FEN helper | `isValidMove` 主要是 pseudo-legal move，未完整保證自將、將帥照面等；不可成為權威合法性引擎 |
| `src/App.jsx` 的 `rebuildPosition` | 從 UCCI 歷史重建棋盤的復原思路 | 現有實作直接移棋，未逐步由權威引擎驗證；新項目正常跳步讀取保存的 state snapshot，只有復原／校驗才由 Python 重播 |

### 24.3 不移植範圍

- `BotLogic.js`、棋力評估、隨機選着及 filter；
- `useEngine.js`、Pikafish WebSocket 連線；
- `server/server.cjs`；新項目使用 FastAPI；
- `Controls.jsx` 內對弈、引擎、bot 設定；
- `FenPanel.jsx`；MVP 不以任意 FEN 作開局辨認輸入；
- `LogPanel.jsx` 的 engine output；新項目改用 recognition Evidence 面板；
- 現有 bot／threat tests，除非個別測試只驗證 UCCI 座標。

### 24.4 移植流程

1. 複製棋盤 SVG、棋子視覺、History layout 及 UCCI coordinate helpers 到新 frontend；
2. 將 JSX 轉成 TSX，清理來源檔案編碼，所有中文字串統一 UTF-8；
3. 用 `/api/advance` 回傳的 `state.positionFen`、`legalMoves` 和 `move.chineseNotation` 取代本地 `boardUtils` 和 `NotationLogic`；
4. 棋盤點擊產生候選 UCCI，連同目前 ply 的 `RecognitionState` 提交 backend；只有 backend 接受後才追加 move 及 next state；
5. 將 History 表格改成只顯示中文記譜，但內部保留 UCCI；
6. 保留跳步、左右鍵及從較早 ply 開新線的互動；跳步讀取對應 snapshot，開新線以該 snapshot 呼叫 `/api/advance`；
7. 在右欄新增 opening Profile、Evidence、rule inspector 和 test case editor；
8. 刪除所有 bot、engine、FEN 輸入及對弈專用 UI。

### 24.5 重用驗收

- 棋盤外觀及基本點擊手感與參考專案相當；
- 前端源碼不再 import 參考專案的 `isValidMove` 或 `NotationLogic`；
- 任一合法落點均來自 backend；
- History 畫面不顯示原始 UCCI，只顯示 backend 中文記譜；
- 跳步後棋盤、分類 snapshot 及 Evidence 來自同一個 backend ply；
- 參考專案本身不被修改。

## 25. 完成定義

本項目第一版完成，不代表已辨認所有 ECCO 分類，而代表：

- 核心資料模型已證明可以正確保存歷史；
- 已確認分類不會被後來局面錯誤覆蓋；
- 選擇轉換能保留完整路徑；
- 新棋形和新 Matchup 可以主要透過新增規則及 fixture 實作；
- 測試前端能清楚展示系統「判斷咗乜、幾時判斷、點解判斷」。

只要呢個骨架穩定，之後擴充 ECCO 相關分類就會由「重寫辨認程式」變成「增加棋形、組合及測試資料」。

### 25.1 MVP 實作校正

- `對兵局` 只由目前 FEN 的三、七路兵卒對稱配對觸發：紅三路兵配黑七路卒，或紅七路兵配黑三路卒；紅三配黑三、紅七配黑七等不相應組合不得觸發。
- `left_three_step_tiger` 及 `right_three_step_tiger` 均必須同時具備「正馬移動、同翼炮平邊、同翼車移動」三項 move facts。未出車時不得升格。

### 25.2 新增棋形與互斥鎖（本次實作）

- `五六炮`、`五七炮`、`五八炮`、`五九炮`：中炮由中路向同方橫線移至六至九路；保留 `central_cannon` 歷史，但有效命名由首次形成的五字炮取代。
- `巡河炮`：炮必須由原始炮位沿原直線直接走到己方河岸；中途先走一步再到河岸不算。
- 上述五字炮與巡河炮共用 `cannon_formation` 鎖，首次形成後其餘不進入命名。
- `橫車`（本專案定義）：原始車沿原直線向前；`直車`：原始車在本方底線橫移。取消 `右橫車`；雙車均形成前者時記 `雙橫車`。
- `巡河車`、`騎河車`、`過河車` 依車到達己方河岸、對方河岸、對方兵行線／卒林線判定，共用 `rook_river_stage` 鎖，首次形成後互斥。
- `平炮兌車`：黑炮由原始炮位平移至相鄰邊線；走子前該黑炮與指定紅黑車對處於同一路並位於兩車之間；走後該車對同一路、車間無子。車對中的黑車必須是已有歷史紀錄的直車，且同一隻黑車受黑馬保護。
- 新增 `七路馬`、`邊馬`、`雙正馬`、`兩頭蛇` 及三／七路兵卒的 `進三兵`、`進七兵`、`挺三卒`、`挺七卒` 形成紀錄。兵卒名稱只在紅方歷史含 `central_cannon` 時加入有效命名；所有形成紀錄仍保留於 `RecognitionState.opening_memory.*.formed_shapes`。

### 25.3 ECCO 目錄命名元件與歷史 Matchup（本次實作）

- `Classification` 保存 `red_main_id`、`red_main_label`、`red_modifiers`、`black_main_id`、`black_main_label`、`black_modifiers`、`base_matchup_id`、`template_id` 及 `display_name`；`red_system`、`black_system` 暫時只作向後相容 alias。
- 所有 formation occurrence 均保存 `lock_group`、`eligible_for_name` 及 `suppressed_by`。互斥組的後來形成者不可進入名稱，但必須永久保留於 evidence。
- 沒有正式主形時，modifier 不得升格為 main；只可進入「紅方／黑方」描述 fallback。
- `仕角炮` 的左右翼只保存於 metadata，正式主形顯示為「仕角炮」。
- `緩開車`：中炮開局體系下，該方完成自己的第三個着次時兩隻原始車均未移動。其後出車不取消名稱；如中炮稍後才形成，以已保存的第三着無車移動事實補判。
- `後補列炮`：黑方先 `h9g7` 起左馬，其後 `b7e7` 炮 2 平 5。保存 `base_matchup_id = opposite_side_cannons`，並以 `template_id = delayed_opposite_side_cannons_after_left_horse` 顯示「後補列炮」。
- 順炮／列炮保存雙方中炮的原始炮 file，以歷史形成鎖定；中炮日後離開中路不取消 matchup。
- ECCO C2、C3、C4、D1、D2、D3、D4、E2／E3 使用具體 `template_id`；具體 template 優先於一般順炮、列炮或雙方主形模板。
