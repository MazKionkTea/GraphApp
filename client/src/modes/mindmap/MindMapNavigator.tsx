import { useEffect, useState } from "react";
import { useMindMapStore } from "./store";
import { mindmapsApi, type MindmapSummary } from "../../api/mindmaps";
import { Plus, FileText, Trash2 } from "lucide-react";

export function MindMapNavigator() {
  const { mindmapId, load, newMindmap } = useMindMapStore();
  const [list, setList] = useState<MindmapSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      setList(await mindmapsApi.list());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const handleNew = async () => {
    const name = prompt("Nama mind map baru:", "Mind Map Baru");
    if (!name) return;
    await newMindmap(name);
    refresh();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Hapus mind map ini?")) return;
    await mindmapsApi.remove(id);
    refresh();
    if (mindmapId === id) {
      useMindMapStore.setState({ mindmapId: null, nodes: [], edges: [] });
    }
  };

  return (
    <>
      <div className="h-9 px-3.5 flex items-center justify-between border-b border-border-soft text-[11px] font-semibold uppercase tracking-wider text-fg-muted flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <FileText size={12} /> Mind Maps
        </div>
        <button onClick={refresh} className="w-5 h-5 grid place-items-center rounded hover:bg-bg-hover text-fg-muted hover:text-fg" title="Refresh">
          ↻
        </button>
      </div>
      <div className="px-3 py-2 border-b border-border-soft flex-shrink-0">
        <button
          onClick={handleNew}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md bg-accent-soft text-accent text-[12px] font-medium hover:bg-accent/20 transition-colors"
        >
          <Plus size={13} /> Mind Map Baru
        </button>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {loading && <div className="px-4 py-2 text-[12px] text-fg-muted">Loading…</div>}
        {!loading && list.length === 0 && (
          <div className="px-4 py-6 text-[12px] text-fg-muted text-center">
            Belum ada mind map.<br />Klik tombol di atas untuk buat.
          </div>
        )}
        {list.map((m) => (
          <div
            key={m.id}
            onClick={() => load(m.id)}
            className={`group px-3.5 py-2 cursor-pointer border-l-2 transition-colors ${
              m.id === mindmapId
                ? "bg-accent-soft border-accent"
                : "border-transparent hover:bg-bg-hover"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-medium truncate">{m.name}</div>
                <div className="text-[10.5px] text-fg-muted font-mono mt-0.5">
                  {m.node_count} node · {m.edge_count} edge · {m.layout}
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(m.id, e)}
                className="opacity-0 group-hover:opacity-100 w-6 h-6 grid place-items-center rounded text-fg-muted hover:text-red-400 hover:bg-bg-elevated transition-all"
                title="Hapus"
              >
                <Trash2 size={11} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
