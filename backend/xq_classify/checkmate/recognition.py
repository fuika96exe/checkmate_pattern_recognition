"""Checkmate pattern recognition: the dispatcher and ``analyze_patterns``.

Each pattern's recogniser lives in ``checkmate/patterns/``.
"""
from __future__ import annotations

from ..board import parse_fen, position_analysis
from ..version import CHECKMATE_RULES_VERSION  # noqa: F401 - re-exported
from .geometry import apply_moves
from .material import classify_mating_material
from .patterns.cannon import (
    recognize_cannons_sandwiching_chariot_checkmate,
    recognize_double_cannon_checkmate,
    recognize_heaven_and_earth_cannon_checkmate,
    recognize_horse_cannon_checkmate,
    recognize_smothered_cannon_checkmate,
)
from .patterns.chariot import (
    recognize_double_chariots_checkmate,
    recognize_drawer_checkmate,
    recognize_iron_bolt_checkmate,
    recognize_three_chariots_attacking_advisor_checkmate,
    recognize_throat_cutting_checkmate,
    recognize_two_devils_knocking_checkmate,
)
from .patterns.general import (
    recognize_centroid_chariot_checkmate,
    recognize_crowned_checkmate,
    recognize_double_check_checkmate,
    recognize_smothered_checkmate,
    recognize_stalemate,
    recognize_tiger_silhouette_checkmate,
    recognize_white_face_general,
)
from .patterns.horse import (
    recognize_angler_horse_checkmate,
    recognize_discovered_horse_checkmate,
    recognize_elbow_horse_checkmate,
    recognize_octagon_horse_checkmate,
    recognize_palcorner_horse_checkmate,
)

PATTERN_ORDER = [
    'CROWNED_CHECKMATE',
    'CENTROID_CHECKMATE',
    'CANNONS_SANDWICHING_CHARIOT_CHECKMATE',
    'DOUBLE_CANNON_CHECKMATE',
    'SMOTHERED_CANNON_CHECKMATE',
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE',
    'IRON_BOLT_CHECKMATE',
    'DRAWER_CHECKMATE',
    'THROAT_CUTTING_CHECKMATE',
    'THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE',
    'TWO_DEVILS_KNOCKING_CHECKMATE',
    'DOUBLE_CHARIOTS_CHECKMATE',
    'DISCOVERED_HORSE_CHECKMATE',
    'TIGER_SILHOUETTE_CHECKMATE',
    'HORSE_CANNON_CHECKMATE',
    'ELBOW_HORSE_CHECKMATE',
    'PALCORNER_HORSE_CHECKMATE',
    'OCTAGON_HORSE_CHECKMATE',
    'ANGLER_HORSE_CHECKMATE',
    'SMOTHERED_CHECKMATE',
    'DOUBLE_CHECK_CHECKMATE',
    'WHITE_FACE_GENERAL',
    'STALEMATE',
]

_RECOGNIZERS = {
    'CROWNED_CHECKMATE': recognize_crowned_checkmate,
    'CENTROID_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CENTROID_PAWN_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CENTROID_CHARIOT_CHECKMATE': recognize_centroid_chariot_checkmate,
    'CANNONS_SANDWICHING_CHARIOT_CHECKMATE': recognize_cannons_sandwiching_chariot_checkmate,
    'DOUBLE_CANNON_CHECKMATE': recognize_double_cannon_checkmate,
    'DISCOVERED_HORSE_CHECKMATE': recognize_discovered_horse_checkmate,
    'SMOTHERED_CANNON_CHECKMATE': recognize_smothered_cannon_checkmate,
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE': recognize_heaven_and_earth_cannon_checkmate,
    'DRAWER_CHECKMATE': recognize_drawer_checkmate,
    'THROAT_CUTTING_CHECKMATE': recognize_throat_cutting_checkmate,
    'THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE': recognize_three_chariots_attacking_advisor_checkmate,
    'TIGER_SILHOUETTE_CHECKMATE': recognize_tiger_silhouette_checkmate,
    'HORSE_CANNON_CHECKMATE': recognize_horse_cannon_checkmate,
    'OCTAGON_HORSE_CHECKMATE': recognize_octagon_horse_checkmate,
    'DOUBLE_CHECK_CHECKMATE': recognize_double_check_checkmate,
    'TWO_DEVILS_KNOCKING_CHECKMATE': recognize_two_devils_knocking_checkmate,
    'ELBOW_HORSE_CHECKMATE': recognize_elbow_horse_checkmate,
    'PALCORNER_HORSE_CHECKMATE': recognize_palcorner_horse_checkmate,
    'ANGLER_HORSE_CHECKMATE': recognize_angler_horse_checkmate,
    'IRON_BOLT_CHECKMATE': recognize_iron_bolt_checkmate,
    'DOUBLE_CHARIOTS_CHECKMATE': recognize_double_chariots_checkmate,
    'SMOTHERED_CHECKMATE': recognize_smothered_checkmate,
    'WHITE_FACE_GENERAL': recognize_white_face_general,
    'STALEMATE': recognize_stalemate,
}

# A pattern is dropped when one of the patterns listed for it is also present.
_EXCLUDED_BY = {
    'DOUBLE_CHARIOTS_CHECKMATE': {'CENTROID_CHECKMATE', 'TWO_DEVILS_KNOCKING_CHECKMATE', 'CROWNED_CHECKMATE'},
    'DISCOVERED_HORSE_CHECKMATE': {'ELBOW_HORSE_CHECKMATE'},
    'PALCORNER_HORSE_CHECKMATE': {'HORSE_CANNON_CHECKMATE'},
    # 2026.11.05-v15 (expert review): 闷宫杀 already names this finish.
    'HEAVEN_AND_EARTH_CANNON_CHECKMATE': {'SMOTHERED_CANNON_CHECKMATE'},
}
_DOUBLE_CHECK = 'DOUBLE_CHECK_CHECKMATE'


def recognize_pattern(pattern_id: str, fen: str, moves: list[str] | None = None) -> dict:
    recognizer = _RECOGNIZERS.get(pattern_id.strip().upper())
    if recognizer is None:
        raise ValueError(f'不支援的 pattern_id：{pattern_id}')
    return recognizer(fen, moves)


def _apply_exclusions(detected: list[dict], request: tuple[str | None, str, list[str] | None]) -> list[dict]:
    pattern_id, fen, moves = request
    present = {match['pattern_id'] for match in detected}
    if pattern_id and detected and detected[0]['pattern_id'] in _EXCLUDED_BY:
        present.update(
            candidate for candidate in _EXCLUDED_BY[detected[0]['pattern_id']]
            if recognize_pattern(candidate, fen, moves)['detected']
        )
    return [match for match in detected if not (_EXCLUDED_BY.get(match['pattern_id'], set()) & present)]


def _drop_redundant_double_check(
    detected: list[dict], position: tuple[str, dict], request: tuple[str | None, str, list[str] | None],
) -> list[dict]:
    """A cannon check alongside a chariot or pawn check is named by the other pattern, when there is one."""
    pattern_id, fen, moves = request
    current_fen, analysis = position
    checker_types = {parse_fen(current_fen).get(item['square'], '').upper() for item in analysis['checking_pieces']}
    if not ('C' in checker_types and checker_types.intersection({'R', 'P'})
            and any(match['pattern_id'] == _DOUBLE_CHECK for match in detected)):
        return detected
    has_other = any(match['pattern_id'] != _DOUBLE_CHECK for match in detected)
    if pattern_id and not has_other:
        has_other = any(recognize_pattern(candidate, fen, moves)['detected']
                        for candidate in PATTERN_ORDER if candidate != _DOUBLE_CHECK)
    return [match for match in detected if match['pattern_id'] != _DOUBLE_CHECK] if has_other else detected


def analyze_patterns(fen: str, moves: list[str] | None = None, pattern_id: str | None = None) -> dict:
    current_fen, applied = apply_moves(fen, moves)
    analysis = position_analysis(current_fen)
    candidate_ids = [pattern_id.strip().upper()] if pattern_id else PATTERN_ORDER
    matches = [recognize_pattern(candidate_id, fen, moves) for candidate_id in candidate_ids]
    request = (pattern_id, fen, moves)
    detected = _apply_exclusions([match for match in matches if match['detected']], request)
    detected = _drop_redundant_double_check(detected, (current_fen, analysis), request)
    return {
        'requested_pattern_id': pattern_id.strip().upper() if pattern_id else None,
        'fen': current_fen,
        'moves': applied,
        'analysis': analysis,
        'best_match': detected[0] if detected else None,
        'matches': detected,
        'material_fallback': (
            classify_mating_material(current_fen, analysis) if not pattern_id and not detected else None
        ),
    }
