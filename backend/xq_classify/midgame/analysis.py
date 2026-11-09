"""Midgame tactic analysis: run the detectors over a replayed line, then merge their findings.

Identity-based and precision-first: no network and no engine PV search.

The order of the two tuples below is part of the rules.  Later detectors read
what earlier ones found, an occurrence's evidence key numbers it within its ply,
and ``reviewReasons`` keeps call order.
"""

from ..version import MIDGAME_RULES_VERSION
from .context import Analysis, move_frame
from .detectors.check_fork import detect_check_forks
from .detectors.clearance import detect_clearances
from .detectors.discovered_attack import detect_discovered_attacks, detect_escaped_discovered_attacks
from .detectors.exchange import detect_exchanges
from .detectors.fork import detect_forks, detect_screen_forks, detect_two_threat_forks
from .detectors.overload import detect_overloads
from .detectors.pin import detect_pins, detect_recapture_pins
from .detectors.remove_defender import detect_removed_defenders
from .detectors.skewer import detect_skewers
from .detectors.trap import detect_traps
from .material import material_result
from .merge import finalize_labels
from .replay import replay

RULES_VERSION = MIDGAME_RULES_VERSION

MOVE_DETECTORS = (
    detect_forks,
    detect_screen_forks,
    detect_discovered_attacks,
    detect_escaped_discovered_attacks,
    detect_skewers,
    detect_two_threat_forks,
    detect_pins,
    detect_check_forks,
    detect_traps,
)
LINE_DETECTORS = (
    detect_recapture_pins,
    detect_clearances,
    detect_removed_defenders,
    detect_overloads,
    detect_exchanges,
)


def analyze_midgame(fen: str, blunder: str, pv: list[str], solver: str) -> dict:
    positions, events = replay(fen, blunder, pv, solver)
    run = Analysis(positions, events, solver)
    for event in events[1:]:
        if event.side == solver:
            frame = move_frame(run, event)
            for detect in MOVE_DETECTORS:
                detect(run, frame)
    for detect in LINE_DETECTORS:
        detect(run)
    material = material_result(positions[0].fen, positions[-1].fen, solver)
    tactics, support = finalize_labels(run.plies, material)
    return {'status': 'matched' if tactics else 'unmatched', 'solver': solver,
            'tactics': tactics, 'fens': [p.fen for p in positions], 'plies': run.plies,
            'material': material, 'supportingEvidence': support, 'reviewReasons': run.reviews}
