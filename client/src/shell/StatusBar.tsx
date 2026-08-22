import { useEffect, useState } from "react";
import { useAppStore } from "../store/useAppStore";
import { CheckCircle2, AlertCircle } from "lucide-react";

export function StatusBar({ mode }: { mode: "mindmap" | "workflow" | "codemap" }) {
  const { currentMindmapId, currentWorkflowId, currentProjectId } = useAppStore();
  const [status, setStatus] = useState<"ok" | "down">("ok");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.ok ? setStatus("ok") : setStatus("down"))
      .catch(() => setStatus("down"));
  }, []);

  const modeLabel = { mindmap: "Mind Map", workflow: "Workflow", codemap: "Code Graph" }[mode];
  const activeId = mode === "mindmap" ? currentMindmapId : mode === "workflow" ? currentWorkflowId : currentProjectId;

  return (
    <footer className="h-[26px] flex items-center px-4 gap-4 bg-bg-panel border-t border-border text-[11px] font-mono text-fg-muted flex-shrink-0">
      <div className="flex items-center gap-1.5">
        {status === "ok" ? (
          <CheckCircle2 size={11} className="text-green-500" />
        ) : (
          <AlertCircle size={11} className="text-red-500" />
        )}
        <span>{status === "ok" ? "Ready" : "Backend down"}</span>
      </div>
      <div>Mode: <span className="text-fg">{modeLabel}</span></div>
      {activeId && <div className="truncate max-w-[300px]">ID: {activeId}</div>}
      <div className="flex-1" />
      <div>Layout: <span className="text-fg">default</span></div>
      <div>100%</div>
      <div>UTF-8 · LF</div>
    </footer>
  );
}
