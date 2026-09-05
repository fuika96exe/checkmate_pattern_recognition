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

export interface GameBranch {
  branchId: number; // 0 for main line, 1..N for variations
  parentBranchId: number; // -1 for main line, >= 0 for parent branch
  branchPly: number; // 1-based ply where divergence starts (0 for main line)
  divergenceMoveUci?: string; // First UCI move of this branch (e.g. "a9b9")
  divergenceMoveChinese?: string; // First Chinese notation move (e.g. "车１平２")
  name: string; // Display name e.g. "主线 (63步)", "变着 13 (第 20 步 车１平２ · 39步)"
  moves: string[]; // Full sequence of UCI moves from start of game to end of branch
  chineseMoves: string[]; // Full sequence of Chinese notation moves
  branchOnlyMoves: string[]; // Moves exclusive to this branch (diverging part)
  comments: Record<number, string>; // Comments mapped by ply (0 = opening remark)
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
  comments?: Record<number, string>; // Main line comments mapped by ply (0 = initial position)
  branches?: GameBranch[]; // Full variation tree (includes branch 0 and variations)
}

