import { describe, expect, it } from "vitest";
import { analyzeTimeline } from "./checks";
import type { EventInput, PrecedenceInput } from "./types";

const events: EventInput[] = [
  { id: "A", device: "M1", seq: 1, observed: 1, lo: 1, hi: 4 },
  { id: "B", device: "M1", seq: 2, observed: 2, lo: 1, hi: 4 },
  { id: "C", device: "M2", seq: 1, observed: 1, lo: 1, hi: 4 },
  { id: "D", device: "M2", seq: 2, observed: 2, lo: 1, hi: 4 },
];

describe("analyzeTimeline", () => {
  it("计算位置、偏差与总代价，约束全部满足", () => {
    const report = analyzeTimeline(events, [], ["A", "B", "C", "D"]);
    expect(report.positions).toEqual({ A: 1, B: 2, C: 3, D: 4 });
    expect(report.eventChecks.map((c) => c.deviation)).toEqual([0, 0, 2, 2]);
    expect(report.totalCost).toBe(4);
    expect(report.allOk).toBe(true);
    expect(report.eventChecks.every((c) => c.inWindow)).toBe(true);
    // 设备链 M1: A→B，M2: C→D
    expect(report.pairChecks).toHaveLength(2);
    expect(report.pairChecks.every((c) => c.kind === "device" && c.ok)).toBe(true);
  });

  it("检出窗口越界", () => {
    const tight: EventInput[] = events.map((e) =>
      e.id === "D" ? { ...e, lo: 1, hi: 2 } : e
    );
    const report = analyzeTimeline(tight, [], ["A", "B", "C", "D"]);
    const d = report.eventChecks.find((c) => c.id === "D")!;
    expect(d.position).toBe(4);
    expect(d.inWindow).toBe(false);
    expect(report.allOk).toBe(false);
  });

  it("检出设备内序号顺序被违反", () => {
    const report = analyzeTimeline(events, [], ["B", "A", "C", "D"]);
    const deviceCheck = report.pairChecks.find((c) => c.kind === "device" && c.beforeId === "A")!;
    expect(deviceCheck.ok).toBe(false);
    expect(report.allOk).toBe(false);
  });

  it("检出显式先后关系被违反", () => {
    const precs: PrecedenceInput[] = [{ before: "D", after: "A" }];
    const report = analyzeTimeline(events, precs, ["A", "B", "C", "D"]);
    const check = report.pairChecks.find((c) => c.kind === "precedence")!;
    expect(check.beforePos).toBe(4);
    expect(check.afterPos).toBe(1);
    expect(check.ok).toBe(false);
    expect(report.allOk).toBe(false);
  });

  it("设备内序号按 seq 排序而非编号", () => {
    const swapped: EventInput[] = [
      { id: "X", device: "M1", seq: 2, observed: 1, lo: 1, hi: 2 },
      { id: "Y", device: "M1", seq: 1, observed: 2, lo: 1, hi: 2 },
      { id: "P", device: "M2", seq: 1, observed: 3, lo: 3, hi: 4 },
      { id: "Q", device: "M2", seq: 2, observed: 4, lo: 3, hi: 4 },
    ];
    const report = analyzeTimeline(swapped, [], ["Y", "X", "P", "Q"]);
    expect(report.allOk).toBe(true);
    expect(report.totalCost).toBe(2);
    const chain = report.pairChecks.find((c) => c.kind === "device")!;
    expect(chain.label).toContain("Y");
    expect(chain.beforeId).toBe("Y");
    expect(chain.afterId).toBe("X");
  });
});
