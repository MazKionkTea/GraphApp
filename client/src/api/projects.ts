import { api } from "./client";

export type Project = {
  id: string;
  name: string;
  root_path: string;
  last_indexed_at: string | null;
  created_at: string;
  file_count: number;
  symbol_count: number;
  call_count: number;
  settings: Record<string, any>;
};

export type ProjectSummary = {
  id: string;
  name: string;
  root_path: string;
  last_indexed_at: string | null;
  created_at: string;
  file_count: number;
  symbol_count: number;
  call_count: number;
};

export type Symbol = {
  id: string;
  fqn: string;
  name: string;
  kind: "package" | "module" | "class" | "function" | "method" | "external";
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  parent_fqn: string | null;
  complexity: number | null;
  loc: number | null;
  fan_in: number;
  fan_out: number;
  total_calls: number;
  is_entry_point: boolean;
  is_leaf: boolean;
};

export type Call = {
  id: string;
  source_fqn: string;
  target_fqn: string;
  file_path: string | null;
  line_number: number | null;
  call_count: number;
  source_type: string;
  mode: string;
};

export type GraphData = {
  nodes: Symbol[];
  edges: Call[];
  summary: {
    total_symbols: number;
    total_calls: number;
    entry_points: number;
    leaf_functions: number;
    avg_fan_in: number;
    avg_fan_out: number;
  };
};

export const projectsApi = {
  list: () => api.get<ProjectSummary[]>("/projects"),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (data: { name: string; root_path: string }) => api.post<Project>("/projects", data),
  remove: (id: string) => api.delete(`/projects/${id}`),

  index: (
    id: string,
    data: {
      include_external?: boolean;
      project_only_edges?: boolean;
      dynamic_trace?: boolean;
      target_script?: string | null;
    } = {}
  ) => api.post<{ project_id: string; duration_seconds: number; summary: any }>(`/projects/${id}/index`, data),

  getGraph: (id: string, kind?: string) =>
    api.get<GraphData>(`/projects/${id}/graph${kind ? `?kind=${kind}` : ""}`),

  listFiles: (id: string) => api.get<{ id: string; path: string; hash: string | null }[]>(`/projects/${id}/files`),
  listSymbols: (id: string, params: { kind?: string; search?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.kind) q.set("kind", params.kind);
    if (params.search) q.set("search", params.search);
    const qs = q.toString();
    return api.get<Symbol[]>(`/projects/${id}/symbols${qs ? `?${qs}` : ""}`);
  },

  getCallers: (id: string, fqn: string) =>
    api.get<Call[]>(`/projects/${id}/symbols/${encodeURI(fqn)}/callers`),
  getCallees: (id: string, fqn: string) =>
    api.get<Call[]>(`/projects/${id}/symbols/${encodeURI(fqn)}/callees`),

  getEntryPoints: (id: string) => api.get<Symbol[]>(`/projects/${id}/entry-points`),
  getLeafFunctions: (id: string) => api.get<Symbol[]>(`/projects/${id}/leaf-functions`),

  getSource: (id: string, path: string, line: number, context = 5) =>
    api.get<{ path: string; line: number; start: number; end: number; snippet: string }>(
      `/projects/${id}/source?path=${encodeURIComponent(path)}&line=${line}&context=${context}`
    ),
};
