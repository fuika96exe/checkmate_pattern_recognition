export type Side = "red" | "black";

export interface ChoiceOccurrence {
  id: string;
  formedAtPly: number;
  wing: "left" | "right" | null;
  originFile: "b" | "h" | null;
  provisional: boolean;
  source: "fen" | "move" | "memory";
  lockGroup: string | null;
  eligibleForName: boolean;
  suppressedBy: string | null;
}

export interface SideMemory {
  choicePath: ChoiceOccurrence[];
  compositeSystems: ChoiceOccurrence[];
  formedShapes: ChoiceOccurrence[];
  locks: Record<string, string>;
  facts: string[];
}

export interface RecognitionState {
  schemaVersion: string;
  rulesVersion: string;
  ply: number;
  fen: string;
  sideMoves: Record<Side, number>;
  pieceIdentity: Record<string, string>;
  currentShapes: Record<Side, string[]>;
  openingMemory: { red: SideMemory; black: SideMemory; baseMatchupId: string | null };
  classification: {
    displayName: string;
    displayNameEn?: string;
    certainty: "pending" | "provisional" | "confirmed";
    redMainId: string | null;
    redMainLabel: string | null;
    redModifiers: string[];
    blackMainId: string | null;
    blackMainLabel: string | null;
    blackModifiers: string[];
    redSystem: string | null;
    blackSystem: string | null;
    baseMatchupId: string | null;
    templateId: string | null;
    evidence: string[];
    diagnostics: string[];
  };
}

export interface MoveRecord {
  ply: number;
  side: Side;
  ucci: string;
  chineseNotation: string;
  fromSquare: string;
  toSquare: string;
}

export interface PositionResponse { state: RecognitionState; legalMoves: string[] }
export interface AdvanceResponse extends PositionResponse { move: MoveRecord }

export interface MemoryPreset {
  redChoicePath: string[];
  blackChoicePath: string[];
  blackComposite: string | null;
  redWing: "left" | "right" | null;
  blackWing: "left" | "right" | null;
}

export interface TestCase {
  id: string;
  name: string;
  fen: string;
  expectedName: string;
  memoryPreset: MemoryPreset;
  notes: string;
  source: "built_in" | "user";
  createdAt?: string;
}

export interface TestRunResult {
  id: string;
  passed: boolean;
  expectedName: string;
  actualName: string;
  diagnostics: string[];
}

export interface RunAllResponse { total: number; passed: number; results: TestRunResult[] }

export type PatternId =
  | "CROWNED_CHECKMATE"
  | "EUNUCHS_CHASING_EMPEROR_CHECKMATE"
  | "CENTROID_PAWN_CHECKMATE"
  | "CANNONS_SANDWICHING_CHARIOT_CHECKMATE"
  | "DOUBLE_CANNON_CHECKMATE"
  | "DOUBLE_TOAST_CHECKMATE"
  | "SMOTHERED_CANNON_CHECKMATE"
  | "HEAVEN_AND_EARTH_CANNON_CHECKMATE"
  | "IRON_BOLT_CHECKMATE"
  | "DRAWER_CHECKMATE"
  | "THROAT_CUTTING_CHECKMATE"
  | "THREE_CHARIOTS_ATTACKING_ADVISOR_CHECKMATE"
  | "TWO_DEVILS_KNOCKING_CHECKMATE"
  | "DOUBLE_CHARIOTS_CHECKMATE"
  | "DISCOVERED_HORSE_CHECKMATE"
  | "CENTROID_CHARIOT_CHECKMATE"
  | "TIGER_SILHOUETTE_CHECKMATE"
  | "HORSE_CANNON_CHECKMATE"
  | "DOUBLE_HORSES_DRINKING_SPRING_CHECKMATE"
  | "DOUBLE_CHECK_CHECKMATE"
  | "ELBOW_HORSE_CHECKMATE"
  | "PALCORNER_HORSE_CHECKMATE"
  | "ANGLER_HORSE_CHECKMATE"
  | "SMOTHERED_CHECKMATE"
  | "WHITE_FACE_GENERAL"
  | "STALEMATE";

export interface PatternMatch { patternId: PatternId; patternNameZh: string; detected: boolean; causal: boolean; fen: string; moves: string[]; analysis: { sideToMove: Side; kingSquare: string; isCheck: boolean; isCheckmate: boolean; isStalemate: boolean; legalMoves: string[]; checkingPieces: { square: string; reason: string }[] }; features: Record<string, unknown>; diagnostics: string[]; }

export interface PatternAnalysis { requestedPatternId: PatternId | null; fen: string; moves: string[]; analysis: { sideToMove: Side; kingSquare: string; isCheck: boolean; isCheckmate: boolean; isStalemate: boolean; legalMoves: string[]; checkingPieces: { square: string; reason: string }[] }; bestMatch: PatternMatch | null; matches: PatternMatch[]; }

export interface PuzzleRecord {
  key: string;
  id: string;
  rating: number | null;
  initialFen: string;
  blunderMove: string;
  solverSide: Side | null;
  pv: string[];
  moveCount: number;
  importStatus: "ready" | "invalid";
  importErrors: string[];
}

export interface PuzzleDataset {
  schemaVersion: string;
  datasetVersion: string;
  generatedAt: string;
  sourceFile: string;
  puzzleCount: number;
  invalidCount: number;
  puzzles: PuzzleRecord[];
}

export interface PuzzleExpectations {
  schemaVersion: string;
  expectations: Record<string, PatternId[]>;
}

export interface PuzzleTimelineEntry {
  index: number;
  fen: string;
  move: string | null;
}

export interface PuzzleLineResponse {
  rulesVersion: string;
  valid: boolean;
  error: string | null;
  failedMoveIndex: number | null;
  timeline: PuzzleTimelineEntry[];
  analysis: PatternAnalysis | null;
}

export type PuzzleRecognitionStatus = "unanalyzed" | "analyzing" | "matched" | "unmatched" | "invalid";

export interface PuzzleRecognitionSummary {
  status: Exclude<PuzzleRecognitionStatus, "analyzing">;
  patternIds: PatternId[];
  error?: string;
}

export interface PuzzleRecognitionDataset {
  schemaVersion: string;
  datasetVersion: string;
  rulesVersion: string;
  generatedAt: string;
  puzzleCount: number;
  results: Record<string, PuzzleRecognitionSummary>;
}

export interface HealthResponse { status: string; rulesVersion: string }
