import { START_FEN, applyMove, legalMoves, uciToChinese } from './board-rules.ts';
import { isChineseNotation, parseChineseGame } from './chinese-parser.ts';
import { isDhtmlXQ, parseDhtmlXQ } from './dpxq-parser.ts';
import { isICCS, parseICCS } from './iccs-parser.ts';
import type { ImportResult } from './types.ts';
import { isWXF, parseWXF } from './wxf-parser.ts';

export * from './board-rules.ts';
export * from './types.ts';

export function importXiangqiGame(rawText: string): ImportResult {
  if (!rawText || !rawText.trim()) {
    return {
      success: false,
      format: 'plain_chinese',
      title: 'Empty Notation',
      initialFen: START_FEN,
      moves: [],
      chineseMoves: [],
      headers: {},
      error: 'Input text is empty',
    };
  }

  // 1. DhtmlXQ format
  if (isDhtmlXQ(rawText)) {
    return parseDhtmlXQ(rawText);
  }

  // 2. ICCS format (e.g. H2-D2 G6-G5)
  if (isICCS(rawText)) {
    return parseICCS(rawText);
  }

  // 3. WXF format (e.g. C8.5 c2.5, H8+7 h2+3)
  if (isWXF(rawText)) {
    return parseWXF(rawText);
  }

  // 4. Chinese notation (Standard PGN, Dpxq plain text, compact unspaced)
  if (isChineseNotation(rawText)) {
    return parseChineseGame(rawText);
  }

  // 5. Raw UCI stream (e.g. h2e2 h9e7 b0c2 ...)
  const uciTokens = rawText
    .replace(/\b\d+\.\s*/g, ' ')
    .split(/\s+/)
    .map((t) => t.trim().toLowerCase())
    .filter((t) => /^[a-i][0-9][a-i][0-9]$/.test(t));

  if (uciTokens.length > 0) {
    let currentFen = START_FEN;
    const moves: string[] = [];
    const chineseMoves: string[] = [];

    for (let i = 0; i < uciTokens.length; i++) {
      const uci = uciTokens[i];
      const legals = legalMoves(currentFen);
      if (!legals.includes(uci)) {
        return {
          success: false,
          format: 'uci',
          title: 'UCI Game',
          initialFen: START_FEN,
          moves,
          chineseMoves,
          headers: {},
          error: `Move ${i + 1} (${uci}) is illegal in position ${currentFen}`,
          failedMoveIndex: i,
        };
      }
      try {
        chineseMoves.push(uciToChinese(currentFen, uci));
        moves.push(uci);
        currentFen = applyMove(currentFen, uci);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return {
          success: false,
          format: 'uci',
          title: 'UCI Game',
          initialFen: START_FEN,
          moves,
          chineseMoves,
          headers: {},
          error: `Move ${i + 1} (${uci}) failed: ${msg}`,
          failedMoveIndex: i,
        };
      }
    }

    return {
      success: true,
      format: 'uci',
      title: 'UCI Game',
      initialFen: START_FEN,
      moves,
      chineseMoves,
      headers: {},
    };
  }

  // Fallback try Chinese parser in case there are odd characters or formatting
  const fallbackResult = parseChineseGame(rawText);
  if (fallbackResult.success) {
    return fallbackResult;
  }

  return {
    success: false,
    format: 'plain_chinese',
    title: 'Unknown Format',
    initialFen: START_FEN,
    moves: [],
    chineseMoves: [],
    headers: {},
    error: fallbackResult.error || '无法识别该棋谱格式或未包含有效走法',
  };
}
