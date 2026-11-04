"""Replay sampled games, freezing opening recognition after ten full rounds."""
from copy import deepcopy

from .board import apply_move, legal_moves, move_piece_identity, side_to_move
from .models import AdvanceResponse, MoveRecord, RecognitionState
from .notation import chinese_notation
from .recognizer import detect_current_shapes, initial_state, update_recognition

OPENING_PLIES = 20


def advance_sample(previous: RecognitionState, ucci: str) -> AdvanceResponse:
    side = side_to_move(previous.fen)
    notation = chinese_notation(previous.fen, ucci)
    fen = apply_move(previous.fen, ucci)
    if previous.ply < OPENING_PLIES:
        state = update_recognition(previous, fen, side, ucci)
    else:
        # Continue observing the board, but never feed later moves into the
        # opening recognizer. Preserve the classification and choice history.
        state = deepcopy(previous)
        state.fen = fen
        state.ply += 1
        state.side_moves[side] = state.side_moves.get(side, 0) + 1
        state.current_shapes = detect_current_shapes(fen)
        state.opening_memory.fen = fen
        state.opening_memory.moves.append(ucci)
    state.piece_identity = move_piece_identity(previous.piece_identity, ucci[:2], ucci[2:])
    return AdvanceResponse(
        state=state,
        legal_moves=legal_moves(fen),
        move=MoveRecord(ply=state.ply, side=side, ucci=ucci, chinese_notation=notation,
                        from_square=ucci[:2], to_square=ucci[2:]),
    )


def replay_sample(moves: list[str], state: RecognitionState | None = None) -> list[AdvanceResponse]:
    state = state if state is not None else initial_state()
    results = []
    for move in moves:
        try:
            result = advance_sample(state, move)
        except ValueError as exc:
            raise ValueError(f"第 {state.ply + 1} 個半手 {move}：{exc}") from exc
        results.append(result)
        state = result.state
    return results
