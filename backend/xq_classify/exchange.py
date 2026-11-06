"""Destination-square exchange evaluation (static exchange evaluation).

Semantics follow xiangqi-server's ``api/util/exchange.py``, which
must match the frontend's ``exchange.js``:

- consider every legal recapturer;
- rebuild the position after each capture;
- allow declining an unfavourable recapture, unless every legal answer to a
  check recaptures here;
- value each piece on the square it moves from.

Moves use UCCI with ranks 0-9 (the server converts from its 1-10 ranks).
``tests/fixtures/server_exchange_reference.json`` holds 10,000 values computed
by the server implementation.

``ExchangeEvaluator`` takes the board functions it runs on, so a host can bind
its own (the lab binds its pyffish-or-pure board).  The module-level functions
use this package's board.
"""

from collections.abc import Callable
from functools import lru_cache

from . import board

MATERIAL_VALUES = {'R': 9, 'N': 4, 'C': 4, 'B': 2, 'A': 2, 'P': 1}
CACHE_SIZE = 8192


def piece_value(piece: str, square: str) -> int:
    """Material value of *piece* standing on *square*; a pawn is worth 2 once across the river."""
    if piece.upper() == 'P':
        crossed = int(square[1]) >= 5 if piece.isupper() else int(square[1]) <= 4
        return 2 if crossed else 1
    return MATERIAL_VALUES.get(piece.upper(), 0)


class ExchangeEvaluator:
    """Exchange evaluation over one set of board functions, with its own caches."""

    def __init__(
        self,
        legal_moves: Callable[[str], list[str]],
        apply_move: Callable[[str, str], str],
        position_analysis: Callable[[str], dict],
    ) -> None:
        self._legal_moves = legal_moves
        self._apply_move = apply_move
        self._position_analysis = position_analysis
        self.evaluate_square = lru_cache(maxsize=CACHE_SIZE)(self._evaluate_square)
        self.evaluate_exchange = lru_cache(maxsize=CACHE_SIZE)(self._evaluate_exchange)

    def clear_caches(self) -> None:
        self.evaluate_square.cache_clear()
        self.evaluate_exchange.cache_clear()

    def _evaluate_square(self, fen: str, square: str, occupant_value: int) -> int:
        """Best net gain from recapturing here, including the option to stop."""
        if occupant_value <= 0:
            return 0
        position = board.parse_fen(fen)
        moves = self._legal_moves(fen)
        recaptures = sorted(
            (piece_value(position[move[:2]], move[:2]), move) for move in moves if move[2:] == square
        )
        if not recaptures:
            return 0
        best = max(
            occupant_value - self.evaluate_square(self._apply_move(fen, move), square, value)
            for value, move in recaptures
        )
        if best < 0:
            forced = len(recaptures) == len(moves) and self._position_analysis(fen)['is_check']
            if not forced:
                return 0
        return best

    def _evaluate_exchange(self, fen: str, move: str) -> int:
        """Net gain after optimal captures on the move's destination have resolved.

        The first move is mandatory; subsequent captures may be declined. Positive
        gains material, zero is even, and negative loses material. Quiet moves are
        supported. Invalid moves and king captures return zero, so callers must
        establish a legal non-king capture before interpreting zero as a trade.
        """
        if not fen or not move or move not in self._legal_moves(fen):
            return 0
        position = board.parse_fen(fen)
        source, target = move[:2], move[2:]
        victim = position.get(target, '')
        if victim.upper() == 'K':
            return 0
        return piece_value(victim, target) - self.evaluate_square(
            self._apply_move(fen, move), target, piece_value(position[source], source),
        )


_PACKAGE_BOARD = ExchangeEvaluator(board.legal_moves, board.apply_move, board.position_analysis)
evaluate_exchange = _PACKAGE_BOARD.evaluate_exchange
evaluate_square = _PACKAGE_BOARD.evaluate_square
clear_caches = _PACKAGE_BOARD.clear_caches
