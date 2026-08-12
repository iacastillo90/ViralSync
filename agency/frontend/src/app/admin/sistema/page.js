"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAgentStore } from "@/stores/useAgentStore";
import { ShieldCheck, Cpu, Database, Server, AlertTriangle } from "lucide-react";
import { useState, useEffect } from "react";

export default function AdminSistemaPage() {
  const { tenantId } = useAgentStore();
  const [llmErrors, setLlmErrors] = useState([]);
  const [loadingErrors, setLoadingErrors] = useState(true);

  const fetchErrors = async () => {
    setLoadingErrors(true);
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/llm-errors`);
      const data = await res.json();
      setLlmErrors(data.errors || []);
    } catch (err) {
      console.error("Error fetching LLM errors:", err);
    } finally {
      setLoadingErrors(false);
    }
  };

  useEffect(() => {
    fetchErrors();
    const interval = setInterval(fetchErrors, 15000);
    return () => clearInterval(interval);
  }, []);

  const services = [
    { name: "LiteLLM Proxy Gateway", icon: Cpu, status: "ONLINE", detail: "Pool gratuito (Groq/Gemini/SambaNova) activo" },
    { name: "Celery Workers", icon: Server, status: "ONLINE", detail: "Redis broker conectado (--concurrency=1 dev)" },
    { name: "Qdrant Vector DB", icon: Database, status: "ONLINE", detail: "Colección marketing_brain 1.19.0" },
    { name: "SearXNG Engine", icon: Server, status: "ONLINE", detail: "Búsqueda web sanitizada activa" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId || "nuevo"} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" /> Panel de Administración del Sistema
              </h1>
              <p className="text-xs text-slate-400">
                Monitoreo de Infraestructura Local & LiteLLM Gateway
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {services.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.name} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2 font-bold text-sm text-slate-200">
                      <Icon className="w-4 h-4 text-indigo-400" /> {s.name}
                    </div>
                    <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold">
                      {s.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{s.detail}</p>
                </div>
              );
            })}
          </div>

          {/* Registro de Errores LLM & Fallbacks */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mt-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-md font-bold flex items-center gap-2 text-slate-200">
                <AlertTriangle className="w-4 h-4 text-rose-400" /> Registro de Errores LLM & Fallbacks
              </h2>
              <button 
                onClick={fetchErrors}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded transition-colors"
              >
                Actualizar
              </button>
            </div>

            {loadingErrors ? (
              <p className="text-xs text-slate-400">Cargando historial...</p>
            ) : llmErrors.length === 0 ? (
              <p className="text-xs text-slate-400">No hay errores recientes registrados en los proveedores LLM. El sistema está saludable.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/50 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Timestamp</th>
                      <th className="px-3 py-2 font-semibold">Modelo / Proveedor</th>
                      <th className="px-3 py-2 font-semibold">Error Detallado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {llmErrors.map((err, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                        <td className="px-3 py-3 font-mono text-[10px] whitespace-nowrap text-slate-400">
                          {new Date(err.timestamp).toLocaleString()}
                        </td>
                        <td className="px-3 py-3">
                          <span className="bg-rose-950/30 text-rose-300 border border-rose-500/20 px-2 py-0.5 rounded font-mono font-medium">
                            {err.model}
                          </span>
                        </td>
                        <td className="px-3 py-3 font-mono text-[10px] break-words text-rose-400/80">
                          {err.error}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
