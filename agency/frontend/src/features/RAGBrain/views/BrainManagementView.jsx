"use client";

import { useTenantResource } from "@/hooks/useTenantResource";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Brain, Database, Sparkles } from "lucide-react";

function PersonaRows({ persona }) {
  if (!persona) return null;
  if (typeof persona === "string") {
    return <p className="text-slate-200">{persona}</p>;
  }
  return (
    <div className="space-y-2 text-xs">
      {Object.entries(persona).map(([k, v]) => (
        <div key={k} className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-500 font-semibold block mb-1 capitalize">{k.replace(/_/g, " ")}:</span>
          <p className="text-slate-200">{Array.isArray(v) ? v.join(" | ") : String(v)}</p>
        </div>
      ))}
    </div>
  );
}

export function BrainManagementView({ tenantId }) {
  const { data, loading, error } = useTenantResource("brain", tenantId);
  const brain = data && typeof data === "object" ? data : null;
  const persona = brain?.persona ?? null;
  const noData = !brain || brain?.status === "no_data" || !persona;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Brain className="w-5 h-5 text-indigo-400" /> Cerebro de Marketing RAG & Qdrant
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          {loading ? (
            <p className="text-sm text-slate-400">Cargando cerebro…</p>
          ) : error ? (
            <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
              Error al cargar el cerebro: {error.message}
            </div>
          ) : noData ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400">Cerebro sin datos aún</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> Brand Persona & Tono
                </h2>
                <PersonaRows persona={persona} />
                {brain?.collection_stats != null && (
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                    <span className="text-slate-500 font-semibold block mb-1">Estadísticas de colección:</span>
                    <p className="text-slate-200">{JSON.stringify(brain.collection_stats)}</p>
                  </div>
                )}
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4 text-emerald-400" /> Colección Qdrant (`{brain?.collection || "marketing_brain"}`)
                </h2>
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                    <span className="text-slate-400">Estado:</span>
                    <span className="font-mono font-bold text-emerald-400">{brain?.status}</span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                    <span className="text-slate-400">Chunks Indexados:</span>
                    <span className="font-mono font-bold text-indigo-400">
                      {Array.isArray(brain?.chunks) ? brain.chunks.length : 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}