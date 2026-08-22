import { useWorkflowStore } from "./store";
import { Trash2, Copy } from "lucide-react";

export function WorkflowProperties() {
  const { nodes, edges, selected, updateNode, removeNode, duplicateNode, status, setStatus } = useWorkflowStore();
  const node = nodes.find((n) => selected.nodes.includes(n.id));

  if (!node) {
    return (
      <div className="flex-1 grid place-items-center p-4 text-center">
        <div>
          <div className="text-3xl mb-2">🔄</div>
          <div className="text-[12px] text-fg-muted">Pilih node/task untuk lihat detail</div>
          <div className="text-[10.5px] text-fg-muted mt-3 font-mono">
            {nodes.length} node · {edges.length} edge
          </div>
        </div>
      </div>
    );
  }

  if (node.type === "group") {
    return (
      <div className="flex-1 overflow-auto">
        <div className="p-3.5 border-b border-border-soft bg-bg-elevated">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted mb-2">Group Node</div>
          <div className="text-[14px] font-semibold">{node.data.title || "Grup"}</div>
          <div className="text-[10.5px] font-mono text-fg-muted mt-1">id: {node.id}</div>
        </div>
        <div className="p-3.5 text-[12px] text-fg-secondary">
          <p>Group adalah container untuk node lain. Drag node ke dalam group untuk memindahkannya.</p>
          <p className="mt-2 text-fg-muted text-[11px]">Tip: collapse/expand via toolbar di atas node.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="p-3.5 border-b border-border-soft bg-bg-elevated">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted mb-2">Task Node</div>
        <div className="text-[14px] font-semibold">{node.data.title || "Tugas"}</div>
        <div className="text-[10.5px] font-mono text-fg-muted mt-1 truncate">id: {node.id}</div>
      </div>

      <div className="p-3.5 space-y-4">
        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Judul</label>
          <input
            value={node.data.title || ""}
            onChange={(e) => updateNode(node.id, { data: { ...node.data, title: e.target.value } })}
            className="w-full bg-bg-base border border-border-soft rounded-md px-2.5 py-1.5 text-[12.5px] outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Aksi</label>
          <input
            value={node.data.action || ""}
            onChange={(e) => updateNode(node.id, { data: { ...node.data, action: e.target.value } })}
            placeholder="Pilih atau ketik aksi…"
            className="w-full bg-bg-base border border-border-soft rounded-md px-2.5 py-1.5 text-[12.5px] outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Deskripsi</label>
          <textarea
            value={node.data.description || ""}
            onChange={(e) => updateNode(node.id, { data: { ...node.data, description: e.target.value } })}
            placeholder="Tulis deskripsi…"
            rows={3}
            className="w-full bg-bg-base border border-border-soft rounded-md px-2.5 py-1.5 text-[12.5px] outline-none focus:border-accent resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="bg-bg-base border border-border-soft rounded-md p-2">
            <div className="text-fg-muted text-[10px] uppercase tracking-wider">Status</div>
            <button
              onClick={() => setStatus(status === "draft" ? "published" : "draft")}
              className={`text-[11px] font-medium ${status === "draft" ? "text-amber-400" : "text-green-400"}`}
            >
              {status === "draft" ? "Draft" : "Published"}
            </button>
          </div>
          <div className="bg-bg-base border border-border-soft rounded-md p-2">
            <div className="text-fg-muted text-[10px] uppercase tracking-wider">Position</div>
            <div className="text-[11px] font-mono">{Math.round(node.position.x)}, {Math.round(node.position.y)}</div>
          </div>
        </div>

        <div className="pt-2 border-t border-border-soft space-y-1.5">
          <button
            onClick={() => duplicateNode(node.id)}
            className="w-full py-1.5 rounded-md bg-bg-base text-fg-secondary text-[12px] font-medium hover:bg-bg-hover transition-colors flex items-center justify-center gap-1.5"
          >
            <Copy size={12} /> Duplikat
          </button>
          <button
            onClick={() => {
              if (confirm("Hapus node ini?")) removeNode(node.id);
            }}
            className="w-full py-1.5 rounded-md bg-red-500/10 text-red-400 text-[12px] font-medium hover:bg-red-500/20 transition-colors flex items-center justify-center gap-1.5"
          >
            <Trash2 size={12} /> Hapus
          </button>
        </div>
      </div>
    </div>
  );
}
