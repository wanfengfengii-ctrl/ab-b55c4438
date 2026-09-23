import type { EventRow, OrderingRow, ParsedEvent } from "./types";

export function parseEvent(row: EventRow): ParsedEvent | null {
  const serial = Number(row.serial);
  const observedRank = Number(row.observedRank);
  const windowLow = Number(row.windowLow);
  const windowHigh = Number(row.windowHigh);
  if (
    !row.id.trim() ||
    !row.device.trim() ||
    !Number.isInteger(serial) ||
    !Number.isInteger(observedRank) ||
    !Number.isInteger(windowLow) ||
    !Number.isInteger(windowHigh)
  ) {
    return null;
  }
  return {
    id: row.id.trim(),
    device: row.device.trim(),
    serial,
    observedRank,
    windowLow,
    windowHigh,
  };
}

export function parseAll(
  events: EventRow[],
): { parsed: Map<string, ParsedEvent>; ok: boolean } {
  const parsed = new Map<string, ParsedEvent>();
  let ok = true;
  for (const row of events) {
    const p = parseEvent(row);
    if (!p) {
      ok = false;
      continue;
    }
    if (!parsed.has(p.id)) parsed.set(p.id, p);
  }
  return { parsed, ok };
}

export function parseOrdering(row: OrderingRow): { before: string; after: string } | null {
  if (!row.before.trim() || !row.after.trim()) return null;
  return { before: row.before.trim(), after: row.after.trim() };
}
