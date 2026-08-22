import { useEffect, useState } from "react";
import { useAppStore, type Mode } from "../store/useAppStore";
import { Search, Download, Upload, Moon, Sun, Github } from "lucide-react";
import { clsx } from "clsx";

const MODES: { id: Mode; label: string; icon: string }[] = [
  { id: "mindmap", label: "Mind Map", icon: "🧠" },
  { id: "workflow", label: "Workflow", icon: "🔄" },
  { id: "codemap", label: "Code Graph", icon: "🐍" },
];

export function TopBar() {
  const { mode, setMode } = useAppStore();
  const [search, setSearch] = useState("");
  const [dark, setDark] = useState(true);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <header className="h-11 flex items-center justify-between px-4 bg-bg-panel border-b border-border flex-shrink-0 gap-4">
      {/* Brand */}
      <div className="flex items-center gap-2 font-semibold text-[13px]">
        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-accent to-purple-500 grid place-items-center text-white text-xs">
          G
        </div>
        <span>Graph App</span>
        <span className="text-fg-muted text-[11px] font-normal">v0.1.0</span>
      </div>

      {/* Mode Switcher */}
      <div className="flex items-center bg-bg-base rounded-md p-0.5 border border-border-soft">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={clsx(
              "px-3 py-1 text-[12px] font-medium rounded transition-colors flex items-center gap-1.5",
              mode === m.id
                ? "bg-accent-soft text-accent"
                : "text-fg-secondary hover:text-fg hover:bg-bg-hover"
            )}
          >
            <span>{m.icon}</span>
            <span>{m.label}</span>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex-1 max-w-md flex items-center gap-2 bg-bg-base border border-border-soft rounded-md px-2.5 h-7 focus-within:border-accent transition-colors">
        <Search size={13} className="text-fg-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search nodes, functions, files…"
          className="flex-1 bg-transparent outline-none text-[12.5px] placeholder:text-fg-muted"
        />
        <kbd className="text-[10px] font-mono bg-bg-elevated border border-border-soft rounded px-1.5 py-px text-fg-muted">
          ⌘K
        </kbd>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button className="flex items-center gap-1.5 px-2 py-1 text-[12px] font-medium text-fg-secondary hover:text-fg hover:bg-bg-hover rounded transition-colors">
          <Upload size={13} /> Import
        </button>
        <button className="flex items-center gap-1.5 px-2 py-1 text-[12px] font-medium text-fg-secondary hover:text-fg hover:bg-bg-hover rounded transition-colors">
          <Download size={13} /> Export
        </button>
        <button
          onClick={() => setDark((d) => !d)}
          className="w-7 h-7 grid place-items-center text-fg-secondary hover:text-fg hover:bg-bg-hover rounded transition-colors"
          title="Toggle theme"
        >
          {dark ? <Moon size={13} /> : <Sun size={13} />}
        </button>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="w-7 h-7 grid place-items-center text-fg-secondary hover:text-fg hover:bg-bg-hover rounded transition-colors"
        >
          <Github size={13} />
        </a>
      </div>
    </header>
  );
}
