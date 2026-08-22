import { api } from "./client";

export type MindmapNode = {
  id: string;
  label: string;
  icon?: string | null;
  color?: string | null;
  pos_x: number;
  pos_y: number;
  parent_id?: string | null;
};

export type MindmapEdge = {
  id: string;
  source_id: string;
  target_id: string;
  label?: string | null;
};

export type Mindmap = {
  id: string;
  name: string;
  theme: string;
  layout: "lr" | "tb" | "radial" | "free";
  created_at: string;
  updated_at: string;
  nodes: MindmapNode[];
  edges: MindmapEdge[];
};

export type MindmapSummary = {
  id: string;
  name: string;
  theme: string;
  layout: string;
  created_at: string;
  updated_at: string;
  node_count: number;
  edge_count: number;
};

export const mindmapsApi = {
  list: () => api.get<MindmapSummary[]>("/mindmaps"),
  get: (id: string) => api.get<Mindmap>(`/mindmaps/${id}`),
  create: (data: { name: string; theme?: string; layout?: Mindmap["layout"] }) =>
    api.post<Mindmap>("/mindmaps", data),
  update: (id: string, data: { name: string; theme: string; layout: Mindmap["layout"] }) =>
    api.put<Mindmap>(`/mindmaps/${id}`, data),
  remove: (id: string) => api.delete(`/mindmaps/${id}`),
  saveNodes: (id: string, nodes: MindmapNode[]) => api.put(`/mindmaps/${id}/nodes`, nodes),
  saveEdges: (id: string, edges: MindmapEdge[]) => api.put(`/mindmaps/${id}/edges`, edges),
};
