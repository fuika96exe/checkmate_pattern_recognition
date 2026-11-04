# Repository Agent Guide

Setup, startup, deployment, the HTTP API table, and fixture format are in [README.md](README.md). This file covers what an agent needs to change rules safely.

## Project purpose

A local Xiangqi (Chinese chess) analysis lab. The Python backend is the single authority for legal moves, Chinese notation, opening recognition, checkmate patterns, tactical labels, midgame tactics, and long-check/long-chase (repetition) adjudication. The React frontend is presentation only: a tabbed workbench that calls the backend or reads pre-generated JSON in `public/data/`.

## Commands

```powershell
python -m pytest backend\tests -q   # backend regressions (canonical)
npm.cmd run lint
npm.cmd run build
.\run-dev.ps1                       # backend :8000 (uvicorn reload=True), frontend :3001
```

- Use `npm.cmd`; PowerShell execution policy may block `npm.ps1`.
- `npm test` runs legacy starter HTML tests (`tests/rendered-html.test.mjs`) and is not a project verification command. `node --test tests/notation-importer.test.mjs` covers the TypeScript notation importer.
- Local runtime is Python 3.12 with `pyffish`. `backend/pyproject.toml` (`>=3.13`, `uv`) exists only for the Cloudflare Python Worker build.

## Architecture

```text
app/components/Workbench.tsx (tabs)
  -> app/lib/api.ts -> backend/app/main.py (FastAPI) -> service.py / analysis modules
  -> or public/data/*.json (pre-generated indexes)
```

Backend (`backend/app/`):

| Module | Responsibility |
|---|---|
| `board.py` | UCCI validation, FEN, legal moves; `pyffish` locally, pure-Python fallback on Cloudflare |
| `notation.py` | Chinese move notation (Red: Chinese numerals; Black: full-width Arabic numerals) |
| `recognizer.py`, `service.py` | Opening shapes, append-only opening memory, immutable state snapshots |
| `opening_sample.py` | Opening-sample advance/replay endpoints |
| `patterns.py` | Checkmate pattern recognition (`CHECKMATE_RULES_VERSION`) |
| `tactics.py` | Move-level tactic labels (`TACTIC_RULES_VERSION`) |
| `tactical_categories.py` | Tactical category labels (`CATEGORY_RULES_VERSION`) |
| `midgame_tactics.py` | Midgame puzzle tactics used by the capturing-tactics dataset (`RULES_VERSION`) |
| `exchange.py` | Destination-square exchange evaluation for Fake Human move labels |
| `cycle_rules.py`, `repetition.py` | Pure long-check/long-chase cycle evaluator and repetition adjudication |
| `builtin_cases.py`, `models.py`, `main.py` | Built-in cases, Pydantic models, HTTP API and fixture management |

Frontend (`app/`):

- `components/XiangqiBoard.tsx`: board interaction and legal-target display only.
- `components/*Lab.tsx`, `PuzzleBrowser.tsx`: one component per workbench tab.
- `lib/notation-import/`: client-side game-record parsers (WXF, ICCS, DPXQ, Chinese). This is the only parsing logic in TypeScript; it must not grow into a recognition engine.

## Sources of truth

- Checkmate rules: `docs/checkmate-recognition-logic.zh-TW.md`
- Tactical and midgame rules: `docs/tactical-recognition-logic.zh-TW.md`
- Opening naming policy: `xiangqi-opening-recognition-spec.md`
- Midgame batch/audit reports: `docs/reports/`

Update the matching document when a rule's behaviour changes, and bump the module's rules-version constant.

## Data and fixtures

| Path | Kind | How to change |
|---|---|---|
| `data/puzzle-sources/*.csv` | Raw source exports | Do not edit by hand |
| `public/data/checkmate-puzzles.json`, `checkmate-puzzle-recognition.json` | Generated | `npm.cmd run puzzles:import -- <csv>` or `npm.cmd run puzzles:analyze` |
| `public/data/capturing-tactics.json` | Generated | `python backend/scripts/generate_capturing_tactics.py`, then `python backend/scripts/audit_midgame_tactics.py` |
| `public/data/fake-human-games.json` | Generated | `backend/scripts/import_fake_human_games.py` |
| `public/data/fake-human-openings.json` | Generated (ply-20 opening per game, read by the Fake Human tab) | `python backend/scripts/generate_fake_human_openings.py` after the games file or the opening recognizer changes |
| `public/data/checkmate-puzzle-expectations.json` | Human review labels | Never overwrite with engine output |
| `backend/tests/fixtures/built_in/` | Opening recognition cases | Hand-written |
| `backend/tests/fixtures/user/` | User-saved cases (created on first save) | Preserve when changing rules |
| `backend/tests/fixtures/midgame_frozen/v*.json`, `MANIFEST.json` | **Frozen human-confirmed midgame regression set** (gate: `test_midgame_frozen.py`) | Human only, by appending a new version file. Agents never edit, delete, regenerate or re-hash them |
| `backend/tests/fixtures/midgame_frozen/known_wrong_v*.json` | Expert-corrected labels for puzzles the engine gets wrong (tracked, not a gate) | Human only |

After a rule change, regenerate every affected `public/data/*.json`; the frontend lists and filters read these indexes, not live analysis. Never back-fill expected values in fixtures from generated output.

## Domain invariants

- UCCI coordinates (ranks 0–9) are the internal source of truth. Do not infer history from a rendered position when move history is available.
- Red file numbers run right-to-left (physical `g` = Red 3, `c` = Red 7); Black is mirrored (`c` = Black 3, `g` = Black 7).
- Opening memory is append-only along a move line. A later position must not erase a confirmed opening choice; the frontend navigates immutable snapshots rather than mutating history.
- Keep recognition, pattern, and tactic IDs stable. Prefer adding a template or modifier over renaming an existing ID.
- Analysis must run both locally (`pyffish`) and on Cloudflare (pure-Python fallback, no threads). Kingless or terminal positions must never reach `pyffish`, which crashes natively. `test_native_board_safety.py` and `test_cloudflare_api.py` guard these paths.

## Change workflow

1. Read the relevant module, its rules doc, and existing tests before editing.
2. Reproduce the reported FEN and UCCI sequence (or puzzle `initialFen` + `blunderMove` + `pv`) first.
3. Make the smallest change in the authoritative backend module.
4. Add a focused pytest regression using the exact sequence; add a mirrored case when the rule is side- or position-sensitive.
5. Bump the rules version, update the rules doc, and regenerate affected `public/data/*.json`.
6. Run pytest, lint, and build. Report unrelated pre-existing failures separately instead of weakening the new rule to pass them.

### Frozen midgame regression gate

`backend/tests/test_midgame_frozen.py` checks every case in `fixtures/midgame_frozen/v*.json`. Each case was confirmed correct by a human expert. The test checks:

- the exact `tactics` set and `material.kind`;
- on both boards (native pyffish and the pure-Python fallback);
- on colour-swapped and mirrored variants of each case.

- **If any frozen case fails after a midgame rule change, the change is rejected.** Stop, do not "fix" the expectation, and return the diff report to the user for a decision. The user then adjusts the rule or the requirement.
- Never edit, delete, regenerate or re-hash frozen files or `MANIFEST.json`. Never skip, mark xfail or loosen the frozen tests. Only a human extends the set, by appending a new `v<N>.json` with its own manifest entry. A human re-ruling of an already frozen puzzle is likewise a new version that lists the puzzle under `supersedes` with a reason. The gate then checks only the newest entry. Agents write such a file only when the user explicitly instructs it.
- `test_known_wrong_tracking` is not a gate. It xfails while the engine disagrees with the expert correction. A `UserWarning` saying a case now matches means a fix landed. Report it to the user, who decides whether to promote it. Do not move it yourself.
- `MIDGAME_FROZEN_FULL=1` also runs the variants on the native board (slow, about 3 min).
- `test_frozen_evidence_is_well_formed` checks only the structural consistency of evidence on frozen cases, such as ply order, piece references and parent keys. A failure there is an engine bug, so fix the engine.
- Hand-written rule-boundary tests for midgame labels were removed on 2026-11-04. Do not reintroduce label expectations outside the frozen set. Coverage for a rule comes from the human adding confirmed puzzles to a new frozen version.

## Style and safety

- Preserve user changes, fixture data, and human review labels unless the task explicitly requires updating them.
- Use UTF-8 for Traditional/Simplified Chinese source, fixtures, and docs.
- Avoid destructive repository commands. Use targeted edits and non-interactive checks.
