# Puzzle batch import — 2026-10-31

Both active libraries now use the complete CSV exports stored in
[`data/puzzle-sources`](../data/puzzle-sources/README.md).

| Dataset | Imported | Matched | Unmatched | Invalid analysis |
| --- | ---: | ---: | ---: | ---: |
| Capturing tactics | 3,135 | 1,371 | 1,764 | 0 |
| Checkmate | 4,729 | 4,166 | 388 | 175 |

All 175 invalid checkmate analyses have the same reason: the supplied PV does
not end in checkmate. These puzzles remain available with their errors. An
unmatched puzzle is retained without assigning an unsupported label.

Tactical rules: `nine-tactics-draft-0.10`.
Checkmate rules: `checkmate-patterns-2026.09.26`.
Checkmate dataset version: `5de49c3f18bd884e`.

## Tactical label counts

Multiple labels can occur in one puzzle.

| Label | Puzzles |
| --- | ---: |
| 交换 | 561 |
| 捉双 | 463 |
| 闪击 | 256 |
| 消除保护 | 211 |
| 围困 | 159 |
| 牵制 | 154 |
| 串打 | 80 |
| 炮兵突破 | 12 |

Material outcomes: 2,480 puzzles win major-piece material, 226 win smaller
material, and 429 do not show a net material gain over the supplied line.

## Native crash fix and validation

The original `qAyl8D` line triggered a Windows access violation in
`pyffish.get_fen`. Trap analysis simulated a capture of a general and then
requested further moves from a position missing that general. The tactical
recognizer now excludes these pseudo captures, and the board layer stops
kingless positions before calling the native engine.

The complete 3,135-puzzle tactical batch finished successfully. Ten focused
board/import/index tests passed, and the updated library component passed
ESLint. The broader tactical/exchange run had 104 passes and two pre-existing
label failures, reproduced using the pre-change tactical recognizer:

- `test_two_separate_black_pieces_can_form_a_fork`
- `test_unanswerable_new_capture_remains_a_discovered_attack`

Dataset counts, unique IDs, solver sides, replay lengths, index keys, and
dataset versions were checked. All three JSON datasets served by the local
frontend were compared with the generated files.
