export type ImportFormat =
  | 'dpxq_ubb'
  | 'dpxq_text'
  | 'pgn'
  | 'iccs'
  | 'wxf'
  | 'compact_chinese'
  | 'plain_chinese'
  | 'uci';

export interface MoveStep {
  uci: string;
  chineseNotation: string;
  ply: number;
  side: 'r' | 'b';
  from: string;
  to: string;
}

export interface ImportResult {
  success: boolean;
  format: ImportFormat;
  title: string;
  initialFen: string;
  moves: string[]; // List of UCI move strings e.g. ["h2e2", "h9e7"]
  chineseMoves: string[]; // List of Chinese notation strings e.g. ["炮二平五", "马８进７"]
  headers: Record<string, string>;
  result?: string;
  error?: string;
  failedMoveIndex?: number;
}
