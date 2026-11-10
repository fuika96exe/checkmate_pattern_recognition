# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""``classify_checkmate``: the one place that decides a checkmate puzzle's labels.

Before phase 0 step 4 this was spread over the lab's FastAPI handler (play the
line, require a final checkmate or stalemate), its batch script (status and
material fallback) and ``analyze_patterns``.  The error strings are unchanged.
"""

from .. import board
from ..contracts import CheckmateResult
from .recognition import analyze_patterns

NOT_MATE_ERROR = '解答線終局不是將死或困斃局面'
EMPTY_LINE_ERROR = '沒有失著時，解答線不能為空'


def _play_line(fen: str, moves: list[str]) -> tuple[list[dict], CheckmateResult | None]:
    """Apply the moves; return the timeline and, if a move cannot be played, the invalid result."""
    timeline: list[dict] = [{'index': 0, 'fen': fen, 'move': None}]
    current = fen
    for index, move in enumerate(moves, start=1):
        try:
            current = board.apply_move(current, move)
        except (ValueError, TypeError) as exc:  # BoardError is a ValueError; TypeError for a non-string move
            failure = CheckmateResult(
                status='invalid',
                error=f'第 {index} 手 {move} 無法套用：{exc}',
                failed_move_index=index,
                timeline=timeline,
            )
            return timeline, failure
        timeline.append({'index': index, 'fen': current, 'move': move})
    return timeline, None


def classify_checkmate(fen: str, blunder: str | None, pv: list[str]) -> CheckmateResult:
    """Classify a checkmate puzzle: *fen* before the *blunder*, then the solution line *pv*.

    With ``blunder=None`` *fen* is the puzzle position and only *pv* is played, so
    ``timeline`` indexes and ``failed_move_index`` count the moves of *pv*.
    """
    moves = [*pv] if blunder is None else [blunder, *pv]
    if not moves:
        return CheckmateResult(
            status='invalid', error=EMPTY_LINE_ERROR, timeline=[{'index': 0, 'fen': fen, 'move': None}]
        )
    timeline, failure = _play_line(fen, moves)
    if failure is not None:
        return failure
    try:
        analysis = analyze_patterns(fen, moves)
    except (ValueError, TypeError, KeyError, IndexError) as exc:  # reported in the result, as the lab API did
        return CheckmateResult(status='invalid', error=f'殺法分析失敗：{exc}', timeline=timeline)
    final = analysis['analysis']
    if not (final['is_checkmate'] or final['is_stalemate']):
        return CheckmateResult(status='invalid', error=NOT_MATE_ERROR, timeline=timeline, analysis=analysis)
    pattern_ids = [match['pattern_id'] for match in analysis['matches']]
    fallback = analysis['material_fallback']
    return CheckmateResult(
        status='matched' if pattern_ids or fallback else 'unmatched',
        pattern_ids=pattern_ids,
        material_id=fallback['id'] if fallback else None,
        timeline=timeline,
        analysis=analysis,
    )
