"use client";

import { useTenantStore } from "@/stores/useTenantStore";
import { Sparkles, DollarSign, Building2 } from "lucide-react";

export function Header() {
  const { activeTenant, availableTenants, setActiveTenant } = useTenantStore();

  return (
    <header className="flex justify-between items-center px-6 py-4 bg-slate-900 border-b border-slate-800 text-slate-100">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-600 p-2 rounded-xl text-white shadow-lg shadow-indigo-500/20">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight">ViralSync</span>
          <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full ml-2">
            v1.0 SaaS
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {/* Presupuesto LLM en Tiempo Real */}
        <div className="flex items-center gap-2 bg-slate-950 px-3.5 py-1.5 rounded-lg border border-slate-800 text-xs">
          <DollarSign className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Gasto LLM:</span>
          <span className="font-mono font-semibold text-emerald-300">
            ${activeTenant.current_llm_spend_usd.toFixed(2)} / ${activeTenant.monthly_llm_budget_usd.toFixed(2)}
          </span>
        </div>

        {/* Selector Multi-Tenant */}
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <Building2 className="w-4 h-4 text-indigo-400" />
          <select
            value={activeTenant.id}
            onChange={(e) => {
              const selected = availableTenants.find((t) => t.id === e.target.value);
              if (selected) setActiveTenant({ ...activeTenant, ...selected });
            }}
            className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
          >
            {availableTenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id} className="bg-slate-900 text-slate-200">
                {tenant.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
