"use client";

import { useState, useEffect } from "react";
import { fetchWithTenant } from "@/services/apiConfig";
import { Brain, Sparkles, TrendingUp, Copy, Check, ShieldCheck } from "lucide-react";

export function HooksLibraryPanel({ tenantId, niche, onSelectHook }) {
  const [hooks, setHooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    if (!tenantId) return;

    const loadHooks = async () => {
      try {
        setLoading(true);
        const data = await fetchWithTenant(
          `/tenants/${tenantId}/rag/hooks?niche=${encodeURIComponent(niche || "General")}&limit=6`,
          {},
          tenantId
        );
        if (Array.isArray(data)) setHooks(data);
      } catch (err) {
        console.error("Error cargando biblioteca RAG de ganchos:", err);
      } finally {
        setLoading(false);
      }
    };

    loadHooks();
  }, [tenantId, niche]);

  const handleCopy = (hook) => {
    navigator.clipboard.writeText(hook.pattern_text);
    setCopiedId(hook.id);
    if (onSelectHook) onSelectHook(hook);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="bg-slate-900/95 border border-indigo-500/30 rounded-3xl p-5 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/40 text-purple-400 flex items-center justify-center">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
              Biblioteca de Ganchos Ganadores (RAG Memory)
            </h3>
            <p className="text-[10px] text-slate-400 font-mono">
              Indexados en Qdrant por el Agente de Analítica a las 72h
            </p>
          </div>
        </div>

        <span className="bg-purple-950 text-purple-300 border border-purple-500/40 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
          <ShieldCheck className="w-3 h-3" /> Qdrant 384d
        </span>
      </div>

      {loading ? (
        <div className="text-center py-6 space-y-2">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-mono">Consultando memoria semántica...</p>
        </div>
      ) : hooks.length === 0 ? (
        <p className="text-xs text-slate-500 text-center py-4">No se encontraron ganchos para este nicho.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {hooks.map((h) => (
            <div
              key={h.id}
              className="bg-slate-950/80 border border-slate-800 hover:border-indigo-500/40 p-3.5 rounded-2xl space-y-2 transition-all flex flex-col justify-between"
            >
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="bg-amber-950/60 border border-amber-500/40 text-amber-300 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> Score {Math.round((h.viral_score || 0.85) * 100)}/100
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">{h.structure || "Gancho Viral"}</span>
                </div>
                <p className="text-xs font-semibold text-slate-200 leading-snug">
                  "{h.pattern_text}"
                </p>
              </div>

              <button
                onClick={() => handleCopy(h)}
                className="w-full mt-2 bg-slate-900 hover:bg-indigo-950 text-indigo-300 hover:text-indigo-200 border border-slate-800 hover:border-indigo-500/50 text-[11px] font-bold py-1.5 rounded-xl transition-all flex items-center justify-center gap-1.5"
              >
                {copiedId === h.id ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" /> Copiado a la Idea
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" /> Usar como Base
                  </>
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
