/** Types mirroring the FastAPI contract (camelCase on the wire). */

export interface EventRow {
  id: string;
  device: string;
  serial: string;
  observedRank: string;
  windowLow: string;
  windowHigh: string;
}

export interface OrderingRow {
  before: string;
  after: string;
}

export interface ErrorItem {
  code: string;
  message: string;
  path: string[];
  eventId?: string | null;
  orderingIndex?: number | null;
}

export interface Witness {
  timeline: string[];
}

export type SolveStatus =
  | "invalid_input"
  | "infeasible"
  | "unique"
  | "multiple";

export interface SolveResponse {
  status: SolveStatus;
  reason?: "cycle" | "window" | null;
  optimalCost?: number | null;
  witnesses: Witness[];
  errors: ErrorItem[];
}

export interface ParsedEvent {
  id: string;
  device: string;
  serial: number;
  observedRank: number;
  windowLow: number;
  windowHigh: number;
}
