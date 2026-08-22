import { memo } from "react";
import { Handle, Position } from "@xyflow/react";

const KIND_COLORS: Record<string, string> = {
  package: "#3fb950",
  module: "#58a6ff",
  class: "#d29922",
  function: "#39c5cf",
  method: "#bc8cff",
  external: "#6e7681",
};

const KIND_LABELS: Record<string, string> = {
  package: "P",
  module: "M",
  class: "C",
  function: "f",
  method: "m",
  external: "E",
};

type Data = {
  label: string;
  kind: string;
  fqn: string;
  fan_in: number;
  fan_out: number;
  is_entry: boolean;
  is_leaf: boolean;
  complexity: number | null;
  highlighted?: boolean;
  dimmed?: boolean;
};

export const CodeNode = memo(({ data, selected }: any) => {
  const color = KIND_COLORS[data.kind] || "#6e7681";
  return (
    <div
      className="rounded-md border-2 bg-bg-elevated transition-all min-w-[140px] max-w-[200px]"
      style={{
        borderColor: selected ? "#58a6ff" : data.highlighted ? color : "#30363d",
        opacity: data.dimmed ? 0.2 : 1,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Right} style={{ background: color, width: 6, height: 6 }} />
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <span
          className="w-4 h-4 rounded text-[9px] font-bold grid place-items-center text-bg-base"
          style={{ background: color }}
        >
          {KIND_LABELS[data.kind] || "?"}
        </span>
        <span className="text-[11px] font-mono text-fg truncate flex-1" title={data.fqn}>{data.label}</span>
      </div>
      {(data.fan_in > 0 || data.fan_out > 0 || data.is_entry || data.is_leaf) && (
        <div className="px-2 pb-1.5 flex items-center gap-1 text-[9.5px] font-mono text-fg-muted">
          {data.is_entry && <span className="text-green-400">→</span>}
          <span title="Fan-in">↑{data.fan_in}</span>
          <span title="Fan-out">↓{data.fan_out}</span>
          {data.is_leaf && <span className="text-amber-400">🍃</span>}
        </div>
      )}
    </div>
  );
});

CodeNode.displayName = "CodeNode";
