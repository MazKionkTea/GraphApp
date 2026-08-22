import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  addEdge as addRFEdge,
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  type Connection,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import { useWorkflowStore } from "./store";
import { TaskNode } from "./nodes/TaskNode";
import { GroupNode } from "./nodes/GroupNode";
import { CustomEdge } from "./edges/CustomEdge";
import { useRef } from "react";
import { Plus, Save, Undo2, Redo2, Lock, Unlock, Camera, Group, Trash2, Map } from "lucide-react";

const nodeTypes = { task: TaskNode, group: GroupNode };
const edgeTypes = { custom: CustomEdge };

function WorkflowCanvasInner() {
  const {
    nodes: wfNodes, edges: wfEdges, addNode, addEdge, updateNode, removeNode, removeEdge,
    setSelected, selected, addGroup, save, dirty, locked, lastSavedAt,
    takeHistory, undo, redo, canUndo, canRedo, toggleLock, name, setName,
  } = useWorkflowStore();

  const flowNodes: Node[] = useMemo(
    () =>
      wfNodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: n.data as any,
        parentId: n.parentId || undefined,
        extent: n.parentId ? "parent" : undefined,
        style: n.width && n.height ? { width: n.width, height: n.height } : undefined,
        hidden: n.hidden,
        zIndex: n.type === "group" ? -1 : 1,
      })),
    [wfNodes]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      wfEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: "custom",
        data: e.data as any,
      })),
    [wfEdges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);
  const dragStartedRef = useRef(false);

  useEffect(() => { setNodes(flowNodes); }, [flowNodes, setNodes]);
  useEffect(() => { setEdges(flowEdges); }, [flowEdges, setEdges]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      changes.forEach((c) => {
        if (c.type === "position" && c.position) {
          updateNode(c.id, { position: { x: c.position.x, y: c.position.y } });
        }
        if (c.type === "remove") {
          removeNode(c.id);
        }
      });
    },
    [onNodesChange, updateNode, removeNode]
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(changes);
      changes.forEach((c) => {
        if (c.type === "remove") removeEdge(c.id);
      });
    },
    [onEdgesChange, removeEdge]
  );

  const handleConnect = useCallback(
    (conn: Connection) => {
      if (!conn.source || !conn.target) return;
      addEdge(conn.source, conn.target);
    },
    [addEdge]
  );

  const handleSelectionChange = useCallback(
    (params: OnSelectionChangeParams) => {
      setSelected({ nodes: params.nodes.map((n) => n.id), edges: params.edges.map((e) => e.id) });
    },
    [setSelected]
  );

  const handleNodeDragStart = useCallback(() => { takeHistory(); }, [takeHistory]);

  // Keyboard shortcuts
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const mod = e.ctrlKey || e.metaKey;
      if (e.key === "Delete" || e.key === "Backspace") {
        const tag = (document.activeElement as HTMLElement)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        selected.nodes.forEach((id) => removeNode(id));
        selected.edges.forEach((id) => removeEdge(id));
        e.preventDefault();
      }
      if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); undo(); }
      if (mod && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) { e.preventDefault(); redo(); }
      if (mod && e.key.toLowerCase() === "g") { e.preventDefault(); addGroup(); }
      if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
      if (e.key.toLowerCase() === "l" && !mod) toggleLock();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, removeNode, removeEdge, undo, redo, addGroup, save, toggleLock]);

  const handleAutoLayout = useCallback(() => {
    takeHistory();
    // Simple layered BFS
    const incoming: Record<string, number> = {};
    wfNodes.forEach((n) => (incoming[n.id] = 0));
    wfEdges.forEach((e) => { if (incoming[e.target] != null) incoming[e.target] += 1; });
    const visited = new Set<string>();
    const layers: string[][] = [];
    let frontier = wfNodes.filter((n) => incoming[n.id] === 0).map((n) => n.id);
    if (frontier.length === 0 && wfNodes.length > 0) frontier = [wfNodes[0].id];
    while (frontier.length > 0) {
      layers.push(frontier);
      frontier.forEach((id) => visited.add(id));
      const next = new Set<string>();
      wfEdges.forEach((e) => {
        if (frontier.includes(e.source) && !visited.has(e.target)) next.add(e.target);
      });
      frontier = Array.from(next);
    }
    const remaining = wfNodes.filter((n) => !visited.has(n.id)).map((n) => n.id);
    if (remaining.length) layers.push(remaining);
    const positions: Record<string, { x: number; y: number }> = {};
    layers.forEach((layer, colIdx) => {
      layer.forEach((id, rowIdx) => {
        positions[id] = { x: colIdx * 300 + 80, y: rowIdx * 180 + 80 };
      });
    });
    wfNodes.forEach((n) => {
      if (positions[n.id]) updateNode(n.id, { position: positions[n.id] });
    });
  }, [wfNodes, wfEdges, takeHistory, updateNode]);

  return (
    <div className="absolute inset-0 flex flex-col">
      {/* Top toolbar */}
      <div className="h-11 px-3 flex items-center justify-between border-b border-border-soft bg-bg-panel flex-shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-transparent text-[13px] font-semibold outline-none focus:bg-bg-elevated px-2 py-1 rounded max-w-[300px]"
          />
          <span className="text-[10.5px] px-1.5 py-0.5 rounded bg-bg-elevated text-fg-muted font-mono">
            {lastSavedAt ? `Saved ${lastSavedAt}` : dirty ? "Unsaved" : "Saved"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={addNode} className="flex items-center gap-1 px-2.5 py-1 text-[11.5px] font-medium rounded text-fg-secondary hover:text-fg hover:bg-bg-hover">
            <Plus size={12} /> Node
          </button>
          <button onClick={addGroup} className="flex items-center gap-1 px-2.5 py-1 text-[11.5px] font-medium rounded text-fg-secondary hover:text-fg hover:bg-bg-hover" title="Grup (Ctrl+G)">
            <Group size={12} /> Grup
          </button>
          <div className="w-px h-5 bg-border-soft mx-0.5" />
          <button onClick={undo} disabled={!canUndo()} className="w-7 h-7 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover disabled:opacity-30 disabled:cursor-not-allowed" title="Undo (Ctrl+Z)">
            <Undo2 size={12} />
          </button>
          <button onClick={redo} disabled={!canRedo()} className="w-7 h-7 grid place-items-center rounded text-fg-secondary hover:text-fg hover:bg-bg-hover disabled:opacity-30 disabled:cursor-not-allowed" title="Redo (Ctrl+Y)">
            <Redo2 size={12} />
          </button>
          <div className="w-px h-5 bg-border-soft mx-0.5" />
          <button onClick={handleAutoLayout} className="flex items-center gap-1 px-2.5 py-1 text-[11.5px] font-medium rounded text-fg-secondary hover:text-fg hover:bg-bg-hover" title="Auto Layout">
            <Map size={12} /> Layout
          </button>
          <button onClick={toggleLock} className={`w-7 h-7 grid place-items-center rounded hover:bg-bg-hover ${locked ? "text-amber-400" : "text-fg-secondary hover:text-fg"}`} title="Lock (L)">
            {locked ? <Lock size={12} /> : <Unlock size={12} />}
          </button>
          <div className="w-px h-5 bg-border-soft mx-0.5" />
          <button onClick={save} className={`flex items-center gap-1 px-2.5 py-1 text-[11.5px] font-medium rounded ${dirty ? "bg-accent-soft text-accent" : "text-fg-secondary hover:text-fg hover:bg-bg-hover"}`}>
            <Save size={12} /> Simpan
          </button>
        </div>
      </div>

      <div className="flex-1 relative">
        {wfNodes.length === 0 ? (
          <div className="absolute inset-0 grid place-items-center">
            <div className="text-center text-fg-muted">
              <div className="text-4xl mb-3">🔄</div>
              <div className="text-sm font-medium">Belum ada workflow</div>
              <div className="text-xs mt-1">Buat workflow baru dari Navigator</div>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onSelectionChange={handleSelectionChange}
            onNodeDragStart={handleNodeDragStart}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            connectionMode={ConnectionMode.Loose}
            nodesDraggable={!locked}
            nodesConnectable={!locked}
            elementsSelectable={!locked}
            deleteKeyCode={null}
            selectionKeyCode="Shift"
            multiSelectionKeyCode={["Meta", "Control"]}
            snapToGrid
            snapGrid={[16, 16]}
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
              nodeColor={(n) => (n.data as any)?.color || "#3b82f6"}
              maskColor="rgba(13,17,23,0.75)"
            />
          </ReactFlow>
        )}
        {locked && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-md bg-bg-elevated border border-border text-[12px] text-fg-secondary">
            🔒 Kanvas terkunci — tekan L untuk buka
          </div>
        )}
      </div>
    </div>
  );
}

export function WorkflowCanvas() {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner />
    </ReactFlowProvider>
  );
}
