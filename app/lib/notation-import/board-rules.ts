export const START_FEN =
  'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1';

const FILES = 'abcdefghi';
const RED_NAMES: Record<string, string> = {
  K: '帅',
  A: '仕',
  B: '相',
  N: '马',
  R: '车',
  C: '炮',
  P: '兵',
};
const BLACK_NAMES: Record<string, string> = {
  k: '将',
  a: '士',
  b: '象',
  n: '马',
  r: '车',
  c: '炮',
  p: '卒',
};
const CHINESE_NUMBERS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];

export type BoardMap = Record<string, string>;

export function parseFen(fen: string): {
  board: BoardMap;
  side: 'red' | 'black';
  halfmove: number;
  fullmove: number;
} {
  const parts = fen.trim().split(/\s+/);
  if (parts.length < 2) {
    throw new Error(`Invalid FEN: ${fen}`);
  }
  const ranks = parts[0].split('/');
  if (ranks.length !== 10) {
    throw new Error(`Xiangqi FEN must have 10 ranks, got ${ranks.length}`);
  }

  const board: BoardMap = {};
  for (let rankIdx = 0; rankIdx < 10; rankIdx++) {
    const rank = 9 - rankIdx;
    const rowStr = ranks[rankIdx];
    let fileIdx = 0;
    for (const char of rowStr) {
      if (char >= '1' && char <= '9') {
        fileIdx += parseInt(char, 10);
      } else if ('rnbakcpRNBAKCP'.includes(char)) {
        if (fileIdx > 8) throw new Error('FEN row exceeds 9 files');
        const square = `${FILES[fileIdx]}${rank}`;
        board[square] = char;
        fileIdx++;
      } else {
        throw new Error(`Unsupported piece in FEN: ${char}`);
      }
    }
  }

  const sideChar = parts[1].toLowerCase();
  const side: 'red' | 'black' = sideChar === 'b' ? 'black' : 'red';
  const halfmove = parts[4] ? parseInt(parts[4], 10) : 0;
  const fullmove = parts[5] ? parseInt(parts[5], 10) : 1;

  return { board, side, halfmove, fullmove };
}

export function boardToFen(
  board: BoardMap,
  side: 'red' | 'black',
  halfmove = 0,
  fullmove = 1,
): string {
  const ranks: string[] = [];
  for (let rank = 9; rank >= 0; rank--) {
    let empty = 0;
    let rankStr = '';
    for (let fileIdx = 0; fileIdx < 9; fileIdx++) {
      const square = `${FILES[fileIdx]}${rank}`;
      const piece = board[square];
      if (!piece) {
        empty++;
      } else {
        if (empty > 0) {
          rankStr += empty.toString();
          empty = 0;
        }
        rankStr += piece;
      }
    }
    if (empty > 0) rankStr += empty.toString();
    ranks.push(rankStr);
  }

  const sideChar = side === 'red' ? 'w' : 'b';
  return `${ranks.join('/')} ${sideChar} - - ${halfmove} ${fullmove}`;
}

function xy(square: string): [number, number] {
  return [FILES.indexOf(square[0]), parseInt(square[1], 10)];
}

function squareAt(x: number, y: number): string | null {
  if (x >= 0 && x < 9 && y >= 0 && y <= 9) {
    return `${FILES[x]}${y}`;
  }
  return null;
}

function isRed(piece: string): boolean {
  return piece === piece.toUpperCase();
}

function insidePalace(x: number, y: number, red: boolean): boolean {
  return x >= 3 && x <= 5 && (red ? y >= 0 && y <= 2 : y >= 7 && y <= 9);
}

function betweenSquares(board: BoardMap, a: string, b: string): string[] {
  const [ax, ay] = xy(a);
  const [bx, by] = xy(b);
  if (ax !== bx && ay !== by) return [];
  const dx = Math.sign(bx - ax);
  const dy = Math.sign(by - ay);
  let x = ax + dx;
  let y = ay + dy;
  const result: string[] = [];
  while (x !== bx || y !== by) {
    result.push(`${FILES[x]}${y}`);
    x += dx;
    y += dy;
  }
  return result;
}

function pseudoLegalTargets(board: BoardMap, source: string, piece: string): string[] {
  const [x, y] = xy(source);
  const red = isRed(piece);
  const kind = piece.toUpperCase();
  const targets: string[] = [];

  const addIfOpen = (target: string | null) => {
    if (!target) return;
    const occ = board[target];
    if (!occ || isRed(occ) !== red) {
      targets.push(target);
    }
  };

  if (kind === 'R' || kind === 'C') {
    const dirs: [number, number][] = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];
    for (const [dx, dy] of dirs) {
      let cx = x + dx;
      let cy = y + dy;
      let screenSeen = false;
      while (true) {
        const target = squareAt(cx, cy);
        if (!target) break;
        const occ = board[target];
        if (kind === 'R') {
          if (!occ) {
            targets.push(target);
          } else {
            if (isRed(occ) !== red) targets.push(target);
            break;
          }
        } else {
          // Cannon
          if (!screenSeen) {
            if (!occ) {
              targets.push(target);
            } else {
              screenSeen = true;
            }
          } else {
            if (occ) {
              if (isRed(occ) !== red) targets.push(target);
              break;
            }
          }
        }
        cx += dx;
        cy += dy;
      }
    }
    return targets;
  }

  if (kind === 'N') {
    const horseSteps: [number, number, number, number][] = [
      [1, 2, 0, 1],
      [-1, 2, 0, 1],
      [1, -2, 0, -1],
      [-1, -2, 0, -1],
      [2, 1, 1, 0],
      [2, -1, 1, 0],
      [-2, 1, -1, 0],
      [-2, -1, -1, 0],
    ];
    for (const [dx, dy, lx, ly] of horseSteps) {
      const leg = squareAt(x + lx, y + ly);
      if (leg && !board[leg]) {
        addIfOpen(squareAt(x + dx, y + dy));
      }
    }
    return targets;
  }

  if (kind === 'B') {
    const bishopDirs: [number, number][] = [
      [2, 2],
      [2, -2],
      [-2, 2],
      [-2, -2],
    ];
    for (const [dx, dy] of bishopDirs) {
      const eye = squareAt(x + dx / 2, y + dy / 2);
      const target = squareAt(x + dx, y + dy);
      if (!target || !eye || board[eye]) continue;
      const targetRank = parseInt(target[1], 10);
      if ((red && targetRank <= 4) || (!red && targetRank >= 5)) {
        addIfOpen(target);
      }
    }
    return targets;
  }

  if (kind === 'A') {
    const advDirs: [number, number][] = [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1],
    ];
    for (const [dx, dy] of advDirs) {
      const target = squareAt(x + dx, y + dy);
      if (target && insidePalace(x + dx, y + dy, red)) {
        addIfOpen(target);
      }
    }
    return targets;
  }

  if (kind === 'K') {
    const kingDirs: [number, number][] = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];
    for (const [dx, dy] of kingDirs) {
      const target = squareAt(x + dx, y + dy);
      if (target && insidePalace(x + dx, y + dy, red)) {
        addIfOpen(target);
      }
    }
    // Flying general
    for (const dir of [-1, 1]) {
      let cy = y + dir;
      while (true) {
        const target = squareAt(x, cy);
        if (!target) break;
        const occ = board[target];
        if (occ) {
          if (occ.toUpperCase() === 'K' && isRed(occ) !== red) {
            targets.push(target);
          }
          break;
        }
        cy += dir;
      }
    }
    return targets;
  }

  if (kind === 'P') {
    const fwd = red ? 1 : -1;
    addIfOpen(squareAt(x, y + fwd));
    const crossedRiver = red ? y >= 5 : y <= 4;
    if (crossedRiver) {
      addIfOpen(squareAt(x - 1, y));
      addIfOpen(squareAt(x + 1, y));
    }
    return targets;
  }

  return targets;
}

function isSquareAttacked(board: BoardMap, target: string, byRed: boolean): boolean {
  const [tx, ty] = xy(target);
  for (const [source, piece] of Object.entries(board)) {
    if (isRed(piece) !== byRed) continue;
    const [sx, sy] = xy(source);
    const dx = tx - sx;
    const dy = ty - sy;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    const kind = piece.toUpperCase();

    if (kind === 'R') {
      if ((dx === 0 || dy === 0) && !betweenSquares(board, source, target).some((sq) => board[sq])) {
        return true;
      }
    } else if (kind === 'C') {
      if (
        (dx === 0 || dy === 0) &&
        betweenSquares(board, source, target).filter((sq) => board[sq]).length === 1
      ) {
        return true;
      }
    } else if (kind === 'K') {
      if (absDx + absDy === 1) return true;
      if (dx === 0 && !betweenSquares(board, source, target).some((sq) => board[sq])) {
        return true;
      }
    } else if (kind === 'N' && ((absDx === 1 && absDy === 2) || (absDx === 2 && absDy === 1))) {
      const leg = absDx === 2 ? squareAt(sx + (dx > 0 ? 1 : -1), sy) : squareAt(sx, sy + (dy > 0 ? 1 : -1));
      if (leg && !board[leg]) return true;
    } else if (kind === 'B' && absDx === 2 && absDy === 2) {
      const eye = squareAt(sx + dx / 2, sy + dy / 2);
      if (eye && !board[eye]) return true;
    } else if (kind === 'A' && absDx === 1 && absDy === 1) {
      return true;
    } else if (kind === 'P') {
      const dir = byRed ? 1 : -1;
      if (dx === 0 && dy === dir) return true;
      const crossedRiver = byRed ? sy >= 5 : sy <= 4;
      if (crossedRiver && dy === 0 && absDx === 1) return true;
    }
  }
  return false;
}

export function legalMoves(fen: string): string[] {
  const { board, side } = parseFen(fen);
  const movingRed = side === 'red';
  const kingPiece = movingRed ? 'K' : 'k';
  const kingSquare = Object.keys(board).find((sq) => board[sq] === kingPiece);
  if (!kingSquare) return [];

  const moves: string[] = [];
  for (const [source, piece] of Object.entries(board)) {
    if (isRed(piece) !== movingRed) continue;
    for (const target of pseudoLegalTargets(board, source, piece)) {
      const nextBoard = { ...board };
      delete nextBoard[source];
      nextBoard[target] = piece;
      const nextKingSquare = source === kingSquare ? target : kingSquare;
      if (!isSquareAttacked(nextBoard, nextKingSquare, !movingRed)) {
        moves.push(`${source}${target}`);
      }
    }
  }

  return moves.sort();
}

export function applyMove(fen: string, uci: string): string {
  const { board, side, halfmove, fullmove } = parseFen(fen);
  const legal = legalMoves(fen);
  if (!legal.includes(uci)) {
    throw new Error(`Illegal move: ${uci} in position ${fen}`);
  }

  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  const piece = board[from];
  const nextBoard = { ...board };
  delete nextBoard[from];
  nextBoard[to] = piece;

  const nextSide: 'red' | 'black' = side === 'red' ? 'black' : 'red';
  const nextHalfmove = halfmove + 1;
  const nextFullmove = side === 'black' ? fullmove + 1 : fullmove;

  return boardToFen(nextBoard, nextSide, nextHalfmove, nextFullmove);
}

export function uciToChinese(fenBefore: string, uci: string): string {
  const { board, side } = parseFen(fenBefore);
  const fromSquare = uci.slice(0, 2);
  const toSquare = uci.slice(2, 4);
  const piece = board[fromSquare];
  if (!piece) throw new Error(`No piece at ${fromSquare}`);

  const movingRed = isRed(piece);
  const names = movingRed ? RED_NAMES : BLACK_NAMES;
  const pieceName = names[piece];

  const fileNumber = (sq: string) => {
    const col = FILES.indexOf(sq[0]);
    return movingRed ? 9 - col : col + 1;
  };

  const numText = (val: number) => {
    return movingRed ? CHINESE_NUMBERS[val] : val.toString();
  };

  const frontOrder = (sq: string) => {
    const rank = parseInt(sq[1], 10);
    return movingRed ? -rank : rank;
  };

  // Check tandem pieces in same column
  const sameCol = Object.keys(board)
    .filter((sq) => board[sq] === piece && sq[0] === fromSquare[0])
    .sort((a, b) => frontOrder(a) - frontOrder(b));

  let head = '';
  if (sameCol.length > 1) {
    const idx = sameCol.indexOf(fromSquare);
    if (sameCol.length === 2) {
      const prefix = idx === 0 ? '前' : '后';
      head = `${prefix}${pieceName}`;
    } else if (sameCol.length === 3) {
      const prefix = ['前', '中', '后'][idx];
      head = `${prefix}${pieceName}`;
    } else {
      const prefix = numText(idx + 1);
      head = `${prefix}${pieceName}`;
    }
  } else {
    head = `${pieceName}${numText(fileNumber(fromSquare))}`;
  }

  const fromRank = parseInt(fromSquare[1], 10);
  const toRank = parseInt(toSquare[1], 10);

  if (fromRank === toRank) {
    return `${head}平${numText(fileNumber(toSquare))}`;
  }

  const forward = movingRed ? toRank > fromRank : toRank < fromRank;
  const action = forward ? '进' : '退';

  if (['n', 'b', 'a'].includes(piece.toLowerCase())) {
    return `${head}${action}${numText(fileNumber(toSquare))}`;
  }

  return `${head}${action}${numText(Math.abs(toRank - fromRank))}`;
}
