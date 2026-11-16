"""``classify_midgame``: the entry point for midgame tactic puzzles."""

from ..contracts import MidgameResult
from .analysis import analyze_midgame


def classify_midgame(fen: str, blunder: str, pv: list[str], solver: str) -> MidgameResult:
    """Classify a midgame puzzle: *fen* before the *blunder*, the solution line *pv*, *solver* ``'red'``/``'black'``.

    Raises ``ReplayError`` (with ``ply``, ``fen`` and ``move``) when the input
    does not replay; callers that index many puzzles record it as an invalid row.
    """
    result = analyze_midgame(fen, blunder, pv, solver)
    return MidgameResult(
        status=result['status'],
        solver=result['solver'],
        tactics=result['tactics'],
        fens=result['fens'],
        plies=result['plies'],
        material=result['material'],
        supporting_evidence=result['supportingEvidence'],
        review_reasons=result['reviewReasons'],
    )
