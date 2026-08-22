import { useEffect, useState } from "react";
import { useCodeMapStore } from "./store";
import { projectsApi, type Symbol, type Call } from "../../api/projects";

type Tab = "info" | "callers" | "callees" | "source" | "metrics";

export function CodeMapProperties() {
  const { project, graph, selectedFqn } = useCodeMapStore();
  const [tab, setTab] = useState<Tab>("info");
  const [callers, setCallers] = useState<Call[]>([]);
  const [callees, setCallees] = useState<Call[]>([]);
  const [source, setSource] = useState<{ snippet: string; start: number; end: number } | null>(null);
  const [loading, setLoading] = useState(false);

  const symbol = graph?.nodes.find((n) => n.fqn === selectedFqn) || null;

  useEffect(() => {
    if (!project || !selectedFqn) return;
    setSource(null);
    if (tab === "callers") {
      projectsApi.getCallers(project.id, selectedFqn).then(setCallers).catch(console.error);
    } else if (tab === "callees") {
      projectsApi.getCallees(project.id, selectedFqn).then(setCallees).catch(console.error);
    } else if (tab === "source" && symbol?.line_start) {
      setLoading(true);
      projectsApi.getSource(project.id, symbol.file_path || "", symbol.line_start, 5)
        .then((res) => setSource({ snippet: res.snippet, start: res.start, end: res.end }))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [project, selectedFqn, tab, symbol]);

  if (!project) {
    return (
      <div className="flex-1 grid place-items-center p-4 text-center">
        <div>
          <div className="text-3xl mb-2">🐍</div>
          <div className="text-[12px] text-fg-muted">Pilih project dari Navigator</div>
        </div>
      </div>
    );
  }

  if (!symbol) {
    return (
      <div className="flex-1 grid place-items-center p-4 text-center">
        <div>
          <div className="text-3xl mb-2">📊</div>
          <div className="text-[12px] text-fg-muted">Pilih node di graph</div>
          <div className="text-[10.5px] text-fg-muted font-mono mt-3">
            {project.name}<br />
            {project.symbol_count} symbols · {project.call_count} edges
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-3.5 border-b border-border-soft bg-bg-elevated flex-shrink-0">
        <div className="text-[10px] font-mono text-fg-muted truncate mb-1">{symbol.fqn}</div>
        <div className="text-[14px] font-semibold mb-1 flex items-center gap-2">
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-soft text-accent uppercase">
            {symbol.kind}
          </span>
          {symbol.name}
        </div>
        {symbol.file_path && (
          <div className="text-[10.5px] font-mono text-fg-muted truncate">
            {symbol.file_path}:{symbol.line_start}
          </div>
        )}
      </div>

      <div className="flex border-b border-border-soft flex-shrink-0">
        {(["info", "callers", "callees", "source", "metrics"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[11px] font-medium capitalize transition-colors ${
              tab === t ? "text-fg border-b-2 border-accent" : "text-fg-muted hover:text-fg"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto">
        {tab === "info" && <InfoTab symbol={symbol} />}
        {tab === "callers" && <CallersTab callers={callers} />}
        {tab === "callees" && <CalleesTab callees={callees} />}
        {tab === "source" && <SourceTab symbol={symbol} source={source} loading={loading} />}
        {tab === "metrics" && <MetricsTab symbol={symbol} />}
      </div>
    </div>
  );
}

function InfoTab({ symbol }: { symbol: Symbol }) {
  return (
    <div className="p-3.5 space-y-1">
      <KV k="FQN" v={symbol.fqn} />
      <KV k="Type" v={symbol.kind} />
      {symbol.parent_fqn && <KV k="Parent" v={symbol.parent_fqn} />}
      {symbol.file_path && <KV k="File" v={symbol.file_path} />}
      {symbol.line_start && <KV k="Lines" v={`${symbol.line_start} – ${symbol.line_end || symbol.line_start}`} />}
      {symbol.loc && <KV k="LOC" v={String(symbol.loc)} />}
      {symbol.complexity && <KV k="Complexity" v={String(symbol.complexity)} />}
    </div>
  );
}

function CallersTab({ callers }: { callers: Call[] }) {
  if (callers.length === 0) return <Empty msg="No callers (entry point)" />;
  return (
    <div className="p-2 space-y-0.5">
      {callers.map((c) => (
        <div key={c.id} className="px-2 py-1.5 rounded hover:bg-bg-hover text-[12px] font-mono">
          <div className="text-fg truncate" title={c.source_fqn}>{c.source_fqn}</div>
          <div className="text-fg-muted text-[10px]">
            {c.file_path}:{c.line_number} · {c.call_count}× call
          </div>
        </div>
      ))}
    </div>
  );
}

function CalleesTab({ callees }: { callees: Call[] }) {
  if (callees.length === 0) return <Empty msg="No callees (leaf function)" />;
  return (
    <div className="p-2 space-y-0.5">
      {callees.map((c) => (
        <div key={c.id} className="px-2 py-1.5 rounded hover:bg-bg-hover text-[12px] font-mono">
          <div className="text-fg truncate" title={c.target_fqn}>{c.target_fqn}</div>
          <div className="text-fg-muted text-[10px]">
            {c.file_path}:{c.line_number} · {c.call_count}× call
          </div>
        </div>
      ))}
    </div>
  );
}

function SourceTab({ symbol, source, loading }: { symbol: Symbol; source: any; loading: boolean }) {
  if (!symbol.file_path || !symbol.line_start) {
    return <Empty msg="No source location" />;
  }
  if (loading) return <Empty msg="Loading source…" />;
  if (!source) return <Empty msg="No source available" />;
  const lines = source.snippet.split("\n");
  return (
    <div className="p-2">
      <pre className="bg-bg-base border border-border-soft rounded-md p-3 text-[11.5px] font-mono overflow-x-auto">
        {lines.map((line: string, i: number) => {
          const lineNum = source.start + i;
          const isTarget = lineNum === symbol.line_start;
          return (
            <div
              key={i}
              className={isTarget ? "bg-accent-soft -mx-3 px-3" : ""}
            >
              <span className="text-fg-muted inline-block w-7 text-right mr-3 select-none">{lineNum}</span>
              <span className="text-fg-secondary">{line || " "}</span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

function MetricsTab({ symbol }: { symbol: Symbol }) {
  return (
    <div className="p-3.5 grid grid-cols-2 gap-2">
      <Metric label="Fan-in" value={symbol.fan_in} />
      <Metric label="Fan-out" value={symbol.fan_out} />
      <Metric label="Total Calls" value={symbol.total_calls} />
      {symbol.complexity && <Metric label="Complexity" value={symbol.complexity} color={symbol.complexity > 10 ? "red" : symbol.complexity > 5 ? "amber" : "green"} />}
      {symbol.loc && <Metric label="LOC" value={symbol.loc} />}
      <div className="col-span-2 pt-2 flex gap-2">
        {symbol.is_entry_point && <span className="text-[10.5px] px-2 py-0.5 rounded bg-green-500/20 text-green-400">Entry Point</span>}
        {symbol.is_leaf && <span className="text-[10.5px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">Leaf</span>}
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: any; color?: "red" | "amber" | "green" }) {
  return (
    <div className="bg-bg-base border border-border-soft rounded-md p-2">
      <div className="text-fg-muted text-[10px] uppercase tracking-wider">{label}</div>
      <div className={`text-[18px] font-mono font-semibold ${color === "red" ? "text-red-400" : color === "amber" ? "text-amber-400" : color === "green" ? "text-green-400" : "text-fg"}`}>
        {value}
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="grid grid-cols-[80px_1fr] gap-2 text-[12px] py-0.5">
      <div className="text-fg-muted">{k}</div>
      <div className="text-fg font-mono break-all">{v}</div>
    </div>
  );
}

function Empty({ msg }: { msg: string }) {
  return <div className="p-4 text-center text-fg-muted text-[12px]">{msg}</div>;
}
