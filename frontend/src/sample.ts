import type { EventRow, OrderingRow } from "./types";

/**
 * Six events over three devices. D and E share observed rank 4, so swapping
 * their positions 4/5 preserves the total deviation: the sample has two
 * optimal timelines (cost 1). The explicit edge C -> E holds in both.
 */
export const sampleEvents: EventRow[] = [
  { id: "A", device: "line-1", serial: "1", observedRank: "1", windowLow: "1", windowHigh: "6" },
  { id: "B", device: "line-2", serial: "1", observedRank: "2", windowLow: "1", windowHigh: "6" },
  { id: "C", device: "line-1", serial: "2", observedRank: "3", windowLow: "1", windowHigh: "6" },
  { id: "D", device: "line-2", serial: "2", observedRank: "4", windowLow: "1", windowHigh: "6" },
  { id: "E", device: "line-3", serial: "1", observedRank: "4", windowLow: "1", windowHigh: "6" },
  { id: "F", device: "line-4", serial: "1", observedRank: "6", windowLow: "1", windowHigh: "6" },
];

export const sampleOrderings: OrderingRow[] = [{ before: "C", after: "E" }];
