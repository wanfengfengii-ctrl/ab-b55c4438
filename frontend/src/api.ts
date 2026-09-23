import type {
  EventRow,
  OrderingRow,
  SolveResponse,
} from "./types";

/**
 * Rebuild the replay through the business API. The backend is the single
 * source of truth for feasibility/optimality; the UI independently
 * re-checks every returned timeline in verifier.ts.
 */
export async function solve(
  events: EventRow[],
  orderings: OrderingRow[],
): Promise<SolveResponse> {
  const resp = await fetch("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ events, orderings }),
  });
  // Body-shape errors come back as 422 with the same response envelope.
  if (resp.status !== 200 && resp.status !== 422) {
    throw new Error(`业务 API 异常: HTTP ${resp.status}`);
  }
  return (await resp.json()) as SolveResponse;
}
