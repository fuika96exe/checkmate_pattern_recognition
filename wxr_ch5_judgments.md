# WXR-2018 第五章：长将／长捉 110 题逐题判断

本报告按当前项目的 `backend/app/repetition.py` 回放。每题的书中线路如只展示了一轮循环，会仅重复其已经证明的末段循环，以触发第三／第四次同局面的裁决门槛。

判定等级：长将（3）> 捉被卧槽马牵制的车（2）> 长捉（1）> 闲着（0）。第三次同局面时等级较高的一方必须变着；同级则警告，第四次同局面判和。

“书中结论”是 `ch5_cases.json` 的标注；“当前判断”是本项目规则的实际结果。它们不一致的题目尤其适合作为后续规则改进参考。

## 汇总

- 共 110 题；当前判断与书中结论一致：59 题；不一致或无法裁决：51 题。
- 本报告不把书中结论强行当成当前引擎输出；每题均保留二者，便于另一位 AI 找到真正的规则分歧。

## d001 — 图 1（第 40 页）

- 分类：1 Perpetual checks by one player
- 书中结论：红方必须变着。Red would be delivering perpetual checks. Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长将、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红R2+1（将）；黑K6+1（捉）；红R2-1（将）；黑K6-1（捉）；红R2+1（将）；黑K6+1（捉）；红R2-1（将）
- 一致性：一致。

## d002 — 图 2（第 40 页）

- 分类：1 Perpetual checks by one player
- 书中结论：红方必须变着。Under ALL circumstances, any player who delivers perpetual checks with one piece or more than one pieces would be dealt with a loss. Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长将、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红R4=5（将）；黑K5=6（捉）；红R5=4（将）；黑K6=5（捉）；红R4=5（将）；黑K5=6（捉）；红R5=4（将）；黑K6=5（捉）
- 一致性：一致。

## d003 — 图 3（第 41 页）

- 分类：1 Perpetual checks by one player
- 书中结论：红方必须变着。Red has been delivering perpetual checks on the Black King. No matter if it were one piece or two pieces that were delivering the perpetual checks, it would not be permitted. Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长将、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红R4+1（将）；黑K4+1（捉）；红R5=6（将）；黑K4=5（捉）；红R6=5（将）；黑K5=4（捉）；红R4-1（将）；黑K4-1（捉）；红R4+1（将）；黑K4+1（捉）
- 一致性：一致。

## d004 — 图 4（第 41 页）

- 分类：2 Simultaneous perpetual cross-checks
- 书中结论：和棋。In this instance, both players would be viewed has having delivered perpetual checks. If neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长将、黑方为长将；双方等级相同，按当前规则判和。
- 回放标签：红R5+1（将）；黑C6=5（将）；红R5=4（将）；黑C5=6（将）；红R4=5（将）；黑C6=5（将）；红R5=4（将）
- 一致性：一致。

## d005 — 图 5（第 42 页）

- 分类：3 Two-to-one Check
- 书中结论：红方必须变着。Red has been delivering perpetual checks while Black had countered by alternating a check with an idle move. Red would be seen as having delivered perpetual checks which are prohibited. Black would not have gone against the rules. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长将、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红P4=5（将）；黑P6=5（将）；红P5=4（将）；黑P5=6（捉）；红P4=5（将）；黑P6=5（将）；红P5=4（将）
- 一致性：一致。

## d006 — 图 6（第 42 页）

- 分类：4 Perpetual Mating Threat
- 书中结论：和棋。Red would have alternated a chase with a mating threat, while Black would have played idle moves. It would be considered to be a draw if neither party wanted to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2=3（捉）；黑E7+9（捉）；红R3=2（捉）；黑E9-7（捉）；红R2=3（捉）；黑E7+9（捉）；红R3=2（捉）；黑E9-7（捉）；红R2=3（捉）
- 一致性：一致。

## d007 — 图 7（第 43 页）

- 分类：4 Perpetual Mating Threat
- 书中结论：和棋。Red's perpetual mating threat is to be considered legal. Hence, if neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红H6+7（捉）；黑K6+1（闲）；红H7-6（闲）；黑K6-1（闲）；红H6+7（捉）；黑K6+1（闲）；红H7-6（闲）
- 一致性：一致。

## d008 — 图 8（第 43 页）

- 分类：4 Perpetual Mating Threat
- 书中结论：和棋。Red would be delivering perpetual mating threats, while Black would have been perpetually blocking the Red Cannon to save himself. Both players have not play against the rules. It would be a draw if neither player wished to change their moves.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C7=3（捉）；黑C3=7（闲）；红C3=7（捉）；黑C7=3（闲）；红C7=3（捉）；黑C3=7（闲）；红C3=7（捉）；黑C7=3（闲）
- 一致性：不一致。

## d009 — 图 9（第 44 页）

- 分类：4 Perpetual Mating Threat
- 书中结论：和棋。In this example, Red was threatening with perpetual mating threats, which would be legal. If neither party wished to vary their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C7=5（捉）；黑C6=5（捉）；红C5=2（捉）；黑C5=8（捉）；红C2=5（捉）；黑C8=5（捉）；红C5=2（捉）
- 一致性：一致。

## d010 — 图 10（第 44 页）

- 分类：5 Resolving mating threat with counter-mating threat
- 书中结论：和棋。Both players have resolved their opponent's mating threat and countered with a mating threat of their own for every move. In essence, they would have threatened each other with perpetual mating threats. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红P5=4（将）；黑K6=5（捉）；红K5=4（闲）；黑P5=6（捉）；红P4=5（将）；黑K5=6（捉）；红K4=5（闲）；黑P6=5（捉）；红P5=4（将）；黑K6=5（捉）；红K5=4（闲）
- 一致性：不一致。

## d011 — 图 11（第 45 页）

- 分类：6 Alternate Check and Mating Threat
- 书中结论：和棋。Red's alternate check and mating threat is legal. It would be a draw if neither party wished to change their moves.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红R4=2（捉）；黑K5=6（捉）；红R2=4（将）；黑K6=5（捉）；红R4=2（捉）；黑K5=6（捉）；红R2=4（将）；黑K6=5（捉）
- 一致性：不一致。

## d012 — 图 12（第 45 页）

- 分类：7 Alternate Check and Chase or Alternating many checks and chase
- 书中结论：和棋。In this case, Red would be treated having alternated a check with a chase, which would not go against the rules. It would be a draw if neither player wished to vary their moves.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红C4=5（捉）；黑K5=6（捉）；红C5=4（将）；黑K6=5（捉）；红C4=5（捉）；黑K5=6（捉）；红C5=4（将）；黑K6=5（捉）
- 一致性：不一致。

## d013 — 图 13（第 46 页）

- 分类：7 Alternate Check and Chase or Alternating many checks and chase
- 书中结论：和棋。In this example, Red has delivered a check or checks before chasing the Black Cannon. Although the Black Cannon was not protected/rooted, this would not be considered to be a perpetual chase by Red. Such a situation would be a draw if neither player wanted to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R2+3（将）；黑K6+1（捉）；红R2-9（捉）；黑C9-5（闲）；红R2+8（将）；黑K6-1（闲）；红R2+1（将）；黑K6+1（闲）；红R2-4（捉）；黑C9-2（闲）；红R2+3（将）；黑K6-1（闲）；红R2-1（捉）；黑C9+4（闲）；红R2+2（将）；黑K6+1（闲）；红R2-6（捉）；黑C9+3（捉）；红R2-3（捉）
- 一致性：一致。

## d014 — 图 14（第 46 页）

- 分类：8 Alternate Chase and Idle, Alternate Check and Threat to capture material after check/discovered check
- 书中结论：和棋。After delivering a check to the Black King, Red's next move (R7-1) would be considered to be an idle move as it would not constitute a check. Even though it threatens to capture a major Black piece using a capture-after-check, Red's moves would be in effect, an alternate check and idle. It would be legal, and if neither party wished to vary their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R7+1（将）；黑A5-4（闲）；红R7-1（闲）；黑A4+5（闲）；红R7+1（将）；黑A5-4（闲）；红R7-1（闲）；黑A4+5（闲）
- 一致性：一致。

## d015 — 图 15（第 47 页）

- 分类：8 Alternate Chase and Idle, Alternate Check and Threat to capture material after check/discovered check
- 书中结论：和棋。When Red retreated his Chariot and then advanced his Chariot again, Red would be prepared to use his Cannon to capture the Black Advisor or Pawn to capture one of the Black Chariots (capture-after-check). Red's moves did not constitute a perpetual check or a perpetual chase. Hence, it would be a draw if neither player wished to vary their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R8-1（将）；黑K5-1（闲）；红R8+1（捉）；黑K5+1（闲）；红R8-1（将）；黑K5-1（闲）；红R8+1（捉）；黑K5+1（闲）；红R8-1（将）；黑K5-1（闲）；红R8+1（捉）
- 一致性：一致。

## d016 — 图 16（第 47 页）

- 分类：8 Alternate Chase and Idle, Alternate Check and Threat to capture material after check/discovered check
- 书中结论：和棋。As can be seen, the nature of Red's moves would be considered to be an alternate check followed by a threat to capture material with a discovered check. Red's moves would be legal. Hence, if neither party wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R7+4（将）；黑K4+1（闲）；红R7-4（闲）；黑K4-1（闲）；红R7+4（将）；黑K4+1（闲）；红R7-4（闲）
- 一致性：一致。

## d017 — 图 17（第 48 页）

- 分类：9 Alternate chase and threat to capture material after check/discovered check
- 书中结论：和棋。Red's moves would constitute an alternate chase with a threat to capture material after check/discovered check. If neither player wished to change their moves, it would be a draw.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红R6=2（闲）；黑K5-1（捉）；红R2=6（捉）；黑K5+1（捉）；红R6=2（闲）；黑K5-1（捉）；红R2=6（捉）；黑K5+1（捉）
- 一致性：不一致。

## d018 — 图 18（第 48 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。Red has been perpetually chasing the protected Black Chariot. This is NOT allowed. Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C4-1（捉）；黑+R+2（捉）；红C4-2（捉）；黑R4-2（闲）；红C4+2（捉）；黑+R+2（捉）；红C4-2（捉）；黑R4-2（闲）；红C4+2（捉）
- 一致性：一致。

## d019 — 图 19（第 49 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。In this case, Red would be treated as though he had perpetually chased the Black Chariot which would not be allowed. Black's moves would be considered to be an alternate chase and idle which would be allowed. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C2-1（捉）；黑R4-2（捉）；红C2+2（捉）；黑R4+2（捉）；红C2-2（捉）；黑R4-2（捉）；红C2+2（捉）
- 一致性：不一致。

## d020 — 图 20（第 49 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。In this position, Red's Cannon has been perpetually chasing the same Chariot for every move. Black, on the other hand, had countered by alternately chasing the Red Horse and Cannon. It would seem to be a two-to-two chase. However, Red's perpetual chase would not be allowed. Black would have alternate chasing two different Red pieces, and this is allowed according to the rules. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C2+1（捉）；黑R4+2（捉）；红C2-2（捉）；黑R4-2（捉）；红C2+2（捉）；黑R4+2（捉）；红C2-2（捉）；黑R4-2（捉）；红C2+2（捉）
- 一致性：一致。

## d021 — 图 21（第 50 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。The Red Cannon had made use of advancing and retreating the Advisor to threaten the Black Chariot which was protected. Red's moves would not be allowed, and Red would have to change his moves or be penalized with a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红H5+6（捉）；黑R3+1（捉）；红C2-1（捉）；黑C7+1（捉）；红A5+6（捉）；黑C7+1（捉）；红A6-5（捉）；黑C7-1（捉）；红A5+6（捉）；黑C7+1（捉）；红A6-5（捉）
- 一致性：一致。

## d022 — 图 22（第 50 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。Red would have made two chases, while Black was considered to have made two idle moves. The act of the Red Cannon chasing the Chariot would not be allowed. Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C8-1（捉）；黑R6-1（捉）；红C8+1（捉）；黑R6+1（捉）；红C8-1（捉）；黑R6-1（捉）；红C8+1（捉）；黑R6+1（捉）；红C8-1（捉）
- 一致性：不一致。

## d023 — 图 23（第 51 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。The Red Cannon was perpetually chasing the Black Chariot. Although Red would lose his own Chariot after capturing the Black Chariot, the moves made would be considered to be a perpetual chase on the Black Chariot, which would not be allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C5=7（捉）；黑R3=4（捉）；红C7=6（捉）；黑R4=3（捉）；红C6=7（捉）；黑E5+3（捉）；红E7-9（捉）；黑E3-5（捉）；红E9+7（捉）；黑R3=4（捉）；红C7=6（捉）；黑R4=3（捉）；红C6=7（捉）
- 一致性：不一致。

## d024 — 图 24（第 51 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。In this example, the two Red Cannons would have been perpetually chasing the Black Chariot in a concerted effort. The Black Chariot had replied by counter-chasing the Red Horse and the Pawn that had crossed the river. The World Xiangqi Rules allow a friendly piece to chase two or more opponent's pieces, but forbid two or more friendly pieces from chasing a single opponent's piece. Hence, in this situation, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C2+4（捉）；黑R4+3（捉）；红C4+1（捉）；黑R4+2（捉）；红C2-5（捉）；黑R4-5（捉）；红C4+3（捉）；黑R4+3（捉）；红C2+2（捉）；黑R4+2（捉）；红C4-5（捉）；黑R4-5（捉）；红C2+3（捉）；黑R4+3（捉）；红C4+2（捉）；黑R4+2（捉）
- 一致性：一致。

## d025 — 图 25（第 52 页）

- 分类：10 Cannon perpetually chasing Chariot
- 书中结论：红方必须变着。The Red Cannons have taken turns at chasing the Black Chariot which was protected. The Black Chariot, in turn, had been chasing two different Red pieces, which is allowed. Red would have gone against the rules and must change his moves or be dealt with a loss.
- 当前判断：未形成可裁决重复。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：给出的着法及其可证明的末段循环未达到当前裁决阈值。
- 回放标签：红C2+4（捉）；黑R4+3（捉）；红C4+1（捉）；黑R4+2（捉）；红C4-2（捉）；黑R4-2（捉）；红C2-3（捉）；黑R4-3（捉）；红C4+5（捉）
- 一致性：不一致。

## d026 — 图 26（第 52 页）

- 分类：11 One Cannon chasing two Opponent's Chariots
- 书中结论：和棋。Red's Cannon had been perpetually chasing both the opponent's Chariots with each alternate move. This repetition is allowed, and Red would not have broken the rules. It would be a draw if neither player wished to change their moves.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红C2=1（捉）；黑R9=8（捉）；红C1=9（捉）；黑R1=2（捉）；红C9=2（捉）；黑R8=9（捉）；红C2=8（捉）；黑R2=1（捉）；红C8=1（捉）
- 一致性：不一致。

## d027 — 图 27（第 53 页）

- 分类：11 One Cannon chasing two Opponent's Chariots
- 书中结论：和棋。The Red Cannon has chased two different Black Chariots on each of the moves although the Black Chariots were not protected. It would be allowed. It will be a draw if both sides refuse to vary their moves.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C4+1（捉）；黑R2+2（捉）；红C4+3（捉）；黑R4+3（捉）；红C4-5（捉）；黑R2-5（闲）；红C4+2（捉）；黑R4+2（捉）；红C4+3（捉）；黑R2+5（捉）；红C4-5（捉）；黑R4-5（捉）；红C4+5（捉）
- 一致性：不一致。

## d028 — 图 28（第 53 页）

- 分类：11 One Cannon chasing two Opponent's Chariots
- 书中结论：和棋。The Red Cannons are attacking the two Black Chariots on alternate moves. Although the Black chariot was not protected, it would be considered that Red had used two pieces (his Cannon) to perpetually chase two different Black pieces. It would be a draw if neither player wished to change his moves. It is not considered to be Red's two Cannon pieces perpetually chasing the same opponent's piece. It would also not be treated as though one of Red's Cannon had perpetually chased the same opponent's Chariot. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C4+1（捉）；黑R2-3（捉）；红C2-1（捉）；黑R4-4（闲）；红C4+2（捉）；黑R4+2（闲）；红C2+2（捉）；黑R4+2（捉）；红C2+3（捉）；黑R2+3（捉）；红C4-4（捉）；黑R4-4（闲）；红C2-3（捉）；黑R2-3（闲）；红C4+4（捉）；黑R4+4（捉）；红C2+3（捉）
- 一致性：不一致。

## d029 — 图 29（第 54 页）

- 分类：12 Chariot chasing protected Cannon
- 书中结论：和棋。The Red Chariot has been perpetually chasing the Black Cannon which was protected by the Black Chariot. It would be allowed. Hence, it would be a draw if neither party wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R1=2（捉）；黑C8=9（捉）；红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）；黑C8=9（捉）；红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）
- 一致性：一致。

## d030 — 图 30（第 54 页）

- 分类：12 Chariot chasing protected Cannon
- 书中结论：和棋。Red's Chariot has been chasing the Black Cannon which was protected every move. Such a position is permissible. It would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4=3（捉）；黑C7=3（捉）；红R3=7（捉）；黑C3=7（捉）；红R7=3（捉）；黑C7=3（捉）；红R3=7（捉）；黑C3=7（捉）；红R7=3（捉）
- 一致性：一致。

## d031 — 图 31（第 55 页）

- 分类：12 Chariot chasing protected Cannon
- 书中结论：和棋。The moves made by Black's riverbank Cannon would be considered to be a perpetual mating threat which is allowed. Red's Chariot would have been chasing Black's Cannon, except that in one of the moves, the Black Cannon would be protected by the Black Horse. Therefore, the Black Chariot would have been chasing a protected opponent's piece on one move and chasing an unprotected opponent's piece on the other move. This is also allowed. Therefore, if neither player wanted to change his moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）；黑C8=9（捉）；红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）；黑C8=9（捉）；红R2=1（捉）
- 一致性：一致。

## d032 — 图 32（第 55 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。The Red Chariot is not allowed to chase an unprotected opponent's Cannon perpetually. Hence, if Red did not vary his moves, it would be a loss for Red.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R8=9（捉）；黑C1=5（捉）；红R9=5（捉）；黑C5=1（闲）；红+R=9（捉）；黑C1=5（捉）；红R9=5（捉）；黑C5=1（闲）
- 一致性：一致。

## d033 — 图 33（第 56 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。Red's Chariot has been perpetually chasing the Black cannon which was not protected during the chase. This is not allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）；黑C8=9（捉）；红R2=1（捉）；黑C9=8（捉）；红R1=2（捉）
- 一致性：不一致。

## d034 — 图 34（第 56 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。Black's perpetual mating threat would not go against the rules. Red's perpetual chase of the unprotected Black Cannon would not be permissible. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R3=2（捉）；黑C8=3（闲）；红R2=7（捉）；黑C3=8（闲）；红R7=2（捉）；黑C8=3（闲）；红R2=7（捉）；黑C3=8（闲）；红R7=2（捉）
- 一致性：一致。

## d035 — 图 35（第 57 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。Red's Chariot is considered to have perpetually chased the unprotected Black Cannon. It is not allowed. Black's Cannon would have been seen to be perpetually threatening with mating threats, which is allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R6=3（捉）；黑C7=3（捉）；红R3=7（捉）；黑C3=7（捉）；红R7=3（捉）；黑C7=3（捉）；红R3=7（捉）；黑C3=7（捉）；红R7=3（捉）
- 一致性：不一致。

## d036 — 图 36（第 57 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。Black's Cannon had been chasing two different opponent's Horses on alternate moves which would be permissible. Red's Chariot would be viewed as having perpetually chased the Black Cannon which was not protected. Such an act would not be allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R2=7（捉）；黑C3=7（捉）；红R7=3（捉）；黑C7=3（捉）；红R3=7（捉）；黑C3=7（捉）；红R7=3（捉）；黑C7=3（捉）；红R3=7（捉）
- 一致性：一致。

## d037 — 图 37（第 58 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。Black would have alternated a check with a chase targeted at the Red Horse. It would be permitted. Red's Chariot is seen as having perpetually chased the unprotected Black Cannon. It would not be permitted. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R8+1（捉）；黑C1+1（将）；红R8-1（捉）；黑C1-1（捉）；红R8+1（捉）；黑C1+1（将）；红R8-1（捉）；黑C1-1（捉）
- 一致性：一致。

## d038 — 图 38（第 58 页）

- 分类：13 Chariot chasing unprotected Cannon
- 书中结论：红方必须变着。In this position, Black would have alternated a mating threat with a chase, which would be permitted. Red would be regarded as having perpetually chased an unprotected Black Cannon which is not permissible. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R1=7（捉）；黑C3=8（捉）；红R7=2（捉）；黑C8=3（捉）；红R2=7（捉）；黑C3=8（捉）；红R7=2（捉）；黑C8=3（捉）；红R2=7（捉）
- 一致性：不一致。

## d039 — 图 39（第 59 页）

- 分类：14 Chariot pinned by opponent's Horse
- 书中结论：红方必须变着。In the above three examples, the Black Chariot has been rendered immobile by the Red Horse. The Black Chariot would not be considered to be chasing the Red Horse in this instance. Red, on the other hand, had used his Cannon-Chariot combination and Horse-Cannon combination to chase the Black Chariot. It would be considered to be a perpetual chase on the Black Chariot, it would not be allowed. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为捉被卧槽马牵制的车、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红R8+2（捉卧槽牵制车）；黑A6+5（捉）；红R8-3（捉卧槽牵制车）；黑A5-6（捉）；红R8+3（捉卧槽牵制车）；黑A6+5（捉）；红R8-2（捉卧槽牵制车）；黑A5-6（捉）；红R8+2（捉卧槽牵制车）
- 一致性：一致。

## d040 — 图 40（第 59 页）

- 分类：14 Chariot pinned by opponent's Horse
- 书中结论：红方必须变着。In the above three examples, the Black Chariot has been rendered immobile by the Red Horse. The Black Chariot would not be considered to be chasing the Red Horse in this instance. Red, on the other hand, had used his Cannon-Chariot combination and Horse-Cannon combination to chase the Black Chariot. It would be considered to be a perpetual chase on the Black Chariot, it would not be allowed. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为捉被卧槽马牵制的车、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红C8-1（捉卧槽牵制车）；黑A5-6（捉）；红C8-1（捉卧槽牵制车）；黑A6+5（捉）；红C8+1（捉卧槽牵制车）；黑A5-6（捉）；红C8-5（捉卧槽牵制车）；黑A6+5（捉）；红C8+5（捉卧槽牵制车）
- 一致性：一致。

## d041 — 图 41（第 60 页）

- 分类：14 Chariot pinned by opponent's Horse
- 书中结论：红方必须变着。In the above three examples, the Black Chariot has been rendered immobile by the Red Horse. The Black Chariot would not be considered to be chasing the Red Horse in this instance. Red, on the other hand, had used his Cannon-Chariot combination and Horse-Cannon combination to chase the Black Chariot. It would be considered to be a perpetual chase on the Black Chariot, it would not be allowed. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为捉被卧槽马牵制的车、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红H9+8（捉卧槽牵制车）；黑A6+5（捉）；红H8-7（捉卧槽牵制车）；黑A5-6（捉）；红H7+6（捉卧槽牵制车）；黑A6+5（捉）；红H6-7（捉卧槽牵制车）；黑A5-6（捉）；红H7+8（捉卧槽牵制车）
- 一致性：一致。

## d042 — 图 42（第 61 页）

- 分类：15 Horse–Cannon, Double Horse combination perpetually chasing opponent's Chariot
- 书中结论：黑方必须变着。In this position, Red's Chariot would have alternated a chase with an idle move, it would be permissible. Black would have perpetually chased the Red Chariot with his cannon and Horse alternately. It would not be allowed. Therefore, Black must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）；红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）
- 一致性：不一致。

## d043 — 图 43（第 61 页）

- 分类：15 Horse–Cannon, Double Horse combination perpetually chasing opponent's Chariot
- 书中结论：黑方必须变着。Red had been using his Chariot to chase two different opponent's pieces on alternate moves it would be permissibe. Black, on the other hand, would be considered to have perpetually chased the Red Chariot with his Cannon-Horse combination , it would not be permissible. Therefore, Black would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4=3（捉）；黑H8-7（捉）；红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）；红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）
- 一致性：不一致。

## d044 — 图 44（第 62 页）

- 分类：15 Horse–Cannon, Double Horse combination perpetually chasing opponent's Chariot
- 书中结论：黑方必须变着。In this position, Red's Chariot would have alternated a chase targed at Black's Cannon with every alternate move. It is not a perpetual chase by Red, and this would be permissible. Black would have used his Cannon–Horse combination to chase the Red Chariot for every move. Black cannot use the excuse that his right Horse on the third file was under attack to validate chasing the Red Chariot. In this position, Black must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4=3（捉）；黑H8-7（捉）；红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）；红R3=4（捉）；黑H7+8（捉）；红R4=3（捉）；黑H8-7（捉）
- 一致性：不一致。

## d045 — 图 45（第 62 页）

- 分类：16 Horse perpetually chasing Chariot
- 书中结论：红方必须变着。The Red Horse has perpetually chased the Chariot, it would not be permissible. Black would be seen as having alternated a chase with an idle move, it is allowed. Therefore, Red would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红H4+3（捉）；黑R5-1（捉）；红H3+4（捉）；黑R5+1（捉）；红H4-3（捉）；黑R5-1（捉）；红H3-4（捉）；黑R5+1（捉）；红H4+3（捉）
- 一致性：不一致。

## d046 — 图 46（第 63 页）

- 分类：16 Horse perpetually chasing Chariot
- 书中结论：黑方必须变着。In the above two examples, a two-to-one chase has occurred. Although the Horse was forced to perpetually chase the opponent's Chariot to avoid capture, this would still not be allowed. The Chariot have alternated a chase with an idle move for both positions, it is perfectly legal. Hence, in both cases, the players with the Horse would have to change his moves or be penalized with a loss. Black has the Horse, so Black must change his moves or be penalized with a loss.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红R7+2（捉）；黑H1+2（捉）；红R7-1（闲）；黑H2-1（捉）；红R7+1（捉）；黑H1+2（捉）；红R7-1（闲）；黑H2-1（捉）；红R7+1（捉）
- 一致性：一致。

## d047 — 图 47（第 63 页）

- 分类：16 Horse perpetually chasing Chariot
- 书中结论：红方必须变着。In the above two examples, a two-to-one chase has occurred. Although the Horse was forced to perpetually chase the opponent's Chariot to avoid capture, this would still not be allowed. The Chariot have alternated a chase with an idle move for both positions, it is perfectly legal. Hence, in both cases, the players with the Horse would have to change his moves or be penalized with a loss. Red has the Horse, so Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红H1+3（捉）；黑R8=7（捉）；红H3-1（捉）；黑R7=8（捉）；红H1+3（捉）；黑R8=7（捉）；红H3-1（捉）；黑R7=8（捉）；红H1+3（捉）
- 一致性：不一致。

## d048 — 图 48（第 64 页）

- 分类：17 Chariot and Horse mutual perpetual chase
- 书中结论：和棋。Both players have perpetually chased each other. If both they do not change their moves, it will be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R8+1（捉）；黑H4+3（捉）；红R8=7（捉）；黑H3-5（捉）；红R7-1（捉）；黑H5-4（捉）；红R7=6（捉）；黑H4+6（捉）；红R6+1（捉）；黑H6+5（捉）；红R6=5（捉）；黑H5-3（捉）；红R5-1（捉）；黑H3-4（捉）；红R5=6（捉）
- 一致性：一致。

## d049 — 图 49（第 65 页）

- 分类：18 Chariot perpetually chasing Horse
- 书中结论：红方必须变着。In this position, Black would be seen as having alternated a chase with an idle move which would be permissible. Red would have perpetually chased the Black Horse, it would not be permitted. Therefore, Red would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R7-1（捉）；黑H2+1（捉）；红R7-2（捉）；黑H1-2（捉）；红R7+2（捉）；黑H2+1（捉）；红R7-2（捉）；黑H1-2（捉）；红R7+2（捉）
- 一致性：不一致。

## d050 — 图 50（第 65 页）

- 分类：18 Chariot perpetually chasing Horse
- 书中结论：红方必须变着。The moves by the Black Horse could be considered to have been an alternate check and chase or a one-to-two chase. It would be permissible. Red would be deemed as having perpetually chased the Black Horse, which would not be allowed. Therefore, Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R6+2（捉）；黑H2+3（将）；红R6-2（捉）；黑H3-2（捉）；红R6+2（捉）；黑H2+3（将）；红R6-2（捉）；黑H3-2（捉）
- 一致性：一致。

## d051 — 图 51（第 66 页）

- 分类：19 Chasing material of the same type
- 书中结论：和棋。Red's Chariot had been perpetually offering an exchange of Chariots which would be allowed. Black's moves are considered to be a perpetual mating threat, which is also permissible. Hence, if neither player wanted to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R3=1（捉）；黑R9=8（捉）；红R1=2（捉）；黑R8=7（捉）；红R2=3（捉）；黑R7=8（捉）；红R3=2（捉）；黑R8=9（捉）；红R2=1（捉）；黑R9=7（捉）；红R1=3（捉）
- 一致性：一致。

## d052 — 图 52（第 67 页）

- 分类：19 Chasing material of the same type
- 书中结论：和棋。Red had been perpetually offering his Chariot to initiate an exchange of pieces. Black's Chariot was not limited in movement and opted not to accept the exchange because of the situation on the board. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：未形成可裁决重复。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：给出的着法及其可证明的末段循环未达到当前裁决阈值。
- 回放标签：红R8+2（捉）；黑R5+3（捉）；红R8-3（捉）；黑R5-2（捉）；红R8+2（捉）；黑R5+2（捉）；红R8-2（捉）；黑R5-1（捉）；红R8+1（捉）
- 一致性：不一致。

## d053 — 图 53（第 67 页）

- 分类：19 Chasing material of the same type
- 书中结论：红方必须变着。Black's Cannon has been pinned to the bottom rank and could not leave that line. Red's riverbank Cannon cannot perpetually chase the Black Cannon under the pretext of trying to issue mating threats perpetually. It would not be allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C3=8（捉）；黑C2=3（闲）；红C8=7（捉）；黑C3=2（闲）；红C7=8（捉）；黑C2=3（闲）；红C8=7（捉）；黑C3=2（闲）；红C7=8（捉）
- 一致性：一致。

## d054 — 图 54（第 68 页）

- 分类：19 Chasing material of the same type
- 书中结论：和棋。Although the Black Cannon was pinned to the bottom rank, when it moved to the 7th file, it would be protected. Hence, Red's Cannon cannot be considered to have been perpetually chasing the Black Cannon in this case. If both players did not wish to change their moves, it would be a draw!
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C7=2（捉）；黑C8=7（捉）；红C2=3（捉）；黑C7=8（捉）；红C3=2（捉）；黑C8=7（捉）；红C2=3（捉）；黑C7=8（捉）；红C3=2（捉）
- 一致性：一致。

## d055 — 图 55（第 68 页）

- 分类：19 Chasing material of the same type
- 书中结论：红方必须变着。In this position, the Black Horse is blocked and cannot capture the Red Horse. Therefore, the moves that Red had made would be treated as though it was a perpetual chase, it would not be allowed. Therefore, Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红H2+4（捉）；黑H7+9（闲）；红H4-2（捉）；黑H9-7（闲）；红H2+4（捉）；黑H7+9（闲）；红H4-2（捉）；黑H9-7（闲）
- 一致性：一致。

## d056 — 图 56（第 69 页）

- 分类：20 Cannon changing cannon mount to chase unprotected opponent's Horse, Advisor, Elephant and Pawn
- 书中结论：红方必须变着。In this position, the Black Horse is unprotected. Red has been attacking the Black Horse by making use of his cannon and with his Pawn and the opponent's Cannon to act as a cannon mount. It would be considered that Red had perpetually chased the Black Horse , it would not be allowed. Therefore, Red would need to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红P1=2（捉）；黑C5=8（闲）；红P2=3（捉）；黑C8=7（闲）；红P3=2（捉）；黑C7=8（闲）；红P2=3（捉）；黑C8=5（闲）；红P3=2（捉）
- 一致性：一致。

## d057 — 图 57（第 70 页）

- 分类：20 Cannon changing cannon mount to chase unprotected opponent's Horse, Advisor, Elephant and Pawn
- 书中结论：红方必须变着。In the above two examples, Red's Cannon has been attacking Black pieces by means of changing cannon mounts. In the first example, Red would be considered to have perpetually chased the Black Advisor; while in the second example, Red's Cannon would have perpetually chased the Black Elephant. In both examples, Black's moves were considered to be legal. Therefore, in both examples, Red would need to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C3=4（捉）；黑C9=6（闲）；红A4-5（捉）；黑C6=8（捉）；红A5+4（捉）；黑C8=6（闲）；红A4-5（捉）；黑C6=8（捉）；红A5+4（捉）；黑C8=6（闲）
- 一致性：一致。

## d058 — 图 58（第 70 页）

- 分类：20 Cannon changing cannon mount to chase unprotected opponent's Horse, Advisor, Elephant and Pawn
- 书中结论：红方必须变着。In the above two examples, Red's Cannon has been attacking Black pieces by means of changing cannon mounts. In the first example, Red would be considered to have perpetually chased the Black Advisor; while in the second example, Red's Cannon would have perpetually chased the Black Elephant. In both examples, Black's moves were considered to be legal. Therefore, in both examples, Red would need to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C4=3（捉）；黑C7=6（捉）；红E1+3（捉）；黑C6=7（捉）；红E3-1（捉）；黑C7=8（捉）；红E5+3（捉）；黑C8=7（捉）；红E3-5（捉）
- 一致性：不一致。

## d059 — 图 59（第 71 页）

- 分类：20 Cannon changing cannon mount to chase unprotected opponent's Horse, Advisor, Elephant and Pawn
- 书中结论：红方必须变着。The Black Pawn under attack was not protected. Red had been using different cannon mounts to chase the Black Pawn, Red would be treated as though he had perpetually chased the Black Pawn, it would be deemed as not allowed. Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红E3+1（捉）；黑C7=9（闲）；红E1+3（捉）；黑C9=6（闲）；红E3-1（捉）；黑C6=9（闲）；红E1+3（捉）；黑C9=6（闲）；红E3-1（捉）
- 一致性：一致。

## d060 — 图 60（第 71 页）

- 分类：20 Cannon changing cannon mount to chase unprotected opponent's Horse, Advisor, Elephant and Pawn
- 书中结论：和棋。In this example, the Black Pawn under attack is unprotected, and yet has not crossed the river.It would be permitted for the Red Cannon to attempt to capture the Black Pawn in the moves mentioned above. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红E3+1（闲）；黑C7=9（闲）；红E1+3（闲）；黑C9=6（闲）；红E3-1（闲）；黑C6=9（闲）；红E1+3（闲）；黑C9=6（闲）；红E3-1（闲）
- 一致性：一致。

## d061 — 图 61（第 72 页）

- 分类：21 Cannon changing cannon mounts to chase opponent's Chariot
- 书中结论：红方必须变着。If a Cannon was using other pieces (friendly or opponent's piece) to act as cannon mounts to chase an enemy Chariot (rooted or unrooted), even though the Chariot was immobile, but the act of changing cannon mounts would still be treated as though Red had been perpetually chasing the opponent's Chariot. It would not be permissible. Therefore, the player with the Cannon would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C2-7（捉）；黑H9+7（捉）；红E5+3（捉）；黑H7+5（捉）；红E3+5（捉）；黑H5-7（捉）；红E5-3（捉）；黑H7-6（捉）；红E3+5（捉）；黑H6+7（捉）
- 一致性：不一致。

## d062 — 图 62（第 72 页）

- 分类：21 Cannon changing cannon mounts to chase opponent's Chariot
- 书中结论：红方必须变着。In the previous two examples, Red has been chasing the Black Chariot by means of changing cannon mounts (advancing and retreating the Advisor, and also advancing and retreating the Elephant). This is not allowed as Red would be deemed as having perpetually chased the Black Chariot. In both examples, Red would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C1-1（捉）；黑C8-1（捉）；红A5-6（捉）；黑C8+1（捉）；红A6+5（捉）；黑C8-1（捉）；红A5-6（捉）；黑C8+1（捉）；红A6+5（捉）
- 一致性：不一致。

## d063 — 图 63（第 73 页）

- 分类：22 Chariot pinned and rendered immobile by Cannon
- 书中结论：和棋。The Black Chariot is pinned to the central file and cannot leave that file without his King being checked. According to the rules mentioned above, when the Black Chariot is placed in the same rank as Red's Cannon on Red's 8th file, such a move would not be considered to be a chase as the Black Chariot cannot leave the central file. Therefore, Black's moves would not constitute a perpetual chase. Red's moves are perfectly legal. Hence, if neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C8+3（捉）；黑R5+1（捉）；红C8+1（捉）；黑R5-1（捉）；红C8-2（捉）；黑R5+2（捉）；红C8+3（捉）；黑R5-3（捉）；红C8-1（捉）；黑R5+1（捉）
- 一致性：一致。

## d064 — 图 64（第 74 页）

- 分类：22 Chariot pinned and rendered immobile by Cannon
- 书中结论：红方必须变着。In the above two examples, the Black Chariot was pinned to the file where it was on. It cannot threaten other opponent's pieces which happened to be on the same rank. The moves by the Black Chariot would be considered legal. Red would be considered to have perpetually chased the Black Chariot which is not allowed. Hence, Red would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R8+4（捉）；黑R5+4（捉）；红R8-4（捉）；黑R5-1（捉）；红R8+1（捉）；黑R5+1（捉）；红R8-1（捉）；黑R5-1（捉）；红R8+1（捉）
- 一致性：不一致。

## d065 — 图 65（第 74 页）

- 分类：22 Chariot pinned and rendered immobile by Cannon
- 书中结论：红方必须变着。In the above two examples, the Black Chariot was pinned to the file where it was on. It cannot threaten other opponent's pieces which happened to be on the same rank. The moves by the Black Chariot would be considered legal. Red would be considered to have perpetually chased the Black Chariot which is not allowed. Hence, Red would have to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2+2（捉）；黑R6+1（捉）；红R2-1（捉）；黑R6+1（捉）；红R2-1（捉）；黑R6-1（捉）；红R2+1（捉）；黑R6+1（捉）；红R2-1（捉）
- 一致性：不一致。

## d066 — 图 66（第 75 页）

- 分类：22 Chariot pinned and rendered immobile by Cannon
- 书中结论：和棋。In this example, when the Black Chariot was being chased, it happened to be protected in every alternate move (when it moved to the seventh file). Hence, the moves by the Red Chariot would not be considered to be a perpetual chase. Instead, it would be permissible. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R3=2（捉）；黑R8=7（闲）；红R2=3（捉）；黑R7=8（闲）；红R3=2（捉）；黑R8=7（闲）；红R2=3（捉）；黑R7=8（闲）
- 一致性：不一致。

## d067 — 图 67（第 75 页）

- 分类：23 King perpetually chasing opponent's material
- 书中结论：和棋。The King is allowed to perpetually chase an opponent's piece. It would be permissible in this position for the Red King to chase the Black Cannon. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红K6=5（捉）；黑C5=6（闲）；红K5=4（捉）；黑C6=5（闲）；红K4=5（捉）；黑C5=6（闲）；红K5=4（捉）
- 一致性：不一致。

## d068 — 图 68（第 76 页）

- 分类：23 King perpetually chasing opponent's material
- 书中结论：和棋。The Red King would be perpetually chasing the Black Pawn, and the Red Horse would aid in chasing the Black Pawn every alternate move. It would be legal for Red to do so. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红K4=5（捉）；黑P5=6（闲）；红K5=4（闲）；黑P6=5（闲）；红K4=5（捉）；黑P5=6（闲）；红K5=4（闲）
- 一致性：一致。

## d069 — 图 69（第 76 页）

- 分类：24 Pawn perpetually chasing opponent's material
- 书中结论：和棋。Pawns are allowed to chase opponent's material perpetually. Therefore, in this position, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红P2=1（闲）；黑C9=8（闲）；红P1=2（闲）；黑C8=9（闲）；红P2=1（闲）；黑C9=8（闲）；红P1=2（闲）
- 一致性：一致。

## d070 — 图 70（第 77 页）

- 分类：24 Pawn perpetually chasing opponent's material
- 书中结论：和棋。In this example, the Red Pawn has been perpetually chasing the Black Horse, with aid from the Red Cannon in one of the moves. Such a move would be permitted. Therefore, it would be a draw if neither player wished to change their rules.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红P2=3（闲）；黑H7-8（闲）；红P3=2（捉）；黑H8+7（闲）；红P2=3（闲）；黑H7-8（闲）；红P3=2（捉）；黑H8+7（闲）；红P2=3（闲）
- 一致性：一致。

## d071 — 图 71（第 77 页）

- 分类：25 King or Pawn combined with other pieces to chase other opponent's pieces for every move
- 书中结论：红方必须变着。In this position, although the Red King was perpetually chasing the Black Pawn, for every move made by the King, one of the Red Horses would also have chased the Red Pawn at the same time. In effect, it would be the Red King and Horse making a combined chase for every move. This situation would be treated as a combined chase and not a perpetual chase by the King. Hence, Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红K6=5（捉）；黑P5=4（闲）；红K5=6（捉）；黑P4=5（闲）；红K6=5（捉）；黑P5=4（闲）；红K5=6（捉）；黑P4=5（闲）
- 一致性：一致。

## d072 — 图 72（第 78 页）

- 分类：25 King or Pawn combined with other pieces to chase other opponent's pieces for every move
- 书中结论：红方必须变着。When the Red Pawn was chasing the Black cannon, the Red Horses would also be chasing the Black Cannon for every move. Hence, it would be a combined chase by the Red Pawn and Horse for every move, and it would not be allowed. Therefore, Red would have to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红P7=8（捉）；黑C2=3（闲）；红P8=7（捉）；黑C3=2（闲）；红P7=8（捉）；黑C2=3（闲）；红P8=7（捉）；黑C3=2（闲）
- 一致性：一致。

## d073 — 图 73（第 78 页）

- 分类：25 King or Pawn combined with other pieces to chase other opponent's pieces for every move
- 书中结论：红方必须变着。While the Red Pawn was 'perpetually chasing' the Black Chariot, it would also act as a cannon mount such that one of the Red Cannons would also be chasing the Black Chariot. Therefore, the moves by the Red Pawn would be treated as a combined chase instead of a perpetual chase by the Pawn. It would not be allowed. Hence, Red would need to change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红P9=8（捉）；黑R2=1（捉）；红P8=9（捉）；黑R1=2（捉）；红P9=8（捉）；黑R2=1（捉）；红P8=9（捉）；黑R1=2（捉）
- 一致性：一致。

## d074 — 图 74（第 79 页）

- 分类：26 Chariot perpetually chasing opponent's Pawn which has crossed the river
- 书中结论：红方必须变着。In this position, Red cannot make the excuse of wanting to protect his Horse while at the same time perpetually chasing the unprotected Black Pawn which has crossed the river. Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4=5（捉）；黑P5=6（捉）；红R5=4（捉）；黑P6=5（捉）；红R4=5（捉）；黑P5=4（捉）；红R5=6（捉）；黑P4=5（捉）；红R6=5（捉）
- 一致性：不一致。

## d075 — 图 75（第 80 页）

- 分类：26 Chariot perpetually chasing opponent's Pawn which has crossed the river
- 书中结论：红方必须变着。Black's Pawn would have been perpetually chasing the Red Cannons for every move. It would be treated as a perpetual chase by the Pawn, it is allowed. On the other hand, Red's Chariot has been perpetually chasing the Black Pawn which has crossed the river. It would not be allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R6=5（捉）；黑P5=4（闲）；红R5=6（捉）；黑P4=5（闲）；红R6=5（捉）；黑P5=4（闲）；红R5=6（捉）；黑P4=5（闲）
- 一致性：一致。

## d076 — 图 76（第 80 页）

- 分类：27 Single piece chasing two or more opponent's pieces
- 书中结论：和棋。A single piece is allowed to chase after two or more opponent's pieces perpetually. If there were two pieces which perpetually chased after two or more opponent's pieces, it would still be allowed. If neither player wished to change their moves, it would be a draw.
- 当前判断：未形成可裁决重复。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：给出的着法及其可证明的末段循环未达到当前裁决阈值。
- 回放标签：红R8=7（捉）；黑H3+2（捉）；红R7=8（捉）；黑H2-3（捉）；红R8=2（捉）；黑C8=9（捉）；红R2=7（捉）；黑H3+2（捉）；红R7=8（捉）；黑H2-3（捉）；红R8=1（捉）
- 一致性：不一致。

## d077 — 图 77（第 81 页）

- 分类：27 Single piece chasing two or more opponent's pieces
- 书中结论：和棋。For the above three examples, the Red Chariot has been perpetually chasing two or more opponent's pieces in the same cycle, it is allowed. If neither player wished to change their moves, it would be a draw.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红R1=2（捉）；黑P8=7（捉）；红R2=8（捉）；黑P2=3（捉）；红R8=3（捉）；黑P7=8（捉）；红R3=7（捉）；黑P3=2（捉）；红R7=2（捉）；黑P8=7（捉）；红R2=8（捉）；黑P2=3（捉）；红R8=3（捉）；黑P7=8（捉）
- 一致性：不一致。

## d078 — 图 78（第 81 页）

- 分类：27 Single piece chasing two or more opponent's pieces
- 书中结论：和棋。For the above three examples, the Red Chariot has been perpetually chasing two or more opponent's pieces in the same cycle, it is allowed. If neither player wished to change their moves, it would be a draw.
- 当前判断：黑方必须变着。
- 当前责任方：黑方。
- 判定原因：第 3 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为长捉；黑方的行为等级更高，因此须变着。
- 回放标签：红R2=7（捉）；黑H3+1（捉）；红R7=5（捉）；黑C5=6（捉）；红R5=4（捉）；黑C6=5（捉）；红R4=3（捉）；黑+P=8（捉）；红R3=9（捉）；黑H1-3（捉）；红R9=7（捉）；黑H3+1（捉）；红R7=5（捉）；黑C5=6（捉）；红R5=4（捉）；黑C6=5（捉）；红R4=2（捉）；黑P8=7（捉）；红R2=9（捉）；黑H1-3（捉）；红R9=7（捉）；黑H3+1（捉）；红R7=5（捉）
- 一致性：不一致。

## d079 — 图 79（第 82 页）

- 分类：27 Single piece chasing two or more opponent's pieces
- 书中结论：黑方必须变着。In this position, the Red Cannon has been chasing two different Black Pawns in alternate moves, it would be allowed. Black, on the other hand, has been perpetually chasing the Red Cannon, which is unprotected, it would not be permitted. Therefore, Black must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C7+1（捉）；黑R4-2（捉）；红C7-2（捉）；黑R4+2（捉）；红C7+2（捉）；黑R4-2（捉）；红C7-2（捉）；黑R4+2（捉）；红C7+2（捉）
- 一致性：不一致。

## d080 — 图 80（第 82 页）

- 分类：27 Single piece chasing two or more opponent's pieces
- 书中结论：和棋。In this position, both the Red Chariots have been chasing the opponent's Cannons alternately. It would be legal. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R1=2（捉）；黑C8=9（捉）；红R8=9（捉）；黑C1=2（捉）；红R2=1（捉）；黑C9=8（捉）；红R9=8（捉）；黑C2=1（捉）
- 一致性：一致。

## d081 — 图 81（第 83 页）

- 分类：28 Two or more pieces chasing same opponent's piece
- 书中结论：红方必须变着。In the above two examples, Red would have used two of his pieces to chase the same opponent's piece. It would amount to a two-to-one perpetual chase, which is not allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2+1（捉）；黑C9-2（捉）；红R3+1（捉）；黑C9+1（捉）；红R2+1（捉）；黑C9+1（捉）；红R3-2（捉）；黑C9-2（捉）；红R2+1（捉）；黑C9+1（捉）；红R3+1（捉）；黑C9+1（捉）；红R2-2（捉）；黑C9-2（捉）；红R3+1（捉）
- 一致性：不一致。

## d082 — 图 82（第 83 页）

- 分类：28 Two or more pieces chasing same opponent's piece
- 书中结论：红方必须变着。In the above two examples, Red would have used two of his pieces to chase the same opponent's piece. It would amount to a two-to-one perpetual chase, which is not allowed. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红H7-5（捉）；黑P5=4（闲）；红H5+7（捉）；黑P4=5（闲）；红H7-5（捉）；黑P5=4（闲）；红H5+7（捉）；黑P4=5（闲）
- 一致性：一致。

## d083 — 图 83（第 84 页）

- 分类：29 Perpetually chasing opponent's piece with a fake root
- 书中结论：红方必须变着。In this example, the Black Cannon on the riverbank would seem to be protected by the Black Elephant. However, the Black Elephant would in effect be a fake root as it cannot move or the Black King would be placed in check by the Red Cannon. Therefore, the Red Chariot would have been seen to have perpetually chased the Black Cannon. Black's moves would be allowed. Hence, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R6=3（捉）；黑C7=3（闲）；红R3=7（捉）；黑C3=7（闲）；红R7=3（捉）；黑C7=3（闲）；红R3=7（捉）；黑C3=7（闲）；红R7=3（捉）
- 一致性：一致。

## d084 — 图 84（第 84 页）

- 分类：29 Perpetually chasing opponent's piece with a fake root
- 书中结论：红方必须变着。In the above two examples, the Red Chariot is seen as having perpetually chased an opponent's piece with a fake root. Black's moves were legal in both examples. Therefore, Red must change his moves in both examples or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R2=3（捉）；黑C7=8（闲）；红R3=2（捉）；黑C8=7（闲）；红R2=3（捉）；黑C7=8（闲）；红R3=2（捉）；黑C8=7（闲）
- 一致性：一致。

## d085 — 图 85（第 85 页）

- 分类：29 Perpetually chasing opponent's piece with a fake root
- 书中结论：红方必须变着。In the above two examples, the Red Chariot is seen as having perpetually chased an opponent's piece with a fake root. Black's moves were legal in both examples. Therefore, Red must change his moves in both examples or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R3-1（捉）；黑C6-2（捉）；红R3+2（捉）；黑C6+2（捉）；红R3-2（捉）；黑C6+2（捉）；红R3-2（捉）；黑C6-2（捉）；红R3+2（捉）
- 一致性：不一致。

## d086 — 图 86（第 85 页）

- 分类：30 Two or more pieces perpetually chasing opponent's piece with a real root
- 书中结论：和棋。When a protected piece with a real root was being chased by two or more opponent's pieces, it would be a draw if neither player wished to change their moves. The opponent's pieces dealing the chase are not considered to have perpetually chased the friendly piece.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2+2（捉）；黑C9+2（捉）；红R2-2（捉）；黑C9+1（捉）；红R2-1（捉）；黑C9-1（捉）；红R2+1（捉）；黑C9-2（捉）；红R2+2（捉）
- 一致性：一致。

## d087 — 图 87（第 86 页）

- 分类：30 Two or more pieces perpetually chasing opponent's piece with a real root
- 书中结论：和棋。In the previous two examples, both Red Chariots had been chasing a protected Black Cannon with a real root. It is permissible. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R7-1（捉）；黑C5-1（捉）；红R7+1（捉）；黑C5+1（捉）；红R7-1（捉）；黑C5-1（捉）；红R7+1（捉）；黑C5+1（捉）；红R7-1（捉）
- 一致性：一致。

## d088 — 图 88（第 86 页）

- 分类：30 Two or more pieces perpetually chasing opponent's piece with a real root
- 书中结论：和棋。Both the Red Chariots and the Red Cannon would have been chasing the Black Cannon, which was protected with real roots. It is permitted. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4+3（捉）；黑+C+1（捉）；红R4-1（捉）；黑+C+1（捉）；红R4-1（捉）；黑C9-2（捉）；红R4+2（捉）；黑+C+1（捉）；红R4-1（捉）
- 一致性：一致。

## d089 — 图 89（第 87 页）

- 分类：30 Two or more pieces perpetually chasing opponent's piece with a real root
- 书中结论：和棋。Red's Chariot and Cannons have been chasing the Black Horse, which happened to be protected by the Black Cannons. As the Black Horse is protected, Red's moves is permissible. Therefore, it would be a draw, if neither player wished to change their moves.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C6=7（捉）；黑H3-1（闲）；红R7=9（捉）；黑H1+3（捉）；红R9=7（捉）；黑H3-1（闲）；红R7=9（捉）；黑H1+3（捉）；红R9=7（捉）
- 一致性：不一致。

## d090 — 图 90（第 87 页）

- 分类：31 Perpetual chase with perpetual exchange
- 书中结论：红方必须变着。In this example, Red's R9=8 could be interpreted as both a chase or exchange (invitation). According to the rules, such a move would be treated as a chase instead of an exchange. Red would be viewed as having perpetually chased the Black Cannon with his Chariot. A perpetual chase would not be permissible. Hence, Red would need to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R2=9（捉）；黑C1=2（捉）；红R9=8（捉）；黑C2=1（捉）；红R8=9（捉）；黑C1=2（捉）；红R9=8（捉）；黑C2=1（捉）；红R8=9（捉）
- 一致性：不一致。

## d091 — 图 91（第 88 页）

- 分类：31 Perpetual chase with perpetual exchange
- 书中结论：红方必须变着。In this example, Red has perpetually chased the Black Cannon and also perpetually offered an exchange. It would be considered that Red would have been perpetually chasing material when passing judgment, and it would not be permitted to do so. Black's moves would be legal. Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R8=9（捉）；黑C1=2（捉）；红R9=8（捉）；黑C2=1（捉）；红R8=9（捉）；黑C1=2（捉）；红R9=8（捉）；黑C2=1（捉）；红R8=9（捉）
- 一致性：不一致。

## d092 — 图 92（第 88 页）

- 分类：31 Perpetual chase with perpetual exchange
- 书中结论：红方必须变着。In the above two examples, although the Red Chariot had perpetually invited the Black Chariot to exchange Chariots, Red's moves could also be interpreted as chasing the Black Chariot as there were other pieces present that also threatened to capture the Black Chariot. Red's moves would be treated as though a perpetual chase had been performed, instead of a perpetual invitation to exchange material. Red's moves would not be allowed. Black's moves are entirely permitted. Therefore, Red would need to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R5=6（捉）；黑R4=5（捉）；红R6=5（捉）；黑R5=4（捉）；红R5=6（捉）；黑R4=5（捉）；红R6=5（捉）；黑R5=4（捉）；红R5=6（捉）
- 一致性：不一致。

## d093 — 图 93（第 89 页）

- 分类：31 Perpetual chase with perpetual exchange
- 书中结论：红方必须变着。In the above two examples, although the Red Chariot had perpetually invited the Black Chariot to exchange Chariots, Red's moves could also be interpreted as chasing the Black Chariot as there were other pieces present that also threatened to capture the Black Chariot. Red's moves would be treated as though a perpetual chase had been performed, instead of a perpetual invitation to exchange material. Red's moves would not be allowed. Black's moves are entirely permitted. Therefore, Red would need to change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R7=8（捉）；黑R2=3（捉）；红R8=7（捉）；黑R3=2（捉）；红R7=8（捉）；黑R2=3（捉）；红R8=7（捉）；黑R3=2（捉）；红R7=8（捉）
- 一致性：不一致。

## d094 — 图 94（第 90 页）

- 分类：32 The case of Chariot-Cannon combination pinning opponent's King and Chariot
- 书中结论：红方必须变着。In the above two examples, Red has attempted to perpetually chase the Black Chariot by advancing and retreating his Horse. It is not allowed. Black's moves are legal. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红H4-2（捉）；黑R6=7（捉）；红H2+4（捉）；黑R7=6（捉）；红H4-2（捉）；黑R6=7（捉）；红H2+4（捉）；黑R7=6（捉）；红H4-2（捉）
- 一致性：不一致。

## d095 — 图 95（第 90 页）

- 分类：32 The case of Chariot-Cannon combination pinning opponent's King and Chariot
- 书中结论：红方必须变着。In the above two examples, Red has attempted to perpetually chase the Black Chariot by advancing and retreating his Horse. It is not allowed. Black's moves are legal. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红H4-2（捉）；黑R8=7（捉）；红H2+4（捉）；黑R7=8（捉）；红H4+2（捉）；黑R8=7（捉）；红H2-1（捉）；黑R7=8（捉）；红H1+2（捉）
- 一致性：不一致。

## d096 — 图 96（第 91 页）

- 分类：32 The case of Chariot-Cannon combination pinning opponent's King and Chariot
- 书中结论：红方必须变着。In this example, Red's Cannon has been perpetually chasing the Black Chariot. Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红C9-6（捉）；黑R6-1（捉）；红C9+1（捉）；黑R6-1（捉）；红C9+1（捉）；黑R6+2（捉）；红C9-2（捉）；黑R6-1（捉）；红C9+1（捉）
- 一致性：不一致。

## d097 — 图 97（第 91 页）

- 分类：33 A perpetual threat to capture material after check is allowed
- 书中结论：和棋。A perpetual threat to capture material after check is allowed. If the opponent did not make any illegal moves, it would be a draw if neither player wished to change their moves.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红C9-1（捉）；黑K6-1（闲）；红C9+1（捉）；黑K6+1（闲）；红C9-1（捉）；黑K6-1（闲）；红C9+1（捉）
- 一致性：不一致。

## d098 — 图 98（第 92 页）

- 分类：33 A perpetual threat to capture material after check is allowed
- 书中结论：和棋。In the above two examples, Red has tried to set up an attack whereby he would threaten to capture material after delivering a check. It would be allowed. Black's moves are also allowed. Therefore, if neither player wished to change their moves, it would be a draw.
- 当前判断：未形成可裁决重复。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：给出的着法及其可证明的末段循环未达到当前裁决阈值。
- 回放标签：红R1=2（闲）；黑C9=8（捉）；红R2=3（闲）；黑C8=7（捉）；红R3=1（闲）；黑C7=9（捉）；红R1=2（闲）；黑C9=8（捉）；红R2=1（闲）
- 一致性：不一致。

## d099 — 图 99（第 92 页）

- 分类：34 Perpetual block
- 书中结论：和棋。In this position, Black has been perpetually threatening Red with a mating threat. Red, on the other hand, has responded with a perpetual block. Perpetual mating threats and perpetual blocks are both allowed. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红C2=1（闲）；黑C9=8（闲）；红C1=2（闲）；黑C8=9（闲）；红C2=1（闲）；黑C9=8（闲）；红C1=2（闲）；黑C8=9（闲）；红C2=1（闲）
- 一致性：一致。

## d100 — 图 100（第 93 页）

- 分类：34 Perpetual block
- 书中结论：和棋。In this example, neither player had gone against the rules. Therefore, the verdict for this situation would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R2=4（闲）；黑C8=6（闲）；红R4=1（闲）；黑C6=9（闲）；红R1=8（闲）；黑C1=2（闲）；红R8=3（捉）；黑C9=7（闲）；红R3=4（闲）；黑C7=6（闲）；红R4=1（闲）；黑C6=9（闲）；红R1=2（闲）；黑C2=1（闲）；红R2=4（闲）；黑C9=6（闲）
- 一致性：一致。

## d101 — 图 101（第 93 页）

- 分类：35 Perpetual exchange, perpetual offer
- 书中结论：和棋。In this position, Red has perpetually invited Black to exchange material which would be allowed. The Black Chariot is not pinned or limited in its movement. Therefore, if neither player wished to change their moves, it would be considered to be a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红+R+1（捉）；黑R1+3（闲）；红R8-3（捉）；黑R1-2（闲）；红R8+2（捉）；黑R1-3（闲）；红R8+3（捉）；黑R1+2（闲）；红R8-2（捉）
- 一致性：不一致。

## d102 — 图 102（第 94 页）

- 分类：35 Perpetual exchange, perpetual offer
- 书中结论：和棋。In the above two examples, neither player has violated the rules. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为闲着／非连续有效追捉、黑方为闲着／非连续有效追捉；双方等级相同，按当前规则判和。
- 回放标签：红R7=3（闲）；黑R6=7（捉）；红R3=2（闲）；黑R7=8（捉）；红R2=4（将）；黑R8=6（捉）；红R4=1（闲）；黑R6=9（捉）；红R1=7（闲）；黑R9=6（闲）
- 一致性：一致。

## d103 — 图 103（第 94 页）

- 分类：35 Perpetual exchange, perpetual offer
- 书中结论：和棋。In the above two examples, neither player has violated the rules. Therefore, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R8-3（捉）；黑R4-1（捉）；红R8+1（捉）；黑R4-2（捉）；红R8+2（捉）；黑R4+3（捉）；红R8-3（捉）
- 一致性：一致。

## d104 — 图 104（第 95 页）

- 分类：35 Perpetual exchange, perpetual offer
- 书中结论：和棋。The Black Chariot has been perpetually threatening with a mating threat. This is allowed. Red, on the other hand, has been perpetually making an offer of material with his Pawn. It is also allowed. Since neither player has gone against the rules, it would be a draw if neither player wished to change their moves.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红P7=8（捉）；黑R2=3（闲）；红P8=7（捉）；黑R3=2（闲）；红P7=8（捉）；黑R2=3（闲）；红P8=7（捉）；黑R3=2（闲）
- 一致性：不一致。

## d105 — 图 105（第 95 页）

- 分类：36.1 Example of perpetual chase
- 书中结论：红方必须变着。In this example, Red has tried to move his Pawn to prevent Black's Cannon from protecting the Black Horse as the Black Cannon would now lost its cannon mount. When Black tried to use his Elephant as a cannon mount, Red would move the Pawn back to the same file to block the Cannon again. In this case, the Red Chariot is viewed as having perpetually chased the Black Horse.
Black's moves are legal. Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红P7=6（捉）；黑E1+3（捉）；红P6=7（捉）；黑E3-1（捉）；红P7=8（捉）；黑E5+3（捉）；红P8=7（捉）；黑E3-5（捉）；红P7=6（捉）；黑E1+3（捉）
- 一致性：不一致。

## d106 — 图 106（第 96 页）

- 分类：36.2 Example of non-perpetual chase
- 书中结论：和棋。In this example, advancing and retreating the Red Chariot would seem to be a perpetual chase by Red targeted at the Black Cannon. However, the Black Cannon does not run away, and there are no other Black pieces to protect it.
Red's moves would not be considered to be a perpetual chase on the Black Cannon.
Hence, if neither player wished to change their moves, it would be a draw.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红R2+1（捉）；黑C8+1（闲）；红R2-1（捉）；黑C8-1（闲）；红R2+1（捉）；黑C8+1（闲）；红R2-1（捉）；黑C8-1（闲）
- 一致性：不一致。

## d107 — 图 107（第 96 页）

- 分类：36.2 Example of non-perpetual chase
- 书中结论：和棋。In this example, advancing the Red Horse to the riverbank would be viewed as a chase by the Red Horse targeting at the Black Chariot. Black's R3+2 could both be described as a chase (targeting at the Red Horse) and also an offer (inviting the Red Elephant to capture it). When a move has more than one nature, it would be treated as the one with more substantial consequences. Hence, Black's moves would be considered to be an alternate chase and idle and judgment would be passed based on this assumption. Red's H6-7 for his second ply would be considered to be an idle move. As for the Red Elephant threatening to capture the Black Chariot, it would be considered to be Black's responsibility as Black had deliberately moved the Chariot there. Hence, Red's moves would be treated as an alternate chase and idle. Since both players were considered to have played an alternate chase and idle, it would be a draw if neither player wished to change their moves.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红H7+6（捉）；黑R3+2（捉）；红H6-7（捉）；黑R3-2（捉）
- 一致性：一致。

## d108 — 图 108（第 97 页）

- 分类：36.3 Example of simultaneous perpetual chase
- 书中结论：和棋。When Red retreated his Chariot on the 4th file, his other Chariot would be chasing the Black Cannon on the 9th file (Black's first file). When the Red Chariot was advanced again, the Black Cannon on Black's first file was still under attack. Hence, since the same Black Cannon was under attack all the time, Red's moves would be considered to be a two-to-one chase, and it would be not allowed.
A similar situation would occur for Black. Whenever the Black Advisor was advanced or retreated, Red's unmoved Chariot on Red's 6th file would be under constant attack. Hence, Black's moves would be deemed as a two-to-one chase on the Red Chariot which has not moved. It would be not allowed.
In this instance, since both players have violated the rules with a perpetual chase at the same time, if neither player wished to change their moves, it would be a draw.
- 当前判断：和棋。
- 当前责任方：无（双方同级或未达到裁决）。
- 判定原因：第 4 次同局面时，循环中红方为长捉、黑方为长捉；双方等级相同，按当前规则判和。
- 回放标签：红R4-2（捉）；黑A4+5（捉）；红R4+2（捉）；黑A5-4（捉）；红R4-2（捉）；黑A4+5（捉）；红R4+2（捉）；黑A5-4（捉）
- 一致性：一致。

## d109 — 图 109（第 98 页）

- 分类：36.4 Perpetual mating threat and perpetual chase
- 书中结论：红方必须变着。Advancing and retreating the Red Horse were mating threats. The same moves could also be treated as a chase targeting at the Black Elephant on bottom rank. There are two natures to Red's moves, and when it is so, the moves by Red would be treated as the nature with more substantial consequences. Hence, the moves by Red would be treated as a chase instead of a mating threat, and Red would be seen as having played a perpetual chase. It is not allowed.
Both of Black's moves were idle moves and are perfectly legal.
Therefore, Red must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为长捉、黑方为闲着／非连续有效追捉；红方的行为等级更高，因此须变着。
- 回放标签：红H3+2（捉）；黑E7-5（闲）；红H2-3（捉）；黑E5+7（闲）；红H3+2（捉）；黑E7-5（闲）
- 一致性：一致。

## d110 — 图 110（第 98 页）

- 分类：36.5 Example of a chase on the opponent's Chariot
- 书中结论：黑方必须变着。Analysis of Red's moves:
a) R3-1: would be a chase on the Black Horse. The Red Cannon would also be chasing the Black Chariot at the Elephant's eye.
b) R3+1: Advancing the Red Chariot would prevent the Chariot from being caught by the Black Horse. The Red Cannon would still be chasing the Black Chariot. However, in this situation, Red would have been considered to have made an alternate chase and idle. Although the Red Cannon was targeting at the Black Chariot, it would not be taken into consideration in this cycle.
Analysis of Black's moves:
Advancing and retreating the Horse was a perpetual chase targeting at the Red Chariot.
Therefore Red's alternate chase and idle was allowed while Black's perpetual chase was not allowed. Black must change his moves or be penalized with a loss.
- 当前判断：红方必须变着。
- 当前责任方：红方。
- 判定原因：第 3 次同局面时，循环中红方为捉被卧槽马牵制的车、黑方为长捉；红方的行为等级更高，因此须变着。
- 回放标签：红R3-1（捉卧槽牵制车）；黑H5+6（捉）；红R3+1（捉卧槽牵制车）；黑H6-5（捉）；红R3-1（捉卧槽牵制车）；黑H5+6（捉）
- 一致性：不一致。
