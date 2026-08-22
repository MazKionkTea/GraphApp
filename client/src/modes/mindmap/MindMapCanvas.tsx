import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  ConnectionMode,
  ReactFlowProvider,
} from "@xyflow/react";
import { useMindMapStore } from "./store";
import { MindMapNodeComponent } from "./MindMapNode";
import { Plus, Save, RefreshCw } from "lucide-react";

const nodeTypes = { mm: MindMapNodeComponent };

function MindMapCanvasInner() {
  const { nodes: mmNodes, edges: mmEdges, layout, setLayout, addNode, save, dirty, selectedNodeId, setSelected, updateNode } =
    useMindMapStore();

  const flowNodes: Node[] = useMemo(
    () =>
      mmNodes.map((n) => ({
        id: n.id,
        type: "mm",
        position: { x: n.pos_x, y: n.pos_y },
        data: { label: n.label, icon: n.icon, color: n.color, selected: n.id === selectedNodeId },
        selected: n.id === selectedNodeId,
      })),
    [mmNodes, selectedNodeId]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      mmEdges.map((e) => ({
        id: e.id,
        source: e.source_id,
        target: e.target_id,
        animated: false,
        style: { stroke: "#6e7681", strokeWidth: 1.5 },
      })),
    [mmEdges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => { setNodes(flowNodes); }, [flowNodes, setNodes]);
  useEffect(() => { setEdges(flowEdges); }, [flowEdges, setEdges]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      // Persist position changes back to store
      changes.forEach((c) => {
        if (c.type === "position" && c.position && !c.dragging) {
          updateNode(c.id, { pos_x: c.position.x, pos_y: c.position.y });
        }
      });
    },
    [onNodesChange, updateNode]
  );

  const handleEdgesChange = useCallback((changes: EdgeChange[]) => onEdgesChange(changes), [onEdgesChange]);

  const handlePaneClick = useCallback(() => setSelected(null), [setSelected]);

  const handlePaneDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.classList.contains("react-flow__pane")) return;
      // Get position in flow coords
      const pane = document.querySelector(".react-flow__viewport") as HTMLElement;
      if (!pane) return;
      const rect = pane.getBoundingClientRect();
      const x = (e.clientX - rect.left) / 1 - 200;
      const y = (e.clientY - rect.top) / 1 - 100;
      addNode(null, { x, y });
    },
    [addNode]
  );

  return (
    <div className="absolute inset-0">
      <div className="absolute top-3 left-3 z-10 flex gap-1 bg-bg-panel border border-border rounded-lg p-1">
        {(["free", "lr", "tb", "radial"] as const).map((l) => (
          <button
            key={l}
            onClick={() => setLayout(l)}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              layout === l ? "bg-accent-soft text-accent" : "text-fg-secondary hover:text-fg hover:bg-bg-hover"
            }`}
          >
            {l === "free" ? "Free" : l === "lr" ? "Left-Right" : l === "tb" ? "Top-Bottom" : "Radial"}
          </button>
        ))}
      </div>
      <div className="absolute top-3 right-3 z-10 flex gap-1 bg-bg-panel border border-border rounded-lg p-1">
        <button
          onClick={() => addNode(null)}
          className="px-2.5 py-1 text-[11px] font-medium rounded text-fg-secondary hover:text-fg hover:bg-bg-hover flex items-center gap-1"
        >
          <Plus size={12} /> Node
        </button>
        <button
          onClick={save}
          className={`px-2.5 py-1 text-[11px] font-medium rounded flex items-center gap-1 transition-colors ${
            dirty ? "bg-accent-soft text-accent" : "text-fg-muted"
          }`}
        >
          <Save size={12} /> {dirty ? "Saving…" : "Saved"}
        </button>
        <button
          onClick={() => setLayout(layout)}
          className="px-2.5 py-1 text-[11px] font-medium rounded text-fg-secondary hover:text-fg hover:bg-bg-hover flex items-center gap-1"
          title="Apply layout"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {mmNodes.length === 0 ? (
        <div className="absolute inset-0 grid place-items-center pointer-events-none">
          <div className="text-center text-fg-muted">
            <div className="text-4xl mb-3">🧠</div>
            <div className="text-sm font-medium">Belum ada mind map</div>
            <div className="text-xs mt-1">Buat mind map baru dari Navigator, atau double-click di sini</div>
          </div>
        </div>
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onPaneClick={handlePaneClick}
          onDoubleClick={handlePaneDoubleClick}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          proOptions={{ hideAttribution: true }}
          minZoom={0.1}
          maxZoom={2}
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1.4} color="#21262d" />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeColor={(n) => (n.data?.color as string) || "#58a6ff"}
            maskColor="rgba(13,17,23,0.75)"
          />
        </ReactFlow>
      )}
    </div>
  );
}

export function MindMapCanvas() {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner />
    </ReactFlowProvider>
  );
}
