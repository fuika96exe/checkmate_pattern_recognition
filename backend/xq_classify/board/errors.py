"""The one exception the board raises."""


class BoardError(ValueError):
    """An invalid FEN, move or position.  Messages are user-facing (Traditional Chinese) and kept stable."""
