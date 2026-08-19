"use client";

import { useState } from "react";
import { fetchWithTenant } from "@/services/apiConfig";
import { Search, Sparkles, Brain, CheckCircle2, TrendingUp } from "lucide-react";

export function CompetitorMiningPanel({ tenantId, niche, onPatternsExtracted }) {
  const [competitorQuery, setCompetitorQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [extractedPatterns, setExtractedPatterns] = useState([]);

  const handleMine = async (e) => {
    e.preventDefault();
    if (!tenantId || !competitorQuery.trim()) return;

    try {
      setLoading(true);
      const data = await fetchWithTenant(
        `/tenants/${tenantId}/competitor-mine`,
        {
          method: "POST",
          body: JSON.stringify({
            competitor_url_or_topic: competitorQuery.trim(),
            niche: niche || "General",
          }),
        },
        tenantId
      );

      if (data && data.patterns) {
        setExtractedPatterns(data.patterns);
        if (onPatternsExtracted) onPatternsExtracted(data.patterns);
      }
    } catch (err) {
      alert(`Error en la minería de competidor: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/95 border border-purple-500/30 rounded-3xl p-6 space-y-4 shadow-xl">
      <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
        <div className="w-9 h-9 rounded-2xl bg-purple-500/20 border border-purple-500/40 text-purple-300 flex items-center justify-center">
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            Minería de Tendencias de Competidores (Auto-Indexado RAG)
          </h3>
          <p className="text-[11px] text-slate-400">
            Ingresa una cuenta o URL de competidor para extraer estructuras virales e inyectarlas en Qdrant.
          </p>
        </div>
      </div>

      <form onSubmit={handleMine} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            required
            placeholder="Ej: @competidor_top / https://instagram.com/reel/... / Tendencia B2B"
            value={competitorQuery}
            onChange={(e) => setCompetitorQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-purple-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-purple-600/30 flex items-center gap-1.5 transition-all disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5" />
          {loading ? "Minando..." : "Minar Tendencias"}
        </button>
      </form>

      {extractedPatterns.length > 0 && (
        <div className="space-y-2 pt-2">
          <span className="text-[10px] font-mono text-emerald-400 font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> ¡{extractedPatterns.length} Patrones indexados en Qdrant!
          </span>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {extractedPatterns.map((p, idx) => (
              <div key={idx} className="bg-slate-950 border border-purple-500/20 p-3 rounded-2xl space-y-1">
                <span className="text-[9px] font-mono text-purple-300 font-bold bg-purple-950 px-2 py-0.5 rounded">
                  Score {Math.round(p.viral_score * 100)}/100
                </span>
                <p className="text-xs font-semibold text-slate-200 leading-snug">"{p.pattern_text}"</p>
                <span className="text-[9px] text-slate-500 font-mono block">{p.structure}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
