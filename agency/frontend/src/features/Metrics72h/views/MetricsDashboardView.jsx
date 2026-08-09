"use client";

import { useTenantResource } from "@/hooks/useTenantResource";
import { MetricClassificationCard } from "../components/MetricClassificationCard";
import { BarChart3 } from "lucide-react";

export function MetricsDashboardView({ tenantId }) {
  const { data, loading, error } = useTenantResource("metrics", tenantId);
  const metrics = Array.isArray(data) ? data : [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Clasificación 80/20 & Métricas 72h
          </h1>
          <p className="text-xs text-slate-400">
            Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
          </p>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Cargando…</p>
      ) : error ? (
        <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
          Error al cargar métricas: {error.message}
        </div>
      ) : metrics.length === 0 ? (
        <p className="text-sm text-slate-400">Sin métricas todavía</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {metrics.map((item) => (
            <MetricClassificationCard key={item.video_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}