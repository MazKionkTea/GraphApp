import { MindMapProperties } from "../modes/mindmap/MindMapProperties";
import { WorkflowProperties } from "../modes/workflow/WorkflowProperties";
import { CodeMapProperties } from "../modes/codemap/CodeMapProperties";

export function Properties({ mode }: { mode: "mindmap" | "workflow" | "codemap" }) {
  return (
    <aside className="bg-bg-panel border-l border-border flex flex-col overflow-hidden">
      {mode === "mindmap" && <MindMapProperties />}
      {mode === "workflow" && <WorkflowProperties />}
      {mode === "codemap" && <CodeMapProperties />}
    </aside>
  );
}
