import { START_FEN, applyMove, legalMoves, parseFen, uciToChinese } from './board-rules.ts';
import {
  isJunkLine,
  isResultToken,
  normalizeFullwidth,
  normalizeMoveChars,
  stripComments,
} from './preprocessor.ts';
import type { ImportResult } from './types.ts';

const FILES = 'abcdefghi';

const CHINESE_DIGIT_MAP: Record<string, number> = {
  一: 1,
  二: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  七: 7,
  八: 8,
  九: 9,
  十: 10,
  '1': 1,
  '2': 2,
  '3': 3,
  '4': 4,
  '5': 5,
  '6': 6,
  '7': 7,
  '8': 8,
  '9': 9,
};

const PIECE_KIND_MAP: Record<string, string> = {
  车: 'r',
  馬: 'n',
  马: 'n',
  炮: 'c',
  相: 'b',
  象: 'b',
  仕: 'a',
  士: 'a',
  帅: 'k',
  将: 'k',
  兵: 'p',
  卒: 'p',
};

export function isChineseNotation(text: string): boolean {
  return /[车马炮相象仕士兵卒帅将][一二三四五六七八九1-9前后中][进退平][一二三四五六七八九1-9]/.test(
    normalizeMoveChars(normalizeFullwidth(text)),
  );
}

function parseDigit(char: string): number | null {
  return CHINESE_DIGIT_MAP[char] ?? null;
}

function matchChineseMove(
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

  const fromCol = FILES.indexOf(from[0]);
  const toCol = FILES.indexOf(to[0]);
  const fromRank = parseInt(from[1], 10);
  const toRank = parseInt(to[1], 10);

  const fileToCol = (fileNum: number) => (isRed ? 9 - fileNum : fileNum - 1);
  const colToFile = (col: number) => (isRed ? 9 - col : col + 1);

  const char0 = token[0];
  const char1 = token[1];
  const char2 = token[2]; // direction: 进/退/平
  const char3 = token[3]; // target/step

  // Check direction
  const isAdvance = isRed ? toRank > fromRank : toRank < fromRank;
  const isRetreat = isRed ? toRank < fromRank : toRank > fromRank;
  const isHorizontal = toRank === fromRank;

  if (char2 === '进' && !isAdvance) return false;
  if (char2 === '退' && !isRetreat) return false;
  if (char2 === '平' && !isHorizontal) return false;

  // Check target or distance
  const targetDigit = parseDigit(char3);
  if (targetDigit === null) return false;

  const isLinear = ['r', 'c', 'p', 'k'].includes(piece.toLowerCase());
  if (char2 === '平') {
    if (toCol !== fileToCol(targetDigit)) return false;
  } else if (isLinear) {
    // distance
    if (Math.abs(toRank - fromRank) !== targetDigit) return false;
    if (fromCol !== toCol) return false;
  } else {
    // diagonal / horse target file
    if (toCol !== fileToCol(targetDigit)) return false;
  }

  // Case A: char0 is piece, char1 is 前/后 (e.g. 车前退二, 炮后平四, 马前进三)
  if (PIECE_KIND_MAP[char0] && (char1 === '前' || char1 === '后')) {
    if (PIECE_KIND_MAP[char0] !== piece.toLowerCase()) return false;
    const sameKindPieces = Object.keys(board)
      .filter((sq) => board[sq] === piece)
      .sort((a, b) => {
        const ra = parseInt(a[1], 10);
        const rb = parseInt(b[1], 10);
        return isRed ? rb - ra : ra - rb; // front to back
      });
    const colGroups: Record<number, string[]> = {};
    for (const sq of sameKindPieces) {
      const c = FILES.indexOf(sq[0]);
      if (!colGroups[c]) colGroups[c] = [];
      colGroups[c].push(sq);
    }
    const multiCol = Object.values(colGroups).find((grp) => grp.length > 1);
    const candidates = multiCol || sameKindPieces;
    const idx = candidates.indexOf(from);
    if (char1 === '前' && idx !== 0) return false;
    if (char1 === '后' && idx !== candidates.length - 1) return false;
    return true;
  }

  // Case B: char0 is prefix (前/后/中/一~五)
  const isPrefix0 = ['前', '后', '中', '一', '二', '三', '四', '五', '1', '2', '3', '4', '5'].includes(
    char0,
  );

  if (isPrefix0) {
    // 中 / 一~五 only apply to pawns in Xiangqi
    if (char0 !== '前' && char0 !== '后' && piece.toLowerCase() !== 'p') {
      return false;
    }

    let candidates: string[] = [];
    if (char1 in PIECE_KIND_MAP) {
      const pieceChar = char1;
      const expectedKind = PIECE_KIND_MAP[pieceChar];
      if (!expectedKind || expectedKind !== piece.toLowerCase()) return false;

      // Find all pieces of this kind
      const sameKindPieces = Object.keys(board)
        .filter((sq) => board[sq] === piece)
        .sort((a, b) => {
          const ra = parseInt(a[1], 10);
          const rb = parseInt(b[1], 10);
          return isRed ? rb - ra : ra - rb; // front to back
        });

      const colGroups: Record<number, string[]> = {};
      for (const sq of sameKindPieces) {
        const c = FILES.indexOf(sq[0]);
        if (!colGroups[c]) colGroups[c] = [];
        colGroups[c].push(sq);
      }

      const multiCol = Object.values(colGroups).find((grp) => grp.length > 1);
      candidates = multiCol || sameKindPieces;
    } else {
      // char1 is column digit, e.g. 前2平4
      const fileDigit = parseDigit(char1);
      if (fileDigit === null) return false;
      const expectedCol = fileToCol(fileDigit);
      if (fromCol !== expectedCol) return false;

      const colPieces = Object.keys(board)
        .filter((sq) => board[sq] === piece && FILES.indexOf(sq[0]) === expectedCol)
        .sort((a, b) => {
          const ra = parseInt(a[1], 10);
          const rb = parseInt(b[1], 10);
          return isRed ? rb - ra : ra - rb;
        });
      candidates = colPieces;
    }

    const idx = candidates.indexOf(from);
    if (idx === -1) return false;

    if (char0 === '前' && idx !== 0) return false;
    if (char0 === '后' && idx !== candidates.length - 1) return false;
    if (char0 === '中') {
      if (candidates.length === 3 && idx !== 1) return false;
      if (candidates.length !== 3 && idx !== Math.floor(candidates.length / 2)) return false;
    }
    const numOrder = parseDigit(char0);
    if (numOrder !== null) {
      if (idx !== numOrder - 1) return false;
    }

    return true;
  }

  // Case C: Standard notation: char0 is piece, char1 is file
  const expectedKind = PIECE_KIND_MAP[char0];
  if (!expectedKind || expectedKind !== piece.toLowerCase()) return false;

  const expectedFile = parseDigit(char1);
  if (expectedFile === null) return false;
  if (fromCol !== fileToCol(expectedFile)) return false;

  return true;
}

export function parseChineseGame(text: string): ImportResult {
  const headers: Record<string, string> = {};

  // 1. Extract PGN bracket headers [Key "Value"]
  const pgnHeaderRegex = /^\[([A-Za-z0-9_]+)\s+"([^"]*)"\]/gm;
  let pgnMatch: RegExpExecArray | null;
  while ((pgnMatch = pgnHeaderRegex.exec(text)) !== null) {
    headers[pgnMatch[1]] = pgnMatch[2];
  }

  // 2. Extract Chinese key-value lines and filter out non-move lines
  const lines = text.split('\n');
  const contentLines: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || isJunkLine(line)) continue;

    if (/^\[[A-Za-z0-9_]+\s+"[^"]*"\]$/.test(line)) {
      continue;
    }

    const colonMatch = line.match(/^([^\s:：]{2,8})[:：]\s*(.+)$/);
    if (colonMatch && !line.match(/^\d+[\.、:]/)) {
      const key = colonMatch[1].trim();
      const val = colonMatch[2].trim();
      if (key === '标题' || key === '棋局标题') headers.Title = val;
      else if (key === '红方' || key === '红方姓名') headers.Red = val;
      else if (key === '黑方' || key === '黑方姓名') headers.Black = val;
      else if (key === '赛事' || key === '比赛名称') headers.Event = val;
      else if (key === '结果') headers.Result = val;
      else if (key === '日期') headers.Date = val;
      else if (key.includes('Fen') || key.includes('FEN')) headers.FEN = val;
      else headers[key] = val;
      continue;
    }

    if (/^棋谱由\s*https?:\/\//i.test(line) || /^来源网站/i.test(line) || /^棋谱主人/i.test(line)) {
      continue;
    }

    contentLines.push(rawLine);
  }

  const initialFen = headers.FEN || START_FEN;
  const title =
    headers.Title ||
    (headers.Red && headers.Black ? `${headers.Red} vs ${headers.Black}` : 'Xiangqi Game');
  let result = headers.Result;

  // 3. Preprocess text: clean comments, normalize fullwidth and characters
  let cleanText = stripComments(contentLines.join('\n'));
  cleanText = cleanText.replace(/\[[A-Za-z0-9_]+\s+"[^"]*"\]/g, ' ');
  cleanText = normalizeFullwidth(cleanText);
  cleanText = normalizeMoveChars(cleanText);

  // 4. Extract Chinese move tokens
  // A Xiangqi move is 4 characters:
  // [Piece or Prefix][File or Piece or Prefix][Direction][Target/Step]
  const STANDARD_MOVE =
    '[车马炮相象仕士兵卒帅将][一二三四五六七八九1-9前后][进退平][一二三四五六七八九1-9]';
  const FRONT_BACK_MOVE =
    '[前后][车马炮相象仕士兵卒一二三四五六七八九1-9][进退平][一二三四五六七八九1-9]';
  const MULTI_PAWN_MOVE =
    '[中一二三四五1-5][兵卒][进退平][一二三四五六七八九1-9]';
  const moveTokenRegex = new RegExp(
    `(${STANDARD_MOVE}|${FRONT_BACK_MOVE}|${MULTI_PAWN_MOVE})`,
    'g',
  );

  const rawTokens = cleanText.match(moveTokenRegex) || [];

  // Check if result exists in trailing text
  const lastLine = lines[lines.length - 1]?.trim() || '';
  if (!result && isResultToken(lastLine)) {
    result = lastLine;
  }

  const moves: string[] = [];
  const chineseMoves: string[] = [];
  let currentFen = initialFen;

  for (let i = 0; i < rawTokens.length; i++) {
    const token = rawTokens[i];
    const legals = legalMoves(currentFen);
    const matchedUci = legals.find((uci) => matchChineseMove(currentFen, uci, token));

    if (!matchedUci) {
      return {
        success: false,
        format: 'plain_chinese',
        title,
        initialFen,
        moves,
        chineseMoves,
        headers,
        result,
        error: `Move ${i + 1} (${token}) could not be resolved in position ${currentFen}`,
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
        format: 'plain_chinese',
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
    format: 'plain_chinese',
    title,
    initialFen,
    moves,
    chineseMoves,
    headers,
    result,
  };
}
