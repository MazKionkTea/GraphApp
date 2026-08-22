import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import { useCodeMapStore, type View } from "./store";
import { CodeNode } from "./CodeNode";
import { Search, RefreshCw, Layers, GitBranch, Network, Filter, Zap } from "lucide-react";

const nodeTypes = { code: CodeNode };

const KIND_FILTERS = [
  { id: null, label: "All" },
  { id: "package", label: "Package" },
  { id: "module", label: "Module" },
  { id: "class", label: "Class" },
  { id: "function", label: "Function" },
  { id: "method", label: "Method" },
  { id: "external", label: "External" },
];

function layoutNodes(nodes: Node[]): Node[] {
  // Simple layered layout (TB): group by kind, then by fqn
  const kinds = ["package", "module", "class", "function", "method", "external"];
  const groups: Record<string, Node[]> = {};
  for (const n of nodes) {
    const k = (n.data as any).kind || "external";
    if (!groups[k]) groups[k] = [];
    groups[k].push(n);
  }
  const result: Node[] = [];
  const COL = 200, ROW = 80;
  kinds.forEach((k, colIdx) => {
    (groups[k] || []).forEach((n, rowIdx) => {
      result.push({ ...n, position: { x: 60 + colIdx * COL, y: 60 + rowIdx * ROW } });
    });
  });
  return result;
}

function CodeMapCanvasInner() {
  const { project, graph, view, setView, filterKind, setFilterKind, search, setSearch, selectedFqn, setSelectedFqn, indexing, indexProject } =
    useCodeMapStore();

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Build filtered graph
  const { nodes: visNodes, edges: visEdges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    let ns = graph.nodes;
    let es = graph.edges;
    if (filterKind) {
      ns = ns.filter((n) => n.kind === filterKind);
      const fqns = new Set(ns.map((n) => n.fqn));
      es = es.filter((e) => fqns.has(e.source_fqn) && fqns.has(e.target_fqn));
    }
    if (search) {
      const s = search.toLowerCase();
      ns = ns.filter((n) => n.fqn.toLowerCase().includes(s) || n.name.toLowerCase().includes(s));
      const fqns = new Set(ns.map((n) => n.fqn));
      es = es.filter((e) => fqns.has(e.source_fqn) && fqns.has(e.target_fqn));
    }
    if (view === "subgraph" && selectedFqn) {
      // N-hop from selected
      const hop = 1;
      const keep = new Set<string>([selectedFqn]);
      for (let i = 0; i < hop; i++) {
        for (const e of es) {
          if (keep.has(e.source_fqn)) keep.add(e.target_fqn);
          if (keep.has(e.target_fqn)) keep.add(e.source_fqn);
        }
      }
      ns = ns.filter((n) => keep.has(n.fqn));
      es = es.filter((e) => keep.has(e.source_fqn) && keep.has(e.target_fqn));
    }
    if (view === "dependency") {
      // module-level only — for now show all but tag externally
      es = es.filter((e) => e.source_type === "external" || true);
    }
    return { nodes: ns, edges: es };
  }, [graph, filterKind, search, view, selectedFqn]);

  useEffect(() => {
    const flowN: Node[] = visNodes.map((n) => ({
      id: n.fqn,
      type: "code",
      position: { x: 0, y: 0 },
      data: {
        label: n.name,
        kind: n.kind,
        fqn: n.fqn,
        fan_in: n.fan_in,
        fan_out: n.fan_out,
        is_entry: n.is_entry_point,
        is_leaf: n.is_leaf,
        highlighted: n.fqn === selectedFqn,
        dimmed: false,
      },
    }));
    const flowE: Edge[] = visEdges.map((e) => ({
      id: e.id,
      source: e.source_fqn,
      target: e.target_fqn,
      animated: false,
      style: { stroke: e.source_type === "external" ? "#f85149" : "#6e7681", strokeWidth: 1, opacity: 0.6 },
      label: e.call_count > 1 ? String(e.call_count) : undefined,
      labelStyle: { fontSize: 9, fill: "#9da7b3" },
    }));
    setFlowNodes(layoutNodes(flowN));
    setFlowEdges(flowE);
  }, [visNodes, visEdges, selectedFqn, setFlowNodes, setFlowEdges]);

  const handleNodeClick = useCallback(
    (_e: any, node: Node) => setSelectedFqn(node.id),
    [setSelectedFqn]
  );

  if (!project) {
    return (
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center text-fg-muted">
          <div className="text-4xl mb-3">🐍</div>
          <div className="text-sm font-medium">Belum ada project</div>
          <div className="text-xs mt-1">Buat project baru dari Navigator dengan path ke folder Python</div>
        </div>
      </div>
    );
  }

  if (!project.last_indexed_at) {
    return (
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="text-sm text-fg-muted mb-3">Project belum di-index</div>
          <button
            onClick={() => indexProject(project.id)}
            disabled={indexing}
            className="px-4 py-2 rounded-md bg-accent text-bg-base text-[12.5px] font-medium hover:bg-accent/90 disabled:opacity-50 flex items-center gap-2 mx-auto"
          >
            <Zap size={13} /> {indexing ? "Indexing…" : "Index sekarang"}
          </button>
        </div>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center text-fg-muted">
          <div className="text-sm">Tidak ada data symbol. Coba re-index.</div>
          <button
            onClick={() => indexProject(project.id)}
            disabled={indexing}
            className="mt-3 px-3 py-1.5 rounded-md bg-accent-soft text-accent text-[12px] font-medium hover:bg-accent/20"
          >
            {indexing ? "Re-indexing…" : "Re-index"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0">
      {/* Top bar */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1 bg-bg-panel border border-border rounded-lg p-1">
          {([
            { id: "full", label: "Full", icon: Network },
            { id: "subgraph", label: "Subgraph", icon: Layers },
            { id: "hierarchy", label: "Hierarchy", icon: GitBranch },
            { id: "dependency", label: "Dependency", icon: Filter },
            { id: "analysis", label: "Analysis", icon: Zap },
          ] as { id: View; label: string; icon: any }[]).map((v) => {
            const Icon = v.icon;
            return (
              <button
                key={v.id}
                onClick={() => setView(v.id)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded flex items-center gap-1.5 transition-colors ${
                  view === v.id ? "bg-accent-soft text-accent" : "text-fg-secondary hover:text-fg hover:bg-bg-hover"
                }`}
              >
                <Icon size={11} /> {v.label}
              </button>
            );
          })}
        </div>
        <div className="flex-1 max-w-xs flex items-center gap-2 bg-bg-panel border border-border rounded-lg px-2.5 h-8 focus-within:border-accent">
          <Search size={12} className="text-fg-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search functions, classes…"
            className="flex-1 bg-transparent outline-none text-[12px] placeholder:text-fg-muted"
          />
        </div>
        <div className="flex items-center gap-1 bg-bg-panel border border-border rounded-lg p-1">
          {KIND_FILTERS.map((k) => (
            <button
              key={k.label}
              onClick={() => setFilterKind(k.id)}
              className={`px-2 py-1 text-[10.5px] font-medium rounded transition-colors ${
                filterKind === k.id ? "bg-accent-soft text-accent" : "text-fg-secondary hover:text-fg hover:bg-bg-hover"
              }`}
            >
              {k.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => indexProject(project.id)}
          disabled={indexing}
          className="px-2.5 py-1.5 text-[11px] font-medium rounded bg-bg-panel border border-border text-fg-secondary hover:text-fg hover:bg-bg-hover flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw size={11} className={indexing ? "animate-spin" : ""} /> {indexing ? "Re-index" : "Re-index"}
        </button>
      </div>

      {/* Legend bottom-left */}
      <div className="absolute bottom-3 left-3 z-10 bg-bg-panel border border-border rounded-lg p-2 flex gap-3 text-[10.5px]">
        {[
          { c: "#3fb950", l: "Package" },
          { c: "#58a6ff", l: "Module" },
          { c: "#d29922", l: "Class" },
          { c: "#39c5cf", l: "Function" },
          { c: "#bc8cff", l: "Method" },
          { c: "#6e7681", l: "External" },
        ].map((x) => (
          <div key={x.l} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded" style={{ background: x.c }} />
            <span className="text-fg-secondary">{x.l}</span>
          </div>
        ))}
      </div>

      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
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
          nodeColor={(n) => {
            const k = (n.data as any)?.kind;
            return k === "package" ? "#3fb950"
              : k === "module" ? "#58a6ff"
              : k === "class" ? "#d29922"
              : k === "function" ? "#39c5cf"
              : k === "method" ? "#bc8cff"
              : "#6e7681";
          }}
          maskColor="rgba(13,17,23,0.75)"
        />
      </ReactFlow>
    </div>
  );
}

export function CodeMapCanvas() {
  return (
    <ReactFlowProvider>
      <CodeMapCanvasInner />
    </ReactFlowProvider>
  );
}
