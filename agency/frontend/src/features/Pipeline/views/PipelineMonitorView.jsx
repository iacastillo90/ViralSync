"use client";

import { useAgentStore } from "@/stores/useAgentStore";
import { useSSEStream } from "@/hooks/useSSEStream";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Activity, Play } from "lucide-react";

export function PipelineMonitorView({ tenantId }) {
  const { nodes, logs, addLog } = useAgentStore();
  useSSEStream(tenantId);

  const handleRunGraph = async () => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    addLog(`Ejecutando StateGraph para tenant '${tenantId}'...`);
    await fetch(`${apiBase}/tenants/${tenantId}/graph/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force_reideation: false }),
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
              <h1 className="text-xl font-bold">Orquestador de Pipeline LangGraph</h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
            <button
              onClick={handleRunGraph}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-all"
            >
              <Play className="w-4 h-4 fill-current" /> Iniciar Hilo de Grafo
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2 text-slate-300 uppercase tracking-wider">
                <Activity className="w-4 h-4 text-indigo-400" /> Mapa de Nodos Activos
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {Object.entries(nodes).map(([nodeName, status]) => (
                  <div
                    key={nodeName}
                    className={`p-4 rounded-xl border transition-all ${
                      status === "running"
                        ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-300 animate-pulse"
                        : status === "completed"
                        ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-300"
                        : "bg-slate-950 border-slate-800 text-slate-400"
                    }`}
                  >
                    <span className="text-[10px] uppercase font-mono tracking-wider">
                      {status}
                    </span>
                    <p className="font-semibold text-sm capitalize text-slate-200 mt-1">
                      {nodeName.replace(/_/g, " ")}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold mb-4 text-slate-300 uppercase tracking-wider">
                Consola SSE en Tiempo Real
              </h2>
              <div className="h-80 overflow-y-auto font-mono text-xs bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5">
                {logs.map((log, idx) => (
                  <div key={idx} className="text-slate-300 leading-relaxed">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
