export interface EventInput {
  id: string;
  device: string;
  seq: number;
  observed: number;
  lo: number;
  hi: number;
}

export interface PrecedenceInput {
  before: string;
  after: string;
}

export interface Timeline {
  order: string[];
}

export interface SolveResponse {
  status: "unique" | "multiple" | "infeasible";
  cost?: number;
  timelines: Timeline[];
}

export interface ApiError {
  loc: string;
  msg: string;
}
