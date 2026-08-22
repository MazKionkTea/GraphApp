import { useState } from "react";
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from "@xyflow/react";
import { nanoid } from "nanoid";
import { useWorkflowStore } from "../store";

const EDGE_COLORS = ["#8a8a8f", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7"];

export function CustomEdge({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, data, selected, animated,
}: any) {
  const { updateEdge, removeEdge } = useWorkflowStore();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(data?.label || "");
  const [menuOpen, setMenuOpen] = useState(false);

  const waypoints: any[] = data?.waypoints || [];
  const points = [{ x: sourceX, y: sourceY }, ...waypoints, { x: targetX, y: targetY }];
  const [bezierPath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const edgePath = waypoints.length > 0 ? points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.y}`).join(" ") : bezierPath;
  const color = data?.color || "#8a8a8f";

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: selected ? 2.5 : 1.75,
          strokeDasharray: animated ? 6 : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          className="absolute pointer-events-auto"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") { updateEdge(id, { data: { ...data, label: draft.trim() } }); setEditing(false); }
                if (e.key === "Escape") setEditing(false);
              }}
              onBlur={() => { updateEdge(id, { data: { ...data, label: draft.trim() } }); setEditing(false); }}
              className="bg-bg-elevated border border-accent rounded px-2 py-0.5 text-[11px] outline-none"
              style={{ minWidth: 80 }}
            />
          ) : (
            <div
              onDoubleClick={() => { setDraft(data?.label || ""); setEditing(true); }}
              onClick={() => setMenuOpen((o) => !o)}
              className="px-1.5 py-0.5 rounded text-[10.5px] font-medium cursor-pointer bg-bg-elevated border-2 hover:bg-bg-hover"
              style={{ borderColor: color, color: "#e6edf3" }}
            >
              {data?.label || "⋯"}
            </div>
          )}
          {menuOpen && (
            <div className="absolute top-full left-0 mt-1 bg-bg-panel border border-border rounded-md p-1 min-w-[140px] z-50 text-[11px]">
              <button
                onClick={() => { setDraft(data?.label || ""); setEditing(true); setMenuOpen(false); }}
                className="w-full text-left px-2 py-1 rounded hover:bg-bg-hover"
              >
                ✎ Edit label
              </button>
              <button
                onClick={() => { updateEdge(id, { animated: !animated } as any); setMenuOpen(false); }}
                className="w-full text-left px-2 py-1 rounded hover:bg-bg-hover"
              >
                {animated ? "◼ Matikan animasi" : "▶ Animasikan"}
              </button>
              <div className="px-2 py-1.5">
                <div className="text-fg-muted text-[10px] mb-1">Warna:</div>
                <div className="flex gap-1">
                  {EDGE_COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={() => { updateEdge(id, { data: { ...data, color: c } }); setMenuOpen(false); }}
                      className="w-4 h-4 rounded hover:scale-110"
                      style={{ background: c }}
                    />
                  ))}
                </div>
              </div>
              {waypoints.length > 0 && (
                <button
                  onClick={() => { updateEdge(id, { data: { ...data, waypoints: [] } }); setMenuOpen(false); }}
                  className="w-full text-left px-2 py-1 rounded hover:bg-bg-hover"
                >
                  ⟲ Reset rute
                </button>
              )}
              <button
                onClick={() => { removeEdge(id); setMenuOpen(false); }}
                className="w-full text-left px-2 py-1 rounded hover:bg-red-500/20 text-red-400"
              >
                🗑 Hapus koneksi
              </button>
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
