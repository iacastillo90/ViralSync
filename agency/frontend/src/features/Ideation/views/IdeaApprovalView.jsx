"use client";

import { useAgentStore } from "@/stores/useAgentStore";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { RUMBreakdownBarChart } from "../components/RUMBreakdownBarChart";
import { Sparkles, CheckCircle, XCircle } from "lucide-react";

export function IdeaApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();

  const mockIdea = {
    id: "idea-101",
    texto: "3 Errores Críticos al Escalar B2B en 2026",
    gancho: "Si trabajas en B2B, deja de cometer este error hoy mismo",
    rum_score: 0.44477,
    threshold: 0.050,
    entendible_nino_5_anos: true,
    interesa_50_de_100: true,
  };

  const handleDecision = async (approved) => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    addLog(`Idea ${approved ? "APROBADA" : "RECHAZADA"} por usuario`);
    await fetch(`${apiBase}/tenants/${tenantId}/ideas/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idea_id: mockIdea.id,
        status: approved ? "approved" : "rejected",
      }),
    });
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2.5 py-1 rounded-full font-bold">
                Candidata RUM (Score: {mockIdea.rum_score} | PASS)
              </span>
              <h2 className="text-lg font-bold text-slate-100">{mockIdea.texto}</h2>
              <p className="text-sm text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-500 block mb-1 uppercase font-semibold">Gancho Viral (0-5s):</span>
                "{mockIdea.gancho}"
              </p>

              <div className="flex gap-4 text-xs text-slate-300">
                <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                  Filtro Niño 5 Años: <strong className="text-emerald-400">SI</strong>
                </span>
                <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                  Filtro 50/100: <strong className="text-emerald-400">SI</strong>
                </span>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => handleDecision(true)}
                  className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all"
                >
                  <CheckCircle className="w-4 h-4" /> Aprobar Idea
                </button>
                <button
                  onClick={() => handleDecision(false)}
                  className="flex-1 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium py-2.5 rounded-lg transition-all"
                >
                  <XCircle className="w-4 h-4" /> Rechazar
                </button>
              </div>
            </div>

            <RUMBreakdownBarChart metrics={mockIdea} threshold={mockIdea.threshold} />
          </div>
        </main>
      </div>
    </div>
  );
}
