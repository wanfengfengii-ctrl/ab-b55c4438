import type { OrderingRow, ParsedEvent } from "./types";
import { parseOrdering } from "./parse";

/**
 * Independent client-side replay verifier. The UI never trusts the API
 * blindly: every returned timeline is checked here, item by item, and the
 * cost is recomputed from the same definition
 * (sum |actual position - observed rank|).
 */
export interface ItemCheck {
  eventId: string;
  device: string;
  serial: number;
  position: number;
  observedRank: number;
  windowLow: number;
  windowHigh: number;
  inWindow: boolean;
  deviation: number;
}

export interface VerifyResult {
  ok: boolean;
  totalCost: number;
  items: ItemCheck[];
  violations: string[];
  deviceOrderOk: boolean;
  orderingOk: boolean;
}

export function verifyTimeline(
  events: ParsedEvent[],
  orderings: OrderingRow[],
  timeline: string[],
): VerifyResult {
  const violations: string[] = [];
  const byId = new Map(events.map((e) => [e.id, e]));
  const n = events.length;

  // Permutation check: every event exactly once.
  const counts = new Map<string, number>();
  for (const id of timeline) counts.set(id, (counts.get(id) ?? 0) + 1);
  for (const e of events) {
    const c = counts.get(e.id) ?? 0;
    if (c === 0) violations.push(`排列缺少事件 ${e.id}`);
    if (c > 1) violations.push(`事件 ${e.id} 在排列中出现 ${c} 次`);
  }
  for (const id of counts.keys()) {
    if (!byId.has(id)) violations.push(`排列中存在未知事件 ${id}`);
  }

  const positionOf = new Map<string, number>();
  timeline.forEach((id, idx) => positionOf.set(id, idx + 1));

  // Per-item window + deviation.
  const items: ItemCheck[] = timeline
    .map((id) => byId.get(id))
    .filter((e): e is ParsedEvent => Boolean(e))
    .map((e) => {
      const position = positionOf.get(e.id)!;
      const inWindow = e.windowLow <= position && position <= e.windowHigh;
      if (!inWindow) {
        violations.push(
          `事件 ${e.id} 位于位置 ${position}, 超出其闭区间 [${e.windowLow}, ${e.windowHigh}]`,
        );
      }
      return {
        eventId: e.id,
        device: e.device,
        serial: e.serial,
        position,
        observedRank: e.observedRank,
        windowLow: e.windowLow,
        windowHigh: e.windowHigh,
        inWindow,
        deviation: Math.abs(position - e.observedRank),
      };
    });

  // Device serial order.
  let deviceOrderOk = true;
  const byDevice = new Map<string, ParsedEvent[]>();
  for (const e of events) {
    const list = byDevice.get(e.device) ?? [];
    list.push(e);
    byDevice.set(e.device, list);
  }
  for (const list of byDevice.values()) {
    list.sort((a, b) => a.serial - b.serial);
    for (let i = 1; i < list.length; i++) {
      const a = list[i - 1];
      const b = list[i];
      const pa = positionOf.get(a.id);
      const pb = positionOf.get(b.id);
      if (pa === undefined || pb === undefined) {
        deviceOrderOk = false;
        continue;
      }
      if (!(pa < pb)) {
        deviceOrderOk = false;
        violations.push(
          `设备 ${a.device} 内序号顺序被破坏: ${a.id}(#${a.serial}) 位置 ${pa} 不早于 ${b.id}(#${b.serial}) 位置 ${pb}`,
        );
      }
    }
  }

  // Explicit orderings.
  let orderingOk = true;
  orderings.forEach((row, idx) => {
    const edge = parseOrdering(row);
    if (!edge) return;
    const pa = positionOf.get(edge.before);
    const pb = positionOf.get(edge.after);
    if (pa === undefined || pb === undefined || !(pa < pb)) {
      orderingOk = false;
      violations.push(
        `第 ${idx + 1} 条显式先后关系 ${edge.before} → ${edge.after} 不成立 (位置 ${pa ?? "?"} vs ${pb ?? "?"})`,
      );
    }
  });

  const totalCost = items.reduce((sum, it) => sum + it.deviation, 0);
  const ok =
    violations.length === 0 &&
    timeline.length === n &&
    deviceOrderOk &&
    orderingOk;

  return { ok, totalCost, items, violations, deviceOrderOk, orderingOk };
}
