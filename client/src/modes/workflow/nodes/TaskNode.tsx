import { memo, useState } from "react";
import { Handle, Position, NodeToolbar, useReactFlow } from "@xyflow/react";
import { useWorkflowStore } from "../store";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#64748b"];
const ICONS = ["📝", "⚙️", "📧", "🔔", "🗂️", "🔗", "⏱️", "🧩", "📊", "🧪"];

export const TaskNode = memo(({ id, data, selected }: any) => {
  const { updateNode, removeNode } = useWorkflowStore();
  const { duplicate } = useReactFlow() as any;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(data.title || "Tugas Baru");
  const [picker, setPicker] = useState<"color" | "icon" | null>(null);

  const color = data.color || "#3b82f6";
  const disabled = !!data.disabled;
  const collapsed = !!data.collapsed;
  const icon = data.icon || "📝";

  const commitTitle = () => {
    updateNode(id, { data: { ...data, title: draft.trim() || "Tugas Tanpa Judul" } });
    setEditing(false);
  };

  return (
    <div
      className={`rounded-lg bg-bg-elevated border-2 transition-all min-w-[220px] ${
        selected ? "shadow-lg" : ""
      } ${disabled ? "opacity-50" : ""}`}
      style={{ borderColor: selected ? color : "#30363d" }}
    >
      <NodeToolbar isVisible={selected} position={Position.Top} className="bg-bg-panel border border-border rounded-md p-0.5 flex gap-0.5">
        <div className="relative">
          <button
            onClick={() => setPicker(picker === "color" ? null : "color")}
            className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover"
            title="Warna"
          >
            <span className="w-3 h-3 rounded-full" style={{ background: color }} />
          </button>
          {picker === "color" && (
            <div className="absolute top-full mt-1 left-0 bg-bg-panel border border-border rounded-md p-1 flex gap-0.5 z-50">
              {COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => { updateNode(id, { data: { ...data, color: c } }); setPicker(null); }}
                  className="w-5 h-5 rounded hover:scale-110 transition-transform"
                  style={{ background: c }}
                />
              ))}
            </div>
          )}
        </div>
        <div className="relative">
          <button
            onClick={() => setPicker(picker === "icon" ? null : "icon")}
            className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[12px]"
            title="Ikon"
          >
            {icon}
          </button>
          {picker === "icon" && (
            <div className="absolute top-full mt-1 left-0 bg-bg-panel border border-border rounded-md p-1 grid grid-cols-5 gap-0.5 z-50">
              {ICONS.map((ic) => (
                <button
                  key={ic}
                  onClick={() => { updateNode(id, { data: { ...data, icon: ic } }); setPicker(null); }}
                  className="w-6 h-6 grid place-items-center rounded hover:bg-bg-hover text-[12px]"
                >
                  {ic}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={() => updateNode(id, { data: { ...data, collapsed: !collapsed } })}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[11px]"
          title={collapsed ? "Perluas" : "Ciutkan"}
        >
          {collapsed ? "▾" : "▴"}
        </button>
        <button
          onClick={() => updateNode(id, { data: { ...data, disabled: !disabled } })}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[11px]"
          title={disabled ? "Aktifkan" : "Nonaktifkan"}
        >
          {disabled ? "⏻" : "⏽"}
        </button>
        <button
          onClick={() => {
            // duplicate via store
            useWorkflowStore.getState().duplicateNode(id);
          }}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[11px]"
          title="Duplikat"
        >
          ⧉
        </button>
        <button
          onClick={() => removeNode(id)}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-red-400 hover:bg-bg-hover text-[11px]"
          title="Hapus"
        >
          🗑
        </button>
      </NodeToolbar>

      <Handle type="source" position={Position.Top} id="t1" style={{ left: "38%", background: color }} />
      <Handle type="source" position={Position.Top} id="t2" style={{ left: "62%", background: color }} />
      <Handle type="source" position={Position.Bottom} id="b1" style={{ left: "38%", background: color }} />
      <Handle type="source" position={Position.Bottom} id="b2" style={{ left: "62%", background: color }} />
      <Handle type="source" position={Position.Left} id="l1" style={{ top: "38%", background: color }} />
      <Handle type="source" position={Position.Left} id="l2" style={{ top: "62%", background: color }} />
      <Handle type="source" position={Position.Right} id="r1" style={{ top: "38%", background: color }} />
      <Handle type="source" position={Position.Right} id="r2" style={{ top: "62%", background: color }} />

      <div className="flex items-center gap-2 px-3 py-2">
        <span className="text-base leading-none">{icon}</span>
        {editing ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitTitle();
              if (e.key === "Escape") { setDraft(data.title); setEditing(false); }
            }}
            onBlur={commitTitle}
            className="flex-1 bg-bg-base border border-border-soft rounded px-2 py-0.5 text-[13px] font-medium outline-none focus:border-accent"
          />
        ) : (
          <span className="flex-1 text-[13px] font-medium text-fg truncate">{data.title || "Tugas Baru"}</span>
        )}
        {!editing && (
          <button
            onClick={() => { setDraft(data.title || ""); setEditing(true); }}
            className="w-5 h-5 grid place-items-center rounded text-fg-muted hover:text-fg hover:bg-bg-hover text-[10px]"
          >
            ✎
          </button>
        )}
      </div>
    </div>
  );
});

TaskNode.displayName = "TaskNode";
