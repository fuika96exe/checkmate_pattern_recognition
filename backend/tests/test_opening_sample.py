from app.board import legal_moves
from app.opening_sample import advance_sample, replay_sample
from app.service import advance, create_initial


MOVES = [
    "c3c4", "h7e7", "h0g2", "h9g7", "i0h0", "i9h9", "h2h6", "g6g5",
    "b0c2", "b7c7", "c2d4", "b9a7", "b2e2", "a9b9", "h6h8", "d9e8",
    "d0e1", "b9b4", "h8h4", "b4b5", "d4e6", "g7e6", "e2e6", "c6c5",
]


def test_sample_matches_workbench_through_first_twenty_plies():
    sample = replay_sample(MOVES[:20])
    state = create_initial().state
    for index, move in enumerate(MOVES[:20]):
        state = advance(state, move).state
        assert sample[index].state.fen == state.fen
        assert sample[index].state.classification == state.classification
        assert sample[index].state.opening_memory == state.opening_memory


def test_later_moves_update_board_without_reclassifying(monkeypatch):
    first_twenty = replay_sample(MOVES[:20])[-1].state

    def forbidden(*args, **kwargs):
        raise AssertionError("Opening recognition ran after the cutoff")

    monkeypatch.setattr("app.opening_sample.update_recognition", forbidden)
    state = first_twenty
    for move in MOVES[20:]:
        result = advance_sample(state, move)
        state = result.state
        assert state.classification == first_twenty.classification
        assert state.opening_memory.red == first_twenty.opening_memory.red
        assert state.opening_memory.black == first_twenty.opening_memory.black
        assert result.legal_moves == legal_moves(state.fen)
    assert state.ply == 24
    assert state.fen != first_twenty.fen
    assert state.current_shapes != first_twenty.current_shapes


def test_branch_before_cutoff_recalculates_recognition():
    state = replay_sample(MOVES[:19])[-1].state
    alternatives = [move for move in legal_moves(state.fen) if move != MOVES[19]]
    branch = advance_sample(state, alternatives[0]).state
    expected = advance(state, alternatives[0]).state
    assert branch.ply == 20
    assert branch.classification == expected.classification


def test_chunked_replay_matches_complete_replay_across_cutoff():
    complete = replay_sample(MOVES)
    first = replay_sample(MOVES[:10])
    second = replay_sample(MOVES[10:20], first[-1].state)
    third = replay_sample(MOVES[20:], second[-1].state)
    assert first + second + third == complete
