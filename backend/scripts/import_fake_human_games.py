"""Import the audited production sample without copying participant data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.board import START_FEN, apply_move, engine_to_ucci  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archives", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    games = []
    for path in sorted(args.archives.glob("*.json")):
        archive = json.loads(path.read_text(encoding="utf-8"))
        players = [archive["rplayer"], archive["bplayer"]]
        bots = [(index, player) for index, player in enumerate(players) if player.get("p_type") == 30]
        if len(bots) != 1:
            continue
        if archive["initial_fen"] != START_FEN:
            raise ValueError(f"Unexpected initial position: {archive['id']}")
        moves = [engine_to_ucci(move) for move in archive["uci_moves"]]
        fen = START_FEN
        for move in moves:
            fen = apply_move(fen, move)
        if fen.split()[:2] != archive["fen"].split()[:2]:
            raise ValueError(f"Final position mismatch: {archive['id']}")
        slot, bot = bots[0]
        side = bot.get("side", slot + 1)
        if side not in (1, 2):
            raise ValueError(f"Invalid bot side: {archive['id']}")
        games.append({"id": archive["id"], "botSide": "red" if side == 1 else "black", "moves": moves})
    if len(games) != 198 or len({game["id"] for game in games}) != 198:
        raise ValueError(f"Expected 198 unique fake-human games, got {len(games)}")
    args.output.write_text(json.dumps({"games": games}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Imported and replayed {len(games)} games to {args.output}")


if __name__ == "__main__":
    main()
