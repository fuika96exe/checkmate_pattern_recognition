"""Midgame tactic analysis: run the detectors over a replayed line and merge their findings.

Identity-based and precision-first: no network and no engine PV search.  Phase 0
step 6 is moving each label's detector out of this module, in the original order.
"""
from __future__ import annotations

from .. import board as b
from ..exchange import evaluate_exchange, piece_value
from ..version import MIDGAME_RULES_VERSION
from .context import LABELS, Analysis, Finding, move_frame
from .detectors.discovered_attack import detect_discovered_attacks, detect_escaped_discovered_attacks
from .detectors.fork import detect_forks, detect_screen_forks, detect_two_threat_forks
from .detectors.pin import detect_pins, detect_recapture_pins
from .detectors.pin_proofs import front_can_trade_pinner
from .detectors.skewer import detect_skewers
from .material import material_result
from .merge import finalize_labels
from .position import MAIN, VALUES, Position, opened_by, other, own, view, without_pieces
from .replay import replay

RULES_VERSION = MIDGAME_RULES_VERSION


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


def analyze_midgame(fen: str, blunder: str, pv: list[str], solver: str):
    positions, events = replay(fen, blunder, pv, solver)
    run = Analysis(positions, events, solver)
    plies, reviews, review = run.plies, run.reviews, run.review

    def emit(label, ply, confirmed, actors, targets, kind, evidence):
        return run.emit(Finding(label, ply, confirmed, actors, targets, kind, evidence))

    for event in events[1:]:
        if event.side != solver:
            continue
        frame = move_frame(run, event)
        p, before, after, response, reply = frame.ply, frame.before, frame.after, frame.response, frame.reply
        excluded, hits, threats, fork_threats = frame.excluded, frame.hits, frame.threats, frame.fork_threats
        detect_forks(run, frame)
        detect_screen_forks(run, frame)
        detect_discovered_attacks(run, frame)
        detect_escaped_discovered_attacks(run, frame)
        detect_skewers(run, frame)
        detect_two_threat_forks(run, frame)
        detect_pins(run, frame)
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

    detect_recapture_pins(run)

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
