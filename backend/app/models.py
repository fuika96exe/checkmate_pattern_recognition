from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


Side = Literal["red", "black"]


class ChoiceOccurrence(ApiModel):
    id: str
    formed_at_ply: int
    wing: Literal["left", "right", "g", "c"] | None = None
    origin_file: Literal["b", "h"] | None = None
    provisional: bool = False
    source: Literal["fen", "move", "memory"] = "fen"
    lock_group: str | None = None
    eligible_for_name: bool = True
    suppressed_by: str | None = None
    # Stable identity for replacing a moving rook's earlier descriptor.
    source_piece_id: str | None = None


class SideMemory(ApiModel):
    choice_path: list[ChoiceOccurrence] = Field(default_factory=list)
    composite_systems: list[ChoiceOccurrence] = Field(default_factory=list)
    formed_shapes: list[ChoiceOccurrence] = Field(default_factory=list)
    locks: dict[str, str] = Field(default_factory=dict)
    facts: list[str] = Field(default_factory=list)


class OpeningMemory(ApiModel):
    red: SideMemory = Field(default_factory=SideMemory)
    black: SideMemory = Field(default_factory=SideMemory)
    base_matchup_id: str | None = None
    base_matchup_confirmed_at_ply: int | None = None
    moves: list[str] = Field(default_factory=list)
    fen: str | None = None


class Classification(ApiModel):
    display_name: str = "未定型"
    display_name_en: str = "Undecided"
    certainty: Literal["pending", "provisional", "confirmed"] = "pending"
    red_main_id: str | None = None
    red_main_label: str | None = None
    red_modifiers: list[str] = Field(default_factory=list)
    black_main_id: str | None = None
    black_main_label: str | None = None
    black_modifiers: list[str] = Field(default_factory=list)
    red_system: str | None = None
    black_system: str | None = None
    base_matchup_id: str | None = None
    template_id: str | None = None
    evidence: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RecognitionState(ApiModel):
    schema_version: str = "2"
    rules_version: str = "ecco-contents-0.3"
    ply: int = 0
    fen: str
    side_moves: dict[str, int] = Field(default_factory=lambda: {"red": 0, "black": 0})
    piece_identity: dict[str, str] = Field(default_factory=dict)
    # Kept with the immutable game snapshot so undo, reconnect and the
    # browser-to-server request boundary all use the same repetition history.
    repetition_positions: list[dict[str, object]] = Field(default_factory=list)
    repetition_actions: list[dict[str, object]] = Field(default_factory=list)
    # The immutable first position for replaying the complete line through
    # the authoritative cycle-rule evaluator.  ``fen`` changes after every
    # ply, so it cannot serve this purpose.
    repetition_initial_fen: str | None = None
    chase_latches: list[list[str]] = Field(default_factory=list)
    repetition_decision: dict[str, object] = Field(default_factory=dict)
    current_shapes: dict[str, list[str]] = Field(default_factory=dict)
    opening_memory: OpeningMemory = Field(default_factory=OpeningMemory)
    classification: Classification = Field(default_factory=Classification)


class MoveRecord(ApiModel):
    ply: int
    side: Side
    ucci: str
    chinese_notation: str
    from_square: str
    to_square: str


class InitialResponse(ApiModel):
    state: RecognitionState
    legal_moves: list[str]


class AdvanceRequest(ApiModel):
    state: RecognitionState
    ucci_move: str


class LiveGameEvent(ApiModel):
    """One auditable rule, tactic, or move-purpose finding for a played move."""

    id: str
    source: Literal["rule", "tactical_category", "move_purpose"]
    label_zh: str
    squares: list[str] = Field(default_factory=list)
    detail: str


class LiveGameReport(ApiModel):
    """Unified referee report generated only after a legal move is accepted."""

    rules_version: str
    ply: int
    side: Side
    ucci: str
    legal: bool = True
    events: list[LiveGameEvent] = Field(default_factory=list)


class LiveGameReportRequest(ApiModel):
    """A stable whole-line snapshot for an asynchronous post-move report.

    ``target_index`` is one-based within ``ucci_moves``.  ``ply`` remains the
    board's absolute ply so reports also work after loading a FEN mid-game.
    """

    initial_fen: str
    ucci_moves: list[str]
    target_index: int = Field(ge=1)
    ply: int
    repetition_decision: dict[str, object] = Field(default_factory=dict)


class AdvanceResponse(ApiModel):
    move: MoveRecord
    state: RecognitionState
    legal_moves: list[str]
    live_report: LiveGameReport | None = None


class AnalyzeRequest(ApiModel):
    ucci_moves: list[str]


class AnalyzeResponse(ApiModel):
    moves: list[MoveRecord]
    states: list[RecognitionState]
    state: RecognitionState
    legal_moves: list[str]


class MemoryPreset(ApiModel):
    red_choice_path: list[str] = Field(default_factory=list)
    black_choice_path: list[str] = Field(default_factory=list)
    black_composite: str | None = None
    red_wing: Literal["left", "right", "g", "c"] | None = None
    black_wing: Literal["left", "right", "g", "c"] | None = None


class InspectRequest(ApiModel):
    fen: str
    memory_preset: MemoryPreset = Field(default_factory=MemoryPreset)
    infer_from_fen: bool = True


class InspectResponse(ApiModel):
    state: RecognitionState
    legal_moves: list[str]


class PositionAnalysisRequest(ApiModel):
    fen: str


class PositionAnalysisResponse(ApiModel):
    side_to_move: Side
    king_square: str
    is_check: bool
    is_checkmate: bool
    is_stalemate: bool
    legal_moves: list[str]
    checking_pieces: list[dict[str, str]]
    attacked_squares: dict[str, list[dict[str, str]]]


class TacticAnalysisRequest(ApiModel):
    """A legal move line to annotate with short-range tactical motifs."""

    fen: str
    ucci_moves: list[str] = Field(default_factory=list)


class TacticOccurrence(ApiModel):
    id: Literal["escape", "protect", "sacrifice", "block", "seal", "trap", "pin"]
    label_zh: str
    squares: list[str] = Field(default_factory=list)
    detail: str


class TacticMoveAnnotation(ApiModel):
    ply: int
    side: Side
    ucci: str
    occurrences: list[TacticOccurrence] = Field(default_factory=list)


class TacticAnalysisResponse(ApiModel):
    rules_version: str
    annotations: list[TacticMoveAnnotation] = Field(default_factory=list)


class TacticalCategoryAnalysisRequest(ApiModel):
    """A legal line to evaluate against the nine tactical categories."""

    fen: str
    ucci_moves: list[str] = Field(default_factory=list)


class TacticalCategoryOccurrence(ApiModel):
    id: Literal[
        "exchange", "fork", "skewer", "discovered_attack", "remove_defender",
        "trap", "pin", "cannon_pawn_breakthrough",
    ]
    label_zh: str
    squares: list[str] = Field(default_factory=list)
    detail: str


class TacticalCategoryMoveAnnotation(ApiModel):
    ply: int
    side: Side
    ucci: str
    occurrences: list[TacticalCategoryOccurrence] = Field(default_factory=list)


class TacticalCategoryAnalysisResponse(ApiModel):
    rules_version: str
    annotations: list[TacticalCategoryMoveAnnotation] = Field(default_factory=list)


class PatternAnalysisRequest(ApiModel):
    fen: str
    ucci_moves: list[str] = Field(default_factory=list)
    pattern_id: str | None = None


class PatternMatch(ApiModel):
    pattern_id: str
    pattern_name_zh: str
    detected: bool
    causal: bool
    fen: str
    moves: list[str]
    analysis: PositionAnalysisResponse
    features: dict[str, object]
    diagnostics: list[str]


class PatternAnalysisResponse(ApiModel):
    requested_pattern_id: str | None = None
    fen: str
    moves: list[str]
    analysis: PositionAnalysisResponse
    best_match: PatternMatch | None = None
    matches: list[PatternMatch] = Field(default_factory=list)


class PuzzleLineRequest(ApiModel):
    fen: str
    blunder_move: str
    pv: list[str] = Field(default_factory=list)


class PuzzleTimelineEntry(ApiModel):
    index: int
    fen: str
    move: str | None = None


class PuzzleLineResponse(ApiModel):
    rules_version: str
    valid: bool
    error: str | None = None
    failed_move_index: int | None = None
    timeline: list[PuzzleTimelineEntry] = Field(default_factory=list)
    analysis: PatternAnalysisResponse | None = None


class TestCaseInput(ApiModel):
    id: str
    name: str
    fen: str
    expected_name: str
    memory_preset: MemoryPreset = Field(default_factory=MemoryPreset)
    notes: str = ""
    source: Literal["built_in", "user"] = "user"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TestRunResult(ApiModel):
    id: str
    passed: bool
    expected_name: str
    actual_name: str
    diagnostics: list[str] = Field(default_factory=list)


class TestRunAllResponse(ApiModel):
    total: int
    passed: int
    results: list[TestRunResult]
