"""子力歸類: when no named pattern matches, classify the mate by the pieces that deliver it."""

from ..board import attacked_squares, parse_fen
from .geometry import is_attacker_piece, orthogonal_palace_neighbors

_PIECE_NAMES = {'R': '车', 'N': '马', 'C': '炮', 'P': '兵'}
_ALLOWED_CODES = {'R', 'N', 'C', 'P', 'RN', 'RC', 'RP', 'RNC', 'RNP', 'RCP', 'NC', 'NCP', 'NP', 'CP'}


def _escape_controls(board: dict[str, str], king: str, defender: str, attacker: str) -> dict[str, dict]:
    """The attacking pieces that cover each square the general could flee to."""
    king_piece = board[king]
    controls: dict[str, dict] = {}
    for target in orthogonal_palace_neighbors(king, defender):
        occupant = board.get(target)
        if occupant and not is_attacker_piece(occupant, attacker):
            continue
        hypothetical = board.copy()
        hypothetical.pop(king)
        hypothetical[target] = king_piece
        for attack in attacked_squares(hypothetical, attacker).get(target, []):
            square = attack['square']
            piece = hypothetical[square].upper()
            if piece in _PIECE_NAMES:
                entry = controls.setdefault(square, {'square': square, 'piece': piece, 'targets': []})
                entry['targets'].append(target)
    return controls


def classify_mating_material(fen: str, analysis: dict) -> dict | None:
    """Classify actual checking pieces and pieces controlling king escape squares."""
    if not analysis['is_checkmate']:
        return None
    board = parse_fen(fen)
    defender = analysis['side_to_move']
    attacker = 'black' if defender == 'red' else 'red'
    checkers = [
        {'square': item['square'], 'piece': board[item['square']].upper()}
        for item in analysis['checking_pieces']
        if board[item['square']].upper() in _PIECE_NAMES
    ]
    controls = _escape_controls(board, analysis['king_square'], defender, attacker)
    types = {item['piece'] for item in checkers} | {item['piece'] for item in controls.values()}
    code = ''.join(piece for piece in 'RNCP' if piece in types)
    if code not in _ALLOWED_CODES:
        return None
    return {
        'id': code,
        'label_zh': ''.join(_PIECE_NAMES[piece] for piece in code) + ('杀' if len(code) == 1 else ''),
        'checking_pieces': checkers,
        'controlling_pieces': sorted(controls.values(), key=lambda item: item['square']),
    }
