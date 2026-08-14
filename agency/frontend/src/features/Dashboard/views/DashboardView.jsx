"use client";

import { useState, useEffect } from "react";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import {
  Video,
  Users,
  TrendingUp,
  Zap,
  Sparkles,
  ArrowRight,
  FileText,
  Play,
  CheckCircle2,
  Clock,
  Activity,
  Layers,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";

export function DashboardView({ tenantId }) {
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboard = async () => {
    try {
      setIsLoading(true);
      const data = await fetchWithTenant(`/tenants/${tenantId}/dashboard`, {}, tenantId);
      setDashboardData(data);
    } catch (err) {
      console.error("Error cargando dashboard:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (tenantId) {
      loadDashboard();
    }
  }, [tenantId]);

  const kpis = dashboardData?.kpis || {
    videos_total: 0,
    leads_total: 0,
    avg_viral_score: 85.0,
    nvidia_credits: 1000,
  };

  const pipeline = dashboardData?.pipeline || {
    ideas_generated: 0,
    scripts_created: 0,
    videos_rendered: 0,
  };

  const nextPub = dashboardData?.next_publication;
  const activity = dashboardData?.recent_activity || [];

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-950 via-slate-900 to-slate-950 border border-indigo-500/20 p-8 shadow-2xl">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> Agencia IA Activa 24/7
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Panel de Control ViralSync 360°
            </h1>
            <p className="text-sm text-slate-400 max-w-xl">
              Monitorea en tiempo real el ciclo de creación, optimización narrativa y generación de Reels con Inteligencia Artificial.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link
              href={`/tenants/${tenantId}/aprobaciones/ideas`}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-3 rounded-2xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all transform hover:-translate-y-0.5"
            >
              <Sparkles className="w-4 h-4" /> Nueva Ideación
            </Link>
            <Link
              href={`/tenants/${tenantId}/guiones`}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-bold px-5 py-3 rounded-2xl transition-all flex items-center gap-2"
            >
              <FileText className="w-4 h-4 text-indigo-400" /> Ver Guiones
            </Link>
          </div>
        </div>
      </div>

      {/* Grid de KPIs Principales */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1: Videos Renderizados */}
        <div className="bg-slate-900/90 border border-slate-800 hover:border-indigo-500/40 rounded-2xl p-6 shadow-xl backdrop-blur-md transition-all space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Reels Renderizados
            </span>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <Video className="w-5 h-5" />
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-slate-100 font-mono">
              {kpis.videos_total}
            </div>
            <p className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Producción continua activa
            </p>
          </div>
        </div>

        {/* KPI 2: Leads Capturados */}
        <div className="bg-slate-900/90 border border-slate-800 hover:border-emerald-500/40 rounded-2xl p-6 shadow-xl backdrop-blur-md transition-all space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Leads Capturados
            </span>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-slate-100 font-mono">
              {kpis.leads_total}
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Conversiones directas por DM
            </p>
          </div>
        </div>

        {/* KPI 3: Score Viral Promedio */}
        <div className="bg-slate-900/90 border border-slate-800 hover:border-amber-500/40 rounded-2xl p-6 shadow-xl backdrop-blur-md transition-all space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Score Viral Promedio
            </span>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-amber-300 font-mono">
              {kpis.avg_viral_score}
              <span className="text-xs text-slate-500">/100</span>
            </div>
            <p className="text-[11px] text-amber-400 font-mono">
              Evaluado por motor híbrido LLM
            </p>
          </div>
        </div>

        {/* KPI 4: Créditos NVIDIA NIM */}
        <div className="bg-slate-900/90 border border-slate-800 hover:border-purple-500/40 rounded-2xl p-6 shadow-xl backdrop-blur-md transition-all space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Créditos NVIDIA NIM
            </span>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-purple-300 font-mono">
              {kpis.nvidia_credits}
            </div>
            <p className="text-[11px] text-purple-400 font-mono">
              Motor Cosmos Video Gen Activo
            </p>
          </div>
        </div>
      </div>

      {/* Fila Central: Pipeline Status + Próxima Publicación */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Embudo / Estado del Pipeline (2 columnas) */}
        <div className="lg:col-span-2 bg-slate-900/95 border border-slate-800 rounded-3xl p-6 space-y-5 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              Estado del Pipeline Creativo
            </h3>
            <Link
              href={`/tenants/${tenantId}/pipeline`}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
            >
              Ver flujo completo <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-950 border border-slate-800/80 p-4 rounded-2xl space-y-2 text-center">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                1. Ideaciones
              </span>
              <span className="text-2xl font-extrabold text-indigo-300 font-mono block">
                {pipeline.ideas_generated}
              </span>
              <span className="text-[10px] text-slate-500">Generadas por Gemini</span>
            </div>

            <div className="bg-slate-950 border border-slate-800/80 p-4 rounded-2xl space-y-2 text-center">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                2. Guiones 4 Bloques
              </span>
              <span className="text-2xl font-extrabold text-amber-300 font-mono block">
                {pipeline.scripts_created}
              </span>
              <span className="text-[10px] text-slate-500">Estructurados y Validados</span>
            </div>

            <div className="bg-slate-950 border border-slate-800/80 p-4 rounded-2xl space-y-2 text-center">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                3. Videos Renderizados
              </span>
              <span className="text-2xl font-extrabold text-emerald-300 font-mono block">
                {pipeline.videos_rendered}
              </span>
              <span className="text-[10px] text-slate-500">NVIDIA / MoviePy</span>
            </div>
          </div>
        </div>

        {/* Próxima Publicación / Último Guion (1 columna) */}
        <div className="bg-slate-900/95 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <Clock className="w-4 h-4 text-emerald-400" />
              Última Pieza Generada
            </h3>

            {nextPub ? (
              <div className="bg-slate-950 border border-emerald-500/30 p-4 rounded-2xl space-y-2">
                <div className="flex justify-between items-start">
                  <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-[10px] font-mono font-bold px-2 py-0.5 rounded">
                    {nextPub.status === "approved" ? "Aprobado" : "Pendiente"}
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-100 line-clamp-2">
                  "{nextPub.title}"
                </p>
              </div>
            ) : (
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-2xl text-center space-y-1">
                <p className="text-xs text-slate-400">No hay piezas recientes</p>
                <p className="text-[10px] text-slate-500">Inicia una ideación para poblar el pipeline</p>
              </div>
            )}
          </div>

          <Link
            href={`/tenants/${tenantId}/guiones`}
            className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold py-2.5 rounded-xl text-center transition-all block"
          >
            Abrir Carpeta de Guiones
          </Link>
        </div>
      </div>

      {/* Feed de Actividad Reciente */}
      <div className="bg-slate-900/95 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Actividad Creativa Reciente
          </h3>
          <span className="text-[10px] font-mono text-slate-500">Últimas 5 acciones</span>
        </div>

        {activity.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-4">Sin actividad registrada aún.</p>
        ) : (
          <div className="space-y-2.5">
            {activity.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between bg-slate-950/80 border border-slate-800 px-4 py-3 rounded-2xl text-xs hover:border-slate-700 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-200 line-clamp-1">"{item.title}"</p>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Estado: {item.status}
                    </span>
                  </div>
                </div>

                {item.trend_score != null && (
                  <span className="bg-amber-950/60 border border-amber-500/40 text-amber-300 font-mono text-[10px] font-bold px-2.5 py-1 rounded-xl shrink-0">
                    Score: {Math.round(item.trend_score)}/100
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
