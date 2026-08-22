import { MindMapNavigator } from "../modes/mindmap/MindMapNavigator";
import { WorkflowNavigator } from "../modes/workflow/WorkflowNavigator";
import { CodeMapNavigator } from "../modes/codemap/CodeMapNavigator";

export function Navigator({ mode }: { mode: "mindmap" | "workflow" | "codemap" }) {
  return (
    <aside className="bg-bg-panel border-r border-border flex flex-col overflow-hidden">
      {mode === "mindmap" && <MindMapNavigator />}
      {mode === "workflow" && <WorkflowNavigator />}
      {mode === "codemap" && <CodeMapNavigator />}
    </aside>
  );
}
