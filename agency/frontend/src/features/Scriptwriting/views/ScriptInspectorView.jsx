"use client";

import { useTenantResource } from "@/hooks/useTenantResource";
import { Script4BlockReader } from "../components/Script4BlockReader";
import { FileText } from "lucide-react";

export function ScriptInspectorView({ tenantId }) {
  const { data, loading, error } = useTenantResource("scripts", tenantId);
  const scripts = Array.isArray(data) ? data : [];
  const script = scripts[0] || null;

  return (
    <div className="space-y-6">
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

      {loading ? (
        <p className="text-sm text-slate-400">Cargando guiones…</p>
      ) : error ? (
        <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
          Error al cargar guiones: {error.message}
        </div>
      ) : !script ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm text-slate-400">Sin guiones todavía</p>
        </div>
      ) : (
        <div className="max-w-3xl bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
            Estructura Narrativa del Video
          </h2>
          <Script4BlockReader script={script} />
        </div>
      )}
    </div>
  );
}