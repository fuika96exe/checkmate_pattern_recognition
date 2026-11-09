"""Stable tactic and checkmate-pattern IDs and their zh-TW display names.

Results refer to these IDs only, and an ID never changes once published.  The
names are the lab's and are not translated here: the midgame table is the one
the classifier uses, the checkmate tables follow
``docs/checkmate-recognition-logic.zh-TW.md``.  Another language gets its own
tables beside these.

The order of ``MIDGAME_LABELS_ZH_TW`` is the order ``tactics`` lists labels in.
"""

MIDGAME_LABELS_ZH_TW = {
    'fork': '捉雙',
    'discovered_attack': '閃擊',
    'skewer': '串打',
    'pin': '牽制',
    'check_fork': '抽將',
    'trap': '圍困',
    'remove_defender': '消除保護',
    'overload': '過載',
    'exchange': '交換',
    'clearance': '消除阻隔',
}

CHECKMATE_PATTERNS_ZH_TW = {
    'CROWNED_CHECKMATE': '平頂冠',
    'CENTROID_CHECKMATE': '花心殺',
    'CANNONS_SANDWICHING_CHARIOT_CHECKMATE': '夾車炮',
    'DOUBLE_CANNON_CHECKMATE': '重炮殺',
    'SMOTHERED_CANNON_CHECKMATE': '悶宮殺',
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE': '天地炮',
    'IRON_BOLT_CHECKMATE': '鐵門栓',
    'DRAWER_CHECKMATE': '進洞出洞',
    'THROAT_CUTTING_CHECKMATE': '大膽穿心',
    'THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE': '三車鬧士',
    'TWO_DEVILS_KNOCKING_CHECKMATE': '雙鬼拍門',
    'DOUBLE_CHARIOTS_CHECKMATE': '雙車錯',
    'DISCOVERED_HORSE_CHECKMATE': '拔簧馬',
    'TIGER_SILHOUETTE_CHECKMATE': '側面虎',
    'HORSE_CANNON_CHECKMATE': '馬後炮',
    'ELBOW_HORSE_CHECKMATE': '臥槽馬',
    'PALCORNER_HORSE_CHECKMATE': '掛角馬',
    'OCTAGON_HORSE_CHECKMATE': '八角馬',
    'ANGLER_HORSE_CHECKMATE': '釣魚馬',
    'SMOTHERED_CHECKMATE': '悶殺',
    'DOUBLE_CHECK_CHECKMATE': '雙將',
    'WHITE_FACE_GENERAL': '白臉將',
    'STALEMATE': '困斃',
}

# The material fallback: R, N, C and P are the pieces that deliver the mate.
MATING_MATERIAL_ZH_TW = {
    'R': '車殺',
    'N': '馬殺',
    'C': '炮殺',
    'P': '兵殺',
    'RN': '車馬',
    'RC': '車炮',
    'RP': '車兵',
    'RNC': '車馬炮',
    'RNP': '車馬兵',
    'RCP': '車炮兵',
    'NC': '馬炮',
    'NCP': '馬炮兵',
    'NP': '馬兵',
    'CP': '炮兵',
}
