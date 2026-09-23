import { useCallback, useMemo, useState } from "react";
import type {
  EventRow,
  OrderingRow,
  SolveResponse,
} from "./types";
import { solve } from "./api";
import { sampleEvents, sampleOrderings } from "./sample";
import { EventTable } from "./components/EventTable";
import { OrderingTable } from "./components/OrderingTable";
import { ErrorPanel } from "./components/ErrorPanel";
import { ResultPanel } from "./components/ResultPanel";

const NEXT_IDS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

function nextFreeId(events: EventRow[]): string {
  const used = new Set(events.map((e) => e.id.trim()));
  return NEXT_IDS.find((c) => !used.has(c)) ?? "";
}

function emptyEvent(id: string): EventRow {
  return { id, device: "", serial: "", observedRank: "", windowLow: "1", windowHigh: "4" };
}

export default function App() {
  const [events, setEvents] = useState<EventRow[]>(sampleEvents);
  const [orderings, setOrderings] = useState<OrderingRow[]>(sampleOrderings);
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [witnessIdx, setWitnessIdx] = useState(0);

  // Every mutator funnels through here: changing the input invalidates any
  // result that was rebuilt from older input.
  const mutate = useCallback(
    (fn: () => void) => {
      fn();
      setResult(null);
      setApiError(null);
      setWitnessIdx(0);
    },
    [],
  );

  const updateEvent = useCallback(
    (index: number, field: keyof EventRow, value: string) => {
      mutate(() => {
        setEvents((prev) =>
          prev.map((e, i) => (i === index ? { ...e, [field]: value } : e)),
        );
      });
    },
    [mutate],
  );

  const addEvent = useCallback(() => {
    mutate(() => {
      setEvents((prev) => {
        if (prev.length >= 20) return prev;
        return [...prev, emptyEvent(nextFreeId(prev))];
      });
    });
  }, [mutate]);

  const removeEvent = useCallback(
    (index: number) => {
      mutate(() => {
        setEvents((prev) => prev.filter((_, i) => i !== index));
      });
    },
    [mutate],
  );

  const updateOrdering = useCallback(
    (index: number, field: keyof OrderingRow, value: string) => {
      mutate(() => {
        setOrderings((prev) =>
          prev.map((o, i) => (i === index ? { ...o, [field]: value } : o)),
        );
      });
    },
    [mutate],
  );

  const addOrdering = useCallback(() => {
    mutate(() => {
      setOrderings((prev) => [...prev, { before: "", after: "" }]);
    });
  }, [mutate]);

  const removeOrdering = useCallback(
    (index: number) => {
      mutate(() => {
        setOrderings((prev) => prev.filter((_, i) => i !== index));
      });
    },
    [mutate],
  );

  const loadSample = useCallback(() => {
    mutate(() => {
      setEvents(sampleEvents.map((e) => ({ ...e })));
      setOrderings(sampleOrderings.map((o) => ({ ...o })));
    });
  }, [mutate]);

  const clearAll = useCallback(() => {
    mutate(() => {
      setEvents([
        emptyEvent("A"),
        emptyEvent("B"),
        emptyEvent("C"),
        emptyEvent("D"),
      ]);
      setOrderings([]);
    });
  }, [mutate]);

  const handleSolve = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    try {
      const res = await solve(events, orderings);
      setResult(res);
      setWitnessIdx(0);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [events, orderings]);

  // Fields/rows implicated by located backend errors.
  const errorCells = useMemo(() => {
    const cells = new Set<string>();
    const orderingRows = new Set<number>();
    result?.errors.forEach((err) => {
      const p = err.path;
      if (p[0] === "events" && p.length >= 3) {
        // The last path element is the offending field; the one before it
        // is the row index.
        cells.add(`event:${p[p.length - 2]}:${p[p.length - 1]}`);
      }
      if (p[0] === "orderings" && p.length >= 2) {
        orderingRows.add(Number(p[1]));
        if (p.length >= 3) cells.add(`ordering:${p[1]}:${p[p.length - 1]}`);
      }
      if (err.orderingIndex != null) orderingRows.add(err.orderingIndex);
    });
    return { cells, orderingRows };
  }, [result]);

  return (
    <div className="app">
      <header className="topbar">
        <h1>停机回放工作台</h1>
        <p className="subtitle">
          编辑各控制器记录的事件与显式先后关系, 由业务 API 重建最优回放排列;
          页面独立逐条复核窗口、顺序与代价。
        </p>
      </header>

      <main>
        <section className="panel">
          <div className="panel-head">
            <h2>① 事件 ({events.length}/4–20)</h2>
            <div className="row-actions">
              <button type="button" onClick={addEvent} disabled={events.length >= 20}>
                + 添加事件
              </button>
            </div>
          </div>
          <EventTable
            events={events}
            onChange={updateEvent}
            onRemove={removeEvent}
            errorCells={errorCells.cells}
          />
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>② 显式先后关系</h2>
            <div className="row-actions">
              <button type="button" onClick={addOrdering}>
                + 添加先后关系
              </button>
            </div>
          </div>
          <OrderingTable
            events={events}
            orderings={orderings}
            onChange={updateOrdering}
            onRemove={removeOrdering}
            errorCells={errorCells.cells}
            errorRows={errorCells.orderingRows}
          />
        </section>

        <section className="panel actions">
          <button
            type="button"
            className="primary"
            onClick={handleSolve}
            disabled={loading}
          >
            {loading ? "重建中…" : "由业务 API 重建"}
          </button>
          <button type="button" onClick={loadSample}>
            载入示例
          </button>
          <button type="button" onClick={clearAll}>
            清空
          </button>
          {apiError && <span className="api-error">{apiError}</span>}
        </section>

        {result && result.status === "invalid_input" && (
          <ErrorPanel errors={result.errors} />
        )}

        {result && result.status !== "invalid_input" && (
          <ResultPanel
            result={result}
            events={events}
            orderings={orderings}
            witnessIdx={witnessIdx}
            onSelectWitness={setWitnessIdx}
          />
        )}

        {!result && !apiError && (
          <section className="panel placeholder">
            输入修改后旧结果会立即失效; 点击「由业务 API 重建」获取新的回放。
          </section>
        )}
      </main>

      <footer>
        目标: 最小化 Σ |实际位置 − 观测位次|, 位置从 1 起算。
      </footer>
    </div>
  );
}
