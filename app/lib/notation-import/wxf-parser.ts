import { START_FEN, applyMove, legalMoves, parseFen, uciToChinese } from './board-rules.ts';
import type { ImportResult } from './types.ts';

const FILES = 'abcdefghi';

const PIECE_LETTER_MAP: Record<string, string> = {
  K: 'K',
  k: 'k',
  A: 'A',
  a: 'a',
  E: 'B',
  e: 'b',
  B: 'B',
  b: 'b',
  H: 'N',
  h: 'n',
  N: 'N',
  n: 'n',
  R: 'R',
  r: 'r',
  C: 'C',
  c: 'c',
  P: 'P',
  p: 'p',
};

export function isWXF(text: string): boolean {
  return (
    text.includes('FORMAT  WXF') ||
    text.includes('FORMAT WXF') ||
    text.includes('[Format "WXF"]') ||
    /\b[CHRPBEAKchrpbeak][1-9][.+-][1-9]\b/.test(text)
  );
}

function matchWXFMove(
  fen: string,
  uci: string,
  token: string,
): boolean {
  const { board, side } = parseFen(fen);
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  const piece = board[from];
  if (!piece) return false;

  const isRed = side === 'red';
  if (isRed !== (piece === piece.toUpperCase())) return false;

  const match = token.match(/^([+-~])?([A-Za-z])([1-9])?([.+-])([1-9])$/);
  if (!match) return false;

  const [, prefix, letter, fileDigit, action, targetDigit] = match;
  const expectedPiece = PIECE_LETTER_MAP[letter];
  if (!expectedPiece || expectedPiece.toLowerCase() !== piece.toLowerCase()) {
    return false;
  }

  const fromCol = FILES.indexOf(from[0]);
  const toCol = FILES.indexOf(to[0]);
  const fromRank = parseInt(from[1], 10);
  const toRank = parseInt(to[1], 10);

  // Check file if specified
  if (fileDigit) {
    const expectedCol = isRed ? 9 - parseInt(fileDigit, 10) : parseInt(fileDigit, 10) - 1;
    if (fromCol !== expectedCol) return false;
  }

  // Check prefix if tandem
  if (prefix) {
    const sameCol = Object.keys(board)
      .filter((sq) => board[sq] === piece && sq[0] === from[0])
      .sort((a, b) => {
        const ra = parseInt(a[1], 10);
        const rb = parseInt(b[1], 10);
        return isRed ? rb - ra : ra - rb;
      });
    const idx = sameCol.indexOf(from);
    if (prefix === '+' && idx !== 0) return false;
    if (prefix === '-' && idx !== sameCol.length - 1) return false;
  }

  const targetNum = parseInt(targetDigit, 10);
  const expectedTargetCol = isRed ? 9 - targetNum : targetNum - 1;

  if (action === '.') {
    if (fromRank !== toRank) return false;
    return toCol === expectedTargetCol;
  }

  const forward = isRed ? toRank > fromRank : toRank < fromRank;
  if (action === '+' && !forward) return false;
  if (action === '-' && forward) return false;

  const isLinear = ['r', 'c', 'p', 'k'].includes(piece.toLowerCase());
  if (isLinear) {
    const dist = Math.abs(toRank - fromRank);
    return dist === targetNum && fromCol === toCol;
  } else {
    // Horse, Elephant, Advisor
    return toCol === expectedTargetCol;
  }
}

export function parseWXF(text: string): ImportResult {
  const headers: Record<string, string> = {};
  const lines = text.split('\n');

  for (const line of lines) {
    const headerMatch = line.match(/^([A-Z0-9_-]+)\s+([^;{\n]+)/);
    if (headerMatch && !line.startsWith('START') && !line.includes('.')) {
      headers[headerMatch[1].trim()] = headerMatch[2].trim();
    }
  }

  const initialFen = START_FEN;
  const red = headers.RED || '';
  const black = headers.BLACK || '';
  const title = red && black ? `${red} vs ${black}` : headers.EVENT || 'PlayOK WXF Game';
  const result = headers.RESULT || '';

  // Extract moves section
  let moveSection = text;
  const startIdx = text.indexOf('START{');
  const endIdx = text.indexOf('}END');
  if (startIdx !== -1) {
    moveSection = text.slice(startIdx + 6, endIdx !== -1 ? endIdx : undefined);
  }

  const moveTokens = moveSection
    .replace(/\b\d+\.\s*/g, ' ')
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t && /^[+-~]?[A-Za-z][1-9]?[.+-][1-9]$/.test(t));

  const moves: string[] = [];
  const chineseMoves: string[] = [];
  let currentFen = initialFen;

  for (let i = 0; i < moveTokens.length; i++) {
    const token = moveTokens[i];
    const legals = legalMoves(currentFen);
    const matchedUci = legals.find((uci) => matchWXFMove(currentFen, uci, token));

    if (!matchedUci) {
      return {
        success: false,
        format: 'wxf',
        title,
        initialFen,
        moves,
        chineseMoves,
        headers,
        result,
        error: `Move ${i + 1} (${token}) could not be resolved or is illegal`,
        failedMoveIndex: i,
      };
    }

    try {
      const ch = uciToChinese(currentFen, matchedUci);
      chineseMoves.push(ch);
      moves.push(matchedUci);
      currentFen = applyMove(currentFen, matchedUci);
    } catch (err: any) {
      return {
        success: false,
        format: 'wxf',
        title,
        initialFen,
        moves,
        chineseMoves,
        headers,
        result,
        error: `Move ${i + 1} (${matchedUci}) error: ${err.message}`,
        failedMoveIndex: i,
      };
    }
  }

  return {
    success: true,
    format: 'wxf',
    title,
    initialFen,
    moves,
    chineseMoves,
    headers,
    result,
  };
}
