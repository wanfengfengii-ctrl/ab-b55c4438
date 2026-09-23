import type { ApiError, EventInput } from "../types";

interface Props {
  events: EventInput[];
  errors: ApiError[];
  onChange: (events: EventInput[]) => void;
}

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function nextId(events: EventInput[]): string {
  const used = new Set(events.map((e) => e.id));
  for (const ch of LETTERS) {
    if (!used.has(ch)) return ch;
  }
  return "?";
}

function toInt(v: string): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : NaN;
}

export default function EventEditor({ events, errors, onChange }: Props) {
  const rowErrors = new Map<number, string[]>();
  for (const e of errors) {
    const m = /^events\[(\d+)\]/.exec(e.loc);
    if (m) {
      const idx = Number(m[1]);
      rowErrors.set(idx, [...(rowErrors.get(idx) ?? []), `${e.loc}: ${e.msg}`]);
    }
  }

  function update(i: number, patch: Partial<EventInput>) {
    onChange(events.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  }

  function add() {
    const device = "M1";
    const maxSeq = Math.max(
      0,
      ...events.filter((e) => e.device === device).map((e) => e.seq)
    );
    onChange([
      ...events,
      {
        id: nextId(events),
        device,
        seq: maxSeq + 1,
        observed: 1,
        lo: 1,
        hi: events.length + 1,
      },
    ]);
  }

  return (
    <div className="editor">
      <div className="editor-head">
        <h3>
          事件（{events.length} / 4–20）
        </h3>
        <button className="ghost" onClick={add} disabled={events.length >= 20}>
          + 添加事件
        </button>
      </div>
      <table className="grid">
        <thead>
          <tr>
            <th>编号</th>
            <th>设备</th>
            <th>设备内序号</th>
            <th>观测位次</th>
            <th>区间 lo</th>
            <th>区间 hi</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr
              key={i}
              className={rowErrors.has(i) ? "row-error" : ""}
              title={rowErrors.get(i)?.join("\n")}
            >
              <td>
                <input
                  className="id-input"
                  value={e.id}
                  onChange={(ev) =>
                    update(i, { id: ev.target.value.toUpperCase().slice(0, 1) })
                  }
                />
              </td>
              <td>
                <input
                  value={e.device}
                  onChange={(ev) => update(i, { device: ev.target.value })}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={1}
                  value={Number.isNaN(e.seq) ? "" : e.seq}
                  onChange={(ev) => update(i, { seq: toInt(ev.target.value) })}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={Number.isNaN(e.observed) ? "" : e.observed}
                  onChange={(ev) =>
                    update(i, { observed: toInt(ev.target.value) })
                  }
                />
              </td>
              <td>
                <input
                  type="number"
                  min={1}
                  value={Number.isNaN(e.lo) ? "" : e.lo}
                  onChange={(ev) => update(i, { lo: toInt(ev.target.value) })}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={1}
                  value={Number.isNaN(e.hi) ? "" : e.hi}
                  onChange={(ev) => update(i, { hi: toInt(ev.target.value) })}
                />
              </td>
              <td>
                <button
                  className="ghost danger"
                  onClick={() => onChange(events.filter((_, j) => j !== i))}
                  disabled={events.length <= 1}
                >
                  删
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
