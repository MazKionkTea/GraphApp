import { useEffect, useState } from "react";
import { useWorkflowStore } from "./store";
import { workflowsApi, type WorkflowSummary } from "../../api/workflows";
import { Plus, FolderOpen, Trash2, Copy } from "lucide-react";

export function WorkflowNavigator() {
  const { workflowId, load, newWorkflow, setSelected } = useWorkflowStore();
  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      setList(await workflowsApi.list(showArchived));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [showArchived]);

  const handleNew = async () => {
    const name = prompt("Nama workflow baru:", "Workflow Baru");
    if (!name) return;
    await newWorkflow(name);
    refresh();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Hapus workflow ini? Semua snapshot juga akan terhapus.")) return;
    await workflowsApi.remove(id);
    refresh();
    if (workflowId === id) {
      useWorkflowStore.setState({ workflowId: null, nodes: [], edges: [] });
    }
  };

  const handleClone = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await workflowsApi.clone(id);
    refresh();
  };

  return (
    <>
      <div className="h-9 px-3.5 flex items-center justify-between border-b border-border-soft text-[11px] font-semibold uppercase tracking-wider text-fg-muted flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <FolderOpen size={12} /> Workflows
        </div>
        <button onClick={refresh} className="w-5 h-5 grid place-items-center rounded hover:bg-bg-hover text-fg-muted hover:text-fg">
          ↻
        </button>
      </div>
      <div className="px-3 py-2 border-b border-border-soft flex-shrink-0 space-y-1.5">
        <button
          onClick={handleNew}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md bg-accent-soft text-accent text-[12px] font-medium hover:bg-accent/20 transition-colors"
        >
          <Plus size={13} /> Workflow Baru
        </button>
        <label className="flex items-center gap-1.5 text-[11px] text-fg-muted cursor-pointer">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="accent-accent"
          />
          Tampilkan yang diarsipkan
        </label>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {loading && <div className="px-4 py-2 text-[12px] text-fg-muted">Loading…</div>}
        {!loading && list.length === 0 && (
          <div className="px-4 py-6 text-[12px] text-fg-muted text-center">
            Belum ada workflow.
          </div>
        )}
        {list.map((w) => (
          <div
            key={w.id}
            onClick={() => load(w.id)}
            className={`group px-3.5 py-2 cursor-pointer border-l-2 transition-colors ${
              w.id === workflowId ? "bg-accent-soft border-accent" : "border-transparent hover:bg-bg-hover"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <div className="text-[12.5px] font-medium truncate">{w.name}</div>
                  {w.archived && <span className="text-[9px] px-1 rounded bg-bg-elevated text-fg-muted">ARSIP</span>}
                </div>
                <div className="text-[10.5px] text-fg-muted font-mono mt-0.5">
                  v{w.version} · {w.node_count} node · {w.edge_count} edge · {w.status}
                </div>
              </div>
              <div className="opacity-0 group-hover:opacity-100 flex gap-0.5">
                <button
                  onClick={(e) => handleClone(w.id, e)}
                  className="w-6 h-6 grid place-items-center rounded text-fg-muted hover:text-accent hover:bg-bg-elevated"
                  title="Clone"
                >
                  <Copy size={11} />
                </button>
                <button
                  onClick={(e) => handleDelete(w.id, e)}
                  className="w-6 h-6 grid place-items-center rounded text-fg-muted hover:text-red-400 hover:bg-bg-elevated"
                  title="Hapus"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
