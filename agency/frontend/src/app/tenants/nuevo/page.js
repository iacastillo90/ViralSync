"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Building2, PlusCircle } from "lucide-react";

export default function NuevoTenantPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    niche: "",
    monthly_llm_budget_usd: 20.00,
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    const res = await fetch(`${apiBase}/tenants`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    if (res.ok) {
      const data = await res.json();
      router.push(`/tenants/${data.id}/pipeline`);
    } else {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId="nuevo" />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-400" /> Onboarding de Nuevo Cliente SaaS
              </h1>
              <p className="text-xs text-slate-400">
                Creación de Tenant con Virtual Key de LiteLLM Gateway
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="max-w-xl bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                Nombre de la Empresa / Cliente
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ej: Gimnasios Elite Fitness"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                Nicho / Categoría de Mercado
              </label>
              <input
                type="text"
                required
                value={formData.niche}
                onChange={(e) => setFormData({ ...formData, niche: e.target.value })}
                placeholder="Ej: Fitness B2B"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                Presupuesto Mensual LLM (USD)
              </label>
              <input
                type="number"
                step="5"
                min="5"
                value={formData.monthly_llm_budget_usd}
                onChange={(e) =>
                  setFormData({ ...formData, monthly_llm_budget_usd: parseFloat(e.target.value) })
                }
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-emerald-400 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-lg transition-all"
            >
              <PlusCircle className="w-4 h-4" /> {loading ? "Registrando..." : "Crear Tenant & Asignar Virtual Key"}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}
