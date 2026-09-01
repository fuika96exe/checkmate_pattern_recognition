from __future__ import annotations

from .board import parse_fen


RED_NAMES = {"K": "帥", "A": "仕", "B": "相", "N": "馬", "R": "車", "C": "炮", "P": "兵"}
BLACK_NAMES = {"k": "將", "a": "士", "b": "象", "n": "馬", "r": "車", "c": "炮", "p": "卒"}
CHINESE_NUMBERS = "零一二三四五六七八九"
FULLWIDTH_NUMBERS = "０１２３４５６７８９"


def _file_number(square: str, side: str) -> int:
    column = ord(square[0]) - ord("a")
    return 9 - column if side == "red" else column + 1


def _number(value: int, side: str) -> str:
    return CHINESE_NUMBERS[value] if side == "red" else FULLWIDTH_NUMBERS[value]


def _front_order(square: str, side: str) -> int:
    rank = int(square[1])
    return -rank if side == "red" else rank


def chinese_notation(fen_before: str, ucci: str) -> str:
    board = parse_fen(fen_before)
    from_square, to_square = ucci[:2], ucci[2:]
    piece = board.get(from_square)
    if piece is None:
        raise ValueError("起點沒有棋子")
    side = "red" if piece.isupper() else "black"
    names = RED_NAMES if side == "red" else BLACK_NAMES
    piece_name = names[piece]

    same_file = [
        square
        for square, candidate in board.items()
        if candidate == piece and square[0] == from_square[0]
    ]
    if len(same_file) > 1:
        ordered = sorted(same_file, key=lambda square: _front_order(square, side))
        index = ordered.index(from_square)
        if len(ordered) == 2:
            prefix = "前" if index == 0 else "後"
        elif len(ordered) == 3:
            prefix = ("前", "中", "後")[index]
        else:
            prefix = _number(index + 1, side)
        head = f"{prefix}{piece_name}"
    else:
        head = f"{piece_name}{_number(_file_number(from_square, side), side)}"

    from_rank, to_rank = int(from_square[1]), int(to_square[1])
    if from_rank == to_rank:
        return f"{head}平{_number(_file_number(to_square, side), side)}"

    forward = to_rank > from_rank if side == "red" else to_rank < from_rank
    action = "進" if forward else "退"
    if piece.lower() in {"n", "b", "a"}:
        suffix = _number(_file_number(to_square, side), side)
    else:
        suffix = _number(abs(to_rank - from_rank), side)
    return f"{head}{action}{suffix}"

