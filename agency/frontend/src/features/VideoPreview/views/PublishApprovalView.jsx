"use client";

import { useState } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Video, CheckCircle, XCircle } from "lucide-react";

export function PublishApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();
  const { data, loading, error } = useTenantResource("scripts", tenantId);
  const [queued, setQueued] = useState(false);
  const [decisionError, setDecisionError] = useState(null);

  const scripts = Array.isArray(data) ? data : [];
  // Provenance honesta: los videos no tienen GET propio en este cambio; el
  // guión más reciente es la procedencia real del video listo para publicar.
  const latestScript = scripts[scripts.length - 1] || null;

  const handleDecision = async (approved) => {
    setDecisionError(null);
    addLog(`Publicación de video ${approved ? "APROBADA" : "RECHAZADA"}`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/publish/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );
      setQueued(true);
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
                <Video className="w-5 h-5 text-indigo-400" /> Checkpoint: Aprobación de Publicación
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          {loading ? (
            <p className="text-sm text-slate-400">Cargando…</p>
          ) : error ? (
            <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
              Error al cargar la cola de publicación: {error.message}
            </div>
          ) : !latestScript ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-sm text-slate-400">No hay videos en cola para publicar todavía</p>
            </div>
          ) : (
            <div className="max-w-2xl bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
                Guion listo — pendiente de aprobación de publicación
              </span>

              <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <p className="text-slate-400">Origen (último guion aprobado):</p>
                <p className="text-sm text-slate-200">
                  CTA: <span className="text-indigo-300">{latestScript.cta_50_60s || "—"}</span>
                </p>
                <p className="text-sm text-slate-200">
                  Keyword: <span className="font-mono text-indigo-400">{latestScript.keyword || "—"}</span>
                </p>
              </div>

              {queued ? (
                <span className="inline-block text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
                  Publicación encolada para procesamiento (202 accepted)
                </span>
              ) : (
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => handleDecision(true)}
                    className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all"
                  >
                    <CheckCircle className="w-4 h-4" /> Aprobar Publicación en Instagram
                  </button>
                  <button
                    onClick={() => handleDecision(false)}
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
          )}
        </main>
      </div>
    </div>
  );
}