import { api } from "./client";

export type WorkflowNode = {
  id: string;
  type: "task" | "group";
  position: { x: number; y: number };
  width?: number | null;
  height?: number | null;
  parentId?: string | null;
  hidden?: boolean;
  data: Record<string, any>;
};

export type WorkflowEdge = {
  id: string;
  source: string;
  target: string;
  data?: Record<string, any>;
};

export type Workflow = {
  id: string;
  name: string;
  status: "draft" | "published";
  version: number;
  archived: boolean;
  viewport?: { x: number; y: number; zoom: number } | null;
  created_at: string;
  updated_at: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export type WorkflowSummary = {
  id: string;
  name: string;
  status: string;
  version: number;
  archived: boolean;
  created_at: string;
  updated_at: string;
  node_count: number;
  edge_count: number;
};

export type Snapshot = {
  id: string;
  workflow_id: string;
  label: string;
  created_at: string;
  node_count: number;
  edge_count: number;
};

export const workflowsApi = {
  list: (includeArchived = false) =>
    api.get<WorkflowSummary[]>(`/workflows${includeArchived ? "?include_archived=true" : ""}`),
  get: (id: string) => api.get<Workflow>(`/workflows/${id}`),
  create: (data: {
    name: string;
    status?: "draft" | "published";
    nodes?: WorkflowNode[];
    edges?: WorkflowEdge[];
  }) => api.post<Workflow>("/workflows", data),
  update: (id: string, data: Partial<Pick<Workflow, "name" | "status" | "archived" | "viewport">>) =>
    api.put<Workflow>(`/workflows/${id}`, data),
  remove: (id: string) => api.delete(`/workflows/${id}`),
  clone: (id: string) => api.post<Workflow>(`/workflows/${id}/clone`),
  saveFull: (id: string, data: {
    name: string;
    status: "draft" | "published";
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    viewport?: { x: number; y: number; zoom: number } | null;
  }) => api.put(`/workflows/${id}/save`, data),

  // Snapshots
  listSnapshots: (wid: string) => api.get<Snapshot[]>(`/workflows/${wid}/snapshots`),
  createSnapshot: (wid: string, data: { label: string; nodes: any[]; edges: any[] }) =>
    api.post<Snapshot>(`/workflows/${wid}/snapshots`, data),
  restoreSnapshot: (wid: string, sid: string) =>
    api.post<Workflow>(`/workflows/${wid}/snapshots/${sid}/restore`),
  deleteSnapshot: (wid: string, sid: string) =>
    api.delete(`/workflows/${wid}/snapshots/${sid}`),

  // Actions
  listActions: () => api.get<{ name: string }[]>("/actions"),
  addAction: async (name: string) => {
    // Add via query string (matches backend route)
    return api.post<{ name: string }>(`/actions?name=${encodeURIComponent(name)}`);
  },
  renameAction: (oldName: string, newName: string) =>
    api.put<{ name: string }[]>(`/actions/${encodeURIComponent(oldName)}?new_name=${encodeURIComponent(newName)}`),
  deleteAction: (name: string) => api.delete(`/actions/${encodeURIComponent(name)}`),
};
