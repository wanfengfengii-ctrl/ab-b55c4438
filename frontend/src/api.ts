import type { ApiError, EventInput, PrecedenceInput, SolveResponse } from "./types";

const API_BASE: string = import.meta.env.VITE_API_BASE ?? "/api";

export class ValidationError extends Error {
  constructor(public errors: ApiError[]) {
    super("输入校验失败");
    this.name = "ValidationError";
  }
}

export function toPayload(events: EventInput[], precedences: PrecedenceInput[]) {
  return {
    events: events.map((e) => ({
      id: e.id,
      device: e.device,
      seq: e.seq,
      observed: e.observed,
      window: { lo: e.lo, hi: e.hi },
    })),
    precedences: precedences.map((p) => ({ before: p.before, after: p.after })),
  };
}

export async function solve(
  events: EventInput[],
  precedences: PrecedenceInput[]
): Promise<SolveResponse> {
  const res = await fetch(`${API_BASE}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toPayload(events, precedences)),
  });
  if (res.status === 422) {
    const body = (await res.json()) as { detail?: ApiError[] };
    throw new ValidationError(body.detail ?? []);
  }
  if (!res.ok) {
    throw new Error(`服务异常（HTTP ${res.status}）`);
  }
  return (await res.json()) as SolveResponse;
}
