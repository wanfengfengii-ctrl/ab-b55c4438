import type { ErrorItem } from "../types";

interface Props {
  errors: ErrorItem[];
}

/** Lists every located input error, referencing the exact row/cell. */
export function ErrorPanel({ errors }: Props) {
  return (
    <section className="panel result invalid">
      <h2>输入校验未通过 · {errors.length} 处问题</h2>
      <ul className="error-list">
        {errors.map((err, i) => {
          let where = "";
          const p = err.path;
          if (p[0] === "events") {
            const rowNo = Number(p[1]) + 1;
            const fieldLabel: Record<string, string> = {
              id: "编号",
              device: "设备",
              serial: "设备内序号",
              observedRank: "观测位次",
              windowLow: "区间下界",
              windowHigh: "区间上界",
            };
            const field = p.length >= 4 ? p[3] ?? p[2] : p[2];
            where = `事件表第 ${rowNo} 行${field && fieldLabel[field] ? ` · ${fieldLabel[field]}` : ""}`;
          } else if (p[0] === "orderings") {
            const rowNo = Number(p[1]) + 1;
            const fieldLabel: Record<string, string> = { before: "before 端", after: "after 端" };
            const field = p[2];
            where = `先后关系第 ${rowNo} 行${field && fieldLabel[field] ? ` · ${fieldLabel[field]}` : ""}`;
          } else {
            where = "输入";
          }
          return (
            <li key={i}>
              <span className="error-loc">{where || "输入"}:</span>{" "}
              <span className="error-msg">{err.message}</span>
              <code className="error-code">[{err.code}]</code>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
