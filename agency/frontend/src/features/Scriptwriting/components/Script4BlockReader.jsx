"use client";

export function Script4BlockReader({ script }) {
  if (!script) return null;

  const fullText = `${script.gancho_0_5s || ""} ${script.contexto_5_30s || ""} ${script.moraleja_30_50s || ""} ${script.cta_50_60s || ""}`.trim();
  const wordCount = fullText ? fullText.split(/\s+/).filter(Boolean).length : 0;

  // Deducir la duración objetivo (15s, 30s, 45s, 60s)
  let duration = script.target_duration;
  if (!duration) {
    if (wordCount <= 45) duration = 15;
    else if (wordCount <= 85) duration = 30;
    else if (wordCount <= 125) duration = 45;
    else duration = 60;
  }

  const ranges = duration <= 15
    ? { b1: "0-3s", b2: "3-8s", b3: "8-12s", b4: "12-15s" }
    : duration <= 30
    ? { b1: "0-5s", b2: "5-15s", b3: "15-25s", b4: "25-30s" }
    : duration <= 45
    ? { b1: "0-5s", b2: "5-25s", b3: "25-38s", b4: "38-45s" }
    : { b1: "0-5s", b2: "5-30s", b3: "30-50s", b4: "50-60s" };

  const blocks = [
    { key: "gancho_0_5s", title: `Bloque 1: Gancho Viral (${ranges.b1})`, text: script.gancho_0_5s, color: "border-indigo-500/50 bg-indigo-950/20 text-indigo-300" },
    { key: "contexto_5_30s", title: `Bloque 2: Contexto & Retención (${ranges.b2})`, text: script.contexto_5_30s, color: "border-emerald-500/50 bg-emerald-950/20 text-emerald-300" },
    { key: "moraleja_30_50s", title: `Bloque 3: Moraleja & Valor (${ranges.b3})`, text: script.moraleja_30_50s, color: "border-amber-500/50 bg-amber-950/20 text-amber-300" },
    { key: "cta_50_60s", title: `Bloque 4: CTA & Keyword Atribución (${ranges.b4})`, text: script.cta_50_60s, color: "border-purple-500/50 bg-purple-950/20 text-purple-300" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between bg-slate-900/80 border border-slate-800 px-3.5 py-2 rounded-xl text-xs text-slate-300">
        <span>⏱️ Duración estimada del guion: <strong className="text-indigo-400 font-mono">{duration} segundos</strong></span>
        <span className="text-[11px] text-slate-400 font-mono">({wordCount} palabras totales)</span>
      </div>

      {blocks.map((b) => (
        <div key={b.key} className={`p-4 rounded-xl border ${b.color}`}>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-xs font-bold uppercase tracking-wider">{b.title}</span>
            {b.key === "cta_50_60s" && script.keyword && (
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
