import { create } from "zustand";

export const useTenantStore = create((set) => ({
  activeTenant: {
    id: "tenant-demo-001",
    name: "Cliente Demo Marketing",
    niche: "Negocios B2B y SaaS",
    litellm_virtual_key: "sk-agency-tenant-demo-001",
    monthly_llm_budget_usd: 20.00,
    current_llm_spend_usd: 4.82,
  },
  availableTenants: [
    {
      id: "tenant-demo-001",
      name: "Cliente Demo Marketing",
      niche: "Negocios B2B y SaaS",
    },
    {
      id: "tenant-fitness-002",
      name: "Gimnasios Elite Fitness",
      niche: "Fitness B2B",
    },
  ],

  setActiveTenant: (tenant) => set({ activeTenant: tenant }),
  updateBudgetSpend: (spendUsd) =>
    set((state) => ({
      activeTenant: { ...state.activeTenant, current_llm_spend_usd: spendUsd },
    })),
}));
