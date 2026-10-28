from __future__ import annotations

from .board import (
    START_FEN,
    apply_move,
    build_piece_identity,
    legal_moves,
    move_piece_identity,
    parse_fen,
    position_analysis,
    side_to_move,
)
from .models import (
    AdvanceResponse,
    AnalyzeResponse,
    InspectRequest,
    InspectResponse,
    InitialResponse,
    LiveGameEvent,
    LiveGameReport,
    LiveGameReportRequest,
    MoveRecord,
    RecognitionState,
)
from .notation import chinese_notation
from .recognizer import initial_state, inspect_position, update_recognition
from .cycle_rules import CycleRuleResult, evaluate_cycle
from .repetition import position_key
from .tactical_categories import CATEGORY_RULES_VERSION, analyze_tactical_categories
from .tactics import TACTIC_RULES_VERSION, analyze_tactics


def _live_game_report(
    next_fen: str,
    move: MoveRecord,
    repetition: dict[str, object],
    purpose: list[dict[str, object]],
    categories: list[dict[str, object]],
) -> LiveGameReport:
    """Merge post-move referee facts with auditable short-horizon findings."""
    events: list[LiveGameEvent] = []

    def add(identifier: str, label: str, detail: str, squares: list[str] | None = None) -> None:
        events.append(LiveGameEvent(
            id=identifier,
            source="rule",
            label_zh=label,
            squares=squares or [],
            detail=detail,
        ))

    position = position_analysis(next_fen)
    checking_squares = [item["square"] for item in position["checking_pieces"]]
    if position["is_checkmate"]:
        add("checkmate", "将死", "本手构成将军，且被将方已无合法应手。", checking_squares)
    elif position["is_check"]:
        add("check", "将军", "本手后对方将／帅正受攻击。", checking_squares)
    if position["is_stalemate"]:
        add("stalemate", "困毙", "轮到的一方无合法着法，且并未被将军。")

    status = repetition.get("status", "none")
    repetition_labels = {
        "watch": ("repetition_watch", "重复局面提示", "本手形成重复局面的观察点，尚未构成长将／长捉裁决。"),
        "warning": ("repetition_warning", "重复局面警告", "该局面已出现三次；若再次出现相同局面，将按循环规则裁决。"),
        "draw": ("repetition_draw", "和棋", "完整重复历史已满足当前规则的和棋裁决。"),
    }
    if status in repetition_labels:
        identifier, label, detail = repetition_labels[status]
        add(identifier, label, detail)

    for occurrence in purpose:
        events.append(LiveGameEvent(
            source="move_purpose",
            **occurrence,  # type: ignore[arg-type]
        ))
    # The purpose and tactical-category engines are intentionally separate,
    # but a shared identifier (for example ``pin``) describes the same event.
    # Keep both views in their dedicated laboratory tabs while presenting just
    # one, non-duplicated fact in the live referee report.
    purpose_ids = {str(occurrence["id"]) for occurrence in purpose}
    for occurrence in categories:
        if str(occurrence["id"]) in purpose_ids:
            continue
        events.append(LiveGameEvent(
            source="tactical_category",
            **occurrence,  # type: ignore[arg-type]
        ))

    return LiveGameReport(
        rules_version=f"live-referee-0.1; {TACTIC_RULES_VERSION}; {CATEGORY_RULES_VERSION}",
        ply=move.ply,
        side=move.side,
        ucci=move.ucci,
        events=events,
    )


def analyze_live_game_report(request: LiveGameReportRequest) -> LiveGameReport:
    """Build a report from an already accepted move without advancing state.

    This intentionally runs separately from ``advance``: the board can render
    as soon as a legal move and its referee decision are known, while the
    heavier tactical analysis continues in a background HTTP request.
    """
    if request.target_index > len(request.ucci_moves):
        raise ValueError("报告目标步超出所提供的棋谱范围")

    # This is intentionally the same full-line invocation used by the two
    # laboratory tabs.  Several purposes depend on what a preceding ply
    # created, so analysing only the final move gives a different answer.
    purpose_line = analyze_tactics(request.initial_fen, request.ucci_moves)
    category_line = analyze_tactical_categories(request.initial_fen, request.ucci_moves)
    current = request.initial_fen
    for ucci in request.ucci_moves[:request.target_index - 1]:
        current = apply_move(current, ucci)
    side = side_to_move(current)
    ucci = request.ucci_moves[request.target_index - 1]
    next_fen = apply_move(current, ucci)
    move = MoveRecord(
        ply=request.ply,
        side=side,
        ucci=ucci,
        chinese_notation=chinese_notation(current, ucci),
        from_square=ucci[:2],
        to_square=ucci[2:],
    )
    return _live_game_report(
        next_fen,
        move,
        request.repetition_decision,
        purpose_line[request.target_index - 1]["occurrences"],  # type: ignore[arg-type]
        category_line[request.target_index - 1]["occurrences"],  # type: ignore[arg-type]
    )


def create_initial() -> InitialResponse:
    state = initial_state()
    return InitialResponse(state=state, legal_moves=legal_moves(START_FEN))


def _cycle_actions(result: CycleRuleResult) -> list[dict[str, object]]:
    """Adapt the pure evaluator trace to the stable browser API shape."""
    return [
        {
            "ply": move.ply,
            "side": move.side,
            "isCheck": move.kind == "check",
            "chasePairs": [list(pair) for pair in move.chase_pairs],
            "chaseTargetIds": sorted({victim for _, victim in move.chase_pairs}),
            "pinnedRookChaseTargetIds": (
                sorted({victim for _, victim in move.chase_pairs})
                if move.kind == "pinned_rook_chase" else []
            ),
        }
        for move in result.moves
    ]


def _cycle_decision(
    result: CycleRuleResult, positions: list[dict[str, object]],
) -> dict[str, object]:
    """Expose a cycle-rule result through the existing repetition contract."""
    current = positions[-1]
    matching = [item for item in positions if item["key"] == current["key"]]
    occurrence_count = len(matching)
    status = {
        "red_must_change": "must_change",
        "black_must_change": "must_change",
        "draw": "draw",
        "warning": "warning",
        "watch": "watch",
        "none": "none",
    }[result.verdict]
    restricted_side = (
        "red" if result.verdict == "red_must_change"
        else "black" if result.verdict == "black_must_change"
        else None
    )
    return {
        "status": status,
        "repeatCount": max(0, occurrence_count - 1),
        "occurrenceCount": occurrence_count,
        "cycleStartPly": None,
        "redClassification": result.red_kind,
        "blackClassification": result.black_kind,
        "restrictedSide": restricted_side,
        "restrictedPositionKeys": [item["key"] for item in matching] if restricted_side else [],
        "reason": result.reason,
    }


def advance(
    previous: RecognitionState,
    ucci: str,
    *,
    include_live_report: bool = False,
) -> AdvanceResponse:
    parse_fen(previous.fen)
    side = side_to_move(previous.fen)
    notation = chinese_notation(previous.fen, ucci)
    next_fen = apply_move(previous.fen, ucci)
    next_state = update_recognition(previous, next_fen, side, ucci)
    previous_identities = previous.piece_identity or build_piece_identity(previous.fen)
    next_state.piece_identity = move_piece_identity(
        previous_identities,
        ucci[:2],
        ucci[2:],
    )
    positions = list(previous.repetition_positions)
    if not positions:
        # Older clients may send a snapshot from before repetition history was
        # introduced.  Start a safe history at that snapshot rather than
        # guessing unseen moves.
        positions = [{"ply": previous.ply, "key": position_key(previous.fen)}]
    positions.append({"ply": next_state.ply, "key": position_key(next_fen)})
    initial_fen = previous.repetition_initial_fen or previous.fen
    moves = list(next_state.opening_memory.moves)
    rule_result = evaluate_cycle(initial_fen, moves)
    actions = _cycle_actions(rule_result)
    decision = _cycle_decision(rule_result, positions)
    if decision["status"] == "must_change" and decision["restrictedSide"] == side:
        raise ValueError("此着会形成长将／长捉重复，请选择其他着法")
    next_state.repetition_positions = positions
    next_state.repetition_actions = actions
    next_state.repetition_initial_fen = initial_fen
    # Kept empty for snapshot compatibility. The evaluator owns its own
    # cross-ply latch state while replaying the complete immutable line.
    next_state.chase_latches = []
    next_state.repetition_decision = decision
    move = MoveRecord(
        ply=next_state.ply,
        side=side,
        ucci=ucci,
        chinese_notation=notation,
        from_square=ucci[:2],
        to_square=ucci[2:],
    )
    # Replay/import and opening-recognition batches deliberately skip this
    # costly optional annotation pass.  The legacy live endpoint can opt in;
    # the workbench uses the asynchronous report endpoint instead.
    report = (
        analyze_live_game_report(LiveGameReportRequest(
            initial_fen=previous.fen,
            ucci_moves=[ucci],
            target_index=1,
            ply=next_state.ply,
            repetition_decision=decision,
        ))
        if include_live_report else None
    )
    return AdvanceResponse(
        move=move,
        state=next_state,
        legal_moves=legal_moves(next_fen),
        live_report=report,
    )


def analyze(moves: list[str]) -> AnalyzeResponse:
    initial = create_initial()
    state = initial.state
    states = [state]
    records: list[MoveRecord] = []
    for ucci in moves:
        result = advance(state, ucci)
        state = result.state
        states.append(state)
        records.append(result.move)
    return AnalyzeResponse(
        moves=records,
        states=states,
        state=state,
        legal_moves=legal_moves(state.fen),
    )


def inspect(request: InspectRequest) -> InspectResponse:
    state = inspect_position(
        request.fen,
        request.memory_preset,
        infer_from_fen=request.infer_from_fen,
    )
    return InspectResponse(state=state, legal_moves=legal_moves(request.fen))
