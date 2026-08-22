import { useMindMapStore } from "./store";

const COLORS = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#39c5cf", "#6e7681"];
const ICONS = ["💡", "📌", "🎯", "⭐", "🔥", "📚", "🛠️", "💬", "📊", "🚀", "✅", "❓"];

export function MindMapProperties() {
  const { nodes, selectedNodeId, updateNode, removeNode, name, setName, save } = useMindMapStore();
  const selected = nodes.find((n) => n.id === selectedNodeId);

  if (!selected) {
    return (
      <div className="flex-1 grid place-items-center p-4 text-center">
        <div>
          <div className="text-3xl mb-2">✨</div>
          <div className="text-[12px] text-fg-muted">Pilih node untuk edit</div>
          {name && (
            <div className="mt-4 text-[12px]">
              <div className="text-fg-muted text-[10px] uppercase tracking-wider mb-1">Current Mind Map</div>
              <div className="font-medium text-fg">{name}</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="p-3.5 border-b border-border-soft bg-bg-elevated">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted mb-2">Properties</div>
        <div className="text-[14px] font-semibold mb-1 truncate">{selected.label || "Untitled"}</div>
        <div className="text-[10.5px] font-mono text-fg-muted truncate">id: {selected.id}</div>
      </div>

      <div className="p-3.5 space-y-4">
        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Label</label>
          <input
            value={selected.label}
            onChange={(e) => updateNode(selected.id, { label: e.target.value })}
            className="w-full bg-bg-base border border-border-soft rounded-md px-2.5 py-1.5 text-[12.5px] outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Icon</label>
          <div className="grid grid-cols-6 gap-1">
            {ICONS.map((ic) => (
              <button
                key={ic}
                onClick={() => updateNode(selected.id, { icon: ic })}
                className={`h-8 rounded text-base grid place-items-center transition-colors ${
                  selected.icon === ic ? "bg-accent-soft ring-1 ring-accent" : "bg-bg-base hover:bg-bg-hover"
                }`}
              >
                {ic}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block mb-1.5">Color</label>
          <div className="flex gap-1.5">
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => updateNode(selected.id, { color: c })}
                className={`w-7 h-7 rounded transition-all ${
                  selected.color === c ? "ring-2 ring-fg scale-110" : "hover:scale-110"
                }`}
                style={{ background: c }}
              />
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="bg-bg-base border border-border-soft rounded-md p-2">
            <div className="text-fg-muted text-[10px] uppercase tracking-wider">Position</div>
            <div className="text-fg">{Math.round(selected.pos_x)}, {Math.round(selected.pos_y)}</div>
          </div>
          {selected.parent_id && (
            <div className="bg-bg-base border border-border-soft rounded-md p-2">
              <div className="text-fg-muted text-[10px] uppercase tracking-wider">Parent</div>
              <div className="text-fg truncate" title={selected.parent_id}>
                {nodes.find((n) => n.id === selected.parent_id)?.label || "—"}
              </div>
            </div>
          )}
        </div>

        <div className="pt-2 border-t border-border-soft">
          <button
            onClick={() => {
              if (confirm("Hapus node ini?")) removeNode(selected.id);
            }}
            className="w-full py-1.5 rounded-md bg-red-500/10 text-red-400 text-[12px] font-medium hover:bg-red-500/20 transition-colors"
          >
            Hapus Node
          </button>
        </div>
      </div>
    </div>
  );
}
