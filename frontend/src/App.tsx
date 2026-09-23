import { useEffect, useRef, useState } from "react";
import { solve, ValidationError } from "./api";
import EventEditor from "./components/EventEditor";
import PrecedenceEditor from "./components/PrecedenceEditor";
import ResultPanel from "./components/ResultPanel";
import { PRESETS } from "./presets";
import type {
  ApiError,
  EventInput,
  PrecedenceInput,
  SolveResponse,
} from "./types";

export default function App() {
  const [events, setEvents] = useState<EventInput[]>(() =>
    PRESETS[0].events.map((e) => ({ ...e }))
  );
  const [precedences, setPrecedences] = useState<PrecedenceInput[]>(() =>
    PRESETS[0].precedences.map((p) => ({ ...p }))
  );
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [errors, setErrors] = useState<ApiError[]>([]);
  const [fatal, setFatal] = useState<string | null>(null);
  const [solving, setSolving] = useState(false);
  const editSeq = useRef(0);

  // 输入一改动便清除旧结果
  useEffect(() => {
    editSeq.current += 1;
    setResult(null);
    setErrors([]);
    setFatal(null);
  }, [events, precedences]);

  async function onSolve() {
    const seq = editSeq.current;
    setSolving(true);
    try {
      const res = await solve(events, precedences);
      if (editSeq.current === seq) setResult(res); // 求解期间输入已变则丢弃
    } catch (e) {
      if (editSeq.current === seq) {
        if (e instanceof ValidationError) setErrors(e.errors);
        else setFatal(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setSolving(false);
    }
  }

  function loadPreset(index: number) {
    const p = PRESETS[index];
    setEvents(p.events.map((e) => ({ ...e })));
    setPrecedences(p.precedences.map((x) => ({ ...x })));
  }

  return (
    <div className="app">
      <header>
        <h1>产线回放工作台</h1>
        <p>
          停机前最后一轮记录散落在多台控制器中：各设备内部顺序可靠，混在一起不能直接回放。
          在此编辑事件与显式先后关系，由后端重建最优回放，页面逐条核对约束与代价。
        </p>
      </header>

      <div className="layout">
        <section className="panel">
          <div className="panel-title">
            <h2>输入</h2>
            <div className="preset-bar">
              {PRESETS.map((p, i) => (
                <button key={p.name} className="ghost" onClick={() => loadPreset(i)}>
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <EventEditor events={events} errors={errors} onChange={setEvents} />
          <PrecedenceEditor
            eventIds={events.map((e) => e.id)}
            precedences={precedences}
            errors={errors}
            onChange={setPrecedences}
          />

          <div className="actions">
            <button className="primary" onClick={onSolve} disabled={solving}>
              {solving ? "求解中…" : "重建回放"}
            </button>
            <span className="hint">
              {events.length} 个事件 · {precedences.length} 条先后关系
            </span>
          </div>

          {errors.length > 0 && (
            <div className="error-box">
              <h3>输入有误（{errors.length}）</h3>
              <ul>
                {errors.map((e, i) => (
                  <li key={i}>
                    <code>{e.loc}</code>：{e.msg}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {fatal && <div className="error-box">{fatal}</div>}
        </section>

        <section className="panel">
          <h2>结果</h2>
          {result ? (
            <ResultPanel
              result={result}
              events={events}
              precedences={precedences}
            />
          ) : (
            <p className="placeholder">
              尚无结果。编辑输入后点击「重建回放」；任何输入改动都会清除旧结果。
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
