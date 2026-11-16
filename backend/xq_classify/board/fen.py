# ruff: noqa: RUF001 - Chinese punctuation in output strings
"""FEN and UCCI text: parsing, validation and serialisation.

A board is a ``dict`` from square name to piece letter (upper case Red, lower
case Black: ``R`` chariot, ``N`` horse, ``B`` elephant, ``A`` advisor, ``K``
general, ``C`` cannon, ``P`` pawn).  UCCI moves are ``<from><to>`` with ranks 0-9.
"""

import re
from functools import lru_cache

from .errors import BoardError
from .geometry import FILES

START_FEN = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
UCCI_RE = re.compile(r'^[a-i][0-9][a-i][0-9]$')
_PIECE_LETTERS = 'rnbakcpRNBAKCP'


def check_ucci(move: str) -> None:
    """Raise ``BoardError`` unless *move* is a well-formed UCCI move (legality is not checked)."""
    if not UCCI_RE.fullmatch(move):
        raise BoardError('UCCI 着法格式不正確')


def _parse_rank(encoded: str, rank: int, board: dict[str, str]) -> None:
    file_index = 0
    for char in encoded:
        if char.isdigit():
            file_index += int(char)
            continue
        if char not in _PIECE_LETTERS:
            raise BoardError(f'FEN 包含不支援棋子：{char}')
        if file_index >= 9:
            raise BoardError('FEN 行超出 9 路')
        board[f'{FILES[file_index]}{rank}'] = char
        file_index += 1
    if file_index != 9:
        raise BoardError('FEN 每行必須正好 9 路')


@lru_cache(maxsize=1024)
def _parse_fen_cached(fen: str) -> dict[str, str]:
    parts = fen.strip().split()
    if len(parts) < 2:
        raise BoardError('FEN 必須包含棋盤及行棋方')
    ranks = parts[0].split('/')
    if len(ranks) != 10:
        raise BoardError('中國象棋 FEN 必須有 10 行')
    board: dict[str, str] = {}
    for fen_index, encoded in enumerate(ranks):
        _parse_rank(encoded, 9 - fen_index, board)
    if parts[1] not in {'w', 'b'}:
        raise BoardError('FEN 行棋方必須是 w 或 b')
    return board


def parse_fen(fen: str) -> dict[str, str]:
    """Parse a FEN into a fresh board while caching its validated shape."""
    return dict(_parse_fen_cached(fen))


def clear_cache() -> None:
    _parse_fen_cached.cache_clear()


def side_to_move(fen: str) -> str:
    return 'red' if fen.split()[1] == 'w' else 'black'


def has_both_generals(board: dict[str, str]) -> bool:
    """A position without both generals is terminal: no moves, and never sent to a native engine."""
    pieces = board.values()
    return 'K' in pieces and 'k' in pieces


def board_to_fen(board: dict[str, str]) -> str:
    """The piece-placement field of a FEN (no side to move or counters)."""
    encoded_ranks: list[str] = []
    for rank in range(9, -1, -1):
        empty = 0
        encoded = ''
        for file_name in FILES:
            piece = board.get(f'{file_name}{rank}')
            if piece is None:
                empty += 1
                continue
            if empty:
                encoded += str(empty)
                empty = 0
            encoded += piece
        if empty:
            encoded += str(empty)
        encoded_ranks.append(encoded)
    return '/'.join(encoded_ranks)
