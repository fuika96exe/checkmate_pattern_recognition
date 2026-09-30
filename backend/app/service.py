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
from .repetition import adjudicate, chase_events, position_key
from .tactical_categories import CATEGORY_RULES_VERSION, analyze_tactical_categories
from .tactics import TACTIC_RULES_VERSION, analyze_tactics


def _live_game_report(
    before_fen: str,
    next_fen: str,
    move: MoveRecord,
    repetition: dict[str, object],
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
        "warning": ("repetition_warning", "重复警告", "重复线路中存在将军或追捉行为，需继续结合完整历史观察。"),
        "draw": ("repetition_draw", "和棋", "完整重复历史已满足当前规则的和棋裁决。"),
    }
    if status in repetition_labels:
        identifier, label, detail = repetition_labels[status]
        add(identifier, label, detail)

    purpose = analyze_tactics(before_fen, [move.ucci])[0]["occurrences"]
    for occurrence in purpose:
        events.append(LiveGameEvent(
            source="move_purpose",
            **occurrence,  # type: ignore[arg-type]
        ))
    categories = analyze_tactical_categories(before_fen, [move.ucci])[0]["occurrences"]
    for occurrence in categories:
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
    side = side_to_move(request.before_fen)
    next_fen = apply_move(request.before_fen, request.ucci_move)
    move = MoveRecord(
        ply=request.ply,
        side=side,
        ucci=request.ucci_move,
        chinese_notation=chinese_notation(request.before_fen, request.ucci_move),
        from_square=request.ucci_move[:2],
        to_square=request.ucci_move[2:],
    )
    return _live_game_report(request.before_fen, next_fen, move, request.repetition_decision)


def create_initial() -> InitialResponse:
    state = initial_state()
    return InitialResponse(state=state, legal_moves=legal_moves(START_FEN))


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
    moved_piece_id = previous_identities.get(ucci[:2])
    next_state.piece_identity = move_piece_identity(
        previous_identities,
        ucci[:2],
        ucci[2:],
    )
    prior_latches = {tuple(pair) for pair in previous.chase_latches if len(pair) == 2}
    chase_target_ids, pinned_rook_chase_target_ids, next_latches = chase_events(
        previous.fen,
        previous_identities,
        next_fen,
        next_state.piece_identity,
        side,
        moved_piece_id,
        prior_latches,
    )
    positions = list(previous.repetition_positions)
    if not positions:
        # Older clients may send a snapshot from before repetition history was
        # introduced.  Start a safe history at that snapshot rather than
        # guessing unseen moves.
        positions = [{"ply": previous.ply, "key": position_key(previous.fen)}]
    actions = list(previous.repetition_actions)
    actions.append(
        {
            "ply": next_state.ply,
            "side": side,
            "is_check": position_analysis(next_fen)["is_check"],
            "chase_target_ids": chase_target_ids,
            "pinned_rook_chase_target_ids": pinned_rook_chase_target_ids,
        }
    )
    positions.append({"ply": next_state.ply, "key": position_key(next_fen)})
    decision = adjudicate(positions, actions)
    if decision["status"] == "must_change" and decision["restricted_side"] == side:
        raise ValueError("此着会形成长将／长捉重复，请选择其他着法")
    next_state.repetition_positions = positions
    next_state.repetition_actions = actions
    next_state.chase_latches = [list(pair) for pair in sorted(next_latches)]
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
    report = _live_game_report(previous.fen, next_fen, move, decision) if include_live_report else None
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
