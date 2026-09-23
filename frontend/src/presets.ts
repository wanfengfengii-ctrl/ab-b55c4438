import type { EventInput, PrecedenceInput } from "./types";

export interface Preset {
  name: string;
  events: EventInput[];
  precedences: PrecedenceInput[];
}

export const PRESETS: Preset[] = [
  {
    name: "产线示例（8 事件）",
    events: [
      { id: "A", device: "炉1", seq: 1, observed: 2, lo: 1, hi: 4 },
      { id: "B", device: "炉1", seq: 2, observed: 6, lo: 3, hi: 7 },
      { id: "C", device: "炉2", seq: 1, observed: 1, lo: 1, hi: 3 },
      { id: "D", device: "炉2", seq: 2, observed: 6, lo: 4, hi: 8 },
      { id: "E", device: "机3", seq: 1, observed: 4, lo: 2, hi: 6 },
      { id: "F", device: "机3", seq: 2, observed: 7, lo: 5, hi: 8 },
      { id: "G", device: "机4", seq: 1, observed: 3, lo: 1, hi: 5 },
      { id: "H", device: "机4", seq: 2, observed: 8, lo: 6, hi: 7 },
    ],
    precedences: [{ before: "C", after: "E" }],
  },
  {
    name: "多最优示例",
    events: [
      { id: "A", device: "M1", seq: 1, observed: 1, lo: 1, hi: 4 },
      { id: "B", device: "M1", seq: 2, observed: 2, lo: 1, hi: 4 },
      { id: "C", device: "M2", seq: 1, observed: 1, lo: 1, hi: 4 },
      { id: "D", device: "M2", seq: 2, observed: 2, lo: 1, hi: 4 },
    ],
    precedences: [],
  },
  {
    name: "无解示例（先后成环）",
    events: [
      { id: "A", device: "M1", seq: 1, observed: 1, lo: 1, hi: 4 },
      { id: "B", device: "M2", seq: 1, observed: 2, lo: 1, hi: 4 },
      { id: "C", device: "M3", seq: 1, observed: 3, lo: 1, hi: 4 },
      { id: "D", device: "M4", seq: 1, observed: 4, lo: 1, hi: 4 },
    ],
    precedences: [
      { before: "A", after: "B" },
      { before: "B", after: "A" },
    ],
  },
  {
    name: "无解示例（窗口互斥）",
    events: [
      { id: "A", device: "M1", seq: 1, observed: 1, lo: 1, hi: 1 },
      { id: "B", device: "M2", seq: 1, observed: 2, lo: 1, hi: 1 },
      { id: "C", device: "M3", seq: 1, observed: 3, lo: 1, hi: 4 },
      { id: "D", device: "M4", seq: 1, observed: 4, lo: 1, hi: 4 },
    ],
    precedences: [],
  },
];
