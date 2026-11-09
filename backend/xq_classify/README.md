# xq_classify

Portable classifiers for Xiangqi puzzles: midgame tactics and checkmate patterns.

The Xiangqi lab owns this package. Other repositories use a vendored copy, so rules change here and never in a copy.

It needs Python 3.12 or 3.13 and only the standard library. It has its own pure-Python move generator, starts no threads or processes, and does no I/O.

## Using it

```python
from xq_classify import ReplayError, classify_checkmate, classify_midgame
from xq_classify.labels import CHECKMATE_PATTERNS_ZH_TW

mate = classify_checkmate(fen, blunder, pv)
names = [CHECKMATE_PATTERNS_ZH_TW[pattern] for pattern in mate.pattern_ids]

try:
    tactic = classify_midgame(fen, blunder, pv, solver='red')
except ReplayError as error:
    print(error.ply, error.fen, error.move)
```

Both entry points read the same puzzle line:

| Argument | Meaning |
|---|---|
| `fen` | The position before the blunder |
| `blunder` | The UCCI move that creates the puzzle |
| `pv` | The solution line, a list of UCCI moves |
| `solver` | Midgame only: `'red'` or `'black'` |

Bad input is reported differently by each:

- `classify_checkmate` returns a result with status `'invalid'` and an `error` message.
- `classify_midgame` raises `ReplayError`, a `ValueError`. `ply` 0 means the input itself was rejected.

Inside xiangqi-server the package imports as `xiangqi_server.vendor.xq_classify`.

## Results

Both results are frozen dataclasses. `to_dict()` gives the JSON-safe record and `from_dict()` rebuilds a result from one. `schema_version` is on the result and not in the record, so a caller that stores records stores the version beside them.

### `CheckmateResult`

| Field | Record key | Meaning |
|---|---|---|
| `status` | `status` | `'matched'`, `'unmatched'` or `'invalid'` |
| `pattern_ids` | `patternIds` | Pattern IDs in rule order |
| `material_id` | `materialId` | Mating-material code, only when the line ends in mate and no pattern matched. Absent from an invalid record. |
| `error` | `error` | Why the line is invalid. Present only in an invalid record. |
| `failed_move_index` | – | 1-based position in blunder + pv of a move that cannot be played |
| `timeline` | – | Positions reached: `index`, `fen`, `move` |
| `analysis` | – | Evidence: see below |
| `schema_version` | – | `SCHEMA_VERSION` |

`analysis` holds `fen`, `moves`, `analysis` (the final position: check, mate, checking pieces, attacked squares), `matches`, `best_match` and `material_fallback`. Each match has `pattern_id`, `features` and `diagnostics`. `features` differs per pattern.

### `MidgameResult`

| Field | Record key | Meaning |
|---|---|---|
| `status` | `status` | `'matched'` when `tactics` is not empty, else `'unmatched'` |
| `solver` | `solver` | `'red'` or `'black'` |
| `tactics` | `tactics` | Label IDs in the fixed label order |
| `fens` | `fens` | The initial position, then the position after each move |
| `plies` | `plies` | One entry per move, see below |
| `material` | `material` | `kind`, `start`, `end`, `delta` |
| `supporting_evidence` | `supportingEvidence` | Occurrences of suppressed labels |
| `review_reasons` | `reviewReasons` | Rejected candidates: `label`, `ply`, `fen`, `reason`, `evidence` |
| `schema_version` | – | `SCHEMA_VERSION` |

`material` is the solver's balance of chariots, horses and cannons. `kind` is `'gain'` when `delta` is at least 4, else `'no_gain'`.

A ply has `ply` (1 is the blunder), `ucci`, `solver` (true on the solver's moves) and `occurrences`. An occurrence has `id`, `label_zh`, `squares`, `detail` and `evidence`. Every `evidence` has `key`, `triggerPly`, `confirmedPly`, `relationKind`, `actors` and `targets`; the other keys depend on the label.

### IDs and display names

`xq_classify.labels` maps every ID to its zh-TW name: `MIDGAME_LABELS_ZH_TW`, `CHECKMATE_PATTERNS_ZH_TW` and `MATING_MATERIAL_ZH_TW`. An ID never changes once published.

Show names from these tables. The `pattern_name_zh`, `label_zh` and `diagnostics` strings inside checkmate evidence are the lab's Simplified Chinese text.

## Coordinates

Squares and moves use UCCI with ranks 0–9: `a0` is Red's left corner and `i9` is Black's. FEN piece letters are `rnbakcp`, uppercase for Red, and the side to move is `w` for Red or `b` for Black.

xiangqi-server numbers ranks 1–10. The server converts at its own boundary: add 1 to each rank coming out of this package and subtract 1 going in. That covers moves and every square in a result, evidence included. FENs need no conversion. The package only ever sees ranks 0–9.

## Move generators

The pure-Python generator is the default. `xq_classify.board.use_backend(generator)` installs any other `board.MoveGenerator`, returns the previous one and clears the board caches. It is a process-wide switch, so set it once at startup. The lab installs pyffish this way.

Labels do not depend on the generator. Two details of the output do:

- The pure generator never resets the FEN halfmove clock on a capture.
- Legal-move order differs, which can change the reply cited in `fork_defences` evidence.

Caches are `lru_cache`s with fixed sizes, so a long-running worker stays bounded. `clear_caches()` empties all of them.

## Versions

All four constants live in `version.py`.

| Constant | Bump when |
|---|---|
| `MIDGAME_RULES_VERSION` | A midgame label or evidence rule changes |
| `CHECKMATE_RULES_VERSION` | A checkmate pattern, material or evidence rule changes |
| `SCHEMA_VERSION` | The shape of a result or its `to_dict()` record changes |
| `PACKAGE_VERSION` | A new copy is vendored into another repository |

A rules bump in the lab also updates the matching document in `docs/` and regenerates the affected `public/data/*.json`.

## Changing the package

- Import only the standard library. Inside the package use relative imports, so the vendored path works.
- No threads, process pools, file access or `print`.
- Keep IDs stable. Add a label or pattern rather than renaming one.
- Keep the result of `to_dict()` stable, or bump `SCHEMA_VERSION`.
- Keep every function at cognitive complexity 15 or lower.

In the lab, `test_xq_classify_isolation.py` checks the import rules. `test_midgame_frozen.py` and `test_checkmate_frozen.py` are the gates for rule changes: a failing frozen case rejects the change.

## Layout

```text
__init__.py     entry points and versions
contracts.py    CheckmateResult, MidgameResult
labels.py       IDs and display names
version.py      the four versions
exchange.py     exchange evaluation
board/          FEN, geometry, the pure generator, use_backend
midgame/        classify, replay, material, detectors/ (one per label)
checkmate/      classify, recognition (dispatch), material, geometry, patterns/
```
