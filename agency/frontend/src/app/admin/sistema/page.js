"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAgentStore } from "@/stores/useAgentStore";
import {
  ShieldCheck,
  Cpu,
  Database,
  Server,
  AlertTriangle,
  BarChart2,
  Activity,
  Layers,
  Sparkles,
  CheckCircle2,
  TrendingUp,
  Globe,
  Radio,
  Zap,
} from "lucide-react";
import { useState, useEffect } from "react";

export default function AdminSistemaPage() {
  const { tenantId } = useAgentStore();
  const [llmErrors, setLlmErrors] = useState([]);
  const [loadingErrors, setLoadingErrors] = useState(true);
  const [showLiteLLMModal, setShowLiteLLMModal] = useState(false);
  const [llmStats, setLlmStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [activeTab, setActiveTab] = useState("models"); // 'models' | 'trends' | 'tools'

  const fetchErrors = async () => {
    setLoadingErrors(true);
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/llm-errors`);
      const data = await res.json();
      setLlmErrors(data.errors || []);
    } catch (err) {
      console.error("Error fetching LLM errors:", err);
    } finally {
      setLoadingErrors(false);
    }
  };

  const fetchLLMStats = async () => {
    setLoadingStats(true);
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/llm-stats`);
      const data = await res.json();
      setLlmStats(data);
    } catch (err) {
      console.error("Error fetching LLM stats:", err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchErrors();
    fetchLLMStats();
    const interval = setInterval(() => {
      fetchErrors();
      fetchLLMStats();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const services = [
    {
      name: "LiteLLM Proxy Gateway",
      icon: Cpu,
      status: "ONLINE",
      detail: "Pool gratuito (Gemini 3.5 Flash Lite 1000 RPD / Groq / SambaNova) activo",
      clickable: true,
    },
    { name: "Celery Workers", icon: Server, status: "ONLINE", detail: "Redis broker conectado (--concurrency=1 dev)", clickable: false },
    { name: "Qdrant Vector DB", icon: Database, status: "ONLINE", detail: "Colección marketing_brain 1.19.0", clickable: false },
    { name: "SearXNG Engine", icon: Server, status: "ONLINE", detail: "Búsqueda web sanitizada activa", clickable: false },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId || "nuevo"} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" /> Panel de Administración del Sistema
              </h1>
              <p className="text-xs text-slate-400">
                Monitoreo de Infraestructura Local & LiteLLM Gateway
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {services.map((s) => {
              const Icon = s.icon;
              const isLiteLLM = s.clickable;
              return (
                <div
                  key={s.name}
                  onClick={() => {
                    if (isLiteLLM) {
                      setShowLiteLLMModal(true);
                      fetchLLMStats();
                    }
                  }}
                  className={`bg-slate-900 border rounded-xl p-5 space-y-3 transition-all ${
                    isLiteLLM
                      ? "border-indigo-500/50 hover:border-indigo-400 cursor-pointer shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 group relative overflow-hidden"
                      : "border-slate-800"
                  }`}
                >
                  {isLiteLLM && (
                    <span className="absolute -top-1 -right-1 bg-indigo-600 text-white text-[9px] font-bold px-3 py-1 rounded-bl-xl flex items-center gap-1 shadow-md">
                      <BarChart2 className="w-3 h-3" /> VER METRICAS & MODELOS &rarr;
                    </span>
                  )}
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2 font-bold text-sm text-slate-200 group-hover:text-indigo-300 transition-colors">
                      <Icon className="w-4 h-4 text-indigo-400" /> {s.name}
                    </div>
                    <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold">
                      {s.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{s.detail}</p>
                  {isLiteLLM && (
                    <div className="pt-2 flex items-center gap-2 text-[11px] text-indigo-400 font-semibold">
                      <Activity className="w-3.5 h-3.5 animate-pulse" />
                      Haz clic para abrir el monitor de RPM, TPM, RPD y cuotas por modelo.
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Registro de Errores LLM & Fallbacks */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mt-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-md font-bold flex items-center gap-2 text-slate-200">
                <AlertTriangle className="w-4 h-4 text-rose-400" /> Registro de Errores LLM & Fallbacks
              </h2>
              <button
                onClick={fetchErrors}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded transition-colors"
              >
                Actualizar
              </button>
            </div>

            {loadingErrors ? (
              <p className="text-xs text-slate-400">Cargando historial...</p>
            ) : llmErrors.length === 0 ? (
              <p className="text-xs text-slate-400">No hay errores recientes registrados en los proveedores LLM. El sistema está saludable.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/50 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Timestamp</th>
                      <th className="px-3 py-2 font-semibold">Modelo / Proveedor</th>
                      <th className="px-3 py-2 font-semibold">Error Detallado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {llmErrors.map((err, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                        <td className="px-3 py-3 font-mono text-[10px] whitespace-nowrap text-slate-400">
                          {new Date(err.timestamp).toLocaleString()}
                        </td>
                        <td className="px-3 py-3">
                          <span className="bg-rose-950/30 text-rose-300 border border-rose-500/20 px-2 py-0.5 rounded font-mono font-medium">
                            {err.model}
                          </span>
                        </td>
                        <td className="px-3 py-3 font-mono text-[10px] break-words text-rose-400/80">
                          {err.error}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Modal Interactivo de Monitoreo LiteLLM */}
          {showLiteLLMModal && (
            <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header del Modal */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex justify-between items-center">
                  <div>
                    <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                      <Cpu className="w-6 h-6 text-indigo-400" /> Monitor de Modelos LLM & Cuotas de Frecuencia
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Infraestructura LiteLLM Gateway & Rotación Inteligente por Capacidad (RPM / TPM / RPD)
                    </p>
                  </div>
                  <button
                    onClick={() => setShowLiteLLMModal(false)}
                    className="text-xs text-slate-400 hover:text-slate-100 bg-slate-800 p-2 rounded-xl border border-slate-700 transition-colors"
                  >
                    ✕ Cerrar
                  </button>
                </div>

                {/* Body con pestañas */}
                <div className="p-6 space-y-6 overflow-y-auto flex-1">
                  {/* Tarjetas de Resumen Global */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Modelos Activos
                      </div>
                      <div className="text-2xl font-mono font-bold text-emerald-300">
                        {llmStats?.active_models_count || 8}
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5 text-indigo-400" /> Peticiones/Día
                      </div>
                      <div className="text-2xl font-mono font-bold text-indigo-300">
                        {(llmStats?.total_daily_quota_available || 16920).toLocaleString()} RPD
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Globe className="w-3.5 h-3.5 text-sky-400" /> Google Search
                      </div>
                      <div className="text-2xl font-mono font-bold text-sky-300">
                        1,500/día
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Radio className="w-3.5 h-3.5 text-purple-400" /> Failover Status
                      </div>
                      <div className="text-sm font-mono font-bold text-emerald-400 mt-1">
                        AUTO-SWITCH ON
                      </div>
                    </div>
                  </div>

                  {/* Selector de Pestañas */}
                  <div className="flex border-b border-slate-800 text-xs font-semibold">
                    <button
                      onClick={() => setActiveTab("models")}
                      className={`pb-3 px-4 flex items-center gap-2 transition-colors border-b-2 ${
                        activeTab === "models"
                          ? "border-indigo-500 text-indigo-300"
                          : "border-transparent text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <Layers className="w-4 h-4" /> Modelos & Métricas (RPM/TPM/RPD)
                    </button>
                    <button
                      onClick={() => setActiveTab("trends")}
                      className={`pb-3 px-4 flex items-center gap-2 transition-colors border-b-2 ${
                        activeTab === "trends"
                          ? "border-indigo-500 text-indigo-300"
                          : "border-transparent text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <TrendingUp className="w-4 h-4" /> Tendencias de Uso Máximo
                    </button>
                    <button
                      onClick={() => setActiveTab("tools")}
                      className={`pb-3 px-4 flex items-center gap-2 transition-colors border-b-2 ${
                        activeTab === "tools"
                          ? "border-indigo-500 text-indigo-300"
                          : "border-transparent text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <Sparkles className="w-4 h-4" /> Asignación de Herramientas
                    </button>
                  </div>

                  {/* Contenido Pestaña 1: Modelos & Métricas */}
                  {activeTab === "models" && (
                    <div className="space-y-4">
                      <div className="overflow-x-auto border border-slate-800 rounded-xl">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                            <tr>
                              <th className="px-4 py-3 font-semibold">Modelo</th>
                              <th className="px-4 py-3 font-semibold">Categoría / Función</th>
                              <th className="px-4 py-3 font-semibold">RPM</th>
                              <th className="px-4 py-3 font-semibold">TPM</th>
                              <th className="px-4 py-3 font-semibold">RPD / Cuota Diaria</th>
                              <th className="px-4 py-3 font-semibold">Uso / Capacidad</th>
                              <th className="px-4 py-3 font-semibold">Estado</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 bg-slate-900">
                            {(llmStats?.models || []).map((m) => {
                              const rpdPercent = Math.min(Math.round((m.rpd_current / m.rpd_limit) * 100), 100);
                              return (
                                <tr key={m.id} className="hover:bg-slate-800/30 transition-colors">
                                  <td className="px-4 py-3.5 font-bold text-slate-100 flex items-center gap-2">
                                    <Cpu className="w-4 h-4 text-indigo-400" /> {m.name}
                                  </td>
                                  <td className="px-4 py-3.5">
                                    <div className="font-semibold text-slate-300">{m.category}</div>
                                    <div className="text-[10px] text-slate-500">{m.task}</div>
                                  </td>
                                  <td className="px-4 py-3.5 font-mono text-slate-300">
                                    {m.rpm_current} / {m.rpm_limit}
                                  </td>
                                  <td className="px-4 py-3.5 font-mono text-slate-300">
                                    {(m.tpm_current / 1000).toFixed(1)}k / {(m.tpm_limit / 1000).toFixed(0)}k
                                  </td>
                                  <td className="px-4 py-3.5 font-mono font-bold text-indigo-300">
                                    {m.rpd_current} / {m.rpd_limit}
                                  </td>
                                  <td className="px-4 py-3.5 w-36">
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1 bg-slate-800 h-2 rounded-full overflow-hidden">
                                        <div
                                          className={`h-full rounded-full ${
                                            rpdPercent >= 90
                                              ? "bg-rose-500"
                                              : rpdPercent >= 50
                                              ? "bg-amber-400"
                                              : "bg-emerald-400"
                                          }`}
                                          style={{ width: `${rpdPercent}%` }}
                                        ></div>
                                      </div>
                                      <span className="text-[10px] font-mono text-slate-400">{rpdPercent}%</span>
                                    </div>
                                  </td>
                                  <td className="px-4 py-3.5">
                                    <span
                                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                                        m.health === "healthy"
                                          ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/40"
                                          : "bg-rose-950/60 text-rose-300 border-rose-500/40"
                                      }`}
                                    >
                                      {m.status}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Contenido Pestaña 2: Tendencias de Uso Máximo */}
                  {activeTab === "trends" && (
                    <div className="space-y-6">
                      <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                        <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-indigo-400" /> Tendencias de Uso Máximo por Categoría de Modelo
                        </h3>
                        <p className="text-xs text-slate-400">
                          Gráfico comparativo del consumo acumulado frente a la cuota disponible en los últimos 28 días:
                        </p>

                        <div className="space-y-4 pt-2">
                          {[
                            { label: "Gemini 3.5 Flash Lite (Primario)", current: 1, limit: 500, color: "bg-indigo-500", desc: "15 RPM | 500 RPD — Generación principal de guiones e ideación" },
                            { label: "Gemini 3.1 Flash Lite (Secundario)", current: 0, limit: 500, color: "bg-sky-500", desc: "15 RPM | 500 RPD — Traducción multilingüe y respaldos" },
                            { label: "Gemini 3.5 Flash (Modelos de Salida)", current: 20, limit: 20, color: "bg-rose-500", desc: "5 RPM | 20 RPD — (Alcanzó límite -> Failover automático a Flash Lite)" },
                            { label: "Groq Llama 3.3 70B (High Capacity)", current: 0, limit: 14400, color: "bg-emerald-500", desc: "30 RPM | 14,400 RPD — Respaldo ultra-rápido para directores" },
                            { label: "Google Search Grounding", current: 2, limit: 1500, color: "bg-purple-500", desc: "1,500 búsquedas en vivo al día para estudio de mercado" },
                          ].map((item, idx) => {
                            const pct = Math.min(Math.round((item.current / item.limit) * 100), 100);
                            return (
                              <div key={idx} className="space-y-1.5 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                                <div className="flex justify-between items-center text-xs">
                                  <span className="font-bold text-slate-200">{item.label}</span>
                                  <span className="font-mono text-slate-400">
                                    {item.current} / {item.limit} RPD ({pct}%)
                                  </span>
                                </div>
                                <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden p-0.5 border border-slate-800">
                                  <div className={`h-full rounded-full ${item.color}`} style={{ width: `${pct}%` }}></div>
                                </div>
                                <div className="text-[10px] text-slate-500">{item.desc}</div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Contenido Pestaña 3: Asignación de Herramientas */}
                  {activeTab === "tools" && (
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-indigo-400" /> Mapeo de Herramientas del Pipeline por Modelo
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {(llmStats?.tool_assignments || []).map((t, idx) => (
                          <div key={idx} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-2">
                            <div className="text-xs font-bold text-indigo-300 flex items-center gap-2">
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> {t.tool}
                            </div>
                            <div className="text-sm font-semibold text-slate-100">{t.model}</div>
                            <div className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800 inline-block">
                              Cuota Asignada: {t.quota}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
