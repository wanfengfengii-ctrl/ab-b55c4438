import { useMemo, useState } from "react";
import { analyzeTimeline } from "../checks";
import type { EventInput, PrecedenceInput, SolveResponse } from "../types";

interface Props {
  result: SolveResponse;
  events: EventInput[];
  precedences: PrecedenceInput[];
}

const DEVICE_COLORS = [
  "#7c9eff",
  "#ffb86b",
  "#7be0a3",
  "#ff8fb2",
  "#c9a7ff",
  "#7bd7e0",
  "#e0d07b",
  "#a3e07b",
];

export default function ResultPanel({ result, events, precedences }: Props) {
  const [tab, setTab] = useState(0);

  const deviceColor = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of events) {
      if (!map.has(e.device)) {
        map.set(e.device, DEVICE_COLORS[map.size % DEVICE_COLORS.length]);
      }
    }
    return map;
  }, [events]);

  if (result.status === "infeasible") {
    return (
      <div className="status-banner infeasible">
        <strong>无解</strong>
        <span>
          不存在满足全部约束的回放（可能先后关系成环，或位置区间互斥）。
        </span>
      </div>
    );
  }

  const timeline = result.timelines[Math.min(tab, result.timelines.length - 1)];
  const report = analyzeTimeline(events, precedences, timeline.order);
  const rows = [...report.eventChecks].sort((a, b) => a.position - b.position);
  const costMatch = report.totalCost === result.cost;
  const byId = new Map(events.map((e) => [e.id, e]));

  return (
    <div>
      <div className={`status-banner ${result.status}`}>
        <strong>{result.status === "unique" ? "唯一最优" : "多最优"}</strong>
        <span>最优代价 = {result.cost}</span>
        {result.status === "multiple" && (
          <span>（按事件编号序列字母序给出最小两份见证，可切换）</span>
        )}
      </div>

      {result.timelines.length > 1 && (
        <div className="tabs">
          {result.timelines.map((_, i) => (
            <button
              key={i}
              className={i === tab ? "tab active" : "tab"}
              onClick={() => setTab(i)}
            >
              见证 {i + 1}
            </button>
          ))}
        </div>
      )}

      <div className="track">
        {timeline.order.map((id, pos) => {
          const e = byId.get(id);
          const color = deviceColor.get(e?.device ?? "") ?? "#999";
          return (
            <div key={id} className="cell" style={{ borderColor: color }}>
              <span className="pos">{pos + 1}</span>
              <span className="chip" style={{ background: color }}>
                {id}
              </span>
              <span className="dev">
                {e?.device}#{e?.seq}
              </span>
            </div>
          );
        })}
      </div>

      <h3>逐条核对</h3>
      <table className="grid checks">
        <thead>
          <tr>
            <th>事件</th>
            <th>设备#序号</th>
            <th>实际位置</th>
            <th>位置区间</th>
            <th>区间内</th>
            <th>观测位次</th>
            <th>偏差</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id}>
              <td>
                <span
                  className="chip"
                  style={{ background: deviceColor.get(c.device) }}
                >
                  {c.id}
                </span>
              </td>
              <td>
                {c.device}#{c.seq}
              </td>
              <td>{c.position}</td>
              <td>
                [{c.lo}, {c.hi}]
              </td>
              <td className={c.inWindow ? "ok" : "bad"}>
                {c.inWindow ? "✓" : "✗"}
              </td>
              <td>{c.observed}</td>
              <td>{c.deviation}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={6}>总代价（Σ|实际位置 − 观测位次|）</td>
            <td className={costMatch ? "ok" : "bad"}>
              {report.totalCost} {costMatch ? "✓" : `✗（API 返回 ${result.cost}）`}
            </td>
          </tr>
        </tfoot>
      </table>

      <h3>先后约束（{report.pairChecks.length}）</h3>
      <ul className="pairs">
        {report.pairChecks.map((c, i) => (
          <li key={i} className={c.ok ? "ok" : "bad"}>
            <span className="tag">
              {c.kind === "device" ? "设备序" : "显式"}
            </span>
            {c.label}：位置 {c.beforePos} &lt; {c.afterPos} {c.ok ? "✓" : "✗"}
          </li>
        ))}
      </ul>
    </div>
  );
}
