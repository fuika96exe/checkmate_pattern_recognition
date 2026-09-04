import { START_FEN, applyMove, uciToChinese } from './board-rules.ts';
import { stripComments } from './preprocessor.ts';
import type { ImportResult } from './types.ts';

export function isICCS(text: string): boolean {
  if (text.includes('[Format "ICCS"]') || text.includes('Format "ICCS"')) return true;
  // Or check if it contains typical ICCS move pattern like H2-D2
  const iccsMoveRegex = /\b[A-I][0-9]-[A-I][0-9]\b/i;
  return iccsMoveRegex.test(text);
}

export function parseICCS(text: string): ImportResult {
  const headers: Record<string, string> = {};
  const headerRegex = /^\[([A-Za-z0-9_]+)\s+"([^"]*)"\]/gm;
  let match: RegExpExecArray | null;
  while ((match = headerRegex.exec(text)) !== null) {
    headers[match[1]] = match[2];
  }

  const initialFen = headers.FEN || START_FEN;
  const title =
    headers.Title ||
    (headers.Red && headers.Black ? `${headers.Red} vs ${headers.Black}` : 'ICCS Game');
  const result = headers.Result;

  // Extract moves after stripping comments and header brackets
  const cleanText = stripComments(text).replace(/^\[[A-Za-z0-9_]+\s+"[^"]*"\]/gm, ' ');
  const moveRegex = /\b([a-i][0-9])-([a-i][0-9])\b/gi;
  const moves: string[] = [];
  const chineseMoves: string[] = [];
  let currentFen = initialFen;

  while ((match = moveRegex.exec(cleanText)) !== null) {
    const uci = `${match[1].toLowerCase()}${match[2].toLowerCase()}`;
    try {
      const ch = uciToChinese(currentFen, uci);
      chineseMoves.push(ch);
      moves.push(uci);
      currentFen = applyMove(currentFen, uci);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        success: false,
        format: 'iccs',
        title,
        initialFen,
        moves,
        chineseMoves,
        headers,
        result,
        error: `Move ${moves.length + 1} (${uci}) failed: ${msg}`,
        failedMoveIndex: moves.length,
      };
    }
  }

  if (moves.length === 0) {
    return {
      success: false,
      format: 'iccs',
      title,
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
    format: 'iccs',
    title,
    initialFen,
    moves,
    chineseMoves,
    headers,
    result,
  };
}
