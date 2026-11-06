"""Identity-based, precision-first midgame rules. No network or engine PV search.

Only this module owns the v2 puzzle contract. The lab's generic workbench recognizer
(tactical_categories.analyze_tactical_categories) is separate and unchanged.

Moved verbatim from the lab's ``backend/app/midgame_tactics.py`` in phase 0 step 5;
only the imports changed. Phase 0 step 6 splits it into a replay context, one
detector per label and the final merge.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import combinations

from .. import board as b
from ..exchange import evaluate_exchange, piece_value
from ..version import MIDGAME_RULES_VERSION

RULES_VERSION = MIDGAME_RULES_VERSION
LABELS = {
    "fork": "捉雙", "discovered_attack": "閃擊", "skewer": "串打",
    "pin": "牽制", "check_fork": "抽將", "trap": "圍困",
    "remove_defender": "消除保護", "overload": "過載", "exchange": "交換",
    "clearance": "消除阻隔",
}
MAIN = frozenset("RNC")
VALUES = {"R": 9, "N": 4, "C": 4, "K": 99999}


def other(side: str) -> str:
    return "black" if side == "red" else "red"


def own(piece: str, side: str) -> bool:
    return bool(piece) and piece.isupper() == (side == "red")


def view(fen: str, side: str) -> str:
    parts = fen.split()
    parts[1] = "w" if side == "red" else "b"
    return " ".join(parts)


def profitable_capture(fen: str, move: str) -> tuple[bool, int | None]:
    """Legal is_capturing_move adapter, including upstream's pawn policy.

    None means inapplicable/illegal, never evidence of an even exchange.
    Signed exchange gains are retained for audit (upstream clamps its output).
    """
    board = b.parse_fen(fen)
    if move not in b.legal_moves(fen):
        return False, None
    src, dst = move[:2], move[2:]
    victim = board.get(dst, "")
    if not victim or victim.upper() == "K":
        return False, None
    red = sum(p in "RNC" for p in board.values())
    black = sum(p in "rnc" for p in board.values())
    endgame = (red <= 2 and black <= 2) or not any(p.upper() == "R" for p in board.values())
    crossed = int(dst[1]) >= 5 if victim.isupper() else int(dst[1]) <= 4
    if victim.upper() == "P" and not crossed and not endgame and board[src].upper() != "P":
        return False, None
    gain = evaluate_exchange(fen, move)
    return gain > 0, gain


class ReplayError(ValueError):
    def __init__(self, message: str, ply: int, fen: str, move: str | None = None):
        super().__init__(message)
        self.ply, self.fen, self.move = ply, fen, move


@dataclass
class Position:
    fen: str
    ids: dict[str, str]
    side: str

    @cached_property
    def board(self):
        return b.parse_fen(self.fen)

    @cached_property
    def squares(self):
        return {identity: square for square, identity in self.ids.items()}

    @cached_property
    def query(self):
        return view(self.fen, self.side)

    def ref(self, identity: str):
        square = self.squares.get(identity)
        return {"id": identity, "square": square, "piece": self.board.get(square, "")}

    @cached_property
    def captures(self):
        """All ordinary legal captures; local losses include minor pieces."""
        result = {}
        for move in sorted(b.legal_moves(self.query)):
            src, dst = move[:2], move[2:]
            victim = self.board.get(dst, "")
            if not victim or own(victim, self.side) or victim.upper() == "K":
                continue
            ok, gain = profitable_capture(self.query, move)
            relation = {"actor": self.ref(self.ids[src]), "target": self.ref(self.ids[dst]),
                        "ucci": move, "gain": gain, "profitable": ok, "check": False,
                        "fen": self.query}
            result.setdefault(self.ids[dst], []).append(relation)
        return result

    @cached_property
    def hits(self):
        """Major targets and actual checking sources, separately from capture values."""
        result = {t: list(rows) for t, rows in self.captures.items()
                  if rows[0]["target"]["piece"].upper() in MAIN}
        # A check is an actual attack on the general, never an exchange input.
        king = next((s for s, p in self.board.items() if p == ("k" if self.side == "red" else "K")), None)
        if king:
            for source, piece in sorted(self.board.items()):
                if not own(piece, self.side) or king not in b.pseudo_legal_targets(self.board, source, piece):
                    continue
                # Occupancy-only safety check; never send a missing-king FEN to pyffish.
                trial = dict(self.board)
                trial[king] = trial.pop(source)
                own_king = next(s for s, p in trial.items() if p == ("K" if self.side == "red" else "k"))
                if b.is_square_attacked(trial, own_king, self.side != "red"):
                    continue
                result.setdefault(self.ids[king], []).append({
                    "actor": self.ref(self.ids[source]), "target": self.ref(self.ids[king]),
                    "ucci": None, "gain": None, "profitable": False, "check": True,
                })
        return result

    @cached_property
    def threats(self):
        return {t: [r for r in rows if r["profitable"] or r["check"]]
                for t, rows in self.hits.items() if any(r["profitable"] or r["check"] for r in rows)}

    @cached_property
    def guards(self):
        """(attacker ID,target ID) -> guard ID -> legal recapture evidence."""
        result = {}
        for target, relations in self.hits.items():
            for r in relations:
                if r["check"]:
                    continue
                child = b.apply_move(self.query, r["ucci"])
                guards = {}
                for reply in sorted(b.legal_moves(child)):
                    if reply[2:] == r["target"]["square"]:
                        identity = self.ids[reply[:2]]
                        guards[identity] = {"guard": self.ref(identity), "capture": r["ucci"], "recapture": reply}
                result[(r["actor"]["id"], target)] = guards
        return result

    def relation(self, actor, target):
        return next((r for r in self.hits.get(target, []) if r["actor"]["id"] == actor), None)

    @cached_property
    def checked(self):
        king = next(s for s, p in self.board.items() if p == ("k" if self.side == "red" else "K"))
        return b.is_square_attacked(self.board, king, self.side == "red")

    @cached_property
    def pins(self):
        return _pin_relations(self)


@dataclass(frozen=True)
class Event:
    ply: int
    side: str
    move: str
    actor: str
    victim: str | None
    victim_kind: str

    @property
    def dst(self):
        return self.move[2:]


def replay(fen: str, blunder: str, pv: list[str], solver: str):
    try:
        board = b.parse_fen(fen)
        if list(board.values()).count("K") != 1 or list(board.values()).count("k") != 1:
            raise ValueError("FEN requires exactly one general per side")
        if not isinstance(pv, list) or not pv or not all(isinstance(m, str) for m in pv):
            raise ValueError("PV must be a nonempty UCCI string list")
        if solver not in {"red", "black"}:
            raise ValueError("first_turn must normalize to red or black")
        ids = b.build_piece_identity(fen)
    except (ValueError, TypeError) as error:
        raise ReplayError(str(error), 0, fen) from error
    positions = [Position(fen, ids, solver)]
    events = []
    for ply, move in enumerate([blunder, *pv], 1):
        before = positions[-1]
        try:
            if not isinstance(move, str) or not b.UCCI_RE.fullmatch(move) or move not in b.legal_moves(before.fen):
                raise ValueError(f"Illegal UCCI move: {move}")
            src, dst = move[:2], move[2:]
            if before.board.get(dst, "").upper() == "K":
                raise ValueError("PV cannot capture a general")
            after = b.apply_move(before.fen, move)
            if ply == 1 and b.side_to_move(after) != solver:
                raise ValueError(f"first_turn mismatch: expected {b.side_to_move(after)}, got {solver}")
            events.append(Event(ply, b.side_to_move(before.fen), move, before.ids[src],
                                before.ids.get(dst), before.board.get(dst, "").upper()))
            positions.append(Position(after, b.move_piece_identity(before.ids, src, dst), solver))
        except (ValueError, TypeError) as error:
            raise ReplayError(str(error), ply, before.fen, move) from error
    return positions, events


def material_result(initial: str, final: str, solver: str):
    def balance(fen):
        return sum(VALUES.get(p.upper(), 0) * (1 if own(p, solver) else -1)
                   for p in b.parse_fen(fen).values() if p.upper() in MAIN)
    start, end = balance(initial), balance(final)
    return {"kind": "gain" if end - start >= 4 else "no_gain",
            "start": start, "end": end, "delta": end - start}


def opened_by(before: Position, after: Position, actor: str, target: str, vacated: str):
    """The vacated source must be a necessary blocker, using occupancy only."""
    src, dst = after.squares[actor], after.squares[target]
    piece = after.board[src]
    if src != before.squares.get(actor) or dst != before.squares.get(target):
        return False
    if dst in b.pseudo_legal_targets(before.board, src, piece):
        return False
    trial = dict(after.board)
    trial[vacated] = before.board[vacated]
    return dst not in b.pseudo_legal_targets(trial, src, piece)


def ray_relations(pos: Position):
    """Geometric front/rear/screen candidates; legal checks happen separately."""
    result = {}
    for src, piece in sorted(pos.board.items()):
        if not own(piece, pos.side) or piece.upper() not in {"R", "C"}:
            continue
        x, y = b.coords(src)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            occupied = []
            cx, cy = x + dx, y + dy
            while (square := b.square_at(cx, cy)) is not None:
                if square in pos.board:
                    occupied.append(square)
                cx, cy = cx + dx, cy + dy
            offset = int(piece.upper() == "C")
            if len(occupied) < offset + 2:
                continue
            front, rear = occupied[offset:offset + 2]
            if any(own(pos.board[s], pos.side) or pos.board[s].upper() not in VALUES for s in (front, rear)):
                continue
            key = (pos.ids[src], pos.ids[front], pos.ids[rear], dx, dy)
            result[key] = {"actor": pos.ref(pos.ids[src]), "front": pos.ref(pos.ids[front]),
                           "rear": pos.ref(pos.ids[rear]),
                           "screen": pos.ref(pos.ids[occupied[0]]) if offset else None,
                           "direction": [dx, dy]}
    return result


def exposed_relation(pos: Position, actor: str, front: str, rear: str):
    """Occupancy-only removal, never a missing-general FEN."""
    trial = dict(pos.board)
    trial.pop(pos.squares[front])
    src, dst = pos.squares[actor], pos.squares[rear]
    if dst not in b.pseudo_legal_targets(trial, src, trial[src]):
        return False
    trial[dst] = trial.pop(src)
    king = next((s for s, p in trial.items() if p == ("K" if pos.side == "red" else "k")), None)
    return bool(king and not b.is_square_attacked(trial, king, pos.side != "red"))


def verified_hits(pos: Position, reply: Position | None = None, excluded=frozenset()):
    """A pending check cannot subsidize a hypothetical second consecutive move."""
    result = {}
    for target, relations in pos.hits.items():
        for relation in relations:
            actor = relation["actor"]["id"]
            if actor in excluded:
                continue
            if relation["check"] or not pos.checked:
                result.setdefault(target, []).append(relation)
            elif reply is not None:
                confirmed = reply.relation(actor, target)
                if confirmed:
                    result.setdefault(target, []).append({**confirmed, "triggerAttack": relation})
    return result


def threats_from(hits):
    return {t: [r for r in rows if r["profitable"] or r["check"]]
            for t, rows in hits.items() if any(r["profitable"] or r["check"] for r in rows)}


def skewer_confirmation(pos: Position, actor: str, front: str, rear: str, front_attack=None):
    # A front piece that can take the attacker immediately breaks the skewer.
    if pos.squares[front] + pos.squares[actor] in b.legal_moves(view(pos.fen, other(pos.side))):
        return None
    relation = front_attack or pos.relation(actor, front)
    if not relation or not (relation["profitable"] or relation["check"]):
        return None
    for move in sorted(b.legal_moves(view(pos.fen, other(pos.side)))):
        if move[:2] != pos.squares[front] or move[2:] in {pos.squares[actor], pos.squares[rear]}:
            continue
        ids = b.move_piece_identity(pos.ids, move[:2], move[2:])
        child = Position(b.apply_move(view(pos.fen, other(pos.side)), move), ids, pos.side)
        rear_attack = child.relation(actor, rear)
        if rear_attack and rear_attack["profitable"]:
            return {"frontAttack": relation, "escape": move, "fen": child.fen, "rearAttack": rear_attack}
    return None


def _pin_relations(pos: Position):
    result = {}
    for src, piece in sorted(pos.board.items()):
        if not own(piece, pos.side) or piece.upper() not in {"R", "C"}:
            continue
        x, y = b.coords(src)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            occupied = []
            cx, cy = x + dx, y + dy
            while (square := b.square_at(cx, cy)) is not None:
                if square in pos.board:
                    occupied.append(square)
                cx, cy = cx + dx, cy + dy
            # Absolute cannon pins: either of the two blockers may be pinned.
            king_index = next((i for i, sq in enumerate(occupied)
                               if pos.board[sq] == ("k" if pos.side == "red" else "K")), None)
            required = 2 if piece.upper() == "C" else 1
            if king_index == required:
                rear = occupied[king_index]
                for front in occupied[:king_index]:
                    if own(pos.board[front], pos.side):
                        continue
                    actor, guard, target = pos.ids[src], pos.ids[front], pos.ids[rear]
                    if not exposed_relation(pos, actor, guard, target):
                        continue
                    screen = next((sq for sq in occupied[:king_index] if sq != front), None)
                    result[(actor, guard, target, "ray")] = {
                        "actor": pos.ref(actor), "front": pos.ref(guard), "rear": pos.ref(target),
                        "screen": pos.ref(pos.ids[screen]) if screen else None,
                        "kind": "ray", "absolute": True,
                    }
            offset = int(piece.upper() == "C")
            if len(occupied) < offset + 2:
                continue
            front, rear = occupied[offset:offset + 2]
            fp, rp = pos.board[front], pos.board[rear]
            if (own(fp, pos.side) or own(rp, pos.side) or fp.upper() not in "RNCBAP" or
                    rp.upper() not in MAIN or piece_value(rp, rear) <= piece_value(fp, front)):
                continue
            actor, guard, target = pos.ids[src], pos.ids[front], pos.ids[rear]
            if exposed_relation(pos, actor, guard, target) and profitable_after_removal(pos, actor, guard, target):
                result[(actor, guard, target, "ray")] = {
                    "actor": pos.ref(actor), "front": pos.ref(guard), "rear": pos.ref(target),
                    "screen": pos.ref(pos.ids[occupied[0]]) if offset else None,
                    "kind": "ray", "absolute": False,
                }
    for src, piece in pos.board.items():
        if not own(piece, pos.side) or piece.upper() != "N":
            continue
        sx, sy = b.coords(src)
        for dst, victim in pos.board.items():
            if own(victim, pos.side) or victim.upper() not in VALUES:
                continue
            tx, ty = b.coords(dst)
            dx, dy = tx - sx, ty - sy
            if sorted((abs(dx), abs(dy))) != [1, 2]:
                continue
            leg = b.square_at(sx + (dx // 2 if abs(dx) == 2 else 0), sy + (dy // 2 if abs(dy) == 2 else 0))
            blocker = pos.board.get(leg, "")
            if not blocker or own(blocker, pos.side) or blocker.upper() == "K":
                continue
            actor, front, rear = pos.ids[src], pos.ids[leg], pos.ids[dst]
            if exposed_relation(pos, actor, front, rear) and (victim.upper() == "K" or profitable_after_removal(pos, actor, front, rear)):
                result[(actor, front, rear, "horse_leg")] = {
                    "actor": pos.ref(actor), "front": pos.ref(front), "rear": pos.ref(rear),
                    "kind": "horse_leg", "absolute": victim.upper() == "K",
                    "review": False,
                }
    # An opposing eye blocker can restrict a rook just as a horse leg does.
    for src, piece in pos.board.items():
        if not own(piece, pos.side) or piece.upper() != "B":
            continue
        sx, sy = b.coords(src)
        for dst, victim in pos.board.items():
            if own(victim, pos.side) or victim.upper() not in MAIN:
                continue
            tx, ty = b.coords(dst)
            if abs(tx - sx) != 2 or abs(ty - sy) != 2:
                continue
            eye = b.square_at((sx + tx) // 2, (sy + ty) // 2)
            if eye not in pos.board or own(pos.board[eye], pos.side) or pos.board[eye].upper() == "K":
                continue
            actor, front, rear = pos.ids[src], pos.ids[eye], pos.ids[dst]
            if exposed_relation(pos, actor, front, rear) and profitable_after_removal(pos, actor, front, rear):
                result[(actor, front, rear, "elephant_eye")] = {
                    "actor": pos.ref(actor), "front": pos.ref(front), "rear": pos.ref(rear),
                    "kind": "elephant_eye", "absolute": False, "review": False}
    kings = [s for s, p in pos.board.items() if p.upper() == "K"]
    if len(kings) == 2 and kings[0][0] == kings[1][0]:
        occupied = [s for s in b.squares_between(*kings) if s in pos.board]
        if len(occupied) == 1 and not own(pos.board[occupied[0]], pos.side):
            front = occupied[0]
            actor = next(s for s in kings if own(pos.board[s], pos.side))
            rear = next(s for s in kings if s != actor)
            result[(pos.ids[actor], pos.ids[front], pos.ids[rear], "flying_general")] = {
                "actor": pos.ref(pos.ids[actor]), "front": pos.ref(pos.ids[front]),
                "rear": pos.ref(pos.ids[rear]), "kind": "flying_general", "absolute": True,
            }
    return result


def pin_relations(pos: Position):
    return pos.pins


def without_pieces(pos: Position, identities):
    """Counterfactual proof only. Both generals must remain; never a PV frame."""
    board, ids = dict(pos.board), dict(pos.ids)
    for identity in identities:
        square = pos.squares.get(identity)
        if square:
            if board[square].upper() == "K":
                return None
            board.pop(square)
            ids.pop(square)
    parts = pos.fen.split()
    parts[0] = b.board_to_fen(board)
    return Position(" ".join(parts), ids, pos.side)


def profitable_after_removal(pos: Position, actor: str, front: str, rear: str):
    trial = without_pieces(pos, {front})
    if not trial:
        return None
    relation = trial.relation(actor, rear)
    return relation if relation and relation["profitable"] else None


def front_can_trade_pinner(pos: Position, relation):
    actor, front = relation["actor"]["id"], relation["front"]["id"]
    if actor not in pos.squares or front not in pos.squares:
        return False
    fen = view(pos.fen, other(pos.side))
    move = pos.squares[front] + pos.squares[actor]
    return move in b.legal_moves(fen) and evaluate_exchange(fen, move) >= 0


def escape_assessment(pos: Position, target: str, move: str):
    defender_fen = view(pos.fen, other(pos.side))
    child = Position(b.apply_move(defender_fen, move),
                     b.move_piece_identity(pos.ids, move[:2], move[2:]), pos.side)
    victim = pos.board.get(move[2:], "")
    credit = piece_value(victim, move[2:]) if victim else 0
    direct = [r for r in child.captures.get(target, []) if r["profitable"]]
    if direct:
        return {"escape": move, "fen": child.fen, "safe": False, "reason": "direct_loss",
                "capture": max(direct, key=lambda r: r["gain"]), "captureCredit": credit}
    baseline = max((r["gain"] for r in pos.captures.get(target, []) if r["profitable"]), default=0)
    owner = other(pos.side)
    old_counters = Position(pos.fen, pos.ids, owner).captures
    newly_exposed = {identity for identity, rows in child.captures.items()
                     if max((r["gain"] for r in rows if r["profitable"]), default=0) >
                     max((r["gain"] for r in pos.captures.get(identity, []) if r["profitable"]), default=0)}
    for identity, rows in child.captures.items():
        if identity == target or any(r["profitable"] for r in pos.captures.get(identity, [])):
            continue
        for attack in rows:
            if not attack["profitable"] or attack["gain"] <= baseline:
                continue
            realized = Position(b.apply_move(child.query, attack["ucci"]),
                                b.move_piece_identity(child.ids, attack["ucci"][:2], attack["ucci"][2:]), owner)
            compensation = 0
            for counter_target, counters in realized.captures.items():
                prior = max((r["gain"] for r in old_counters.get(counter_target, []) if r["profitable"]), default=0)
                for counter in counters:
                    if (counter["profitable"] and counter["actor"]["id"] not in newly_exposed
                            and counter["target"]["square"] != attack["target"]["square"]
                            and counter["gain"] > prior):
                        compensation = max(compensation, counter["gain"])
            recovered = max(0, piece_value(attack["target"]["piece"], attack["target"]["square"]) - attack["gain"])
            net = attack["gain"] - max(0, compensation - recovered) - credit
            if net > baseline:
                return {"escape": move, "fen": child.fen, "safe": False, "reason": "indirect_loss",
                        "capture": attack, "previousLoss": 0, "netLoss": net,
                        "originalLoss": baseline, "captureCredit": credit}
    return {"escape": move, "fen": child.fen, "safe": True, "captureCredit": credit}

def trap_state(pos: Position, target: str, excluded=frozenset()):
    initial = [r for r in pos.threats.get(target, []) if r["profitable"] and r["actor"]["id"] not in excluded]
    if not initial or pos.checked:
        return None
    escapes = []
    for move in sorted(b.legal_moves(view(pos.fen, other(pos.side)))):
        if move[:2] != pos.squares[target]:
            continue
        assessment = escape_assessment(pos, target, move)
        if assessment["safe"]:
            return None
        escapes.append(assessment)
    return {"initialAttack": initial[0], "escapes": escapes}


def functional_pin_capture(relation, positions, events, start_ply):
    """Minor pins need an actual profitable major capture enabled by the pin."""
    guard, pinner = relation["front"]["id"], relation["actor"]["id"]
    key = (pinner, guard, relation["rear"]["id"], relation["kind"])
    for capture in events[start_ply - 1:]:
        if capture.side != positions[0].side or capture.victim_kind not in MAIN:
            continue
        pre, post = positions[capture.ply - 1:capture.ply + 1]
        if key not in pre.pins or any(key not in pos.pins for pos in positions[start_ply:capture.ply]):
            continue
        if capture.victim == guard:
            gain = evaluate_exchange(pre.fen, capture.move)
            if gain > 0:
                return {"guard": pre.ref(guard), "defendedTarget": pre.ref(guard),
                        "capturePly": capture.ply, "capture": capture.move, "gain": gain,
                        "mode": "pinned_piece_captured"}
        if guard not in pre.squares or pinner not in pre.squares or pinner == capture.actor:
            continue
        gain = evaluate_exchange(pre.fen, capture.move)
        if gain <= 0:
            continue
        gs = post.squares.get(guard)
        if not gs:
            continue
        reply = gs + capture.dst
        if capture.dst not in b.pseudo_legal_targets(post.board, gs, post.board[gs]) or reply in b.legal_moves(post.fen):
            continue
        released_post, released_pre = without_pieces(post, [pinner]), without_pieces(pre, [pinner])
        if not released_post or not released_pre or reply not in b.legal_moves(released_post.fen):
            continue
        if capture.move not in b.legal_moves(released_pre.fen):
            continue
        without_gain = evaluate_exchange(released_pre.fen, capture.move)
        if without_gain > 0:
            continue
        return {"guard": pre.ref(guard), "defendedTarget": pre.ref(capture.victim),
                "capturePly": capture.ply, "capture": capture.move, "captureFen": pre.fen,
                "gain": gain, "preventedRecapture": reply, "afterCaptureFen": post.fen,
                "releasedFen": released_post.fen, "gainWithoutPin": without_gain}
    return None


def absolute_pin_sacrifice(relation, positions, events, start_ply):
    """The pinned piece captures its pinner and is then captured at a net loss."""
    guard, pinner = relation["front"]["id"], relation["actor"]["id"]
    key = (pinner, guard, relation["rear"]["id"], relation["kind"])
    for event in events[start_ply:]:
        if event.actor != guard or event.victim != pinner or key not in positions[event.ply - 1].pins:
            continue
        gain = -evaluate_exchange(positions[event.ply - 1].fen, event.move)
        if gain <= 0:
            continue
        realized = next((e for e in events[event.ply:] if e.actor in positions[e.ply - 1].squares
                         and e.side == positions[0].side and e.victim == guard), None)
        if realized:
            return {"guard": positions[event.ply - 1].ref(guard), "defendedTarget": positions[event.ply - 1].ref(guard),
                    "capturePly": realized.ply, "capture": realized.move, "gain": gain,
                    "mode": "pinner_sacrifice", "response": event.move}
    return None


def relative_pin_front_capture(relation, positions, events, start_ply):
    """The defender saves the rear piece, then the pinned front is won."""
    if relation.get("absolute"):
        return None
    pinner, guard, rear = (relation[name]["id"] for name in ("actor", "front", "rear"))
    key = (pinner, guard, rear, relation["kind"])
    for capture in events[start_ply - 1:]:
        if capture.side != positions[0].side or capture.victim != guard:
            continue
        history = events[start_ply - 1:capture.ply - 1]
        departure = next((e for e in history if e.actor == rear and e.side != positions[0].side), None)
        if not departure or key not in positions[departure.ply - 1].pins:
            continue
        if any(positions[i].squares.get(guard) != positions[start_ply].squares.get(guard) or
               positions[i].squares.get(pinner) != positions[start_ply].squares.get(pinner)
               for i in range(start_ply, capture.ply)):
            continue
        gain = evaluate_exchange(positions[capture.ply - 1].fen, capture.move)
        if gain > 0:
            return {"guard": positions[start_ply].ref(guard), "defendedTarget": positions[start_ply].ref(guard),
                    "capturePly": capture.ply, "capture": capture.move, "gain": gain,
                    "mode": "rear_evades_front_captured", "response": departure.move}
    return None


def pinned_front_won(relation, positions, events, start_ply):
    """v2.6: the pinned front never moves again and is later won outright.

    Experts call this 借牽制得子 even when the defender first interposes or
    reinforces, so the relation itself need not survive until the capture.
    """
    pinner, guard = relation["actor"]["id"], relation["front"]["id"]
    if relation["front"]["piece"].upper() not in MAIN:
        return None
    home = positions[start_ply].squares.get(guard)
    for capture in events[start_ply:]:
        if capture.actor == guard:
            return None
        if capture.side != positions[0].side or capture.victim != guard:
            continue
        if positions[capture.ply - 1].squares.get(guard) != home:
            return None
        gain = evaluate_exchange(positions[capture.ply - 1].fen, capture.move)
        if gain > 0:
            return {"guard": positions[start_ply].ref(guard), "defendedTarget": positions[start_ply].ref(guard),
                    "capturePly": capture.ply, "capture": capture.move, "gain": gain,
                    "mode": "pinned_front_won", "pinner": positions[start_ply].ref(pinner)}
        return None
    return None


def guard_line_squares(pos: Position, guard: str, target: str) -> set[str]:
    """Squares whose occupancy decides whether `guard` can recapture on `target`:
    the rook/cannon line between them, a horse leg, or an elephant eye."""
    gs, ts = pos.squares.get(guard), pos.squares.get(target)
    if not gs or not ts:
        return set()
    kind = pos.board[gs].upper()
    if kind in {"R", "C"}:
        return set(b.squares_between(gs, ts))
    gx, gy = b.coords(gs)
    tx, ty = b.coords(ts)
    dx, dy = tx - gx, ty - gy
    if kind == "N" and sorted((abs(dx), abs(dy))) == [1, 2]:
        leg = b.square_at(gx + (dx // 2 if abs(dx) == 2 else 0), gy + (dy // 2 if abs(dy) == 2 else 0))
        return {leg} if leg else set()
    if kind == "B" and abs(dx) == 2 and abs(dy) == 2:
        eye = b.square_at(gx + dx // 2, gy + dy // 2)
        return {eye} if eye else set()
    return set()


def checking_interception(before: Position, release: Position, move: str, guard: str, actor: str, target: str) -> bool:
    """v3.1 (ruling E1): `move` checks and, in the same move, blocks the
    guard's recapture line (rook/cannon line, horse leg, elephant eye) or
    removes its cannon screen. Guard, attacker and target stay put through
    the forced reply, so the reply did not restore or cause the loss."""
    if any(before.squares.get(x) is None or before.squares.get(x) != release.squares.get(x)
           for x in (guard, actor, target)):
        return False
    line = guard_line_squares(before, guard, target)
    return move[:2] in line or move[2:4] in line


def illegal_recapture_pin(positions, events, capture):
    """v2.6: a profitable capture whose natural recapture is illegal only
    because the recapturing piece is pinned to its own general (including the
    facing-generals rule). Returns (pinner, guard, king, proof) or None."""
    solver = positions[0].side
    pre, post = positions[capture.ply - 1:capture.ply + 1]
    gain = evaluate_exchange(pre.fen, capture.move)
    if gain <= 0 or piece_value(pre.board[capture.move[:2]], capture.move[:2]) < VALUES[capture.victim_kind]:
        return None
    legal = set(b.legal_moves(post.fen))
    enemy_king = next((s for s, p in post.board.items() if p == ("k" if solver == "red" else "K")), None)
    own_king = next((s for s, p in post.board.items() if p == ("K" if solver == "red" else "k")), None)
    if not enemy_king or not own_king:
        return None
    for square, piece in sorted(post.board.items()):
        if own(piece, solver) or piece.upper() == "K":
            continue
        if capture.dst not in b.pseudo_legal_targets(post.board, square, piece) or square + capture.dst in legal:
            continue
        trial = dict(post.board)
        trial[capture.dst] = trial.pop(square)
        pinner = None
        if enemy_king[0] == own_king[0] and not any(s in trial for s in b.squares_between(enemy_king, own_king)):
            pinner = post.ids[own_king]
        else:
            for src, attacker in sorted(trial.items()):
                if own(attacker, solver) and src != capture.dst and enemy_king in b.pseudo_legal_targets(trial, src, attacker):
                    pinner = post.ids[src]
                    break
        if pinner:
            return pinner, post.ids[square], post.ids[enemy_king], {
                "guard": post.ref(post.ids[square]), "defendedTarget": pre.ref(capture.victim),
                "capturePly": capture.ply, "capture": capture.move, "gain": gain,
                "preventedRecapture": square + capture.dst, "mode": "illegal_recapture"}
    return None


def relative_recapture_pin(positions, events, capture):
    """v2.8 (expert, Lb3VlR): the natural recapture is legal, but the
    recapturing piece is the front of a pin, so recapturing lets another
    player piece win the more valuable rear piece. Returns
    (pinner, guard, rear, proof) or None."""
    solver = positions[0].side
    pre, post = positions[capture.ply - 1:capture.ply + 1]
    capturer_value = piece_value(pre.board[capture.move[:2]], capture.move[:2])
    nxt = events[capture.ply] if capture.ply < len(events) else None
    legal = set(b.legal_moves(post.fen))
    for key, relation in sorted(post.pins.items()):
        pinner, guard, rear = key[:3]
        if relation.get("absolute") or pinner == capture.actor or guard not in post.squares:
            continue
        reply = post.squares[guard] + capture.dst
        if reply not in legal or (nxt and nxt.move == reply):
            continue
        rear_square = post.squares.get(rear)
        if not rear_square or piece_value(post.board[rear_square], rear_square) <= capturer_value:
            continue
        child = Position(b.apply_move(post.fen, reply), b.move_piece_identity(post.ids, reply[:2], reply[2:]), solver)
        punish = child.relation(pinner, rear)
        if not punish or not punish["profitable"]:
            continue
        return pinner, guard, rear, {
            "guard": post.ref(guard), "defendedTarget": pre.ref(capture.victim), "capturePly": capture.ply,
            "capture": capture.move, "gain": evaluate_exchange(pre.fen, capture.move),
            "deterredRecapture": reply, "punishment": punish["ucci"], "punishmentGain": punish["gain"],
            "mode": "recapture_costs_rear"}
    return None


def fork_defences(pos: Position, actor: str, pair):
    """Only a legal non-losing immediate capture of the attacker refutes a fork.

    v2.9 (expert, R20g7j): a capture by the front piece of a pin does not
    count when the pinned rear piece is worth more than the attacker, because
    leaving the line loses that piece."""
    fen = view(pos.fen, other(pos.side))
    square = pos.squares[actor]
    attacker_value = piece_value(pos.board[square], square)
    pinned = {}
    for (_, front, rear, _), relation in pos.pins.items():
        rear_square = pos.squares.get(rear)
        if rear_square and piece_value(pos.board[rear_square], rear_square) > attacker_value:
            pinned[front] = relation
    for move in b.legal_moves(fen):
        if move[2:] == square and pos.ids.get(move[:2]) not in pinned and evaluate_exchange(fen, move) >= 0:
            return move
    return None


def finalize_labels(plies, material):
    """Keep supporting proof separately so suppressed parent keys remain usable."""
    raw = {o["id"] for ply in plies for o in ply["occurrences"]}
    suppressed = {}
    if material["kind"] == "gain":
        if raw - {"exchange"}:
            suppressed["exchange"] = "gain_has_other_tactic"
    support = []
    for ply in plies:
        visible = []
        for occurrence in ply["occurrences"]:
            if occurrence["id"] in suppressed:
                support.append({**occurrence, "suppressedBy": suppressed[occurrence["id"]]})
            else:
                visible.append(occurrence)
        ply["occurrences"] = visible
    tactics = [label for label in LABELS if label in raw and label not in suppressed]
    return tactics, support


def analyze_midgame(fen: str, blunder: str, pv: list[str], solver: str):
    positions, events = replay(fen, blunder, pv, solver)
    plies = [{"ply": e.ply, "ucci": e.move, "solver": e.ply >= 2 and e.side == solver,
              "occurrences": []} for e in events]
    reviews = []

    def review(label, ply, reason, evidence):
        reviews.append({"label": label, "ply": ply, "fen": positions[ply].fen,
                        "reason": reason, "evidence": evidence})

    def emit(label, ply, confirmed, actors, targets, kind, evidence):
        key = f"{label}:{ply}:{len(plies[ply - 1]['occurrences'])}"
        pos = positions[ply]
        def reference(identity):
            for snapshot in reversed(positions[:ply + 1]):
                if identity in snapshot.squares:
                    return snapshot.ref(identity)
            # A future participant in an exchange still existed initially.
            return positions[0].ref(identity)
        actors, targets = list(dict.fromkeys(actors)), list(dict.fromkeys(targets))
        refs = [reference(i) for i in dict.fromkeys([*actors, *targets])]
        occurrence = {"id": label, "label_zh": LABELS[label],
                      "squares": list(dict.fromkeys(r["square"] for r in refs if r["square"])),
                      "detail": f"{LABELS[label]}：第 {ply} 手觸發，第 {confirmed} 手確認；" +
                                "、".join(f"{r['id']}@{r['square']}" for r in refs),
                      "evidence": {"key": key, "triggerPly": ply, "confirmedPly": confirmed,
                                   "actors": [reference(i) for i in actors], "targets": [reference(i) for i in targets],
                                   "relationKind": kind, **evidence}}
        plies[ply - 1]["occurrences"].append(occurrence)
        return occurrence

    for event in events[1:]:
        if event.side != solver:
            continue
        p = event.ply
        before, after = positions[p - 1:p + 1]
        response = events[p] if p < len(events) else None
        reply = positions[p + 1] if response else None
        excluded = set()
        if response and response.victim == event.actor and evaluate_exchange(before.fen, event.move) <= 0:
            excluded.add(event.actor)
            review("threat", p, "nonpositive_mover_recaptured_next_ply", {
                "actor": before.ref(event.actor), "move": event.move,
                "gain": evaluate_exchange(before.fen, event.move), "response": response.move,
                "responsePly": response.ply})
        hits = verified_hits(after, reply, excluded)
        threats = threats_from(hits)
        if after.checked and reply is None:
            review("check_fork", p, "missing_actual_check_response", {})
        # Forks have their own immediate-capture test. A losing capture of the
        # attacker must not be rejected by the general PV recapture filter.
        fork_threats = threats_from(after.hits)
        for actor in {r["actor"]["id"] for rows in fork_threats.values() for r in rows}:
            targets = sorted(t for t, rows in fork_threats.items() if any(
                r["actor"]["id"] == actor and (r["profitable"] or r["check"]) for r in rows))
            for pair in combinations(targets, 2):
                def existed(target):
                    if actor not in before.squares or target not in before.squares:
                        return False
                    src, dst = before.squares[actor], before.squares[target]
                    old = before.relation(actor, target)
                    return bool(old and (old["profitable"] or old["check"])) or (b.position_analysis(before.query)["is_check"] and
                        dst in b.pseudo_legal_targets(before.board, src, before.board[src]))
                if all(existed(t) for t in pair):
                    continue
                # v2.6: a new check alone does not make a fork; the non-king
                # target must also be newly attacked by this move.
                if any(after.board.get(after.squares[t], "").upper() == "K" for t in pair) and any(
                        existed(t) for t in pair if after.board.get(after.squares[t], "").upper() != "K"):
                    review("fork", p, "check_with_preexisting_attack", {"actor": after.ref(actor)})
                    continue
                defence = fork_defences(after, actor, pair)
                if defence:
                    review("fork", p, "defensible", {"reply": defence, "actor": after.ref(actor)})
                    continue
                # v2.8 (expert, R18wlL): while the opponent is in check, a
                # non-king target is confirmed only in the position after the
                # actual reply, like every other label (no free second move).
                # Applies to forks of two non-king targets made while another
                # check is pending; check forks are judged by ruling D3.
                if after.checked and reply is not None and not any(
                        after.board.get(after.squares[t], "").upper() == "K" for t in pair) and any(
                        not (reply.relation(actor, t) or {}).get("profitable") for t in pair):
                    review("fork", p, "target_not_confirmed_after_check", {"actor": after.ref(actor)})
                    continue
                attacks = [next(r for r in fork_threats[t] if r["actor"]["id"] == actor and (r["profitable"] or r["check"])) for t in pair]
                emit("fork", p, p, [actor], list(pair), "new_target_pair",
                     {"attacks": attacks, "response": response.move if after.checked and response else None})
        # A cannon check through a friendly screen, where the screen itself
        # newly attacks another piece. v2.9 (expert, RPx5jO): either the
        # checking cannon or its screen may be the piece that just moved.
        if after.checked:
            for king, rows in fork_threats.items():
                for check in rows:
                    cannon = check["actor"]["id"]
                    if not check["check"] or after.board.get(after.squares.get(cannon, ""), "").upper() != "C":
                        continue
                    king_sq = after.squares[king]
                    between = [sq for sq in b.squares_between(after.squares[cannon], king_sq) if sq in after.board]
                    if len(between) != 1 or not own(after.board[between[0]], solver):
                        continue
                    screen = after.ids[between[0]]
                    if event.actor not in {cannon, screen}:
                        continue
                    for target, attacks in fork_threats.items():
                        for attack in attacks:
                            if attack["actor"]["id"] != screen or not attack["profitable"]:
                                continue
                            old = before.relation(screen, target) if screen in before.squares and target in before.squares else None
                            if old and old["profitable"]:
                                continue
                            defence = fork_defences(after, cannon, (king, target)) or fork_defences(after, screen, (king, target))
                            if defence:
                                continue
                            emit("fork", p, p, [cannon, screen], [king, target],
                                 "friendly_cannon_screen_check", {"attacks": [check, attack],
                                 "screen": after.ref(screen)})
        for target, relations in hits.items():
            for relation in relations:
                actor = relation["actor"]["id"]
                if actor == event.actor or before.relation(actor, target):
                    continue
                if opened_by(before, after, actor, target, event.move[:2]):
                    # v2.7 (expert ruling D1): the revealed attack must be a
                    # real check or a capture with exchange value > 0. An even
                    # trade offer still counts when the same move gives check,
                    # because the opponent must answer the check first.
                    if not (relation["check"] or relation["profitable"] or after.checked):
                        review("discovered_attack", p, "revealed_attack_not_profitable",
                               {"attack": relation, "vacated": event.move[:2]})
                        continue
                    emit("discovered_attack", p, p + int(after.checked and not relation["check"]),
                         [event.actor, actor], [target], "vacated_blocker",
                         {"vacated": event.move[:2], "attack": relation, "beforeFen": before.fen})
        # v2.8 (expert, o7PaGq): with a pending check, a revealed attack whose
        # target escapes by answering the check (e.g. capturing the checker)
        # still counts when the player then wins that piece on its new square.
        if after.checked and reply is not None and response.actor in after.squares:
            target = response.actor
            for relation in after.hits.get(target, []):
                actor = relation["actor"]["id"]
                if (relation["check"] or actor == event.actor or before.relation(actor, target) or
                        any(r["actor"]["id"] == actor for r in hits.get(target, [])) or
                        not opened_by(before, after, actor, target, event.move[:2])):
                    continue
                follow = events[p + 1] if p + 1 < len(events) else None
                if (follow and follow.victim == target and
                        evaluate_exchange(positions[p + 1].fen, follow.move) > 0):
                    emit("discovered_attack", p, follow.ply, [event.actor, actor], [target], "vacated_blocker",
                         {"vacated": event.move[:2], "attack": relation, "beforeFen": before.fen,
                          "escapedBy": response.move, "wonOn": follow.move})
        old_rays = ray_relations(before)
        for key, line in ray_relations(after).items():
            actor, front, rear = key[:3]
            if (key in old_rays or actor in excluded or (response and response.victim == actor) or
                    VALUES[line["front"]["piece"].upper()] < VALUES[line["rear"]["piece"].upper()]):
                continue
            front_attack = next((r for r in hits.get(front, []) if r["actor"]["id"] == actor), None)
            if not front_attack:
                continue
            confirmation = skewer_confirmation(after, actor, front, rear, front_attack)
            if confirmation:
                confirmed = p
                for later in events[p:]:
                    pos = positions[later.ply]
                    current_line = ray_relations(positions[later.ply - 1]).get(key)
                    if not current_line or current_line["screen"] != line["screen"]:
                        break
                    if later.actor == front:
                        relation = pos.relation(actor, rear) if actor in pos.squares and rear in pos.squares else None
                        if relation and relation["profitable"]:
                            confirmation = {"frontAttack": front_attack, "escape": later.move,
                                            "fen": pos.fen, "rearAttack": relation}
                            confirmed = later.ply
                        break
                    if later.actor in {actor, rear} or later.victim in {actor, front, rear}:
                        break
                # v2.6 (expert review): a skewer must actually win one of the
                # two line pieces in the PV; a blockable check or a protected
                # rear is not a real skewer.
                won = next((e for e in events[p:] if e.side == solver and e.victim in {front, rear}
                            and e.victim_kind in MAIN), None)
                if not won:
                    review("skewer", p, "skewer_not_realized", line)
                    continue
                emit("skewer", p, confirmed, [actor], [front, rear], "ray", {"line": line, "continuation": confirmation})
            else:
                review("skewer", p, "no_profitable_two_stage_confirmation", line)
        # v3.0 (expert ruling on qGXnbL): one move creating two new effective
        # threats on two different non-king majors counts as a fork even when
        # the threats come from different pieces, provided the moving piece
        # makes one of them and the move is not already a discovered attack or
        # skewer (those labels explain it instead). A capturing move is
        # excluded: its threats are the aftermath of the capture.
        if not event.victim and not any(o["id"] in {"fork", "discovered_attack", "skewer"}
                                        for o in plies[p - 1]["occurrences"]):
            fresh = {}
            for target, relations in hits.items():
                if after.board.get(after.squares.get(target, ""), "").upper() not in MAIN:
                    continue
                for relation in relations:
                    actor = relation["actor"]["id"]
                    if relation["check"] or not relation["profitable"]:
                        continue
                    old = before.relation(actor, target) if actor in before.squares and target in before.squares else None
                    if old and old["profitable"]:
                        continue
                    if actor != event.actor and opened_by(before, after, actor, target, event.move[:2]):
                        continue
                    fresh.setdefault(target, relation)
            if len(fresh) >= 2 and len({r["actor"]["id"] for r in fresh.values()}) >= 2 and                     any(r["actor"]["id"] == event.actor for r in fresh.values()):
                pair = sorted(fresh)[:2] if len(fresh) == 2 else sorted(
                    fresh, key=lambda t: (fresh[t]["actor"]["id"] != event.actor, t))[:2]
                emit("fork", p, p, list(dict.fromkeys(fresh[t]["actor"]["id"] for t in pair)), list(pair),
                     "two_new_threats", {"attacks": [fresh[t] for t in pair]})
        # Structural relations are tracked continuously. Emit an existing pin
        # only when this player move exploits it, including an actual capture.
        candidates = {}
        for key, relation in after.pins.items():
            guard = key[1]
            minor = relation["front"]["piece"].upper() not in MAIN
            proof = functional_pin_capture(relation, positions, events, p)
            if relation.get("absolute") and not proof:
                proof = absolute_pin_sacrifice(relation, positions, events, p)
            if not relation.get("absolute") and not proof:
                proof = relative_pin_front_capture(relation, positions, events, p)
            if not proof:
                proof = pinned_front_won(relation, positions, events, p)
            newly_attacked = any(r["profitable"] and not (
                before.relation(r["actor"]["id"], guard) or {}).get("profitable", False)
                for r in hits.get(guard, []))
            if key not in before.pins:
                candidates[key] = (relation, p, "created", proof)
            elif newly_attacked:
                candidates[key] = (relation, p, "exploited", proof)
            elif proof:
                target = proof["defendedTarget"]["id"]
                new_attack = any(r["profitable"] and not (
                    before.relation(r["actor"]["id"], target) or {}).get("profitable", False)
                    for r in hits.get(target, []))
                if proof["capturePly"] == p or new_attack:
                    candidates[key] = (relation, p, "defensive_duty_exploited", proof)
        if event.victim:
            for key, relation in before.pins.items():
                if key[1] == event.victim and relation["front"]["piece"].upper() in MAIN:
                    proof = functional_pin_capture(relation, positions, events, p - 1)
                    candidates[key] = (relation, p, "pinned_piece_captured", proof)
        if reply:
            # Actual recapture pulls a small blocker off an enemy cannon ray.
            for key, relation in after.pins.items():
                if (relation.get("absolute") or relation["front"]["piece"].upper() in MAIN or
                        response.actor != key[1] or response.victim != event.actor):
                    continue
                realized = next((e for e in events[p + 1:] if e.side == solver and e.actor == key[0]
                                 and e.victim == key[2]), None)
                if realized:
                    gain = evaluate_exchange(positions[realized.ply - 1].fen, realized.move)
                    if gain > 0 and opened_by(after, reply, key[0], key[2], response.move[:2]):
                        proof = {"guard": after.ref(key[1]), "defendedTarget": after.ref(key[2]),
                                 "capturePly": realized.ply, "capture": realized.move, "gain": gain,
                                 "mode": "blocker_recapture", "response": response.move}
                        candidates[key] = (relation, p + 1, "blocker_recapture", proof)
        if reply and (after.checked or any(r["profitable"] for rows in threats.values() for r in rows)):
            for key, relation in reply.pins.items():
                if key in after.pins:
                    continue
                # The actual response must move the restricted piece or the
                # protected rear target; unrelated preexisting pins do not count.
                if response.actor not in {key[1], key[2]}:
                    continue
                minor = relation["front"]["piece"].upper() not in MAIN
                proof = functional_pin_capture(relation, positions, events, p + 1)
                candidates[key] = (relation, p + 1, "formed_by_response", proof)
        for key, (relation, confirmed, mode, proof) in candidates.items():
            if relation.get("review"):
                review("pin", p, "horse_leg_value_boundary", relation)
                continue
            # v3.1 (ruling E2): a relation that holds only while the defender
            # is in check (a recapture is illegal until the check is answered)
            # and is gone after a reply that moved none of its pieces is not a pin.
            if (mode in {"created", "exploited", "defensive_duty_exploited"} and confirmed == p and
                    after.checked and reply is not None and key not in reply.pins and
                    all(after.squares.get(x) == reply.squares.get(x) for x in key[:3])):
                review("pin", p, "pin_only_while_in_check", relation)
                continue
            if not proof:
                continue
            relation_pos = before if mode == "pinned_piece_captured" else positions[confirmed]
            if front_can_trade_pinner(relation_pos, relation):
                continue
            emit("pin", p, max(confirmed, proof["capturePly"] if proof else confirmed),
                 [key[0]], [key[1], key[2]], key[3],
                 {"restriction": relation, "use": mode, "functionalCapture": proof,
                  "relationFen": positions[confirmed].fen,
                  "response": response.move if confirmed == p + 1 else None})
        # Derived only after rejecting dead actors and resolving pending check.
        for parent in list(plies[p - 1]["occurrences"]):
            if parent["id"] not in {"fork", "discovered_attack", "skewer"} or not after.checked:
                continue
            ev = parent["evidence"]
            targets = ev["targets"][:1] if parent["id"] == "skewer" else ev["targets"]
            # v2.9 (expert ruling on R0g40E): a discovered attack whose moving
            # piece itself gives check is a checking parent as well.
            mover_checks = parent["id"] == "discovered_attack" and any(
                r["check"] and r["actor"]["id"] == event.actor for rs in after.hits.values() for r in rs)
            if mover_checks or any(t["piece"].upper() == "K" for t in targets):
                # v2.7 (expert ruling D3): after the actual reply to the check
                # the player must have a profitable capture of a major piece,
                # or the discovering piece itself captured a major piece.
                options = [r for rows in (reply.captures.values() if reply else []) for r in rows
                           if r["profitable"] and r["target"]["piece"].upper() in MAIN]
                mover_capture = parent["id"] == "discovered_attack" and event.victim_kind in MAIN
                if not options and not mover_capture:
                    review("check_fork", p, "no_profitable_capture_after_check", {"parentKey": ev["key"]})
                    continue
                emit("check_fork", p, ev["confirmedPly"], [r["id"] for r in ev["actors"]],
                     [r["id"] for r in ev["targets"]], "checking_parent",
                     {"parentKey": ev["key"], "checks": [r for rs in after.hits.values() for r in rs if r["check"]],
                      "gainOptions": options[:4], "moverCapture": event.move if mover_capture else None})
        for target, attacks in threats.items():
            if not any(r["profitable"] for r in attacks):
                continue
            # An actively labelled pin takes precedence over trapping its front piece.
            active_pins = {(r["actor"]["id"], r["front"]["id"], r["rear"]["id"], r["kind"])
                           for r in after.pins.values()}
            if any(o["id"] == "pin" and
                   (o["evidence"]["restriction"]["actor"]["id"],
                    o["evidence"]["restriction"]["front"]["id"],
                    o["evidence"]["restriction"]["rear"]["id"],
                    o["evidence"]["restriction"]["kind"]) in active_pins and
                   o["evidence"]["restriction"]["front"]["id"] == target
                   for ply in plies[:p] for o in ply["occurrences"]):
                continue
            if after.checked:
                review("trap", p, "defender_in_check", {"target": after.ref(target)})
                continue
            # v2.6 (expert review): a piece that cannot run because it is the
            # front of any pin relation is pinned, not trapped; and a target
            # already explained by this move's skewer or discovered attack is
            # not additionally a trap.
            pinned_by = next((r for pos in (before, after) for r in pos.pins.values()
                              if r["front"]["id"] == target), None)
            if pinned_by:
                review("trap", p, "target_is_pinned_front", {"target": after.ref(target), "restriction": pinned_by})
                # v2.7 (expert ruling D4): an attacked piece that cannot escape
                # because of the pin is labelled as a pin.
                # Only a pin newly created by this move, with the moving piece
                # as the pinner, is credited this way.
                created = next((r for key, r in after.pins.items() if r["front"]["id"] == target
                                and key not in before.pins and key[0] == event.actor), None)
                already = any(o["id"] == "pin" and o["evidence"]["targets"][0]["id"] == target
                              for ply in plies[:p] for o in ply["occurrences"])
                stuck = trap_state(after, target, excluded) if created else None
                if stuck and not already and not front_can_trade_pinner(after, created):
                    emit("pin", p, p, [created["actor"]["id"]], [target, created["rear"]["id"]], created["kind"],
                         {"restriction": created, "use": "pinned_target_cannot_escape", "functionalCapture": None,
                          "escapeAnalysis": stuck, "relationFen": after.fen, "response": None})
                continue
            # v2.7 (ruling D2): only a same-move skewer target is excluded; a
            # discovered-attack target can still be trapped (q8Xlzq).
            if any(o["id"] == "skewer" and
                   any(t["id"] == target for t in o["evidence"]["targets"])
                   for o in plies[p - 1]["occurrences"]):
                review("trap", p, "target_explained_by_line_tactic", {"target": after.ref(target)})
                continue
            trapped = trap_state(after, target, excluded)
            if not trapped or (target in before.squares and trap_state(before, target)):
                continue
            constraints = [(key, r) for key, r in after.pins.items()
                           if key[1] == target and r.get("absolute")]
            if constraints:
                relaxed = without_pieces(after, {key[0] for key, _ in constraints})
                if relaxed is None or not trap_state(relaxed, target):
                    pins = [o for o in plies[p - 1]["occurrences"] if o["id"] == "pin" and
                            o["evidence"]["restriction"]["front"]["id"] == target]
                    if not pins:
                        review("pin", p, "absolute_pin_without_proven_gain", {"restriction": constraints[0][1]})
                    for occurrence in pins:
                        occurrence["evidence"]["escapeAnalysis"] = trapped
                    continue
            emit("trap", p, p, [trapped["initialAttack"]["actor"]["id"]], [target], "all_legal_escapes", trapped)

    # v2.6: 借牽制得子 through an illegal recapture (pinned to the general,
    # including facing generals) that the structural pin scan cannot key.
    for capture in events[1:]:
        if capture.side != solver or capture.victim_kind not in MAIN:
            continue
        if any(o["id"] == "pin" for ply in plies for o in ply["occurrences"]):
            break
        found = illegal_recapture_pin(positions, events, capture) or relative_recapture_pin(positions, events, capture)
        if found:
            pinner, guard, king, proof = found
            mode = proof["mode"]
            emit("pin", capture.ply, capture.ply, [pinner], [guard, king], mode,
                 {"restriction": {"actor": positions[capture.ply].ref(pinner), "front": positions[capture.ply].ref(guard),
                                  "rear": positions[capture.ply].ref(king), "kind": mode, "absolute": mode == "illegal_recapture"},
                  "use": mode, "functionalCapture": proof,
                  "relationFen": positions[capture.ply].fen, "response": None})

    # Forcing an enemy blocker away opens a previously unavailable attack.
    # The later profitable capture, the vacated obstruction and the pressure
    # are all identity-linked; voluntary unrelated moves cannot confirm it.
    for trigger in events[1:]:
        p = trigger.ply
        if trigger.side != solver or p >= len(events):
            continue
        response = events[p]
        before, pressure, release = positions[p - 1:p + 2]
        blocker, vacated = response.actor, response.move[:2]
        new_pressure = [r for r in pressure.threats.get(blocker, []) if r["profitable"] and not (
            before.relation(r["actor"]["id"], blocker) or {}).get("profitable", False)]
        if not new_pressure and not pressure.checked:
            continue
        for target, relations in release.hits.items():
            if target == blocker:
                continue
            for attack in relations:
                actor = attack["actor"]["id"]
                if attack["check"] or not attack["profitable"] or actor == trigger.actor:
                    continue
                if (before.relation(actor, target) or pressure.relation(actor, blocker) or
                        not opened_by(pressure, release, actor, target, vacated)):
                    continue
                realization = next((e for e in events[p + 1:] if e.side == solver and e.actor == actor and e.victim == target), None)
                if not realization or evaluate_exchange(positions[realization.ply - 1].fen, realization.move) <= 0:
                    continue
                if any(pos.squares.get(actor) != release.squares[actor] or
                       pos.squares.get(target) != release.squares[target] or
                       not pos.relation(actor, target) or not pos.relation(actor, target)["profitable"]
                       for pos in positions[p + 1:realization.ply] if not pos.checked):
                    continue
                emit("clearance", p, realization.ply, [trigger.actor, actor], [blocker, target], "forced_blocker_departure",
                     {"blocker": pressure.ref(blocker), "vacated": vacated,
                      "pressure": new_pressure, "pressureFen": pressure.fen,
                      "response": {"ply": response.ply, "ucci": response.move},
                      "releaseFen": release.fen, "openedAttack": attack,
                      "realization": {"ply": realization.ply, "ucci": realization.move, "gain":
                                      evaluate_exchange(positions[realization.ply - 1].fen, realization.move)}})

    # D7: actual profitable realization, with the same attacker/target and
    # uninterrupted release. Independent later blunders cannot confirm it.
    for capture in events[1:]:
        if capture.side != solver or capture.victim_kind not in MAIN:
            continue
        q, actor, target = capture.ply, capture.actor, capture.victim
        realized = positions[q - 1].relation(actor, target)
        if not realized or not realized["profitable"]:
            continue
        for trigger in events[1:q - 1]:
            if trigger.side != solver:
                continue
            p = trigger.ply
            before = positions[p - 1]
            old = before.relation(actor, target)
            guards = before.guards.get((actor, target), {})
            if not old:
                # A geometric protector is only a review candidate here: we
                # have no earlier legal attack with which to prove recapture.
                if trigger.victim and target in before.squares:
                    protectors = b.attacked_squares(before.board, other(solver)).get(before.squares[target], [])
                    if any(before.ids[r["square"]] == trigger.victim for r in protectors):
                        review("remove_defender", p, "no_prior_legal_attack", {
                            "target": before.ref(target), "removedGuard": before.ref(trigger.victim),
                            "realizationPly": q})
                continue
            if old["profitable"] or not guards:
                continue
            for release_ply in (p, p + 1):
                if release_ply >= q:
                    continue
                release = positions[release_ply]
                new = release.relation(actor, target)
                if release.checked or not new or not new["profitable"]:
                    continue
                remaining = release.guards.get((actor, target), {})
                lost = set(guards) - set(remaining)
                if not lost:
                    continue
                causal = []
                for guard in sorted(lost):
                    if trigger.victim == guard:
                        causal.append(guard)
                    elif release_ply == p:
                        # Direct removal or demonstrable interception of the
                        # same guard's recapture line, with both targets alive.
                        if trigger.victim == guard or (guard in release.squares and
                                before.squares[guard] == release.squares[guard] and
                                before.squares[actor] == release.squares[actor] and
                                before.squares[target] == release.squares[target]):
                            causal.append(guard)
                    elif (positions[p].checked and
                          checking_interception(before, release, trigger.move, guard, actor, target)):
                        # v3.1 (E1): the trigger position was skipped because it
                        # is check; the line it cut is still cut after the reply.
                        causal.append(guard)
                    elif events[p].actor == guard:
                        pressure = positions[p]
                        if pressure.checked or guard in pressure.threats:
                            causal.append(guard)
                if not causal:
                    review("remove_defender", p, "release_not_proven_forced", {"target": before.ref(target), "guards": sorted(lost), "realizationPly": q})
                    continue
                uninterrupted = True
                for intermediate in positions[release_ply:q]:
                    if intermediate.checked:
                        continue
                    rel = intermediate.relation(actor, target)
                    if not rel or not rel["profitable"] or any(g in intermediate.guards.get((actor, target), {}) for g in causal):
                        uninterrupted = False
                        break
                if uninterrupted:
                    emit("remove_defender", p, q, [trigger.actor, actor], [target], "profitable_release",
                         {"beforeFen": before.fen, "releaseFen": release.fen, "releasePly": release_ply,
                          "guardsBefore": list(guards.values()), "guardsAfter": list(remaining.values()),
                          "removedGuards": [before.ref(g) for g in causal], "beforeAttack": old,
                          "releaseAttack": new, "realization": {"ply": q, "ucci": capture.move, "attack": realized}})
                    break

    # D8: actual recapture chain. v2.1 intentionally removes the sole-legal-
    # response gate; it does not claim exhaustive proof over alternative replies.
    for trigger in events[1:]:
        p = trigger.ply
        if trigger.side != solver or trigger.victim_kind not in MAIN or p >= len(events):
            continue
        response = events[p]
        before, pressure = positions[p - 1:p + 1]
        guards1 = before.guards.get((trigger.actor, trigger.victim), {})
        if response.actor not in guards1 or response.victim != trigger.actor or response.dst != trigger.dst:
            continue
        guard = response.actor
        for (actor2, target2), guards2 in before.guards.items():
            if target2 == trigger.victim or guard not in guards2:
                continue
            old = before.relation(actor2, target2)
            released = positions[p + 1]
            new = released.relation(actor2, target2)
            if not old or old["profitable"] or not new or not new["profitable"] or guard in released.guards.get((actor2, target2), {}):
                continue
            realization = next((e for e in events[p + 1:] if e.side == solver and e.actor == actor2 and e.victim == target2), None)
            if not realization:
                continue
            if any(not pos.relation(actor2, target2) or not pos.relation(actor2, target2)["profitable"] or
                   guard in pos.guards.get((actor2, target2), {}) for pos in positions[p + 1:realization.ply] if not pos.checked):
                continue
            emit("overload", p, realization.ply, [trigger.actor, actor2], [trigger.victim, target2], "actual_guard_response",
                 {"guard": before.ref(guard), "guarding": [guards1[guard], guards2[guard]],
                  "actualResponse": {"ply": response.ply, "ucci": response.move},
                  "beforeAttack": old, "releaseAttack": new,
                  "realization": {"ply": realization.ply, "ucci": realization.move}})

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
