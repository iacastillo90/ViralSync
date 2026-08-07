import { create } from "zustand";

export const useAgentStore = create((set) => ({
  tenantId: null,  // Inicializado vacío — se setea desde el TenantStore tras login.
  nodes: {
    ideation: "idle",
    human_approval_idea: "idle",
    scriptwriting: "idle",
    video_edit: "idle",
    human_approval_publish: "idle",
    publish: "idle",
  },
  logs: ["[System] Dashboard ViralSync iniciado."],
  pausedCheckpoint: null,
  ideas: [],
  selectedIdea: null,
  leads: [],
  metrics: [],

  setTenantId: (tenantId) => set({ tenantId }),
  setNodeState: (node, status) =>
    set((state) => ({
      nodes: { ...state.nodes, [node]: status },
    })),
  addLog: (message) =>
    set((state) => ({
      logs: [
        ...state.logs,
        `[${new Date().toLocaleTimeString()}] ${message}`,
      ].slice(-100), // Mantener últimos 100 logs
    })),
  setCheckpointPaused: (node, paused) =>
    set({ pausedCheckpoint: paused ? node : null }),
  setIdeas: (ideas) => set({ ideas }),
  setSelectedIdea: (selectedIdea) => set({ selectedIdea }),
  setLeads: (leads) => set({ leads }),
  setMetrics: (metrics) => set({ metrics }),
}));
