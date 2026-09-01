from __future__ import annotations

from .board import (
    START_FEN,
    apply_move,
    build_piece_identity,
    legal_moves,
    move_piece_identity,
    parse_fen,
    side_to_move,
)
from .models import (
    AdvanceResponse,
    AnalyzeResponse,
    InspectRequest,
    InspectResponse,
    InitialResponse,
    MoveRecord,
    RecognitionState,
)
from .notation import chinese_notation
from .recognizer import initial_state, inspect_position, update_recognition


def create_initial() -> InitialResponse:
    state = initial_state()
    return InitialResponse(state=state, legal_moves=legal_moves(START_FEN))


def advance(previous: RecognitionState, ucci: str) -> AdvanceResponse:
    parse_fen(previous.fen)
    side = side_to_move(previous.fen)
    notation = chinese_notation(previous.fen, ucci)
    next_fen = apply_move(previous.fen, ucci)
    next_state = update_recognition(previous, next_fen, side, ucci)
    next_state.piece_identity = move_piece_identity(
        previous.piece_identity or build_piece_identity(previous.fen),
        ucci[:2],
        ucci[2:],
    )
    move = MoveRecord(
        ply=next_state.ply,
        side=side,
        ucci=ucci,
        chinese_notation=notation,
        from_square=ucci[:2],
        to_square=ucci[2:],
    )
    return AdvanceResponse(
        move=move,
        state=next_state,
        legal_moves=legal_moves(next_fen),
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

