import { create } from "zustand";
import { nanoid } from "nanoid";
import type { WorkflowNode, WorkflowEdge, Workflow } from "../../api/workflows";
import { workflowsApi } from "../../api/workflows";
import { useAppStore } from "../../store/useAppStore";

const MAX_HISTORY = 60;

type History = { nodes: WorkflowNode[]; edges: WorkflowEdge[] };

type WorkflowState = {
  workflowId: string | null;
  name: string;
  status: "draft" | "published";
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selected: { nodes: string[]; edges: string[] };
  loading: boolean;
  dirty: boolean;
  locked: boolean;
  lastSavedAt: string | null;

  // History
  past: History[];
  future: History[];

  // Actions
  load: (id: string) => Promise<void>;
  newWorkflow: (name: string) => Promise<void>;
  save: () => Promise<void>;
  setName: (n: string) => void;
  setStatus: (s: "draft" | "published") => void;
  toggleLock: () => void;
  setSelected: (s: { nodes: string[]; edges: string[] }) => void;

  // Node operations
  addNode: () => void;
  updateNode: (id: string, patch: Partial<WorkflowNode>) => void;
  removeNode: (id: string) => void;
  duplicateNode: (id: string) => void;
  addGroup: () => void;

  // Edge operations
  addEdge: (source: string, target: string) => void;
  updateEdge: (id: string, patch: Partial<WorkflowEdge>) => void;
  removeEdge: (id: string) => void;

  // History
  takeHistory: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
};

function starterNodes(): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  const a: WorkflowNode = {
    id: `node_${nanoid(8)}`,
    type: "task",
    position: { x: 120, y: 160 },
    data: { title: "Tugas 1", action: "", description: "", showDescription: false, color: "#3b82f6", icon: "📝" },
  };
  const b: WorkflowNode = {
    id: `node_${nanoid(8)}`,
    type: "task",
    position: { x: 480, y: 160 },
    data: { title: "Tugas 2", action: "", description: "", showDescription: false, color: "#22c55e", icon: "⚙️" },
  };
  return { nodes: [a, b], edges: [] };
}

function deepClone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflowId: null,
  name: "",
  status: "draft",
  nodes: [],
  edges: [],
  selected: { nodes: [], edges: [] },
  loading: false,
  dirty: false,
  locked: false,
  lastSavedAt: null,
  past: [],
  future: [],

  load: async (id) => {
    set({ loading: true });
    try {
      const w = await workflowsApi.get(id);
      set({
        workflowId: w.id,
        name: w.name,
        status: w.status as "draft" | "published",
        nodes: w.nodes,
        edges: w.edges,
        selected: { nodes: [], edges: [] },
        past: [],
        future: [],
        loading: false,
        dirty: false,
      });
      useAppStore.getState().setCurrentWorkflow(w.id);
    } catch (e) {
      console.error("Failed to load workflow", e);
      set({ loading: false });
    }
  },

  newWorkflow: async (name) => {
    const start = starterNodes();
    const w = await workflowsApi.create({ name, status: "draft", nodes: start.nodes, edges: start.edges });
    set({
      workflowId: w.id,
      name: w.name,
      status: w.status as "draft",
      nodes: w.nodes,
      edges: w.edges,
      selected: { nodes: [], edges: [] },
      past: [],
      future: [],
      dirty: false,
    });
    useAppStore.getState().setCurrentWorkflow(w.id);
  },

  save: async () => {
    const { workflowId, nodes, edges, name, status } = get();
    if (!workflowId) return;
    try {
      await workflowsApi.saveFull(workflowId, { name, status, nodes, edges });
      set({ dirty: false, lastSavedAt: new Date().toLocaleTimeString("id-ID") });
    } catch (e) {
      console.error("Save failed", e);
    }
  },

  setName: (n) => set({ name: n, dirty: true }),
  setStatus: (s) => set({ status: s, dirty: true }),
  toggleLock: () => set((s) => ({ locked: !s.locked })),
  setSelected: (s) => set({ selected: s }),

  takeHistory: () => {
    const { nodes, edges, past, future } = get();
    const newPast = [...past, { nodes: deepClone(nodes), edges: deepClone(edges) }];
    if (newPast.length > MAX_HISTORY) newPast.shift();
    set({ past: newPast, future: [] });
  },

  undo: () => {
    const { past, future, nodes, edges } = get();
    if (past.length === 0) return;
    const prev = past[past.length - 1];
    const newFuture = [...future, { nodes: deepClone(nodes), edges: deepClone(edges) }];
    set({ nodes: prev.nodes, edges: prev.edges, past: past.slice(0, -1), future: newFuture, dirty: true });
  },

  redo: () => {
    const { past, future, nodes, edges } = get();
    if (future.length === 0) return;
    const next = future[future.length - 1];
    const newPast = [...past, { nodes: deepClone(nodes), edges: deepClone(edges) }];
    set({ nodes: next.nodes, edges: next.edges, past: newPast, future: future.slice(0, -1), dirty: true });
  },

  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,

  addNode: () => {
    get().takeHistory();
    const newNode: WorkflowNode = {
      id: `node_${nanoid(8)}`,
      type: "task",
      position: { x: Math.random() * 400 + 100, y: Math.random() * 300 + 100 },
      data: { title: "Tugas Baru", action: "", description: "", showDescription: false, color: "#3b82f6", icon: "📝" },
    };
    set({ nodes: [...get().nodes, newNode], dirty: true, selected: { nodes: [newNode.id], edges: [] } });
  },

  updateNode: (id, patch) => {
    set({
      nodes: get().nodes.map((n) => (n.id === id ? { ...n, ...patch, data: { ...n.data, ...(patch.data || {}) } } : n)),
      dirty: true,
    });
  },

  removeNode: (id) => {
    get().takeHistory();
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
      selected: { nodes: [], edges: [] },
      dirty: true,
    });
  },

  duplicateNode: (id) => {
    get().takeHistory();
    const src = get().nodes.find((n) => n.id === id);
    if (!src) return;
    const newId = `node_${nanoid(8)}`;
    const clone: WorkflowNode = {
      ...deepClone(src),
      id: newId,
      position: { x: src.position.x + 40, y: src.position.y + 40 },
    };
    set({ nodes: [...get().nodes, clone], dirty: true, selected: { nodes: [newId], edges: [] } });
  },

  addGroup: () => {
    const sel = get().selected.nodes;
    if (sel.length < 2) {
      alert("Pilih minimal 2 node (Shift + drag) untuk membuat grup.");
      return;
    }
    get().takeHistory();
    const nodes = get().nodes;
    const selected = nodes.filter((n) => sel.includes(n.id));
    const PAD = 36;
    const HEADER = 44;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    selected.forEach((n) => {
      const w = n.width || 240;
      const h = n.height || 130;
      minX = Math.min(minX, n.position.x);
      minY = Math.min(minY, n.position.y);
      maxX = Math.max(maxX, n.position.x + w);
      maxY = Math.max(maxY, n.position.y + h);
    });
    const groupX = minX - PAD;
    const groupY = minY - PAD - HEADER;
    const groupW = maxX - minX + PAD * 2;
    const groupH = maxY - minY + PAD * 2 + HEADER;
    const groupId = `group_${nanoid(8)}`;
    const groupNode: WorkflowNode = {
      id: groupId,
      type: "group",
      position: { x: groupX, y: groupY },
      width: groupW,
      height: groupH,
      data: { title: "Grup Baru", color: "#3b82f6", collapsed: false, expandedSize: { width: groupW, height: groupH } },
    };
    const newNodes = nodes.map((n) => {
      if (!sel.includes(n.id)) return n;
      return {
        ...n,
        parentId: groupId,
        position: { x: n.position.x - groupX, y: n.position.y - groupY },
      } as WorkflowNode;
    });
    set({ nodes: [groupNode, ...newNodes], dirty: true, selected: { nodes: [groupId], edges: [] } });
  },

  addEdge: (source, target) => {
    get().takeHistory();
    const newEdge: WorkflowEdge = {
      id: `edge_${nanoid(8)}`,
      source,
      target,
      data: { label: "", color: "#8a8a8f", waypoints: [] },
    };
    set({ edges: [...get().edges, newEdge], dirty: true });
  },

  updateEdge: (id, patch) => {
    set({
      edges: get().edges.map((e) => (e.id === id ? { ...e, ...patch, data: { ...e.data, ...(patch.data || {}) } } : e)),
      dirty: true,
    });
  },

  removeEdge: (id) => {
    get().takeHistory();
    set({
      edges: get().edges.filter((e) => e.id !== id),
      selected: { nodes: [], edges: [] },
      dirty: true,
    });
  },
}));

// Autosave debounce
let saveTimer: ReturnType<typeof setTimeout> | null = null;
useWorkflowStore.subscribe((state) => {
  if (!state.dirty || !state.workflowId) return;
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    useWorkflowStore.getState().save();
  }, 1000);
});
