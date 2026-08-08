"use client";

import { useState } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { RUMBreakdownBarChart } from "../components/RUMBreakdownBarChart";
import { Sparkles, CheckCircle, XCircle } from "lucide-react";

export function IdeaApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();
  const { data, loading, error } = useTenantResource("ideas", tenantId);
  const [queuedIds, setQueuedIds] = useState([]);
  const [decisionError, setDecisionError] = useState(null);

  const ideas = Array.isArray(data) ? data : [];

  const handleDecision = async (idea, approved) => {
    setDecisionError(null);
    if (!idea || !idea.id) return;
    addLog(`Idea ${approved ? "APROBADA" : "RECHAZADA"} por usuario: ${idea.id}`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/ideas/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            idea_id: idea.id,
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );
      setQueuedIds((prev) => [...prev, idea.id]);
    } catch (err) {
      setDecisionError(err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" /> Checkpoint: Evaluación de Ideas RUM
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          {loading ? (
            <p className="text-sm text-slate-400">Cargando ideas…</p>
          ) : error ? (
            <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
              Error al cargar ideas: {error.message}
            </div>
          ) : ideas.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400">No hay ideas pendientes</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {ideas.map((idea) => {
                const queued = queuedIds.includes(idea.id);
                return (
                  <div key={idea.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                    <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2.5 py-1 rounded-full font-bold">
                      Candidata RUM (Score: {idea.rum_score ?? "—"} |{" "}
                      {idea.passes_threshold === true ? "PASS" : "PENDIENTE"})
                    </span>
                    <h2 className="text-lg font-bold text-slate-100">{idea.texto}</h2>
                    <p className="text-sm text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-500 block mb-1 uppercase font-semibold">Gancho Viral (0-5s):</span>
                      "{idea.gancho ?? "—"}"
                    </p>

                    <div className="flex gap-4 text-xs text-slate-300">
                      <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                        Filtro Niño 5 Años:{" "}
                        <strong className={idea.entendible_nino_5_anos === true ? "text-emerald-400" : "text-slate-400"}>
                          {idea.entendible_nino_5_anos === true ? "SI" : idea.entendible_nino_5_anos === false ? "NO" : "—"}
                        </strong>
                      </span>
                      <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                        Filtro 50/100:{" "}
                        <strong className={idea.interesa_50_de_100 === true ? "text-emerald-400" : "text-slate-400"}>
                          {idea.interesa_50_de_100 === true ? "SI" : idea.interesa_50_de_100 === false ? "NO" : "—"}
                        </strong>
                      </span>
                    </div>

                    {["universalidad", "intensidad", "claridad", "shareability", "distribucion", "alineacion"].every(
                        (k) => idea[k] != null
                      ) && <RUMBreakdownBarChart metrics={idea} />}

                    {queued ? (
                      <span className="inline-block text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
                        Encolada para procesamiento (202 accepted)
                      </span>
                    ) : (
                      <div className="flex gap-3 pt-4">
                        <button
                          onClick={() => handleDecision(idea, true)}
                          className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all"
                        >
                          <CheckCircle className="w-4 h-4" /> Aprobar Idea
                        </button>
                        <button
                          onClick={() => handleDecision(idea, false)}
                          className="flex-1 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium py-2.5 rounded-lg transition-all"
                        >
                          <XCircle className="w-4 h-4" /> Rechazar
                        </button>
                      </div>
                    )}
                    {decisionError && (
                      <p className="text-xs text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-2">
                        Error al enviar decisión: {decisionError.message}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}