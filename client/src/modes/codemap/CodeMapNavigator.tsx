import { useEffect, useState } from "react";
import { useCodeMapStore } from "./store";
import { FolderTree, Plus, Trash2, RefreshCw, FileCode } from "lucide-react";

export function CodeMapNavigator() {
  const { projects, project, loadProject, createProject, removeProject, refreshProjects, indexing, indexProject } =
    useCodeMapStore();
  const [newName, setNewName] = useState("");
  const [newPath, setNewPath] = useState("");

  useEffect(() => { refreshProjects(); }, [refreshProjects]);

  const handleCreate = async () => {
    if (!newPath) {
      alert("Masukkan path direktori project");
      return;
    }
    const name = newName || newPath.split("/").filter(Boolean).pop() || "Project";
    const p = await createProject(name, newPath);
    setNewName(""); setNewPath("");
    await indexProject(p.id);
    await loadProject(p.id);
  };

  return (
    <>
      <div className="h-9 px-3.5 flex items-center justify-between border-b border-border-soft text-[11px] font-semibold uppercase tracking-wider text-fg-muted flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <FolderTree size={12} /> Projects
        </div>
        <button onClick={refreshProjects} className="w-5 h-5 grid place-items-center rounded hover:bg-bg-hover text-fg-muted hover:text-fg">
          <RefreshCw size={11} />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-border-soft flex-shrink-0 space-y-1.5">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Nama project (opsional)"
          className="w-full bg-bg-base border border-border-soft rounded-md px-2 py-1 text-[12px] outline-none focus:border-accent"
        />
        <input
          value={newPath}
          onChange={(e) => setNewPath(e.target.value)}
          placeholder="/path/ke/project/python"
          className="w-full bg-bg-base border border-border-soft rounded-md px-2 py-1 text-[12px] font-mono outline-none focus:border-accent"
        />
        <button
          onClick={handleCreate}
          disabled={indexing}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md bg-accent-soft text-accent text-[12px] font-medium hover:bg-accent/20 transition-colors disabled:opacity-50"
        >
          <Plus size={12} /> {indexing ? "Indexing…" : "Open & Index"}
        </button>
      </div>

      <div className="flex-1 overflow-auto py-1">
        {projects.length === 0 && (
          <div className="px-4 py-6 text-[12px] text-fg-muted text-center">
            Belum ada project.<br />Masukkan path di atas.
          </div>
        )}
        {projects.map((p) => (
          <div
            key={p.id}
            onClick={() => loadProject(p.id)}
            className={`group px-3.5 py-2 cursor-pointer border-l-2 transition-colors ${
              p.id === project?.id ? "bg-accent-soft border-accent" : "border-transparent hover:bg-bg-hover"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-medium truncate flex items-center gap-1.5">
                  <FileCode size={11} className="text-fg-muted" /> {p.name}
                </div>
                <div className="text-[10.5px] text-fg-muted font-mono mt-0.5 truncate" title={p.root_path}>
                  {p.symbol_count} sym · {p.call_count} edge
                </div>
                <div className="text-[10px] text-fg-muted font-mono truncate" title={p.root_path}>
                  {p.root_path}
                </div>
              </div>
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  if (confirm("Hapus project ini?")) await removeProject(p.id);
                }}
                className="opacity-0 group-hover:opacity-100 w-6 h-6 grid place-items-center rounded text-fg-muted hover:text-red-400 hover:bg-bg-elevated"
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
