import { create } from "zustand";
import { useAppStore } from "../../store/useAppStore";
import { projectsApi, type Project, type ProjectSummary, type Symbol, type Call, type GraphData } from "../../api/projects";

export type View = "full" | "subgraph" | "hierarchy" | "dependency" | "analysis";

type CodeMapState = {
  project: Project | null;
  projects: ProjectSummary[];
  graph: GraphData | null;
  loading: boolean;
  indexing: boolean;
  selected: { symbol: Symbol | null };
  selectedFqn: string | null;
  view: View;
  filterKind: string | null;
  search: string;
  metrics: any;

  // Setters
  setView: (v: View) => void;
  setFilterKind: (k: string | null) => void;
  setSearch: (s: string) => void;
  setSelectedFqn: (fqn: string | null) => void;

  // Actions
  refreshProjects: () => Promise<void>;
  loadProject: (id: string) => Promise<void>;
  createProject: (name: string, root_path: string) => Promise<Project>;
  removeProject: (id: string) => Promise<void>;
  indexProject: (id: string, opts?: { dynamic_trace?: boolean; target_script?: string }) => Promise<void>;
};

export const useCodeMapStore = create<CodeMapState>((set, get) => ({
  project: null,
  projects: [],
  graph: null,
  loading: false,
  indexing: false,
  selected: { symbol: null },
  selectedFqn: null,
  view: "full",
  filterKind: null,
  search: "",
  metrics: null,

  setView: (v) => set({ view: v }),
  setFilterKind: (k) => set({ filterKind: k }),
  setSearch: (s) => set({ search: s }),
  setSelectedFqn: (fqn) => set({ selectedFqn: fqn }),

  refreshProjects: async () => {
    try {
      const list = await projectsApi.list();
      set({ projects: list });
    } catch (e) {
      console.error(e);
    }
  },

  loadProject: async (id) => {
    set({ loading: true, graph: null, selectedFqn: null, project: null });
    try {
      const project = await projectsApi.get(id);
      useAppStore.getState().setCurrentProject(id);
      let graph: GraphData | null = null;
      if (project.last_indexed_at) {
        try {
          graph = await projectsApi.getGraph(id);
        } catch (e) {
          console.error("Failed to load graph", e);
        }
      }
      const settings = project.settings || {};
      set({
        project,
        graph,
        loading: false,
        metrics: settings?.phase4_summary || null,
      });
    } catch (e) {
      console.error("Failed to load project", e);
      set({ loading: false });
    }
  },

  createProject: async (name, root_path) => {
    const p = await projectsApi.create({ name, root_path });
    await get().refreshProjects();
    return p;
  },

  removeProject: async (id) => {
    await projectsApi.remove(id);
    if (get().project?.id === id) {
      set({ project: null, graph: null, selectedFqn: null });
    }
    await get().refreshProjects();
  },

  indexProject: async (id, opts = {}) => {
    set({ indexing: true });
    try {
      await projectsApi.index(id, opts);
      // Reload
      const project = await projectsApi.get(id);
      const graph = await projectsApi.getGraph(id);
      set({
        project,
        graph,
        metrics: project.settings?.phase4_summary || null,
        indexing: false,
      });
      await get().refreshProjects();
    } catch (e) {
      console.error("Index failed", e);
      set({ indexing: false });
      throw e;
    }
  },
}));
