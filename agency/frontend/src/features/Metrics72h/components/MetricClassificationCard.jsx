"use client";

export function MetricClassificationCard({ item }) {
  const isVerde = item.classification === "VERDE";
  const isRojo = item.classification === "ROJO";

  const views72h = item.views_72h != null ? Number(item.views_72h) : null;
  const ratio = item.ratio_relativo != null ? Number(item.ratio_relativo) : null;

  return (
    <div
      className={`p-5 rounded-xl border ${
        isVerde
          ? "bg-emerald-950/30 border-emerald-500/40"
          : isRojo
          ? "bg-rose-950/30 border-rose-500/40"
          : "bg-amber-950/30 border-amber-500/40"
      }`}
    >
      <div className="flex justify-between items-center mb-3">
        <span className="font-mono text-xs text-slate-400">{item.video_id}</span>
        <span
          className={`px-3 py-1 rounded-full text-xs font-bold ${
            isVerde
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
              : isRojo
              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
              : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
          }`}
        >
          {item.classification}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 my-3 text-sm">
        <div>
          <p className="text-xs text-slate-400">Vistas 72h</p>
          <p className="text-lg font-bold">{views72h != null ? views72h.toLocaleString() : "—"}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Ratio Relativo</p>
          <p className="text-lg font-bold text-indigo-400">{ratio != null ? `${ratio}x` : "—"}</p>
        </div>
      </div>

      <p className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
        <span className="font-semibold text-slate-400">Acción:</span> {item.action_taken}
      </p>
    </div>
  );
}