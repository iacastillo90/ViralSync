"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Script4BlockReader } from "../components/Script4BlockReader";
import { FileText } from "lucide-react";

export function ScriptInspectorView({ tenantId }) {
  const mockScript = {
    gancho_0_5s: "Si trabajas en Negocios B2B, deja de cometer este error hoy mismo",
    contexto_5_30s: "El problema principal no es la falta de herramientas, sino intentar abarcar todo sin foco. Cuando aplicas la simplificación estructural, tu tasa de conversión se triplica en cuestión de días.",
    moraleja_30_50s: "No necesitas invertir miles de dólares en anuncios antes de validar tu oferta. Primero domina la tracción orgánica y la entrega de valor sin fricción.",
    cta_50_60s: "Comenta la palabra CONSULTA abajo y te enviamos el desglose estratégico por DM.",
    keyword: "CONSULTA",
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
                <FileText className="w-5 h-5 text-indigo-400" /> Inspector de Guiones en 4 Bloques
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          <div className="max-w-3xl bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
              Estructura Narrativa del Video
            </h2>
            <Script4BlockReader script={mockScript} />
          </div>
        </main>
      </div>
    </div>
  );
}
