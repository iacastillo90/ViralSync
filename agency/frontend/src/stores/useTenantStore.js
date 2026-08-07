import { create } from "zustand";

export const useTenantStore = create((set) => ({
  // Estado inicial vacío — se popula desde la respuesta real del backend tras login.
  // NUNCA hardcodear tenant IDs ni claves LiteLLM aquí.
  activeTenant: null,
  availableTenants: [],

  setActiveTenant: (tenant) => set({ activeTenant: tenant }),
  setAvailableTenants: (tenants) => set({ availableTenants: tenants }),
  updateBudgetSpend: (spendUsd) =>
    set((state) => ({
      activeTenant: state.activeTenant
        ? { ...state.activeTenant, current_llm_spend_usd: spendUsd }
        : null,
    })),
  clearTenant: () => set({ activeTenant: null, availableTenants: [] }),
}));
