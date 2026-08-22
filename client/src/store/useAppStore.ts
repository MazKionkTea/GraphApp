import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Mode = "mindmap" | "workflow" | "codemap";

type AppState = {
  mode: Mode;
  setMode: (m: Mode) => void;

  // Currently open artifact
  currentMindmapId: string | null;
  currentWorkflowId: string | null;
  currentProjectId: string | null;
  setCurrentMindmap: (id: string | null) => void;
  setCurrentWorkflow: (id: string | null) => void;
  setCurrentProject: (id: string | null) => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      mode: "mindmap",
      setMode: (mode) => set({ mode }),

      currentMindmapId: null,
      currentWorkflowId: null,
      currentProjectId: null,
      setCurrentMindmap: (id) => set({ currentMindmapId: id, mode: "mindmap" }),
      setCurrentWorkflow: (id) => set({ currentWorkflowId: id, mode: "workflow" }),
      setCurrentProject: (id) => set({ currentProjectId: id, mode: "codemap" }),
    }),
    { name: "graph-app" }
  )
);
