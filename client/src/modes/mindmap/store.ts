import { create } from "zustand";
import { nanoid } from "nanoid";
import type { MindmapNode, MindmapEdge } from "../../api/mindmaps";
import { mindmapsApi } from "../../api/mindmaps";
import { useAppStore } from "../../store/useAppStore";

export type Layout = "lr" | "tb" | "radial" | "free";

type MindMapState = {
  mindmapId: string | null;
  name: string;
  layout: Layout;
  nodes: MindmapNode[];
  edges: MindmapEdge[];
  selectedNodeId: string | null;
  loading: boolean;
  dirty: boolean;

  // Actions
  load: (id: string) => Promise<void>;
  newMindmap: (name: string) => Promise<void>;
  save: () => Promise<void>;
  setLayout: (l: Layout) => void;
  setName: (n: string) => void;
  addNode: (parentId?: string | null, pos?: { x: number; y: number }) => void;
  updateNode: (id: string, patch: Partial<MindmapNode>) => void;
  removeNode: (id: string) => void;
  setSelected: (id: string | null) => void;
  applyAutoLayout: (l: Layout) => void;
};

function layoutLR(nodes: MindmapNode[], edges: MindmapEdge[]): MindmapNode[] {
  // Build child map
  const children: Record<string, string[]> = {};
  const roots: string[] = [];
  for (const n of nodes) {
    const pid = n.parent_id || "_root";
    if (!children[pid]) children[pid] = [];
    children[pid].push(n.id);
  }
  for (const n of nodes) if (!n.parent_id) roots.push(n.id);
  if (roots.length === 0 && nodes.length > 0) {
    // No parent - treat first as root
    roots.push(nodes[0].id);
  }
  // BFS to assign depth + row
  const positions: Record<string, { x: number; y: number }> = {};
  const depth: Record<string, number> = {};
  const row: Record<string, number> = {};
  const colCount: Record<number, number> = {};
  function walk(nid: string, d: number) {
    depth[nid] = d;
    const kids = children[nid] || [];
    kids.forEach((cid, i) => {
      row[cid] = i;
      walk(cid, d + 1);
    });
  }
  roots.forEach((rid) => walk(rid, 0));
  // Compute x by depth, y by row within depth
  const depthBuckets: Record<number, string[]> = {};
  for (const id of Object.keys(depth)) {
    const d = depth[id];
    if (!depthBuckets[d]) depthBuckets[d] = [];
    depthBuckets[d].push(id);
  }
  const COL = 240, ROW = 100;
  Object.keys(depthBuckets).forEach((d) => {
    depthBuckets[+d].forEach((id, idx) => {
      positions[id] = { x: 400 + (+d) * COL, y: 80 + idx * ROW };
    });
  });
  return nodes.map((n) => ({ ...n, pos_x: positions[n.id]?.x ?? n.pos_x, pos_y: positions[n.id]?.y ?? n.pos_y }));
}

function layoutTB(nodes: MindmapNode[], edges: MindmapEdge[]): MindmapNode[] {
  const children: Record<string, string[]> = {};
  for (const n of nodes) {
    const pid = n.parent_id || "_root";
    if (!children[pid]) children[pid] = [];
    children[pid].push(n.id);
  }
  const positions: Record<string, { x: number; y: number }> = {};
  const depth: Record<string, number> = {};
  function walk(nid: string, d: number) {
    depth[nid] = d;
    const kids = children[nid] || [];
    kids.forEach((cid) => walk(cid, d + 1));
  }
  if (nodes.length > 0) walk(nodes[0].id, 0);
  const depthBuckets: Record<number, string[]> = {};
  for (const id of Object.keys(depth)) {
    const d = depth[id];
    if (!depthBuckets[d]) depthBuckets[d] = [];
    depthBuckets[d].push(id);
  }
  Object.keys(depthBuckets).forEach((d) => {
    depthBuckets[+d].forEach((id, idx) => {
      positions[id] = { x: 80 + idx * 220, y: 80 + (+d) * 130 };
    });
  });
  return nodes.map((n) => ({ ...n, pos_x: positions[n.id]?.x ?? n.pos_x, pos_y: positions[n.id]?.y ?? n.pos_y }));
}

function layoutRadial(nodes: MindmapNode[], edges: MindmapEdge[]): MindmapNode[] {
  if (nodes.length === 0) return nodes;
  const root = nodes.find((n) => !n.parent_id) || nodes[0];
  const children: Record<string, string[]> = {};
  for (const n of nodes) {
    const pid = n.parent_id || "_root";
    if (!children[pid]) children[pid] = [];
    children[pid].push(n.id);
  }
  const positions: Record<string, { x: number; y: number }> = { [root.id]: { x: 0, y: 0 } };
  const radius = 280;
  // Place root at center
  positions[root.id] = { x: 0, y: 0 };
  // Place children on first ring
  const firstRing = children[root.id] || [];
  firstRing.forEach((cid, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, firstRing.length);
    positions[cid] = { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  });
  // Place deeper levels outward
  const queue: { id: string; depth: number }[] = firstRing.map((id) => ({ id, depth: 1 }));
  while (queue.length) {
    const { id, depth } = queue.shift()!;
    const kids = children[id] || [];
    const parentPos = positions[id];
    const ringR = radius * (depth + 1);
    kids.forEach((cid, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, kids.length);
      positions[cid] = {
        x: parentPos.x + Math.cos(angle) * (radius * 0.8),
        y: parentPos.y + Math.sin(angle) * (radius * 0.8),
      };
      queue.push({ id: cid, depth: depth + 1 });
    });
  }
  // Normalize to positive coords (offset)
  const xs = Object.values(positions).map((p) => p.x);
  const ys = Object.values(positions).map((p) => p.y);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  return nodes.map((n) => ({
    ...n,
    pos_x: (positions[n.id]?.x ?? 0) - minX + 80,
    pos_y: (positions[n.id]?.y ?? 0) - minY + 80,
  }));
}

export const useMindMapStore = create<MindMapState>((set, get) => ({
  mindmapId: null,
  name: "",
  layout: "free",
  nodes: [],
  edges: [],
  selectedNodeId: null,
  loading: false,
  dirty: false,

  load: async (id: string) => {
    set({ loading: true });
    try {
      const m = await mindmapsApi.get(id);
      set({
        mindmapId: m.id,
        name: m.name,
        layout: m.layout as Layout,
        nodes: m.nodes,
        edges: m.edges,
        selectedNodeId: null,
        loading: false,
        dirty: false,
      });
      useAppStore.getState().setCurrentMindmap(m.id);
    } catch (e) {
      console.error("Failed to load mindmap", e);
      set({ loading: false });
    }
  },

  newMindmap: async (name: string) => {
    const m = await mindmapsApi.create({ name, layout: "free" });
    set({
      mindmapId: m.id,
      name: m.name,
      layout: m.layout as Layout,
      nodes: m.nodes,
      edges: m.edges,
      selectedNodeId: null,
      dirty: false,
    });
    useAppStore.getState().setCurrentMindmap(m.id);
  },

  save: async () => {
    const { mindmapId, nodes, edges, name, layout } = get();
    if (!mindmapId) return;
    try {
      await mindmapsApi.update(mindmapId, { name, theme: "default", layout });
      await mindmapsApi.saveNodes(mindmapId, nodes);
      await mindmapsApi.saveEdges(mindmapId, edges);
      set({ dirty: false });
    } catch (e) {
      console.error("Save failed", e);
    }
  },

  setLayout: (l) => {
    set({ layout: l, dirty: true });
    get().applyAutoLayout(l);
  },

  setName: (n) => set({ name: n, dirty: true }),

  addNode: (parentId = null, pos) => {
    const { nodes, selectedNodeId, layout } = get();
    const newNode: MindmapNode = {
      id: `mm_${nanoid(8)}`,
      label: "New Node",
      icon: "💡",
      color: "#58a6ff",
      pos_x: pos?.x ?? (selectedNodeId
        ? (nodes.find((n) => n.id === selectedNodeId)?.pos_x ?? 100) + 200
        : 100 + nodes.length * 30),
      pos_y: pos?.y ?? (selectedNodeId
        ? (nodes.find((n) => n.id === selectedNodeId)?.pos_y ?? 100) + 60
        : 100 + nodes.length * 30),
      parent_id: parentId ?? selectedNodeId,
    };
    const newNodes = [...nodes, newNode];
    let newEdges = get().edges;
    if (parentId || selectedNodeId) {
      const pid = parentId ?? selectedNodeId!;
      newEdges = [
        ...get().edges,
        { id: `mme_${nanoid(8)}`, source_id: pid, target_id: newNode.id },
      ];
    }
    set({ nodes: newNodes, edges: newEdges, selectedNodeId: newNode.id, dirty: true });
    // For free layout, no auto-positioning
    if (layout !== "free") get().applyAutoLayout(layout);
  },

  updateNode: (id, patch) => {
    set({
      nodes: get().nodes.map((n) => (n.id === id ? { ...n, ...patch } : n)),
      dirty: true,
    });
  },

  removeNode: (id) => {
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source_id !== id && e.target_id !== id),
      selectedNodeId: get().selectedNodeId === id ? null : get().selectedNodeId,
      dirty: true,
    });
  },

  setSelected: (id) => set({ selectedNodeId: id }),

  applyAutoLayout: (l) => {
    const { nodes, edges } = get();
    if (l === "lr") set({ nodes: layoutLR(nodes, edges) });
    else if (l === "tb") set({ nodes: layoutTB(nodes, edges) });
    else if (l === "radial") set({ nodes: layoutRadial(nodes, edges) });
  },
}));

// Autosave debounce
let saveTimer: ReturnType<typeof setTimeout> | null = null;
useMindMapStore.subscribe((state) => {
  if (!state.dirty || !state.mindmapId) return;
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    useMindMapStore.getState().save();
  }, 800);
});
