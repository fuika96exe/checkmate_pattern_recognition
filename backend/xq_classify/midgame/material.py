"""Did the solver win material over the line?"""

from .. import board as b
from .position import MAIN, VALUES, own


def material_result(initial: str, final: str, solver: str) -> dict:
    def balance(fen: str) -> int:
        return sum(
            VALUES.get(p.upper(), 0) * (1 if own(p, solver) else -1)
            for p in b.parse_fen(fen).values()
            if p.upper() in MAIN
        )

    start, end = balance(initial), balance(final)
    return {'kind': 'gain' if end - start >= 4 else 'no_gain', 'start': start, 'end': end, 'delta': end - start}
