import { START_FEN, applyMove, boardToFen, uciToChinese } from './board-rules.ts';
import type { ImportResult } from './types.ts';

const DPXQ_PIECE_ORDER = [
  'R',
  'N',
  'B',
  'A',
  'K',
  'A',
  'B',
  'N',
  'R',
  'C',
  'C',
  'P',
  'P',
  'P',
  'P',
  'P',
  'r',
  'n',
  'b',
  'a',
  'k',
  'a',
  'b',
  'n',
  'r',
  'c',
  'c',
  'p',
  'p',
  'p',
  'p',
  'p',
];

export function isDhtmlXQ(text: string): boolean {
  return (
    text.includes('[DhtmlXQ]') ||
    text.includes('[DhtmlXQ_movelist]') ||
    text.includes('[DhtmlXQ_binit]')
  );
}

function parseBinit(binitStr: string): string {
  // Standard binit
  const stdBinit =
    '8979695949392919097717866646260600102030405060708012720323436383';
  if (!binitStr || binitStr.trim() === stdBinit) {
    return START_FEN;
  }

  const trimmed = binitStr.trim();
  if (trimmed.length !== 64) {
    return START_FEN;
  }

  const board: Record<string, string> = {};
  for (let i = 0; i < 32; i++) {
    const x = parseInt(trimmed[i * 2], 10);
    const y = parseInt(trimmed[i * 2 + 1], 10);
    // 99 or invalid coordinate means piece was captured or not present
    if (x >= 0 && x <= 8 && y >= 0 && y <= 9) {
      const square = `${String.fromCharCode(97 + x)}${9 - y}`;
      board[square] = DPXQ_PIECE_ORDER[i];
    }
  }

  return boardToFen(board, 'red', 0, 1);
}

export function parseDhtmlXQ(text: string): ImportResult {
  const getTag = (tag: string): string => {
    const regex = new RegExp(`\\[${tag}\\]([\\s\\S]*?)\\[\\/${tag}\\]`, 'i');
    const match = text.match(regex);
    return match ? match[1].trim() : '';
  };

  const title = getTag('DhtmlXQ_title') || 'DhtmlXQ Game';
  const red = getTag('DhtmlXQ_red');
  const black = getTag('DhtmlXQ_black');
  const event = getTag('DhtmlXQ_event');
  const date = getTag('DhtmlXQ_date');
  const result = getTag('DhtmlXQ_result');
  const binit = getTag('DhtmlXQ_binit');
  const movelist = getTag('DhtmlXQ_movelist').replace(/\s+/g, '');

  const headers: Record<string, string> = {};
  if (title) headers.Title = title;
  if (red) headers.Red = red;
  if (black) headers.Black = black;
  if (event) headers.Event = event;
  if (date) headers.Date = date;
  if (result) headers.Result = result;

  const initialFen = binit ? parseBinit(binit) : START_FEN;

  const moves: string[] = [];
  const chineseMoves: string[] = [];
  let currentFen = initialFen;

  for (let i = 0; i + 4 <= movelist.length; i += 4) {
    const x1 = parseInt(movelist[i], 10);
    const y1 = parseInt(movelist[i + 1], 10);
    const x2 = parseInt(movelist[i + 2], 10);
    const y2 = parseInt(movelist[i + 3], 10);

    const from = `${String.fromCharCode(97 + x1)}${9 - y1}`;
    const to = `${String.fromCharCode(97 + x2)}${9 - y2}`;
    const uci = `${from}${to}`;

    try {
      const ch = uciToChinese(currentFen, uci);
      chineseMoves.push(ch);
      moves.push(uci);
      currentFen = applyMove(currentFen, uci);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        success: false,
        format: 'dpxq_ubb',
        title,
        initialFen,
        moves,
        chineseMoves,
        headers,
        result,
        error: `Move ${Math.floor(i / 4) + 1} (${uci}) failed: ${msg}`,
        failedMoveIndex: Math.floor(i / 4),
      };
    }
  }

  if (moves.length === 0) {
    return {
      success: false,
      format: 'dpxq_ubb',
      title: red && black ? `${red} vs ${black}` : title,
      initialFen,
      moves: [],
      chineseMoves: [],
      headers,
      result,
      error: '未识别到任何有效着法 (No valid moves found)',
    };
  }

  return {
    success: true,
    format: 'dpxq_ubb',
    title: red && black ? `${red} vs ${black}` : title,
    initialFen,
    moves,
    chineseMoves,
    headers,
    result,
  };
}
