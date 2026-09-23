import type { ApiError, PrecedenceInput } from "../types";

interface Props {
  eventIds: string[];
  precedences: PrecedenceInput[];
  errors: ApiError[];
  onChange: (p: PrecedenceInput[]) => void;
}

function IdSelect({
  value,
  ids,
  onChange,
}: {
  value: string;
  ids: string[];
  onChange: (v: string) => void;
}) {
  const known = ids.includes(value);
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {!known && (
        <option value={value}>{value ? `${value}（未知）` : "（空）"}</option>
      )}
      {ids.map((id) => (
        <option key={id} value={id}>
          {id}
        </option>
      ))}
    </select>
  );
}

export default function PrecedenceEditor({
  eventIds,
  precedences,
  errors,
  onChange,
}: Props) {
  const validIds = [...new Set(eventIds.filter((id) => /^[A-Z]$/.test(id)))];

  const rowErrors = new Map<number, string[]>();
  for (const e of errors) {
    const m = /^precedences\[(\d+)\]/.exec(e.loc);
    if (m) {
      const idx = Number(m[1]);
      rowErrors.set(idx, [...(rowErrors.get(idx) ?? []), `${e.loc}: ${e.msg}`]);
    }
  }

  function update(i: number, patch: Partial<PrecedenceInput>) {
    onChange(precedences.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  }

  function add() {
    onChange([
      ...precedences,
      { before: validIds[0] ?? "", after: validIds[1] ?? validIds[0] ?? "" },
    ]);
  }

  return (
    <div className="editor">
      <div className="editor-head">
        <h3>显式先后关系（{precedences.length}）</h3>
        <button className="ghost" onClick={add} disabled={validIds.length < 2}>
          + 添加关系
        </button>
      </div>
      {precedences.length === 0 && (
        <p className="hint">无。同设备事件会自动按设备内序号排序。</p>
      )}
      {precedences.map((p, i) => (
        <div
          key={i}
          className={`prec-row ${rowErrors.has(i) ? "row-error" : ""}`}
          title={rowErrors.get(i)?.join("\n")}
        >
          <IdSelect
            value={p.before}
            ids={validIds}
            onChange={(v) => update(i, { before: v })}
          />
          <span className="arrow">先于 →</span>
          <IdSelect
            value={p.after}
            ids={validIds}
            onChange={(v) => update(i, { after: v })}
          />
          <button
            className="ghost danger"
            onClick={() => onChange(precedences.filter((_, j) => j !== i))}
          >
            删
          </button>
        </div>
      ))}
    </div>
  );
}
