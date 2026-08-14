"use client";

import { useState, useEffect } from "react";
import { Building2, Video, Users, FileText, ExternalLink, Plus, RefreshCw, DollarSign, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function MultiTenantAdminPage() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${apiBase}/admin/tenants/details`);
      if (res.ok) {
        const data = await res.json();
        setTenants(data);
      }
    } catch (err) {
      console.error("Error cargando lista multi-tenant:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-3xl shadow-xl">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600/20 p-3 rounded-2xl border border-indigo-500/30 text-indigo-400">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              Gestión Multi-Tenant de Agencias
            </h1>
            <p className="text-xs text-slate-400">
              Administra todas las marcas y clientes activos en la plataforma ViralSync 360°.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadTenants}
            className="p-2.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-slate-300 transition-colors"
            title="Refrescar lista"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <Link
            href="/tenants/nuevo"
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 transition-all"
          >
            <Plus className="w-4 h-4" /> Registrar Nuevo Tenant
          </Link>
        </div>
      </div>

      {/* Tabla de Tenants */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">
            Cargando clientes de la agencia...
          </div>
        ) : tenants.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">
            No hay clientes registrados aún.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 border-b border-slate-800 text-[10px] uppercase font-mono text-slate-400">
                <tr>
                  <th className="p-4">Cliente / Agencia</th>
                  <th className="p-4">Nicho & Categoría</th>
                  <th className="p-4 text-center">Gasto LLM</th>
                  <th className="p-4 text-center">Contenido & Leads</th>
                  <th className="p-4 text-center">Estado</th>
                  <th className="p-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {tenants.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-4">
                      <div className="font-bold text-slate-100 text-sm font-sans">{t.name}</div>
                      <span className="text-[10px] text-slate-500">ID: {t.id}</span>
                    </td>

                    <td className="p-4">
                      <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2.5 py-1 rounded-lg text-[10px] font-bold">
                        {t.niche || "General"}
                      </span>
                    </td>

                    <td className="p-4 text-center">
                      <span className="text-emerald-400 font-bold">
                        ${t.current_llm_spend_usd?.toFixed(2)} / ${t.monthly_llm_budget_usd?.toFixed(2)}
                      </span>
                    </td>

                    <td className="p-4">
                      <div className="flex justify-center items-center gap-3 text-[11px]">
                        <span className="flex items-center gap-1 text-indigo-300" title="Guiones">
                          <FileText className="w-3.5 h-3.5" /> {t.counts?.scripts || 0}
                        </span>
                        <span className="flex items-center gap-1 text-emerald-300" title="Videos">
                          <Video className="w-3.5 h-3.5" /> {t.counts?.videos || 0}
                        </span>
                        <span className="flex items-center gap-1 text-amber-300" title="Leads">
                          <Users className="w-3.5 h-3.5" /> {t.counts?.leads || 0}
                        </span>
                      </div>
                    </td>

                    <td className="p-4 text-center">
                      <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold px-2 py-0.5 rounded-full">
                        {t.status || "ACTIVO"}
                      </span>
                    </td>

                    <td className="p-4 text-right">
                      <Link
                        href={`/tenants/${t.id}`}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-sans text-[11px] font-bold px-3 py-1.5 rounded-lg inline-flex items-center gap-1 shadow-md transition-all"
                      >
                        Abrir Dashboard <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
