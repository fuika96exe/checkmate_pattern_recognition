# Puzzle upload sources

The active datasets are built from the complete exports below:

| Source | Theme | Rows |
| --- | --- | ---: |
| `Puzzles_2026-10-22_08-12-00_tactic_upload.csv` | CAPTURING | 3,135 |
| `Puzzles_2026-10-22_08-12-00_checkmate_upload.csv` | CHECKMATE | 4,729 |

The export's `game_id` is a placeholder. Importers use the puzzle ID from
`url`, normalize `first_turn` to `red`/`black`, and replay `blunder_move`
followed by `pv` from `fen_before`. Upload exports are imported in full
unless `--start`/`--limit` select a contiguous slice in source order; the
legacy published-puzzle export still supports random sampling.

The capturing lab currently holds puzzles 501–1000 (CSV rows 502–1001):

```powershell
python backend/scripts/generate_capturing_tactics.py --csv data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv --start 500 --limit 500 --workers 8
```

`audit_midgame_tactics.py` still assumes a full-CSV dataset and a v2.0
baseline with the same IDs, so it does not audit a slice.

From the repository root:

```powershell
python backend/scripts/generate_capturing_tactics.py --csv data/puzzle-sources/Puzzles_2026-10-22_08-12-00_tactic_upload.csv --workers 4
python backend/scripts/import_puzzles.py data/puzzle-sources/Puzzles_2026-10-22_08-12-00_checkmate_upload.csv --workers 4
```

These replace `public/data/capturing-tactics.json`,
`public/data/checkmate-puzzles.json`, and
`public/data/checkmate-puzzle-recognition.json`. Labels are produced by the
current recognizers, not human-reviewed answers. An unmatched puzzle remains
in the dataset; an invalid line retains its error.

The tactical generator reports progress and writes the output only after the
whole batch succeeds. Its default worker count is four; `--workers 1` runs
without a process pool for diagnosis. Native fault traces are enabled in pool
workers.

The `qAyl8D` regression covers the original Windows access violation: tactical
trap probes must not replay captures of a general, and terminal positions
without both generals must not be passed to the native move generator.
