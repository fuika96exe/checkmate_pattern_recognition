"""The final merge: apply the suppression rules and list the visible labels."""

from .context import LABELS


def finalize_labels(plies: list[dict], material: dict) -> tuple[list[str], list[dict]]:
    """Keep supporting proof separately so suppressed parent keys remain usable."""
    raw = {o['id'] for ply in plies for o in ply['occurrences']}
    suppressed = {}
    if material['kind'] == 'gain' and raw - {'exchange'}:
        suppressed['exchange'] = 'gain_has_other_tactic'
    support = []
    for ply in plies:
        visible = []
        for occurrence in ply['occurrences']:
            if occurrence['id'] in suppressed:
                support.append({**occurrence, 'suppressedBy': suppressed[occurrence['id']]})
            else:
                visible.append(occurrence)
        ply['occurrences'] = visible
    tactics = [label for label in LABELS if label in raw and label not in suppressed]
    return tactics, support
