import type { EventRow } from "../types";

interface Props {
  events: EventRow[];
  onChange: (index: number, field: keyof EventRow, value: string) => void;
  onRemove: (index: number) => void;
  errorCells: Set<string>;
}

const FIELDS: { key: keyof EventRow; label: string; hint: string; width: string }[] = [
  { key: "id", label: "编号", hint: "A–Z", width: "3.4rem" },
  { key: "device", label: "设备", hint: "设备标识", width: "9rem" },
  { key: "serial", label: "设备内序号", hint: "正整数", width: "6.5rem" },
  { key: "observedRank", label: "观测位次", hint: "1–20", width: "5.5rem" },
  { key: "windowLow", label: "区间下界", hint: "1–n", width: "5.5rem" },
  { key: "windowHigh", label: "区间上界", hint: "1–n", width: "5.5rem" },
];

export function EventTable({ events, onChange, onRemove, errorCells }: Props) {
  return (
    <div className="table-wrap">
      <table className="editor">
        <thead>
          <tr>
            <th>#</th>
            {FIELDS.map((f) => (
              <th key={f.key} style={{ minWidth: f.width }}>
                {f.label}
                <span className="col-hint">{f.hint}</span>
              </th>
            ))}
            <th aria-label="操作" />
          </tr>
        </thead>
        <tbody>
          {events.map((row, index) => (
            <tr key={index}>
              <td className="row-index">{index + 1}</td>
              {FIELDS.map((f) => {
                const key = `event:${index}:${f.key}`;
                const bad =
                  errorCells.has(key) || errorCells.has(`event:${index}`);
                return (
                  <td key={f.key}>
                    <input
                      className={bad ? "bad" : ""}
                      value={row[f.key]}
                      onChange={(e) => onChange(index, f.key, e.target.value)}
                      spellCheck={false}
                      maxLength={f.key === "device" ? 64 : 4}
                    />
                  </td>
                );
              })}
              <td>
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => onRemove(index)}
                  title="删除该事件"
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
