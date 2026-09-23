import { useMemo } from "react";
import type {
  EventRow,
  OrderingRow,
  SolveResponse,
} from "../types";
import { parseAll } from "../parse";
import { verifyTimeline } from "../verifier";

interface Props {
  result: SolveResponse;
  events: EventRow[];
  orderings: OrderingRow[];
  witnessIdx: number;
  onSelectWitness: (idx: number) => void;
}

const REASON_TEXT: Record<string, string> = {
  cycle: "先后关系(含同设备序号链)构成环路, 任何排列都无法同时满足。",
  window: "位置闭区间互斥或与先后关系冲突, 不存在能放下全部事件的排列。",
};

export function ResultPanel({
  result,
  events,
  orderings,
  witnessIdx,
  onSelectWitness,
}: Props) {
  const { parsed } = useMemo(() => parseAll(events), [events]);
  const parsedEvents = useMemo(() => Array.from(parsed.values()), [parsed]);

  const witnesses = result.witnesses;
  const idx = Math.min(witnessIdx, Math.max(0, witnesses.length - 1));
  const timeline = witnesses[idx]?.timeline ?? [];

  const verification = useMemo(
    () => verifyTimeline(parsedEvents, orderings, timeline),
    [parsedEvents, orderings, timeline],
  );

  if (result.status === "infeasible") {
    return (
      <section className="panel result infeasible">
        <h2>无解</h2>
        <p className="verdict">
          {result.reason ? REASON_TEXT[result.reason] : "约束互相矛盾, 不存在可行回放。"}
        </p>
        <p className="verdict-sub">
          诊断类别: <code>{result.reason ?? "unknown"}</code> ·
          环路 (cycle) 或窗口互斥 (window) 均属于无解。
        </p>
      </section>
    );
  }

  const costMatches = verification.totalCost === result.optimalCost;
  const multiple = result.status === "multiple";

  return (
    <section className="panel result feasible">
      <div className="result-head">
        <h2>{multiple ? "多最优解" : "唯一最优解"}</h2>
        <div className="cost-badge">
          最优代价 <strong>{result.optimalCost}</strong>
        </div>
      </div>

      {multiple && (
        <div className="witness-switch">
          <span>切换最优时间线 (按事件编号序列字母序):</span>
          {witnesses.map((w, i) => (
            <button
              key={i}
              type="button"
              className={i === idx ? "tab active" : "tab"}
              onClick={() => onSelectWitness(i)}
            >
              见证 {i + 1}: {w.timeline.join("")}
            </button>
          ))}
        </div>
      )}

      <div className="timeline">
        {timeline.map((id, pos) => (
          <span key={pos} className="chip">
            <span className="chip-pos">{pos + 1}</span>
            <span className="chip-id">{id}</span>
          </span>
        ))}
      </div>

      <h3 className="check-title">逐条核对</h3>
      <div className="check-summary">
        <span className={verification.ok ? "ok-dot" : "bad-dot"}>
          {verification.ok ? "✓ 全部约束成立" : "✗ 存在违反项"}
        </span>
        <span className={verification.deviceOrderOk ? "ok" : "bad"}>
          同设备序号顺序 {verification.deviceOrderOk ? "✓" : "✗"}
        </span>
        <span className={verification.orderingOk ? "ok" : "bad"}>
          显式先后关系 {verification.orderingOk ? "✓" : "✗"}
        </span>
        <span className={costMatches ? "ok" : "bad"}>
          页面重算代价 {verification.totalCost}
          {costMatches ? " = API 最优代价 ✓" : " ≠ API 最优代价 ✗"}
        </span>
      </div>

      <div className="table-wrap">
        <table className="check-table">
          <thead>
            <tr>
              <th>位置</th>
              <th>事件</th>
              <th>设备</th>
              <th>设备内序号</th>
              <th>观测位次</th>
              <th>允许区间</th>
              <th>窗口</th>
              <th>|位置−观测|</th>
            </tr>
          </thead>
          <tbody>
            {verification.items.map((it) => (
              <tr key={it.eventId}>
                <td>{it.position}</td>
                <td className="ev-id">{it.eventId}</td>
                <td>{it.device}</td>
                <td>{it.serial}</td>
                <td>{it.observedRank}</td>
                <td>
                  [{it.windowLow}, {it.windowHigh}]
                </td>
                <td className={it.inWindow ? "ok" : "bad"}>
                  {it.inWindow ? "✓" : "✗"}
                </td>
                <td>{it.deviation}</td>
              </tr>
            ))}
            <tr className="sum-row">
              <td colSpan={7}>总绝对差 (代价)</td>
              <td>{verification.totalCost}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {verification.violations.length > 0 && (
        <ul className="violation-list">
          {verification.violations.map((v, i) => (
            <li key={i}>{v}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
