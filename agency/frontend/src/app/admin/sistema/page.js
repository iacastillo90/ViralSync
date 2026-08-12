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
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function AdminSistemaPage() {
  const { tenantId, setTenantId } = useAgentStore();
  const router = useRouter();
  const [llmErrors, setLlmErrors] = useState([]);
  const [loadingErrors, setLoadingErrors] = useState(true);
  const [showLiteLLMModal, setShowLiteLLMModal] = useState(false);
  const [showWorkersModal, setShowWorkersModal] = useState(false);
  const [showQdrantModal, setShowQdrantModal] = useState(false);
  const [llmStats, setLlmStats] = useState(null);
  const [workersData, setWorkersData] = useState(null);
  const [qdrantStats, setQdrantStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingWorkers, setLoadingWorkers] = useState(false);
  const [loadingQdrant, setLoadingQdrant] = useState(false);
  const [activeTab, setActiveTab] = useState("models"); // 'models' | 'trends' | 'tools'

  // Formulario de ingesta de conocimiento en Qdrant
  const [newDocTitle, setNewDocTitle] = useState("");
  const [newDocCategory, setNewDocCategory] = useState("Marketing Digital");
  const [newDocContent, setNewDocContent] = useState("");
  const [isIngestingVector, setIsIngestingVector] = useState(false);
  const [ingestSuccessMsg, setIngestSuccessMsg] = useState("");

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

  const fetchWorkersStatus = async () => {
    setLoadingWorkers(true);
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/workers-status`);
      const data = await res.json();
      setWorkersData(data);
    } catch (err) {
      console.error("Error fetching workers status:", err);
    } finally {
      setLoadingWorkers(false);
    }
  };

  const fetchQdrantStats = async () => {
    setLoadingQdrant(true);
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/qdrant/stats`);
      const data = await res.json();
      setQdrantStats(data);
    } catch (err) {
      console.error("Error fetching Qdrant stats:", err);
    } finally {
      setLoadingQdrant(false);
    }
  };

  const handleIngestQdrantDocument = async (e) => {
    e.preventDefault();
    if (!newDocTitle.trim() || !newDocContent.trim()) {
      alert("Por favor ingresa un título y el contenido del conocimiento.");
      return;
    }
    setIsIngestingVector(true);
    setIngestSuccessMsg("");
    try {
      const baseUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace("/api/v1", "");
      const res = await fetch(`${baseUrl}/system/qdrant/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newDocTitle,
          category: newDocCategory,
          content: newDocContent,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al indexar documento");

      setIngestSuccessMsg(`¡Éxito! "${newDocTitle}" fue vectorizado e indexado correctamente.`);
      setNewDocTitle("");
      setNewDocContent("");
      fetchQdrantStats();
    } catch (err) {
      alert(`Error al alimentar Qdrant: ${err.message}`);
    } finally {
      setIsIngestingVector(false);
    }
  };

  useEffect(() => {
    fetchErrors();
    fetchLLMStats();
    fetchWorkersStatus();
    fetchQdrantStats();
    const interval = setInterval(() => {
      fetchErrors();
      fetchLLMStats();
      fetchWorkersStatus();
      fetchQdrantStats();
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
      type: "litellm",
    },
    {
      name: "Celery Workers & Tenants",
      icon: Server,
      status: "ONLINE",
      detail: "Redis broker conectado (--concurrency=1 dev) • Ver Tenants Asociados",
      clickable: true,
      type: "celery",
    },
    {
      name: "Qdrant Vector DB",
      icon: Database,
      status: "ONLINE",
      detail: "Colección marketing_brain • Alimentar Base Vectorial con Marketing & Frameworks",
      clickable: true,
      type: "qdrant",
    },
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
              const isClickable = s.clickable;
              return (
                <div
                  key={s.name}
                  onClick={() => {
                    if (s.type === "litellm") {
                      setShowLiteLLMModal(true);
                      fetchLLMStats();
                    } else if (s.type === "celery") {
                      setShowWorkersModal(true);
                      fetchWorkersStatus();
                    } else if (s.type === "qdrant") {
                      setShowQdrantModal(true);
                      fetchQdrantStats();
                    }
                  }}
                  className={`bg-slate-900 border rounded-xl p-5 space-y-3 transition-all ${
                    isClickable
                      ? s.type === "qdrant"
                        ? "border-purple-500/50 hover:border-purple-400 cursor-pointer shadow-lg shadow-purple-500/10 hover:shadow-purple-500/20 group relative overflow-hidden"
                        : "border-indigo-500/50 hover:border-indigo-400 cursor-pointer shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 group relative overflow-hidden"
                      : "border-slate-800"
                  }`}
                >
                  {s.type === "litellm" && (
                    <span className="absolute -top-1 -right-1 bg-indigo-600 text-white text-[9px] font-bold px-3 py-1 rounded-bl-xl flex items-center gap-1 shadow-md">
                      <BarChart2 className="w-3 h-3" /> VER METRICAS & MODELOS &rarr;
                    </span>
                  )}
                  {s.type === "celery" && (
                    <span className="absolute -top-1 -right-1 bg-emerald-600 text-white text-[9px] font-bold px-3 py-1 rounded-bl-xl flex items-center gap-1 shadow-md">
                      <Server className="w-3 h-3" /> VER WORKERS & TENANTS &rarr;
                    </span>
                  )}
                  {s.type === "qdrant" && (
                    <span className="absolute -top-1 -right-1 bg-purple-600 text-white text-[9px] font-bold px-3 py-1 rounded-bl-xl flex items-center gap-1 shadow-md">
                      <Database className="w-3 h-3" /> ALIMENTAR BASE VECTORIAL &rarr;
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
                  {s.type === "litellm" && (
                    <div className="pt-2 flex items-center gap-2 text-[11px] text-indigo-400 font-semibold">
                      <Activity className="w-3.5 h-3.5 animate-pulse" />
                      Haz clic para abrir el monitor de RPM, TPM, RPD y cuotas por modelo.
                    </div>
                  )}
                  {s.type === "celery" && (
                    <div className="pt-2 flex items-center gap-2 text-[11px] text-emerald-400 font-semibold">
                      <Server className="w-3.5 h-3.5 animate-pulse" />
                      Haz clic para ver los Celery Workers y la lista de Tenants asociados.
                    </div>
                  )}
                  {s.type === "qdrant" && (
                    <div className="pt-2 flex items-center gap-2 text-[11px] text-purple-400 font-semibold">
                      <Database className="w-3.5 h-3.5 animate-pulse" />
                      Haz clic para alimentar Qdrant con documentos de Marketing, Tendencias o Frameworks.
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

          {/* Modal Interactivo Celery Workers & Tenants */}
          {showWorkersModal && (
            <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header del Modal */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex justify-between items-center">
                  <div>
                    <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                      <Server className="w-6 h-6 text-emerald-400" /> Celery Workers & Tenants Asociados
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Monitoreo de Infraestructura de Procesamiento Async & Aislamiento por Tenant
                    </p>
                  </div>
                  <button
                    onClick={() => setShowWorkersModal(false)}
                    className="text-xs text-slate-400 hover:text-slate-100 bg-slate-800 p-2 rounded-xl border border-slate-700 transition-colors"
                  >
                    ✕ Cerrar
                  </button>
                </div>

                <div className="p-6 space-y-6 overflow-y-auto flex-1">
                  {/* Tarjetas de Estadísticas Principales */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Estado Celery
                      </div>
                      <div className="text-lg font-mono font-bold text-emerald-300">
                        {workersData?.celery_status || "ONLINE"}
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-indigo-400" /> Tenants Registrados
                      </div>
                      <div className="text-2xl font-mono font-bold text-indigo-300">
                        {workersData?.tenants_count || 1}
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Radio className="w-3.5 h-3.5 text-sky-400" /> Broker Redis
                      </div>
                      <div className="text-xs font-mono font-bold text-sky-300 truncate mt-1">
                        redis:6379/0
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5 text-amber-400" /> Concurrencia
                      </div>
                      <div className="text-sm font-mono font-bold text-amber-300 mt-1">
                        --concurrency=1 (Dev)
                      </div>
                    </div>
                  </div>

                  {/* Sección de Tenants Asociados */}
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400" /> Tenants Registrados y Asociados al Sistema
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {(workersData?.tenants || []).map((t) => (
                        <div
                          key={t.id}
                          className="bg-slate-950 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-5 space-y-3 transition-all"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="font-bold text-slate-100 text-sm">{t.name}</h4>
                              <p className="text-xs text-indigo-400 font-mono mt-0.5">ID: {t.id}</p>
                            </div>
                            <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                              {t.status || "ACTIVO"}
                            </span>
                          </div>

                          <div className="text-xs space-y-1 text-slate-400 border-t border-slate-900 pt-2">
                            <div><strong>Nicho / Industria:</strong> {t.niche}</div>
                            <div><strong>Presupuesto LLM Mensual:</strong> ${t.budget_usd || 20.0} USD</div>
                            {t.created_at && (
                              <div className="text-[10px] text-slate-500">
                                🕒 Creado: {new Date(t.created_at).toLocaleString("es-ES")}
                              </div>
                            )}
                          </div>

                          <div className="pt-2">
                            <button
                              onClick={() => {
                                setTenantId(t.id);
                                setShowWorkersModal(false);
                                router.push(`/tenants/${t.id}`);
                              }}
                              className="w-full bg-slate-900 hover:bg-indigo-950/80 border border-slate-800 hover:border-indigo-500/50 text-indigo-300 text-xs font-bold py-2 rounded-lg transition-all flex items-center justify-center gap-1.5"
                            >
                              🚀 Ir al Dashboard de {t.name} &rarr;
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Sección de Tareas Async Celery */}
                  <div className="space-y-3 pt-4 border-t border-slate-800">
                    <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-emerald-400" /> Tareas Async en Colas Redis
                    </h3>
                    <div className="overflow-x-auto border border-slate-800 rounded-xl">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="px-4 py-2.5 font-semibold">Tarea Celery</th>
                            <th className="px-4 py-2.5 font-semibold">Cola Redis</th>
                            <th className="px-4 py-2.5 font-semibold">Descripción del Job</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 bg-slate-900">
                          {(workersData?.tasks_supported || []).map((task, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                              <td className="px-4 py-2.5 font-mono text-indigo-300 font-bold">{task.task}</td>
                              <td className="px-4 py-2.5">
                                <span className="bg-slate-950 text-slate-300 border border-slate-800 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                                  {task.queue}
                                </span>
                              </td>
                              <td className="px-4 py-2.5 text-slate-400">{task.description}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
          {/* Modal Interactivo Qdrant Vector DB & Alimentación del Cerebro */}
          {showQdrantModal && (
            <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header del Modal */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex justify-between items-center">
                  <div>
                    <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                      <Database className="w-6 h-6 text-purple-400" /> Administrador de Base Vectorial Qdrant
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Alimentar el Cerebro IA con Frameworks de Marketing Digital, Tendencias y Modelos Persuasivos
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setShowQdrantModal(false);
                      setIngestSuccessMsg("");
                    }}
                    className="text-xs text-slate-400 hover:text-slate-100 bg-slate-800 p-2 rounded-xl border border-slate-700 transition-colors"
                  >
                    ✕ Cerrar
                  </button>
                </div>

                <div className="p-6 space-y-6 overflow-y-auto flex-1">
                  {/* Tarjetas de Estadísticas Principales */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Database className="w-3.5 h-3.5 text-purple-400" /> Colección Qdrant
                      </div>
                      <div className="text-sm font-mono font-bold text-purple-300">
                        {qdrantStats?.collection_name || "marketing_brain"}
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-indigo-400" /> Vectores Guardados
                      </div>
                      <div className="text-2xl font-mono font-bold text-indigo-300">
                        {qdrantStats?.points_count || 0}
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5 text-sky-400" /> Dimensión Embeddings
                      </div>
                      <div className="text-sm font-mono font-bold text-sky-300 mt-1">
                        384 (Cosine)
                      </div>
                    </div>
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
                      <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> RAG Status
                      </div>
                      <div className="text-sm font-mono font-bold text-emerald-300 mt-1">
                        HABILITADO
                      </div>
                    </div>
                  </div>

                  {/* Formulario de Alimentación Vectorial (Ingestar Conocimiento) */}
                  <div className="bg-slate-950 border border-purple-500/30 rounded-xl p-5 space-y-4 shadow-lg shadow-purple-500/5">
                    <h3 className="text-sm font-bold text-purple-300 flex items-center gap-2 border-b border-slate-800 pb-2">
                      <Sparkles className="w-4 h-4 text-purple-400" /> Ingestar Nuevo Conocimiento de Marketing
                    </h3>
                    <p className="text-xs text-slate-400">
                      Sube metodologías, ganchos virales o análisis de tendencias para que todos los agentes (Ideador RUM, Guionista) se alimenten semánticamente de este conocimiento:
                    </p>

                    <form onSubmit={handleIngestQdrantDocument} className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-2 space-y-1">
                          <label className="text-[11px] font-semibold text-slate-300">
                            Título del Documento / Framework *
                          </label>
                          <input
                            type="text"
                            required
                            placeholder="Ej: Metodología de Ganchos Virales 2026 para TikTok & Reels"
                            value={newDocTitle}
                            onChange={(e) => setNewDocTitle(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-purple-500"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-slate-300">
                            Categoría *
                          </label>
                          <select
                            value={newDocCategory}
                            onChange={(e) => setNewDocCategory(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-purple-500"
                          >
                            <option value="Marketing Digital">Marketing Digital</option>
                            <option value="Tendencias de Mercado">Tendencias de Mercado</option>
                            <option value="Modelos de Trabajo & Frameworks">Modelos de Trabajo & Frameworks</option>
                            <option value="Copywriting Persuasivo">Copywriting Persuasivo</option>
                          </select>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[11px] font-semibold text-slate-300">
                          Contenido / Texto del Conocimiento a Vectorizar *
                        </label>
                        <textarea
                          required
                          rows={4}
                          placeholder="Escribe o pega aquí el conocimiento clave, reglas de retención de 3 segundos, estructuras de CTA, análisis de audiencia..."
                          value={newDocContent}
                          onChange={(e) => setNewDocContent(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-xs text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                        />
                      </div>

                      {ingestSuccessMsg && (
                        <div className="bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs p-3 rounded-lg flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          {ingestSuccessMsg}
                        </div>
                      )}

                      <button
                        type="submit"
                        disabled={isIngestingVector}
                        className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-purple-600/30 flex items-center gap-2 disabled:opacity-50"
                      >
                        <Database className="w-4 h-4" />
                        {isIngestingVector ? "Indexando Vectores en Qdrant..." : "🧠 Ingestar & Indexar en Qdrant"}
                      </button>
                    </form>
                  </div>

                  {/* Lista de Documentos Vectorizados Existentes */}
                  <div className="space-y-3 pt-2">
                    <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-purple-400" /> Documentos Vectorizados en 'marketing_brain' ({qdrantStats?.documents?.length || 0})
                    </h3>

                    {loadingQdrant ? (
                      <p className="text-xs text-slate-400">Cargando base vectorial Qdrant...</p>
                    ) : (qdrantStats?.documents || []).length === 0 ? (
                      <p className="text-xs text-slate-400">Aún no hay documentos vectorizados. Utiliza el formulario arriba para alimentar el cerebro.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {qdrantStats.documents.map((doc) => (
                          <div key={doc.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
                            <div className="flex justify-between items-start">
                              <h4 className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                                <Database className="w-3.5 h-3.5 text-purple-400" /> {doc.title}
                              </h4>
                              <span className="bg-purple-950/60 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded text-[10px] font-mono">
                                {doc.category}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 line-clamp-2 italic font-mono bg-slate-900/60 p-2 rounded-lg">
                              "{doc.snippet}"
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
