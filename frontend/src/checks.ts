import type { EventInput, PrecedenceInput } from "./types";

export interface EventCheck {
  id: string;
  device: string;
  seq: number;
  position: number;
  lo: number;
  hi: number;
  inWindow: boolean;
  observed: number;
  deviation: number;
}

export interface PairCheck {
  kind: "device" | "precedence";
  label: string;
  beforeId: string;
  afterId: string;
  beforePos: number;
  afterPos: number;
  ok: boolean;
}

export interface TimelineReport {
  positions: Record<string, number>;
  eventChecks: EventCheck[];
  pairChecks: PairCheck[];
  totalCost: number;
  allOk: boolean;
}

/** 对一条回放时间线逐条核对：窗口、设备内序号顺序、显式先后关系，并汇总代价。 */
export function analyzeTimeline(
  events: EventInput[],
  precedences: PrecedenceInput[],
  order: string[]
): TimelineReport {
  const positions: Record<string, number> = {};
  order.forEach((id, i) => {
    positions[id] = i + 1; // 位置从 1 起算
  });

  const eventChecks: EventCheck[] = events.map((e) => {
    const position = positions[e.id];
    return {
      id: e.id,
      device: e.device,
      seq: e.seq,
      position,
      lo: e.lo,
      hi: e.hi,
      inWindow: e.lo <= position && position <= e.hi,
      observed: e.observed,
      deviation: Math.abs(position - e.observed),
    };
  });

  const pairChecks: PairCheck[] = [];

  const byDevice = new Map<string, EventInput[]>();
  for (const e of events) {
    const list = byDevice.get(e.device) ?? [];
    list.push(e);
    byDevice.set(e.device, list);
  }
  for (const [device, list] of byDevice) {
    const sorted = [...list].sort((a, b) => a.seq - b.seq);
    for (let i = 0; i + 1 < sorted.length; i += 1) {
      const a = sorted[i];
      const b = sorted[i + 1];
      pairChecks.push({
        kind: "device",
        label: `${device}: #${a.seq} ${a.id} → #${b.seq} ${b.id}`,
        beforeId: a.id,
        afterId: b.id,
        beforePos: positions[a.id],
        afterPos: positions[b.id],
        ok: positions[a.id] < positions[b.id],
      });
    }
  }

  for (const p of precedences) {
    pairChecks.push({
      kind: "precedence",
      label: `${p.before} → ${p.after}`,
      beforeId: p.before,
      afterId: p.after,
      beforePos: positions[p.before],
      afterPos: positions[p.after],
      ok: positions[p.before] < positions[p.after],
    });
  }

  const totalCost = eventChecks.reduce((sum, c) => sum + c.deviation, 0);
  const allOk =
    eventChecks.every((c) => c.inWindow) && pairChecks.every((c) => c.ok);
  return { positions, eventChecks, pairChecks, totalCost, allOk };
}
