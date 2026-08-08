"use client";

export function RUMBreakdownBarChart({ metrics, threshold = null }) {
  const variables = [
    { label: "Universalidad (U)", value: metrics.universalidad },
    { label: "Intensidad (I)", value: metrics.intensidad },
    { label: "Claridad (C)", value: metrics.claridad },
    { label: "Shareability (S)", value: metrics.shareability },
    { label: "Distribución (D)", value: metrics.distribucion },
    { label: "Alineación (A)", value: metrics.alineacion },
  ];

  return (
    <div className="space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>Desglose de Componentes RUM</span>
        <span>
          Umbral del Nicho:{" "}
          <strong className="text-indigo-400 font-mono">
            {Number.isFinite(Number(threshold)) ? threshold : "—"}
          </strong>
        </span>
      </div>
      {variables.map((v) => (
        <div key={v.label} className="space-y-1">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-slate-300">{v.label}</span>
            <span className="text-indigo-400 font-semibold">
              {v.value != null ? `${(Number(v.value) * 100).toFixed(0)}%` : "—"}
            </span>
          </div>
          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-500"
              style={{ width: v.value != null ? `${Math.max(0, Math.min(100, Number(v.value) * 100))}%` : "0%" }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}