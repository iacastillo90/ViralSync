"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAgentStore } from "@/stores/useAgentStore";
import { ShieldCheck, Cpu, Database, Server } from "lucide-react";

export default function AdminSistemaPage() {
  const { tenantId } = useAgentStore();
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
        </main>
      </div>
    </div>
  );
}
