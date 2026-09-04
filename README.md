# 象棋開局辨識實驗室

本地 MVP，用 Python/FastAPI 處理中國象棋合法著法、中文記譜、FEN 檢視、開局辨識及殺法辨識；前端提供可點擊棋盤、開局記憶、不可變時間線、棋題瀏覽器及回歸案例管理。

## 最新技術設定

- 前端：Next.js 16.2.6、React 19.2.6、TypeScript、Fluent UI、Vinext
- 後端：Python 3.12、FastAPI、Uvicorn、Pydantic 2、Pyffish
- 前端開發伺服器：`http://127.0.0.1:3001`
- 後端 API：`http://127.0.0.1:8000`
- Node.js：`>=22.13.0`
- 前端 API 位址環境變數：`NEXT_PUBLIC_API_BASE`，預設為 `http://127.0.0.1:8000`

## 安裝

PowerShell：

```powershell
npm.cmd install
python -m pip install -r backend\requirements-local.txt
```

若 PowerShell 因執行原則拒絕 `npm`，請使用 `npm.cmd`。

## 啟動

```powershell
.\run-dev.ps1
```

腳本會以隱藏視窗啟動：

- FastAPI：`backend\run.py`，port 8000
- Vinext 前端：`npm.cmd run dev`，port 3001

腳本不會自動停止舊進程。若畫面仍顯示舊的辨識結果，請重啟 8000 port 的後端，然後在前端重新整理或按「重設」。

也可以分開啟動：

```powershell
# 終端機一：後端
cd backend
python run.py

# 終端機二：前端
cd ..
npm.cmd run dev
```

## Windows 桌面版

需要安裝 Electron、PyInstaller 及前端依賴後，可建立免命令列操作的便攜版：

```powershell
npm.cmd run desktop:portable
```

完成後雙擊 `release-portable\象棋殺法識別.exe` 即可啟動；應用程式會自動啟動內置前後端服務，關閉視窗時一併停止服務。Electron Builder 的 NSIS 安裝包命令為 `npm.cmd run desktop:dist`。

## 開發與測試命令

```powershell
# 後端回歸測試
python -m pytest backend\tests -q

# 前端 lint
npm.cmd run lint

# 前端 production build
npm.cmd run build
```

## 棋題資料匯入

棋題瀏覽器使用標準化 JSON，不在執行時直接解析 CSV。任何具有相同欄位的後續匯出檔都可用同一命令重新匯入：

```powershell
npm.cmd run puzzles:import -- "C:\path\to\Puzzles.csv"
```

輸出會寫入 `public/data/checkmate-puzzles.json`。格式錯誤的資料列不會被丟棄，而會以「無效」狀態及錯誤原因保留。人工覆核標籤另存於 `public/data/checkmate-puzzle-expectations.json`，不會把目前引擎輸出當成標準答案。

「棋題瀏覽器」會在打開一道棋題時即時分析整條 `Initial Fen → Blunder Move → Pv`。棋盤預設停在失着之後，仍可退回初始局面、逐着前進或自動播放。按「分析全部」會以有限並行度執行整個語料庫，並把精簡結果按資料版本及規則版本快取在瀏覽器。

`npm test` 目前仍會執行 `tests/rendered-html.test.mjs` 的舊 starter skeleton 測試；該測試尚未遷移到現有實驗室頁面，因此不是目前的 canonical 驗證命令。請使用上面的 pytest、lint 及 build 組合。

## 主要目錄

```text
app/                         React/Next.js 前端
  components/                棋盤、工作台及案例測試 UI
  lib/                       API client 與 TypeScript 型別
backend/app/                 FastAPI、棋盤、記譜及辨識引擎
backend/tests/               pytest 與內置／使用者案例
backend/tests/fixtures/      JSON 回歸案例
public/                      靜態資源
run-dev.ps1                  本地前後端啟動腳本
xiangqi-opening-recognition-spec.md
                             完整辨識規格及命名政策
```

## API

目前前端使用的端點：

| 方法 | 路徑 | 用途 |
|---|---|---|
| GET | `/api/health` | 健康檢查 |
| POST | `/api/state/initial` | 建立初始棋局 |
| POST | `/api/advance` | 套用一步合法著法並更新辨識狀態 |
| POST | `/api/analyze` | 重播一組 UCCI 著法 |
| POST | `/api/inspect` | 以 FEN 及 memory preset 檢視局面 |
| POST | `/api/analyze-checkmate-pattern` | 以 FEN 及 UCCI 序列辨識全部命中殺法 |
| POST | `/api/analyze-puzzle-line` | 驗證棋題、建立重播時間線並辨識全部殺法 |
| GET | `/api/test-cases` | 取得所有案例 |
| POST | `/api/test-cases` | 儲存使用者案例 |
| DELETE | `/api/test-cases/{case_id}` | 刪除使用者案例 |
| POST | `/api/test-cases/{case_id}/run` | 執行單一案例 |
| POST | `/api/test-cases/run-all` | 執行全部案例 |

## 最新辨識約定

- UCCI 是內部權威格式；合法著法由 Pyffish 驗證。
- 紅方記譜由右至左：實體 `g` 路是紅三路，`c` 路是紅七路。
- 黑方相反：實體 `c` 路是黑三路，`g` 路是黑七路。
- 紅方 `g3g4` 是「進三兵」，`c3c4` 是「進七兵」。
- `仕角炮` 的左右翼只保留在 metadata，正式主名稱不顯示翼別。
- `緩開車` 與同方的「直車／橫車」名稱互斥；歷史棋形仍保留在 RecognitionState evidence。
- 順炮支援兩個對稱方向：`順炮直車對橫車` 及 `順炮橫車對直車`。
- 已確認的 opening choice 與 composite system 會保存在 append-only 的開局記憶；後續棋子移動不會抹除歷史判定。

## 案例資料

- 內置案例：`backend/tests/fixtures/built_in/*.json`
- 使用者案例：`backend/tests/fixtures/user/*.json`

每個案例包含 `id`、`name`、`fen`、`expectedName`、`memoryPreset`、`notes` 及 `source`。需要依賴走子次序的分類，應在 `memoryPreset` 或完整 UCCI 測試中提供最小歷史，而不能只依靠 FEN 推測。

## One-command local startup

Open one Command Prompt in the project folder and run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\start-local.ps1
```

The script starts both services in hidden windows and opens the browser at `http://127.0.0.1:3001/`. Keep the Command Prompt open while using the app. Press Enter in that window to close the launcher. To stop services later, run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\stop-local.ps1
```

## Cloudflare deployment

Current production deployments:

- Frontend: `https://checkmate-pattern-recognition.kwand7910.workers.dev`
- Recognition API: `https://checkmate-pattern-api.kwand7910.workers.dev`

The Cloudflare API uses the same recognition modules with a pure-Python
Xiangqi move/FEN layer because native CPython extensions such as `pyffish`
cannot run in the Python Workers WebAssembly runtime. Built-in fixtures are
available in production; saving and deleting fixture files remains a local-only
feature.

To redeploy the API and frontend:

```powershell
cd backend
uv run pywrangler deploy --config wrangler.jsonc
cd ..
.\node_modules\.bin\vinext.cmd deploy
```

The frontend calls `/api/*` on its own origin. Its Worker forwards those
requests to `checkmate-pattern-api` through the `API` Service Binding, so no
browser CORS configuration is required. `NEXT_PUBLIC_API_BASE` remains
available when a separate API URL is needed for development.
