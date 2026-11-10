"""交換 (exchange): both sides capture major pieces in the line."""

from ..context import Analysis, Finding
from ..position import MAIN, VALUES
from ..replay import Event


def _capture_refs(run: Analysis, captures: tuple[Event, Event]) -> list[dict]:
    return [
        {
            'ply': e.ply,
            'ucci': e.move,
            'actor': run.positions[e.ply - 1].ref(e.actor),
            'victim': run.positions[e.ply - 1].ref(e.victim),
        }
        for e in captures
    ]


def _detect_bilateral_captures(run: Analysis) -> None:
    captures = [e for e in run.events[1:] if e.victim_kind in MAIN]
    for u in captures:
        if u.side != run.solver:
            continue
        for v in captures:
            if v.side == run.solver or (u.dst != v.dst and abs(u.ply - v.ply) != 1):
                continue
            run.emit(
                Finding(
                    'exchange',
                    u.ply,
                    max(u.ply, v.ply),
                    [u.actor, v.actor],
                    [u.victim, v.victim],
                    'bilateral_major_captures',
                    {'captures': _capture_refs(run, (u, v))},
                )
            )


def _detect_blunder_trade(run: Analysis) -> None:
    """v2.6: the blunder itself may be the opponent's half of an even trade.

    Only an immediate same-value major recapture counts; winning a larger
    piece back is a material gain, not an exchange.  A puzzle without a
    blunder has no opponent half, so this rule never fires there.
    """
    if len(run.events) <= 1 or run.events[0].move is None:
        return
    blunder, answer = run.events[0], run.events[1]
    if (
        blunder.victim_kind in MAIN
        and answer.side == run.solver
        and answer.victim_kind in MAIN
        and VALUES[blunder.victim_kind] == VALUES[answer.victim_kind]
        and not any(o['id'] == 'exchange' for o in run.occurrences(2))
    ):
        run.emit(
            Finding(
                'exchange',
                2,
                2,
                [answer.actor, blunder.actor],
                [answer.victim, blunder.victim],
                'blunder_trade_recaptured',
                {'captures': _capture_refs(run, (answer, blunder))},
            )
        )


def detect_exchanges(run: Analysis) -> None:
    _detect_bilateral_captures(run)
    _detect_blunder_trade(run)
