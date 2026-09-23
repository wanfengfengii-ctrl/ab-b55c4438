import type { EventRow, OrderingRow } from "../types";

interface Props {
  events: EventRow[];
  orderings: OrderingRow[];
  onChange: (index: number, field: keyof OrderingRow, value: string) => void;
  onRemove: (index: number) => void;
  errorCells: Set<string>;
  errorRows: Set<number>;
}

export function OrderingTable({
  events,
  orderings,
  onChange,
  onRemove,
  errorCells,
  errorRows,
}: Props) {
  const knownIds = events.map((e) => e.id.trim()).filter(Boolean);

  const endSelect = (index: number, field: "before" | "after", value: string) => {
    const rowBad =
      errorCells.has(`ordering:${index}:${field}`) ||
      errorRows.has(index);
    return (
      <select
        className={rowBad ? "bad" : ""}
        value={value}
        onChange={(e) => onChange(index, field, e.target.value)}
      >
        <option value="">选择编号…</option>
        {knownIds.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
    );
  };

  return (
    <div className="table-wrap">
      {orderings.length === 0 ? (
        <p className="empty-hint">暂无显式先后关系 (同设备内仍按序号升序回放)。</p>
      ) : (
        <table className="editor">
          <thead>
            <tr>
              <th>#</th>
              <th>先发生 (before)</th>
              <th />
              <th>后发生 (after)</th>
              <th aria-label="操作" />
            </tr>
          </thead>
          <tbody>
            {orderings.map((row, index) => (
              <tr key={index} className={errorRows.has(index) ? "row-bad" : ""}>
                <td className="row-index">{index + 1}</td>
                <td>{endSelect(index, "before", row.before)}</td>
                <td className="arrow">→</td>
                <td>{endSelect(index, "after", row.after)}</td>
                <td>
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => onRemove(index)}
                    title="删除该关系"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
