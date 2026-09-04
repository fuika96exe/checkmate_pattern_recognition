# Repository Agent Guide

## Project purpose

Xiangqi Opening Recognition is a local MVP for recognizing Chinese chess opening systems from legal move history and FEN positions. The Python backend is authoritative for legal moves, Chinese notation, recognition state, opening memory, and classification. The React frontend is a client UI for playing moves, browsing immutable snapshots, inspecting FEN observations, and running recognition fixtures.

## Runtime and commands

- Node.js: `>=22.13.0`
- Python: Python 3.12 is the supported local runtime.
- Frontend: Next.js 16.2.6 / React 19.2.6, built and served through `vinext`.
- Backend: FastAPI, Uvicorn, Pydantic 2, `pyffish`, and pytest.
- Frontend URL: `http://127.0.0.1:3000`
- Backend URL: `http://127.0.0.1:8000`
- Frontend API base: `NEXT_PUBLIC_API_BASE`, defaulting to `http://127.0.0.1:8000`.

Install dependencies:

```powershell
npm.cmd install
python -m pip install -r backend\requirements-local.txt
```

Start the local app:

```powershell
.\run-dev.ps1
```

The script starts the backend and frontend as hidden processes. It does not stop an existing server. If the UI shows an old classification, check the process on ports 8000 and 3000, restart the backend, and refresh or reset the frontend timeline.

Run the canonical checks:

```powershell
python -m pytest backend\tests -q
npm.cmd run lint
npm.cmd run build
```

PowerShell may block `npm.ps1`; use `npm.cmd` when `npm` is rejected by the execution policy. The `npm test` script currently points at legacy starter HTML tests in `tests/rendered-html.test.mjs`; it is not the canonical project verification command until those tests are migrated.

## Architecture

```text
app/components/Workbench.tsx
  -> app/lib/api.ts
  -> FastAPI endpoints in backend/app/main.py
  -> backend/app/service.py
  -> backend/app/board.py, notation.py, recognizer.py
```

- `backend/app/board.py`: UCCI validation, FEN parsing, legal moves, and move application through local `pyffish` or the Cloudflare-compatible pure-Python fallback.
- `backend/app/notation.py`: standard Chinese move notation. Red uses Chinese numerals; Black uses full-width Arabic numerals.
- `backend/app/recognizer.py`: current-shape detection, historical facts, append-only opening memory, composite systems, modifiers, and classification names.
- `backend/app/service.py`: service-level state transitions and immutable snapshot creation.
- `backend/app/main.py`: HTTP API and fixture management.
- `app/components/XiangqiBoard.tsx`: board interaction and legal-target display only; it must not duplicate backend legality rules.
- `app/components/Workbench.tsx`: timeline, classification, opening memory, current shapes, and move history UI.
- `backend/tests/fixtures/built_in`: checked-in recognition cases.
- `backend/tests/fixtures/user`: user-created JSON cases; preserve them when changing built-in rules.
- `xiangqi-opening-recognition-spec.md`: detailed domain specification and naming policy.

## API surface

The frontend currently uses these endpoints:

- `GET /api/health`
- `POST /api/state/initial`
- `POST /api/advance`
- `POST /api/analyze`
- `POST /api/inspect`
- `GET /api/test-cases`
- `POST /api/test-cases`
- `DELETE /api/test-cases/{case_id}`
- `POST /api/test-cases/{case_id}/run`
- `POST /api/test-cases/run-all`

`RecognitionState.openingMemory` is append-only along a move line. The frontend stores each returned state as an immutable timeline snapshot; undo or navigation should select an existing snapshot instead of mutating recognition history.

## Current domain rules

- UCCI coordinates are the internal source of truth. Do not infer opening names from rendered board position alone when move history is available.
- Red Chinese file numbers run right-to-left: the physical `g` file is Red 3 and `c` is Red 7.
- Black uses the opposite physical mapping: `c` is Black 3 and `g` is Black 7.
- Red `g3g4` is `advance_three_pawn`; Red `c3c4` is `advance_seven_pawn`.
- `palcorner_cannon` keeps left/right as metadata only. Its formal displayed name is always `仕角炮`, never a winged main name.
- `slow_rook` conflicts with same-side `straight_rook` and `horizontal_rook` in the displayed modifier list. Historical shape occurrences remain available in memory and evidence.
- Same-side central cannons have directional templates in both orientations, including `順炮直車對橫車` and `順炮橫車對直車`.
- A rule change must preserve the distinction between current FEN shapes and historical opening memory. A later board position must not erase a previously confirmed opening choice.
- When adding or changing a naming rule, add a pytest regression using the exact UCCI sequence that demonstrates it. Add a FEN fixture or mirrored case when the rule is position-sensitive.

## Change workflow

1. Read the relevant recognizer code, models, service path, and existing tests before editing.
2. Reproduce the reported move sequence or FEN first.
3. Make the smallest change in the authoritative backend rule layer.
4. Add or update a focused regression test and fixture.
5. Run backend pytest, frontend lint, and frontend build as applicable.
6. If a live backend is running, restart it after backend changes; Uvicorn is launched without reload in `run-dev.ps1`.
7. Report any unrelated legacy test failures separately instead of weakening the new rule to satisfy them.

## Style and safety

- Preserve existing user changes and fixture data unless the task explicitly requires an update.
- Keep recognition IDs stable; prefer adding a template or modifier policy over renaming an existing ID.
- Keep frontend components focused on presentation and API state; do not create a second recognition engine in TypeScript.
- Use UTF-8 for Traditional Chinese source, fixture, and documentation files.
- Avoid destructive repository commands. Use targeted patches and non-interactive checks.
