import { START_FEN, applyMove, boardToFen, uciToChinese } from './board-rules.ts';
import type { GameBranch, ImportResult } from './types.ts';

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

function dpxqToUciList(movelist: string): string[] {
  const moves: string[] = [];
  for (let i = 0; i + 4 <= movelist.length; i += 4) {
    const x1 = parseInt(movelist[i], 10);
    const y1 = parseInt(movelist[i + 1], 10);
    const x2 = parseInt(movelist[i + 2], 10);
    const y2 = parseInt(movelist[i + 3], 10);
    const from = `${String.fromCharCode(97 + x1)}${9 - y1}`;
    const to = `${String.fromCharCode(97 + x2)}${9 - y2}`;
    moves.push(`${from}${to}`);
  }
  return moves;
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

  // 1. Extract raw comments
  // Format: [DhtmlXQ_comment0]...[/DhtmlXQ_comment0] or [DhtmlXQ_comment13_28]...[/DhtmlXQ_comment13_28]
  const rawComments: Array<{ branchId: number; ply: number; text: string }> = [];
  const commentRegex = /\[DhtmlXQ_comment(\d+)(?:_(\d+))?\]([\s\S]*?)\[\/DhtmlXQ_comment\1(?:_\2)?\]/gi;
  let commentMatch: RegExpExecArray | null;
  while ((commentMatch = commentRegex.exec(text)) !== null) {
    const isBranchComment = commentMatch[2] !== undefined;
    const branchId = isBranchComment ? parseInt(commentMatch[1], 10) : 0;
    const ply = isBranchComment ? parseInt(commentMatch[2], 10) : parseInt(commentMatch[1], 10);
    const commentBody = commentMatch[3]
      .replace(/\|\|\|\|/g, '\n\n')
      .replace(/\|\|/g, '\n')
      .trim();
    if (commentBody) {
      rawComments.push({ branchId, ply, text: commentBody });
    }
  }

  // 2. Validate and build main line (Branch 0)
  const mainMoves = dpxqToUciList(movelist);
  const mainChineseMoves: string[] = [];
  let currentFen = initialFen;

  for (let i = 0; i < mainMoves.length; i++) {
    const uci = mainMoves[i];
    try {
      const ch = uciToChinese(currentFen, uci);
      mainChineseMoves.push(ch);
      currentFen = applyMove(currentFen, uci);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        success: false,
        format: 'dpxq_ubb',
        title,
        initialFen,
        moves: mainMoves.slice(0, i),
        chineseMoves: mainChineseMoves,
        headers,
        result,
        error: `Move ${i + 1} (${uci}) failed: ${msg}`,
        failedMoveIndex: i,
      };
    }
  }

  if (mainMoves.length === 0) {
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

  // 3. Extract and parse branch definitions
  // Format: [DhtmlXQ_move_parentBranchId_branchPly_branchId]...[/DhtmlXQ_move_...]
  interface RawBranchInfo {
    branchId: number;
    parentBranchId: number;
    branchPly: number;
    branchOnlyMoves: string[];
  }

  const rawBranchMap = new Map<number, RawBranchInfo>();
  rawBranchMap.set(0, {
    branchId: 0,
    parentBranchId: -1,
    branchPly: 0,
    branchOnlyMoves: mainMoves,
  });

  const branchRegex = /\[DhtmlXQ_move_(\d+)_(\d+)_(\d+)\]([\s\S]*?)\[\/DhtmlXQ_move_\1_\2_\3\]/gi;
  let branchMatch: RegExpExecArray | null;
  while ((branchMatch = branchRegex.exec(text)) !== null) {
    const parentBranchId = parseInt(branchMatch[1], 10);
    const branchPly = parseInt(branchMatch[2], 10);
    const branchId = parseInt(branchMatch[3], 10);
    const branchMoveStr = branchMatch[4].replace(/\s+/g, '');
    const bMoves = dpxqToUciList(branchMoveStr);

    rawBranchMap.set(branchId, {
      branchId,
      parentBranchId,
      branchPly,
      branchOnlyMoves: bMoves,
    });
  }

  // Helper to resolve full line moves for any branch
  function getFullLineMoves(bId: number): string[] {
    if (bId === 0) {
      return rawBranchMap.get(0)?.branchOnlyMoves || [];
    }
    const b = rawBranchMap.get(bId);
    if (!b) return [];
    const parentLine = getFullLineMoves(b.parentBranchId);
    const inherited = parentLine.slice(0, Math.max(0, b.branchPly - 1));
    return inherited.concat(b.branchOnlyMoves);
  }

  // Build comment map per branch (with parent comment inheritance before divergence point)
  const branchCommentsMap = new Map<number, Record<number, string>>();
  function getBranchComments(bId: number): Record<number, string> {
    if (branchCommentsMap.has(bId)) {
      return branchCommentsMap.get(bId)!;
    }
    const resultComments: Record<number, string> = {};
    const b = rawBranchMap.get(bId);
    if (b && b.parentBranchId >= 0) {
      const parentComments = getBranchComments(b.parentBranchId);
      for (const [pStr, cText] of Object.entries(parentComments)) {
        const p = parseInt(pStr, 10);
        if (p < b.branchPly) {
          resultComments[p] = cText;
        }
      }
    }
    for (const c of rawComments) {
      if (c.branchId === bId) {
        resultComments[c.ply] = c.text;
      }
    }
    branchCommentsMap.set(bId, resultComments);
    return resultComments;
  }

  // 4. Validate and construct GameBranch objects
  const branches: GameBranch[] = [];

  // Sort branches: branch 0 first, then by branchId
  const sortedBranchIds = Array.from(rawBranchMap.keys()).sort((a, b) => a - b);

  for (const bId of sortedBranchIds) {
    const bInfo = rawBranchMap.get(bId)!;
    const fullMoves = getFullLineMoves(bId);
    const commentsForBranch = getBranchComments(bId);

    // Validate branch moves and generate Chinese notation
    const fullChineseMoves: string[] = [];
    let branchFen = initialFen;
    let isValid = true;

    for (let i = 0; i < fullMoves.length; i++) {
      const uci = fullMoves[i];
      try {
        const ch = uciToChinese(branchFen, uci);
        fullChineseMoves.push(ch);
        branchFen = applyMove(branchFen, uci);
      } catch {
        // If a variation has an invalid move, skip or truncate it gracefully
        isValid = false;
        break;
      }
    }

    if (!isValid && bId !== 0) {
      continue; // Skip invalid non-main variation
    }

    let divergenceMoveUci: string | undefined;
    let divergenceMoveChinese: string | undefined;
    let branchName = `主线 (${fullMoves.length}步)`;

    if (bId !== 0) {
      divergenceMoveUci = bInfo.branchOnlyMoves[0];
      divergenceMoveChinese = fullChineseMoves[bInfo.branchPly - 1] || '';
      const roundNum = Math.ceil(bInfo.branchPly / 2);
      const isBlack = (initialFen.split(' ')[1] === 'b' ? bInfo.branchPly % 2 === 1 : bInfo.branchPly % 2 === 0);
      const sideStr = isBlack ? '黑方' : '红方';
      const parentLabel = bInfo.parentBranchId === 0 ? '' : `分自变着 ${bInfo.parentBranchId} `;
      branchName = `变着 ${bId} (${parentLabel}第 ${roundNum} 回合${sideStr}: ${divergenceMoveChinese} · ${fullMoves.length}步)`;
    }

    branches.push({
      branchId: bId,
      parentBranchId: bInfo.parentBranchId,
      branchPly: bInfo.branchPly,
      divergenceMoveUci,
      divergenceMoveChinese,
      name: branchName,
      moves: fullMoves,
      chineseMoves: fullChineseMoves,
      branchOnlyMoves: bInfo.branchOnlyMoves,
      comments: commentsForBranch,
    });
  }

  const mainLineComments = getBranchComments(0);

  return {
    success: true,
    format: 'dpxq_ubb',
    title: red && black ? `${red} vs ${black}` : title,
    initialFen,
    moves: mainMoves,
    chineseMoves: mainChineseMoves,
    headers,
    result,
    comments: mainLineComments,
    branches,
  };
}

