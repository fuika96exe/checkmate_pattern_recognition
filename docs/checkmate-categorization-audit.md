# Checkmate categorization audit

Audited rules version: `checkmate-patterns-2026.09.26`.
Corpus version: `5de49c3f18bd884e` — 4,729 imported puzzles.

**There are significant false positives and false negatives.** The clearest
problems are incorrect attacker/reply pairing, invented horse contribution,
and rejection of supported stalemate wins. Several other rules recognize only
a narrow example template or mistake the presence of pieces for cooperation.

This audit adds evidence and a reproducible audit script. It does not change
the production recognizers, their priorities, or the generated labels.

## What was checked

- Read all 27 recognizers and the puzzle-analysis/import path.
- Ran `backend/tests/test_position_analysis.py`: **67 passed, 14 failed**.
- Replayed all 4,729 final positions. Their check status agreed with the
  independent native `pyffish.gives_check` result in every case.
- Checked 146 distinct existing example calls, including literal case-list
  loops, covering all 27 categories. Tested horizontal reflection and
  180-degree rotation with colors exchanged.
- Checked all seven manually maintained puzzle expectations. Every expected
  label is present. These are positive expectations, not exhaustive truth
  sets: additional returned labels are not thereby verified.
- Added 15 focused probes, including positive controls and counterexamples.
  All reach native-engine-confirmed checkmate positions. Counterfactual
  removals show whether the alleged supporting pieces matter in selected cases.

The full evidence, FENs, move lists, affected IDs, features, and transformations
are in [checkmate-audit-evidence.json](checkmate-audit-evidence.json). The evidence
includes a SHA-256 hash of the recognizer source.

Pattern names were cross-checked with the source platform's
[published checkmate guide](https://www.xiangqi.com/articles/checkmate-strategies)
and [smothered-cannon explanation](https://www.xiangqi.com/strategy/smothered-cannon-checkmate).
The repository intentionally supports some broader conventions, especially
rook/pawn combinations under 双鬼拍门; those are identified as policy choices
rather than automatically treated as bugs.

## Findings, ordered by priority

### 1. P1 — Replies are paired with the wrong attacking move

Source: `backend/app/patterns.py:97`, `:700`, `:1371`, and `:1181`.

`_attacker_and_defender_trace` retains the initial defensive blunder. Consumers
then use `defender_trace[index]` as the reply to `attacker_trace[index]`. When
the sequence starts with the defender, that defensive move actually happened
**before** the attacking move.

This is the normal format of every uploaded puzzle: blunder followed by PV.
Starting the analysis immediately after the blunder, without changing any
solver move or the final board, restores:

| Missing label | Confirmed corpus cases | Example IDs |
| --- | ---: | --- |
| 双杯献酒 | 16 | `RPx5x1`, `Ll626B` |
| 挂角马 | 92 | `ojl2N3`, `R6jDy3` |

These are 108 distinct puzzles; 11 currently have no recognized pattern at
all. The corpus currently contains **zero** 双杯献酒 labels.

The same failure is reproduced for a built-in 进洞出洞 example by prepending a
legal defensive move. See probes `toast_with_legal_blunder_prefix` and
`drawer_with_legal_blunder_prefix`.

**Recommendation:** pair entries by actual ply adjacency, not by independent
list indices. Verify both attacker-first examples and blunder-first exports.

### 2. P1 — 侧面虎 invents horse control through boolean precedence

Source: `backend/app/patterns.py:1676`.

The expression is effectively:

```python
target == defender_king or (target in escape_squares and horse_attacks_target)
```

The king square is accepted even when that horse does not attack it. Since a
mated king necessarily appears in the overall attack map, the horse is given
a fictitious contribution.

**16 of 187 current 侧面虎 labels** have no actual horse attack on the king or
any adjacent palace square. Nine are the primary returned label. For example,
`o74w5P` reports that a black horse on `g3` controls the red king on `d0`.
That is not a horse move.

**Recommendation:** parenthesize the king/escape membership test, then require
an attack by the particular horse. Add blocked-leg and remote-horse negatives.

### 3. P1 — 59 stalemate wins are discarded as invalid checkmates

Source: `backend/app/main.py:244` and
`backend/scripts/generate_puzzle_recognition.py:29`.

The rule `STALEMATE` correctly recognizes 困毙, but the API marks every result
without `analysis.is_checkmate` invalid. The index generator then discards the
returned analysis and stores no labels.

Of the 175 previously reported “PV does not end in checkmate” records:

- **59 are true stalemates:** no check and no legal move.
- 116 are neither terminal checkmate nor stalemate.

Examples: `RZgpll`, `onp1b6`, `qre1lQ`. The native check-status cross-check
agrees with these classifications. Zero 困毙 labels consequently appear in the
active index despite the category being implemented and tested.

**Recommendation:** accept supported terminal wins and retain the distinction
between checkmate and stalemate. Continue rejecting the 116 nonterminal endings.

### 4. P1 — 卧槽马's static fallback does not require horse participation

Source: `backend/app/patterns.py:1284`.

`final_support` requires only a horse on a designated square, a mating board,
and some rook/cannon/pawn check. It does not check the horse's leg, attacks,
support of the checking piece, or contribution earlier in the line.

There are **70 current labels with zero final horse control of the king and
adjacent palace squares**. Of these, **50 also have no qualifying earlier
卧槽马 checking move**; 20 have historical checks and should not automatically
be called false positives. Example unsupported cases include `ReEekl` and
`ROxwXx`.

The focused `elbow_blocked_leg_no_palace_control` probe has a blocked horse
leg and an independent two-rook mate. Removing the horse preserves checkmate,
yet the current classifier labels it 卧槽马.

**Recommendation:** require a verified relevant attack/support relation or a
correctly paired historical forcing sequence.

### 5. P2 — 铁门栓 tests for an advisor between pieces, not an actual lock

Source: `backend/app/patterns.py:2236` and `:2258`.

Finding an advisor somewhere between a central line piece and the king is not
sufficient to establish a pin. Other intervening pieces may prevent any
check after that advisor leaves. The general fallback has the same problem.

**26 of 510 labeled positions** have no central candidate that checks the king
or exposes a check when the central advisor is removed. All 26 currently use
铁门栓 as their primary label. These are structural audit flags, not a complete
human adjudication of every historical line.

In `LxN1XK`, the claimed lock is the red general on `e0`, with multiple pieces
blocking its file before the black advisor on `e8`. The decisive attack is a
rook/cannon combination on the back rank; the claimed general pin is absent.

**Recommendation:** verify the actual constraint on the particular defender
and the relevant line, including screen counts and intervening pieces.

### 6. P2 — 双车错 and 钓鱼马 ignore capture of the checking piece as an escape

Sources: `backend/app/patterns.py:862` and `:1461`.

Both rules exclude occupied neighboring squares from support analysis. But a
king capturing the checking rook is a relevant escape, and another rook or
horse can be essential precisely because it prevents that capture.

Two focused probes demonstrate this:

- `double_rooks_guarding_occupied_capture_square`: returns false although the
  second rook is necessary to defend the mating rook.
- `angler_guards_checking_rook_capture_square`: returns false although the
  fishing horse is necessary to defend that same square.

In both cases, removing the supporting piece restores the legal defense
`e9f9`, capturing the checking rook. This is direct evidence of participation,
not just a nearby-piece heuristic.

**Recommendation:** include legal king captures of attacking occupants when
measuring restricted escapes. For 钓鱼马, also review the requirement that no
other non-horse piece may reinforce the horse's controlled square.

### 7. P2 — 白脸将 is hard-coded to an attacking general on the e-file

Source: `backend/app/patterns.py:2456`.

The flying-general constraint also applies on `d` and `f` files. The current
rule rejects those arrangements outright.

The corpus contains **125 mating positions** where an off-center attacking
general uniquely closes an otherwise unattacked, empty palace escape, yet
白脸将 is absent. Examples: `RPx5nB`, `LJXVQM`.

Probe `white_face_off_center_general` is a small native-confirmed reproduction
with the attacking general on `d0` and the mated king on `e9`.

### 8. P2 — 闷杀 excludes all horse checks, contradicting an existing example

Source: `backend/app/patterns.py:2375`;
test: `backend/tests/test_position_analysis.py:263`.

The blanket condition `"N" not in checking_piece_types` rejects horse-only
smothered mates. An existing test explicitly expects the `f6g8` horse finish
to be 闷杀, and currently fails.

There are **87 corpus horse mates** in which every orthogonal palace neighbor
is occupied by the defender's own piece, but 闷杀 is missing. Examples:
`LkMzrl`, `oyMnpl`. These are strong structural candidates; confirm the desired
overlap policy with horse-specific labels before relabeling all 87.

### 9. P2 — Last-move template restrictions miss valid mating structures

- **马后炮**, `backend/app/patterns.py:1788`: the final mover must be a cannon
  or horse. A rook can instead vacate the second screen and reveal the cannon
  mate behind the horse. Probe `horse_cannon_rook_unblocks_screen` reproduces
  this. Three current corpus records (`qKXY8M`, `qre1gv`, `LEnkrN`) have a
  qualifying final cannon/horse structure that the rule accepts in FEN-only
  mode and rejects with the actual line.
- **天地炮**, `backend/app/patterns.py:989`: the finishing move must capture a
  guard. Probe `heaven_earth_quiet_finish` has both cannons constraining the
  advisors, followed by the quiet mating move `f6f9`; it is rejected solely
  because the destination was empty.

**Recommendation:** test the mating mechanism, including discovered checks
and quiet finishes, rather than requiring the precise last move of a lesson
example.

### 10. P2 — 进洞出洞 recognizes only one horizontal orientation

Source: `backend/app/patterns.py:1142`.

The rook's file is fixed to `f` when attacking Black and `d` when attacking
Red. All **three existing positive Drawer examples** become false after
horizontal reflection, although the reflected lines remain checkmate.

No other category changed detection under horizontal reflection in the tested
examples. No example changed under 180-degree rotation with colors exchanged.

### 11. P2 — 八角马 chooses one horse before checking the alternatives

Source: `backend/app/patterns.py:1920`.

When several horses occupy palace corners, the rule selects one and checks
whether it is opposite the defending king. It does not try every candidate.

Probe `octagon_two_corner_horses` is rejected with horses on `d7` and `f7`.
Removing only `d7` leaves the mating board and the actual octagonal horse on
`f7`, making recognition possible. The existing corpus scan did not find a
miss of this exact geometric form; this is a reproduced edge case, not a
measured corpus error rate.

### 12. P2 — Material presence can stand in for cooperation

- **夹车炮**, `backend/app/patterns.py:619`: a rook and two cannons in any one
  flank group suffice; the final checker need not belong to that group, and
  cooperation is not verified. Probe `sandwich_uninvolved_home_half_cannons`
  is just a rook/horse mate with a decorative rook and two cannons in the
  attacker's home half. Removing all three decorative pieces preserves mate.
- **三车闹士**, `backend/app/patterns.py:2050`: counting three rook/pawn pieces
  in a broad rank zone, plus an advisor somewhere on the board, does not
  establish an advisor-breaking combination. Probe `three_chariots_remote_pawns`
  is labeled despite both pawns being on `a6`/`i6`, far from the palace;
  removing both leaves the same rook/horse mate.
- **双鬼拍门**: the repository deliberately permits rook/pawn combinations,
  but it counts *all* starting rooks and pawns and uses their starting zone.
  Spare pawns or a pawn that joins the net later can suppress a label. This
  needs an explicit decision about what “two participating attackers” means;
  do not silently replace the project's broader convention with a two-pawn-only
  definition.

### 13. P2 — 太监追皇帝 excludes support by the attacking general alone

Source: `backend/app/patterns.py:329`.

The support list includes only rooks, cannons and horses. A pawn chasing the
king with support from its own general is therefore rejected.

Probe `eunuch_pawn_supported_by_general` contains three consecutive advances
by the same checking pawn and two king replies. It ends in checkmate, with
the attacking general preventing capture of the pawn. Recognition is false
because the permitted support-piece list is empty.

## Per-category review

Counts are current emitted labels, not adjudicated truth. Labels overlap.
“No defect reproduced” describes the checks performed, not proof of complete
correctness.

| Category | Count | Audit result |
| --- | ---: | --- |
| 平顶冠 | 62 | No significant defect reproduced; exact cannon screen and front checker are checked. |
| 太监追皇帝 | 76 | FN: general-only support excluded; historical counts also need stronger causal linkage. |
| 花心兵 | 171 | No logic defect reproduced; backend Chinese name is mojibake. Center occupancy is weaker evidence than a verified necessary contribution. |
| 夹车炮 | 82 | FP reproduced with uninvolved home-half pieces. |
| 重炮杀 | 229 | No significant defect reproduced; friendly cannon as actual screen is required. |
| 双杯献酒 | 0 | 16 corpus FNs from reply misalignment. |
| 闷宫杀 | 319 | No concrete defect reproduced; deliberately limited to advisor screen, two advisors, cannon-only checks. One-advisor cases are routed differently. |
| 天地炮 | 15 | FN reproduced for a quiet finish; capture and king-location requirements cover only a subset of the mechanism. |
| 铁门栓 | 510 | 26 unsupported-lock structural flags; no pin validation. |
| 进洞出洞 | 1 | FNs from reply indexing and fixed horizontal orientation. |
| 大胆穿心 | 196 | Guard-control tests are broad and do not ensure the relevant central restraint. The 172 cases without immediate recapture are review-only: declining a sacrifice can be legitimate. |
| 三车闹士 | 18 | FP reproduced with two uninvolved outer-file pawns; global starting-piece count is brittle. |
| 双鬼拍门 | 84 | Broad rook/pawn convention is intentional; global count, starting zone, and participation policy need clarification. |
| 双车错 | 804 | FN when the second rook prevents capture of the checking rook on an occupied square. |
| 拔簧马 | 83 | No significant defect reproduced; actual final checking horse and vacated horse leg are checked. History is inherently required. |
| 花心车 | 349 | No significant defect reproduced; does not independently establish necessity of the center rook. |
| 侧面虎 | 187 | Confirmed precedence defect; 16 labels lack real palace control, including nine primary labels. |
| 马后炮 | 266 | FN from final-mover restriction; three corpus line/FEN inconsistencies. |
| 卧槽马 | 639 | Static fallback too permissive; 70 no-final-control flags, 50 without prior qualifying horse check. |
| 挂角马 | 169 | 92 corpus FNs restored by starting after the blunder. |
| 八角马 | 120 | FN reproduced with multiple corner-horse candidates. |
| 钓鱼马 | 240 | FN when support prevents capture of the checking rook; exclusive-control condition is also restrictive. |
| 双马饮泉 | 81 | No significant defect reproduced in line mode; FEN-only mode cannot recognize it even when the final geometry is available. |
| 闷杀 | 1,312 | Horse-check exclusion contradicts a positive example; 87 fully self-blocked horse-mate candidates omitted. |
| 双将 | 472 | No significant defect reproduced on valid mating positions. |
| 白脸将 | 156 | Misses off-center general support; 125 corpus positions uniquely constrain an empty escape this way. |
| 困毙 | 0 | Rule works; pipeline discards all 59 actual stalemate endings. |

## Reliability of the existing examples

The 14 failing tests are not 14 independent confirmed rule bugs. They include
the horse-smothered contradiction, overlap/priority expectations that have
drifted, and a plain fixture error: the Drawer board has a cannon on `i9`, while
`test_drawer_checkmate_examples` expects `h9` at line 1115.

Conversely, passing examples do not establish specificity. The tested
blocked-leg, decorative-piece, legal-prefix, quiet-finish and king-capture
counterexamples expose mistakes despite many positive tests passing.

The `causal` output field is assigned directly from `detected`; it is not a
separate causal verification. `best_match` is the first matching category in
`PATTERN_ORDER`, not a confidence-based judgment. False positives can therefore
hide a better primary label.

There are only seven human-maintained positive expectations for 4,729 puzzles.
That is insufficient to estimate overall precision or recall. Structural
flags overlap, and flagged historical cases still require review; do not sum
them into an “incorrect puzzle” percentage.

## Suggested implementation order

1. Correct ply pairing, Tiger precedence, and terminal stalemate handling.
2. Add the reproduced negative/positive cases before tightening contribution
   checks. Include king captures of occupied checking squares.
3. Remove the unjustified last-move/file/candidate-selection restrictions and
   preserve intentionally broader repository taxonomy choices.
4. Resolve the stale example expectations and the one coordinate typo.
5. Bump the rule version, rebuild the index, and review a stratified sample of
   added/removed labels for every category. Keep reviewed truth separate from
   generated predictions.

Reproduce the audit from the repository root:

```powershell
python backend/scripts/audit_checkmate_patterns.py --workers 4
python -m pytest backend/tests/test_position_analysis.py -q -p no:cacheprovider
```
