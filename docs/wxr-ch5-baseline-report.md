# WXR 2018 Chapter 5 baseline report

Source corpus: `C:/Users/user/Downloads/wxr-test-viewer-main/wxr-test-viewer-main/ch5_cases.json`.

This is a baseline for the current repetition implementation, not a claim of
complete WXF adjudication. The replayer converts the corpus's ranks 1--10 to
the application's UCCI ranks 0--9 and repeats the final proven cycle until a
third- or fourth-occurrence decision is reached.

## Result

- 110 cases total
- 46 matched
- 64 did not match

## 第 1–30 例逐条中文检查表

说明：`红方变着` / `黑方变着` 表示该方应停止继续该循环；`和棋`表示双方没有唯一责任方。当前版本先找“同一棋盘 + 同一方走”的重复局面，再把每方着法粗略分成：全程将军、持续攻击同一枚棋子、或其他。这里的“攻击”仍只是基础攻击格，尚未实现完整 WXF 的保护、牵制、兑子和杀势例外。

| 例 | 是否匹配 | 预期 → 当前 | 原因／当前逻辑 |
|---|---|---|---|
| d001 | 是 | 红方变着 → 红方变着 | 红方重复段内每手都将军，黑方没有同等级行为；将军优先，红方是唯一责任方。 |
| d002 | 是 | 红方变着 → 红方变着 | 同 d001；即使是多枚棋子轮流将军，只要红方每个相关回合都将军，仍判长将。 |
| d003 | 是 | 红方变着 → 红方变着 | 红方相关着法持续将军，循环局面被识别，因此第三次出现时正确锁定红方。 |
| d004 | 是 | 和棋 → 和棋 | 双方都构成长将，严重度相同；没有唯一责任方，所以进入和棋流程。 |
| d005 | 是 | 红方变着 → 红方变着 | 红方全程将军；黑方不是全程将军，红方级别较高。 |
| d006 | 是 | 和棋 → 和棋 | 更新后的局面中，双方都被基础攻击逻辑归为同级；没有唯一责任方，因此结果为和棋。 |
| d007 | 否 | 和棋 → 红方变着 | 同 d006：杀势被基础攻击格逻辑误提升为长捉。 |
| d008 | 否 | 和棋 → 红方变着 | 当前没有“炮的杀势／封锁”例外，看到持续攻击目标便错误判红方有责任。 |
| d009 | 是 | 和棋 → 和棋 | 当前循环中没有形成唯一较高的将军或同一目标长捉，双方同级，结果恰好正确。 |
| d010 | 否 | 和棋 → 黑方变着 | 双方是在化解并反制杀势；当前代码把黑方持续攻击误认成了持续捉同一子。 |
| d011 | 否 | 和棋 → 黑方变着 | 黑方的动作应是“交替将军与杀势”，应降为 Idle；当前基础攻击判断仍将其错误提升。 |
| d012 | 否 | 和棋 → 黑方变着 | 章节本身是“交替将军和长捉”；正确规则应判混合行为 Idle，当前代码对黑方的攻击集合过于宽松。 |
| d013 | 是 | 和棋 → 和棋 | 红方并非每手都将军，也没有稳定同一被捉子；当前归为无唯一责任方，结果正确。 |
| d014 | 是 | 和棋 → 和棋 | 将军后的吃子威胁不应自动算长捉；该例当前没有产生唯一较高方，结果正确。 |
| d015 | 否 | 和棋 → 黑方变着 | 应是“交替长捉与闲着”；当前代码只要攻击目标有交集就把黑方误判成长捉。 |
| d016 | 否 | 和棋 → 黑方变着 | 应是“将军后威胁吃子”的例外；当前没有这项降级规则。 |
| d017 | 否 | 和棋 → 黑方变着 | 同类问题：应区分普通攻击和 WXF 认可的有效长捉，当前未区分。 |
| d018 | 否 | 红方变着 → 和棋 | 语料认定红炮持续捉黑车；当前只做攻击格交集，未正确表达炮架／保护关系，最后把双方判为同级。 |
| d019 | 否 | 红方变着 → 和棋 | 同 d018：缺少“有效炮捉车”的 WXF 条件，未能让红方成为唯一责任方。 |
| d020 | 是 | 红方变着 → 红方变着 | 当前能在每个红方相关回合找到同一黑车实体 ID，且黑方没有更高或同级的持续行为。 |
| d021 | 是 | 红方变着 → 红方变着 | 红方通过改变炮架持续针对同一黑车；基础身份交集在该例恰好足够识别。 |
| d022 | 否 | 红方变着 → 和棋 | 应识别红方炮的持续捉车；目前的攻击格方法没有涵盖这个炮架/保护组合。 |
| d023 | 否 | 红方变着 → 和棋 | 同 d022：真实规则有有效长捉，当前简化规则没有把红方单独升为 Chase。 |
| d024 | 否 | 红方变着 → 和棋 | 同 d022，基础攻击判定遗漏了该循环中的有效捉车关系。 |
| d025 | 否 | 红方变着 → 和棋 | 同 d022，缺少炮架变化和被捉车保护状态的判断。 |
| d026 | 否 | 和棋 → 黑方变着 | 一个炮轮流针对两辆车不应形成“同一被捉子”的长捉；当前对黑方的攻击归集出现误判。 |
| d027 | 否 | 和棋 → 红方变着 | 同 d026：交替捉不同目标应是 Idle，当前基础攻击集合仍保留了错误的共同目标。 |
| d028 | 否 | 和棋 → 红方变着 | 同 d026，缺少“每一手必须捉同一实体棋子”的更严格有效捉子筛选。 |
| d029 | 是 | 和棋 → 和棋 | 受保护炮的循环中当前没有形成唯一更严重方；虽尚未完整理解保护规则，最终裁决恰好正确。 |
| d030 | 是 | 和棋 → 和棋 | 同 d029：当前结果是双方同级/无唯一责任方，符合语料的和棋结果。 |

第 31–110 例仍保留在下方的分组清单中；确认这张表的格式合适后，再以完全相同格式继续展开。

## Matched cases

### Correct offender / must-change result (21)

`d001 d002 d003 d005 d020 d021 d032 d034 d036 d037 d046 d050 d053 d055 d056 d057 d059 d071 d073 d082 d084`

Why these match: the repeated-position detection finds the same board and
side to move; the relevant player is classified above the opponent by the
current baseline (all checks, or a common attacked piece identity across the
cycle), so the third occurrence identifies that player as the sole offender.

### Correct draw result (24)

`d004 d006 d009 d013 d014 d029 d030 d031 d048 d051 d054 d063 d066 d068 d080 d086 d087 d088 d089 d099 d100 d102 d103 d107 d108`

Why these match: the repeated position reaches the configured threshold and
the two sides are equal under the baseline classification, or neither side is
classified as a sole more-serious offender. The fourth occurrence therefore
draws.

## Unmatched cases

### False positive: expected draw, baseline prohibited Red (13)

`d007 d008 d027 d028 d060 d067 d069 d070 d097 d101 d104 d106`

Why: the baseline equates an attack on an opposing non-general piece with a
qualifying chase. These examples include legal mating threats, blocks,
exchange offers, or other WXF exceptions which must be downgraded to Idle.

### False positive: expected draw, baseline prohibited Black (9)

`d010 d011 d012 d015 d016 d017 d026 d077 d078`

Why: same underlying issue as above, but Black is the side whose ordinary
attack was incorrectly promoted to a perpetual chase.

### False negative: expected Red must change, baseline drew (35)

`d018 d019 d022 d023 d024 d025 d033 d035 d038 d039 d040 d041 d045 d047 d049 d058 d061 d062 d064 d065 d072 d074 d075 d081 d083 d085 d090 d091 d092 d093 d094 d095 d096 d105 d109`

Why: the current attack-only test misses WXF-qualified chases that depend on
protection/root status, cannon mounts, pins, multi-piece pressure, or the
victim's response. It therefore rates both players equal and reaches a draw.

### False negative: expected Black must change, baseline drew (5)

`d042 d043 d044 d079 d110`

Why: same missed-qualifying-chase problem as the Red group, with Black as the
expected offender.

### No repeat decision reached automatically (3)

`d052 d076 d098`

Why: the supplied line does not end with a two-occurrence cycle from which
the replayer can safely infer an extension. These need a manually approved
continuation before they can be used as threshold tests.

## Next implementation target

Replace the baseline `chased_piece_ids()` attack scan with an explicit
`is_qualifying_chase()` rule. Start by reviewing one group at a time against
the corpus: legal-threat false positives first, then protected/rooted and
pin/cannon-mount false negatives. Do not change the position-cycle or
third/fourth occurrence machinery while resolving those rule details.
