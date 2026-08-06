"use client";

export function Script4BlockReader({ script }) {
  const blocks = [
    { key: "gancho_0_5s", title: "Bloque 1: Gancho Viral (0-5s)", text: script.gancho_0_5s, color: "border-indigo-500/50 bg-indigo-950/20 text-indigo-300" },
    { key: "contexto_5_30s", title: "Bloque 2: Contexto & Retención (5-30s)", text: script.contexto_5_30s, color: "border-emerald-500/50 bg-emerald-950/20 text-emerald-300" },
    { key: "moraleja_30_50s", title: "Bloque 3: Moraleja & Valor (30-50s)", text: script.moraleja_30_50s, color: "border-amber-500/50 bg-amber-950/20 text-amber-300" },
    { key: "cta_50_60s", title: "Bloque 4: CTA & Keyword Atribución (50-60s)", text: script.cta_50_60s, color: "border-purple-500/50 bg-purple-950/20 text-purple-300" },
  ];

  return (
    <div className="space-y-4">
      {blocks.map((b) => (
        <div key={b.key} className={`p-4 rounded-xl border ${b.color}`}>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-xs font-bold uppercase tracking-wider">{b.title}</span>
            {b.key === "cta_50_60s" && (
              <span className="text-xs bg-purple-900/60 text-purple-200 border border-purple-400/40 px-2 py-0.5 rounded font-mono">
                Keyword: {script.keyword}
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-slate-200 font-sans">{b.text}</p>
        </div>
      ))}
    </div>
  );
}
