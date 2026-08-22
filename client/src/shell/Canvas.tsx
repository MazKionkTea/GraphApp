import { MindMapCanvas } from "../modes/mindmap/MindMapCanvas";
import { WorkflowCanvas } from "../modes/workflow/WorkflowCanvas";
import { CodeMapCanvas } from "../modes/codemap/CodeMapCanvas";

export function Canvas({ mode }: { mode: "mindmap" | "workflow" | "codemap" }) {
  return (
    <main className="bg-bg-base relative overflow-hidden">
      {mode === "mindmap" && <MindMapCanvas />}
      {mode === "workflow" && <WorkflowCanvas />}
      {mode === "codemap" && <CodeMapCanvas />}
    </main>
  );
}
