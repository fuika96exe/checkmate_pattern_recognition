"""Midgame tactic analysis: run the detectors over a replayed line and merge their findings.

Identity-based and precision-first: no network and no engine PV search.  Phase 0
step 6 is moving each label's detector out of this module, in the original order.
"""
from __future__ import annotations

from .. import board as b
from ..exchange import evaluate_exchange, piece_value
from ..version import MIDGAME_RULES_VERSION
from .context import LABELS, Analysis, Finding, move_frame
from .detectors.check_fork import detect_check_forks
from .detectors.clearance import detect_clearances
from .detectors.discovered_attack import detect_discovered_attacks, detect_escaped_discovered_attacks
from .detectors.fork import detect_forks, detect_screen_forks, detect_two_threat_forks
from .detectors.overload import detect_overloads
from .detectors.pin import detect_pins, detect_recapture_pins
from .detectors.remove_defender import detect_removed_defenders
from .detectors.skewer import detect_skewers
from .detectors.trap import detect_traps
from .material import material_result
from .merge import finalize_labels
from .position import MAIN, VALUES, Position, opened_by, other, own, view, without_pieces
from .replay import replay

RULES_VERSION = MIDGAME_RULES_VERSION


def analyze_midgame(fen: str, blunder: str, pv: list[str], solver: str):
    positions, events = replay(fen, blunder, pv, solver)
    run = Analysis(positions, events, solver)
    plies, reviews, review = run.plies, run.reviews, run.review

    def emit(label, ply, confirmed, actors, targets, kind, evidence):
        return run.emit(Finding(label, ply, confirmed, actors, targets, kind, evidence))

    for event in events[1:]:
        if event.side != solver:
            continue
        frame = move_frame(run, event)
        p, before, after, response, reply = frame.ply, frame.before, frame.after, frame.response, frame.reply
        excluded, hits, threats, fork_threats = frame.excluded, frame.hits, frame.threats, frame.fork_threats
        detect_forks(run, frame)
        detect_screen_forks(run, frame)
        detect_discovered_attacks(run, frame)
        detect_escaped_discovered_attacks(run, frame)
        detect_skewers(run, frame)
        detect_two_threat_forks(run, frame)
        detect_pins(run, frame)
        detect_check_forks(run, frame)
        detect_traps(run, frame)

    detect_recapture_pins(run)

    detect_clearances(run)

    detect_removed_defenders(run)

    detect_overloads(run)

    captures = [e for e in events[1:] if e.victim_kind in MAIN]
    for u in captures:
        if u.side != solver:
            continue
        for v in captures:
            if v.side == solver or (u.dst != v.dst and abs(u.ply - v.ply) != 1):
                continue
            emit("exchange", u.ply, max(u.ply, v.ply), [u.actor, v.actor], [u.victim, v.victim], "bilateral_major_captures",
                 {"captures": [{"ply": e.ply, "ucci": e.move, "actor": positions[e.ply - 1].ref(e.actor),
                                "victim": positions[e.ply - 1].ref(e.victim)} for e in (u, v)]})
    # v2.6: the blunder itself may be the opponent's half of an even trade.
    # Only an immediate same-value major recapture counts; winning a larger
    # piece back is a material gain, not an exchange.
    if len(events) > 1:
        blunder, answer = events[0], events[1]
        if (blunder.victim_kind in MAIN and answer.side == solver and answer.victim_kind in MAIN
                and VALUES[blunder.victim_kind] == VALUES[answer.victim_kind]
                and not any(o["id"] == "exchange" for o in plies[1]["occurrences"])):
            emit("exchange", 2, 2, [answer.actor, blunder.actor], [answer.victim, blunder.victim],
                 "blunder_trade_recaptured",
                 {"captures": [{"ply": e.ply, "ucci": e.move, "actor": positions[e.ply - 1].ref(e.actor),
                                "victim": positions[e.ply - 1].ref(e.victim)} for e in (answer, blunder)]})
    material = material_result(positions[0].fen, positions[-1].fen, solver)
    tactics, support = finalize_labels(plies, material)
    return {"status": "matched" if tactics else "unmatched", "solver": solver,
            "tactics": tactics, "fens": [p.fen for p in positions], "plies": plies,
            "material": material, "supportingEvidence": support, "reviewReasons": reviews}
