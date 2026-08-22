import { memo, useState } from "react";
import { NodeResizer, NodeToolbar, Position, useReactFlow } from "@xyflow/react";
import { useWorkflowStore } from "../store";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#64748b"];

export const GroupNode = memo(({ id, data, selected }: any) => {
  const { updateNode } = useWorkflowStore();
  const { deleteElements } = useReactFlow() as any;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = draftState(data.title);
  const [colorOpen, setColorOpen] = useState(false);

  const color = data.color || "#3b82f6";
  const collapsed = !!data.collapsed;

  const commitTitle = () => {
    updateNode(id, { data: { ...data, title: draft.trim() || "Grup" } });
    setEditing(false);
  };

  const toggleCollapse = () => {
    if (!collapsed) {
      updateNode(id, { width: 260, height: 46, data: { ...data, collapsed: true, expandedSize: { width: data.expandedSize?.width || 320, height: data.expandedSize?.height || 220 } } });
      useWorkflowStore.setState((s) => ({
        nodes: s.nodes.map((n) => n.parentId === id ? { ...n, hidden: true } : n),
      }));
    } else {
      const size = data.expandedSize || { width: 320, height: 220 };
      updateNode(id, { width: size.width, height: size.height, data: { ...data, collapsed: false } });
      useWorkflowStore.setState((s) => ({
        nodes: s.nodes.map((n) => n.parentId === id ? { ...n, hidden: false } : n),
      }));
    }
  };

  const ungroup = () => {
    useWorkflowStore.setState((s) => {
      const groupNode = s.nodes.find((n) => n.id === id);
      return {
        nodes: s.nodes
          .filter((n) => n.id !== id)
          .map((n) => {
            if (n.parentId !== id) return n;
            const { parentId: _p, extent: _e, hidden: _h, ...rest } = n as any;
            return {
              ...rest,
              position: groupNode
                ? { x: n.position.x + groupNode.position.x, y: n.position.y + groupNode.position.y }
                : n.position,
            } as any;
          }),
      };
    });
  };

  const deleteWithContents = () => {
    const childIds = useWorkflowStore.getState().nodes.filter((n) => n.parentId === id).map((n) => n.id);
    if (deleteElements) {
      deleteElements({ nodes: [{ id }, ...childIds.map((id) => ({ id }))] });
    } else {
      useWorkflowStore.setState((s) => ({
        nodes: s.nodes.filter((n) => n.id !== id && n.parentId !== id),
        edges: s.edges.filter((e) => !s.nodes.some((n) => n.id === e.source && (n.id === id || n.parentId === id)) && !s.nodes.some((n) => n.id === e.target && (n.id === id || n.parentId === id))),
      }));
    }
  };

  return (
    <div
      className="rounded-lg border-2 border-dashed w-full h-full"
      style={{ borderColor: color, background: `${color}1A` }}
    >
      <NodeResizer
        isVisible={selected && !collapsed}
        minWidth={200}
        minHeight={120}
        lineStyle={{ borderColor: color }}
        handleStyle={{ background: color, width: 8, height: 8, borderRadius: 2 }}
      />
      <NodeToolbar isVisible={selected} position={Position.Top} className="bg-bg-panel border border-border rounded-md p-0.5 flex gap-0.5">
        <div className="relative">
          <button
            onClick={() => setColorOpen((o) => !o)}
            className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover"
            title="Warna"
          >
            <span className="w-3 h-3 rounded-full" style={{ background: color }} />
          </button>
          {colorOpen && (
            <div className="absolute top-full mt-1 left-0 bg-bg-panel border border-border rounded-md p-1 flex gap-0.5 z-50">
              {COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => { updateNode(id, { data: { ...data, color: c } }); setColorOpen(false); }}
                  className="w-5 h-5 rounded hover:scale-110 transition-transform"
                  style={{ background: c }}
                />
              ))}
            </div>
          )}
        </div>
        <button
          onClick={toggleCollapse}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[11px]"
          title={collapsed ? "Perluas" : "Ciutkan"}
        >
          {collapsed ? "▾" : "▴"}
        </button>
        <button
          onClick={ungroup}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover text-[11px]"
          title="Urai"
        >⛓</button>
        <button
          onClick={deleteWithContents}
          className="w-6 h-6 grid place-items-center rounded text-fg-secondary hover:text-red-400 hover:bg-bg-hover text-[11px]"
          title="Hapus grup + isi"
        >🗑</button>
      </NodeToolbar>

      <div className="px-3 py-1.5 flex items-center gap-2" style={{ background: color }}>
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
            className="flex-1 bg-white/20 text-white px-2 py-0.5 text-[12.5px] font-semibold rounded outline-none"
          />
        ) : (
          <span className="flex-1 text-[12.5px] font-semibold text-white">{data.title || "Grup"}</span>
        )}
        {collapsed && data.childCount && (
          <span className="text-[10px] text-white/80 font-mono">{data.childCount} node</span>
        )}
        {!editing && (
          <button
            onClick={() => { setDraft(data.title || ""); setEditing(true); }}
            className="w-5 h-5 grid place-items-center rounded text-white/80 hover:text-white hover:bg-white/20 text-[10px]"
          >✎</button>
        )}
      </div>
    </div>
  );
});

function draftState(initial: string) {
  const [v, setV] = useState(initial || "Grup");
  return [v, setV] as const;
}

GroupNode.displayName = "GroupNode";
