"""Square names and coordinates.

Squares are named file letter + rank digit (``a0`` .. ``i9``): files ``a``-``i``
from Red's left, ranks 0-9 from Red's side.  Coordinates are ``(file index, rank)``.
"""

FILES = 'abcdefghi'


def coords(square: str) -> tuple[int, int]:
    """``'e0'`` -> ``(4, 0)``."""
    return FILES.index(square[0]), int(square[1])


def square_at(x: int, y: int) -> str | None:
    """``(4, 0)`` -> ``'e0'``; ``None`` off the board."""
    if 0 <= x < 9 and 0 <= y <= 9:
        return f'{FILES[x]}{y}'
    return None


def is_red(piece: str) -> bool:
    return piece.isupper()


def inside_palace(x: int, y: int, red: bool) -> bool:
    return 3 <= x <= 5 and ((0 <= y <= 2) if red else (7 <= y <= 9))


def squares_between(a: str, b: str) -> list[str]:
    """Squares strictly between two squares on one file or rank; ``[]`` if they share neither."""
    ax, ay = coords(a)
    bx, by = coords(b)
    if ax != bx and ay != by:
        return []
    dx = (bx > ax) - (bx < ax)
    dy = (by > ay) - (by < ay)
    x, y = ax + dx, ay + dy
    result: list[str] = []
    while (x, y) != (bx, by):
        result.append(f'{FILES[x]}{y}')
        x, y = x + dx, y + dy
    return result
