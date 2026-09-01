"use client";

import { useMemo, useState } from "react";
import type { MoveRecord } from "../lib/types";

const PIECE_TEXT: Record<string, string> = {
  K: "帥", A: "仕", B: "相", N: "馬", R: "車", C: "炮", P: "兵",
  k: "將", a: "士", b: "象", n: "馬", r: "車", c: "砲", p: "卒",
};

function parseFen(fen: string): Record<string, string> {
  const board: Record<string, string> = {};
  fen.split(" ")[0].split("/").forEach((rank, row) => {
    let file = 0;
    for (const char of rank) {
      if (/\d/.test(char)) file += Number(char);
      else {
        board[`${String.fromCharCode(97 + file)}${9 - row}`] = char;
        file += 1;
      }
    }
  });
  return board;
}

interface Props {
  fen: string;
  legalMoves: string[];
  lastMove?: MoveRecord;
  disabled?: boolean;
  onMove: (move: string) => void;
}

export function XiangqiBoard({ fen, legalMoves, lastMove, disabled, onMove }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const board = useMemo(() => parseFen(fen), [fen]);
  const legalTargets = useMemo(
    () => new Set(selected ? legalMoves.filter((m) => m.startsWith(selected)).map((m) => m.slice(2)) : []),
    [legalMoves, selected],
  );
  const side = fen.split(" ")[1] === "b" ? "black" : "red";

  function click(square: string) {
    if (disabled) return;
    if (selected && legalTargets.has(square)) {
      const move = `${selected}${square}`;
      setSelected(null);
      onMove(move);
      return;
    }
    const piece = board[square];
    const isOwn = piece && (side === "red" ? piece === piece.toUpperCase() : piece === piece.toLowerCase());
    if (isOwn && legalMoves.some((move) => move.startsWith(square))) setSelected(square);
    else setSelected(null);
  }

  return (
    <div className="board-shell" aria-label="中國象棋棋盤">
      <div className="board-stage">
        <svg className="board-lines" viewBox="0 0 90 100" aria-hidden="true">
          <rect x="1" y="1" width="88" height="98" rx="1" fill="#ead2a5" stroke="#624729" strokeWidth="1.2" />
          {Array.from({ length: 10 }, (_, i) => <line key={`h${i}`} x1="5" y1={5 + i * 10} x2="85" y2={5 + i * 10} />)}
          {Array.from({ length: 9 }, (_, i) => <g key={`v${i}`}><line x1={5 + i * 10} y1="5" x2={5 + i * 10} y2="45" /><line x1={5 + i * 10} y1="55" x2={5 + i * 10} y2="95" /></g>)}
          <line x1="5" y1="45" x2="5" y2="55" /><line x1="85" y1="45" x2="85" y2="55" />
          <path d="M35 5L55 25M55 5L35 25M35 75L55 95M55 75L35 95" />
          <text x="25" y="52.5">楚 河</text><text x="65" y="52.5">漢 界</text>
        </svg>
        <div className="board-cells">
          {Array.from({ length: 10 }, (_, row) => Array.from({ length: 9 }, (_, file) => {
            const square = `${String.fromCharCode(97 + file)}${9 - row}`;
            const piece = board[square];
            const isRed = piece && piece === piece.toUpperCase();
            const isSelected = selected === square;
            const isTarget = legalTargets.has(square);
            const isLast = lastMove && (lastMove.fromSquare === square || lastMove.toSquare === square);
            return (
              <button type="button" key={square} className={`board-cell${isSelected ? " selected" : ""}${isTarget ? " target" : ""}${isLast ? " last" : ""}`} onClick={() => click(square)} aria-label={`${square}${piece ? ` ${PIECE_TEXT[piece]}` : ""}`}>
                {isTarget && <span className="target-dot" />}
                {piece && <span className={`piece ${isRed ? "red" : "black"}`}>{PIECE_TEXT[piece]}</span>}
              </button>
            );
          }))}
        </div>
      </div>
    </div>
  );
}
