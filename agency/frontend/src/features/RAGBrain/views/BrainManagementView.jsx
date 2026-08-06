"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Brain, Database, Sparkles } from "lucide-react";

export function BrainManagementView({ tenantId }) {
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" /> Brand Persona & Tono
              </h2>
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-semibold block mb-1">3 Atributos de Tono:</span>
                  <p className="text-slate-200">1. Directo y Pragmático | 2. Cero Humo | 3. Orientado a ROI</p>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-semibold block mb-1">Objeto / Elemento de Identidad:</span>
                  <p className="text-slate-200">Pizarra de Estrategia + Neón Azul</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Database className="w-4 h-4 text-emerald-400" /> Colección Qdrant (`marketing_brain`)
              </h2>
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Dimensión de Embeddings:</span>
                  <span className="font-mono font-bold text-emerald-400">384 (FastEmbed)</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Vectores Indexados:</span>
                  <span className="font-mono font-bold text-indigo-400">1,240 Chunks</span>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
