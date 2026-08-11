"use client";
 
import { useState, useEffect } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantStore } from "@/stores/useTenantStore";
import { useSSEStream } from "@/hooks/useSSEStream";
import {
  Play,
  CheckCircle,
  XCircle,
  UserCheck,
  TrendingUp,
  Activity,
  MessageSquare,
  BarChart3,
  Layers,
  Sparkles,
  Building2,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

import ProductIngestModal from "@/components/ProductIngestModal";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { fetchWithTenant } from "@/services/apiConfig";
import { useTenantResource } from "@/hooks/useTenantResource";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("monitor");
  const [queuedIdeaId, setQueuedIdeaId] = useState(null);
  const [queuedPublish, setQueuedPublish] = useState(false);
  const { activeTenant, setActiveTenant, availableTenants, setAvailableTenants } = useTenantStore();
  const {
    tenantId,
    setTenantId,
    nodes,
    logs,
    pausedCheckpoint,
    leads,
    setLeads,
    addLog,
  } = useAgentStore();

  // Recursos compartidos: mismas GETs que las vistas de features (REQ-FEAT-4).
  const scopedTenantId =
    tenantId && tenantId !== "null" && tenantId !== "nuevo" ? tenantId : null;
  const ideasResource = useTenantResource("ideas", scopedTenantId);
  const scriptsResource = useTenantResource("scripts", scopedTenantId);
  const metricsResource = useTenantResource("metrics", scopedTenantId);
  const ideaItems = Array.isArray(ideasResource.data) ? ideasResource.data : [];
  const scriptItems = Array.isArray(scriptsResource.data) ? scriptsResource.data : [];
  const metricItems = Array.isArray(metricsResource.data) ? metricsResource.data : [];
  const pendingIdea = ideaItems[0] || null;
  const latestScript = scriptItems[scriptItems.length - 1] || scriptItems[0] || null;

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 1. Cargar la lista de tenants en el arranque
  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    async function loadTenants() {
      try {
        const res = await fetch(`${apiBase}/tenants`);
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setAvailableTenants(data);
          
          // Si no hay tenant seleccionado, intentar recuperar de localStorage o usar el primero
          let savedTenantId = typeof window !== "undefined" ? localStorage.getItem("tenantId") : null;
          let match = data.find((t) => t.id === savedTenantId && t.id !== "nuevo") || data[0];
          
          if (match) {
            setActiveTenant(match);
            setTenantId(match.id);
            if (typeof window !== "undefined") {
              localStorage.setItem("tenantId", match.id);
            }
          }
        }
      } catch (err) {
        console.warn("Servidor backend FastAPI no disponible temporalmente. Modo offline o esperando conexión.");
      }
    }
    loadTenants();
  }, [setAvailableTenants, setActiveTenant, setTenantId]);


  // Iniciar conexión SSE en tiempo real (sólo si hay un tenantId válido)
  useSSEStream(tenantId && tenantId !== "null" && tenantId !== "nuevo" ? tenantId : null);

  // Cargar datos iniciales desde el backend FastAPI
  useEffect(() => {
    if (!tenantId || tenantId === "null" || tenantId === "nuevo") return;

    fetchWithTenant(`/tenants/${tenantId}/leads`, {}, tenantId)
      .then((data) => setLeads(data))
      .catch(() => {});
  }, [tenantId, setLeads]);

  const handleRunGraph = async () => {
    addLog("Solicitando inicio de StateGraph en FastAPI...");
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/graph/run`,
        {
          method: "POST",
          body: JSON.stringify({ force_reideation: false }),
        },
        tenantId
      );
    } catch (err) {}
  };

  const handleApproveIdea = async (approved, ideaId) => {
    if (!ideaId) return;
    addLog(`Enviando decisión de idea: ${approved ? "APROBADA" : "RECHAZADA"}`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/ideas/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            idea_id: ideaId,
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );
      setQueuedIdeaId(ideaId);
    } catch (err) {}
  };

  const handleApprovePublish = async (approved) => {
    addLog(`Enviando decisión de publicación: ${approved ? "APROBADA" : "RECHAZADA"}`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/publish/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );
      setQueuedPublish(true);
    } catch (err) {}
  };

  const handleTakeover = async (leadId) => {
    addLog(`Account Manager asumiendo control humano para lead '${leadId}'`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/leads/${leadId}/takeover`,
        {
          method: "POST",
          body: JSON.stringify({ operator_id: "admin_uuid_443", action: "pause_bot" }),
        },
        tenantId
      );
    } catch (err) {}
    setLeads(
      leads.map((l) =>
        l.id === leadId
          ? { ...l, handled_by_human_at: new Date().toISOString() }
          : l
      )
    );
  };


  if (!tenantId || tenantId === "null") {

    return (
      <main suppressHydrationWarning className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6">
        <div suppressHydrationWarning className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-6 shadow-xl shadow-indigo-950/20">
          <div suppressHydrationWarning className="bg-indigo-600/10 border border-indigo-500/30 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto text-indigo-400">
            <Building2 className="w-8 h-8" />
          </div>
          <div suppressHydrationWarning className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">Bienvenido a ViralSync</h1>
            <p className="text-sm text-slate-400">
              Para comenzar a generar tus videos de marketing con inteligencia artificial, necesitas configurar o registrar tu primer inquilino (tenant).
            </p>
          </div>
          <Link
            href="/tenants/nuevo"
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/30 group"
          >
            Configurar Primer Tenant <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </main>
    );
  }

  return (
    <div suppressHydrationWarning className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">

      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
          {/* Header Empresarial */}
          <div className="flex justify-between items-center pb-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-xl text-white shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">ViralSync Platform</h1>
            <p className="text-sm text-slate-400">
              Tenant ID: <span className="font-mono text-indigo-400">{tenantId}</span>
            </p>
          </div>
        </div>
        <button
          onClick={handleRunGraph}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2.5 rounded-lg transition-all shadow-md shadow-indigo-600/30"
        >
          <Play className="w-4 h-4 fill-current" /> Ejecutar Grafo
        </button>
      </div>

      {/* Formulario de Ingesta de Producto/Servicio a MinIO */}
      <ProductIngestModal />

      {/* Navegación por Pestañas */}
      <nav className="flex gap-2 my-6 border-b border-slate-800 pb-2">
        {[
          { id: "monitor", label: "Pipeline Monitor", icon: Layers },
          { id: "approvals", label: "Aprobaciones Humana", icon: CheckCircle },
          { id: "leads", label: "Leads Inbound", icon: MessageSquare },
          { id: "metrics", label: "Métricas 72h", icon: BarChart3 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                isActive
                  ? "bg-slate-800 text-indigo-400 border border-slate-700"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Tab 1: Monitor de Pipeline LangGraph */}
      {activeTab === "monitor" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" /> Mapa de Nodos LangGraph
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(nodes).map(([nodeName, status]) => (
                <div
                  key={nodeName}
                  className={`p-4 rounded-xl border transition-all ${
                    status === "running"
                      ? "bg-indigo-950/40 border-indigo-500/50 text-indigo-300 animate-pulse"
                      : status === "completed"
                      ? "bg-emerald-950/30 border-emerald-500/40 text-emerald-300"
                      : "bg-slate-950 border-slate-800 text-slate-400"
                  }`}
                >
                  <span className="text-xs uppercase font-mono tracking-wider">
                    {status}
                  </span>
                  <p className="font-semibold capitalize text-slate-200 mt-1">
                    {nodeName.replace(/_/g, " ")}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Consola SSE Realtime</h2>
            <div className="h-72 overflow-y-auto font-mono text-xs bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5">
              {logs.map((log, idx) => (
                <div key={idx} className="text-slate-300 leading-relaxed">
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Aprobaciones Humanas (Checkpoints) */}
      {activeTab === "approvals" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold mb-2">Checkpoint: Idea Candidata RUM</h2>
            {ideasResource.loading ? (
              <p className="text-sm text-slate-400">Cargando ideas…</p>
            ) : ideasResource.error ? (
              <p className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
                Error al cargar ideas: {ideasResource.error.message}
              </p>
            ) : !pendingIdea ? (
              <>
                <p className="text-sm text-slate-400 mb-4">No hay ideas pendientes</p>
                <div className="flex gap-3">
                  <button disabled className="flex items-center gap-2 bg-slate-800 text-slate-500 font-medium px-4 py-2 rounded-lg cursor-not-allowed">
                    <CheckCircle className="w-4 h-4" /> Aprobar Idea
                  </button>
                  <button disabled className="flex items-center gap-2 bg-slate-800 text-slate-500 font-medium px-4 py-2 rounded-lg cursor-not-allowed">
                    <XCircle className="w-4 h-4" /> Rechazar Idea
                  </button>
                </div>
              </>
            ) : queuedIdeaId === pendingIdea.id ? (
              <>
                <p className="text-sm text-slate-400 mb-2">
                  Idea: <span className="text-slate-200 font-medium">{pendingIdea.texto}</span> (Score RUM: {pendingIdea.rum_score ?? "—"})
                </p>
                <span className="inline-block text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
                  Idea encolada para procesamiento (202 accepted)
                </span>
              </>
            ) : (
              <>
                <p className="text-sm text-slate-400 mb-4">
                  Idea: <span className="text-slate-200 font-medium">{pendingIdea.texto}</span> (Score RUM: {pendingIdea.rum_score ?? "—"})
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleApproveIdea(true, pendingIdea.id)}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-lg"
                  >
                    <CheckCircle className="w-4 h-4" /> Aprobar Idea
                  </button>
                  <button
                    onClick={() => handleApproveIdea(false, pendingIdea.id)}
                    className="flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium px-4 py-2 rounded-lg"
                  >
                    <XCircle className="w-4 h-4" /> Rechazar Idea
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold mb-2">Checkpoint: Publicación de Video Editado</h2>
            {scriptsResource.loading ? (
              <p className="text-sm text-slate-400">Cargando cola de publicación…</p>
            ) : scriptsResource.error ? (
              <p className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
                Error al cargar cola de publicación: {scriptsResource.error.message}
              </p>
            ) : !latestScript ? (
              <>
                <p className="text-sm text-slate-400 mb-4">No hay videos en cola para publicar todavía</p>
                <div className="flex gap-3">
                  <button disabled className="flex items-center gap-2 bg-slate-800 text-slate-500 font-medium px-4 py-2 rounded-lg cursor-not-allowed">
                    <CheckCircle className="w-4 h-4" /> Aprobar Publicación en Instagram
                  </button>
                  <button disabled className="flex items-center gap-2 bg-slate-800 text-slate-500 font-medium px-4 py-2 rounded-lg cursor-not-allowed">
                    <XCircle className="w-4 h-4" /> Rechazar
                  </button>
                </div>
              </>
            ) : queuedPublish ? (
              <>
                <p className="text-sm text-slate-400 mb-2">
                  Último guion: keyword <span className="font-mono text-indigo-400">{latestScript.keyword || "—"}</span> — CTA: {latestScript.cta_50_60s || "—"}
                </p>
                <span className="inline-block text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
                  Publicación encolada para procesamiento (202 accepted)
                </span>
              </>
            ) : (
              <>
                <p className="text-sm text-slate-400 mb-4">
                  Último guion: keyword <span className="font-mono text-indigo-400">{latestScript.keyword || "—"}</span> — CTA: {latestScript.cta_50_60s || "—"}
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleApprovePublish(true)}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-lg"
                  >
                    <CheckCircle className="w-4 h-4" /> Aprobar Publicación en Instagram
                  </button>
                  <button
                    onClick={() => handleApprovePublish(false)}
                    className="flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium px-4 py-2 rounded-lg"
                  >
                    <XCircle className="w-4 h-4" /> Rechazar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Leads Inbound */}
      {activeTab === "leads" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4">Leads Capturados vía Webhook Meta</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase text-xs">
                <tr>
                  <th className="p-3">ID Lead</th>
                  <th className="p-3">Instagram User</th>
                  <th className="p-3">Keyword</th>
                  <th className="p-3">Mensaje Original</th>
                  <th className="p-3">Estado</th>
                  <th className="p-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-850">
                    <td className="p-3 font-mono text-xs">{lead.id}</td>
                    <td className="p-3 font-medium">{lead.ig_user_id}</td>
                    <td className="p-3 font-mono text-indigo-400">{lead.keyword}</td>
                    <td className="p-3">{lead.mensaje_original}</td>
                    <td className="p-3">
                      {lead.handled_by_human_at ? (
                        <span className="bg-amber-950/60 text-amber-400 border border-amber-500/40 px-2.5 py-1 rounded-full text-xs">
                          Operador Asignado
                        </span>
                      ) : (
                        <span className="bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full text-xs">
                          Bot Activo
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      {!lead.handled_by_human_at && (
                        <button
                          onClick={() => handleTakeover(lead.id)}
                          className="flex items-center gap-1.5 bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
                        >
                          <UserCheck className="w-3.5 h-3.5" /> Asumir Control Humano
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 4: Métricas 72h */}
      {activeTab === "metrics" && (
        metricsResource.loading ? (
          <p className="text-sm text-slate-400">Cargando métricas…</p>
        ) : metricsResource.error ? (
          <p className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
            Error al cargar métricas: {metricsResource.error.message}
          </p>
        ) : metricItems.length === 0 ? (
          <p className="text-sm text-slate-400">Sin métricas todavía</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {metricItems.map((item) => (
              <div
                key={item.video_id}
                className={`p-5 rounded-xl border ${
                  item.classification === "VERDE"
                    ? "bg-emerald-950/30 border-emerald-500/40"
                    : item.classification === "ROJO"
                    ? "bg-rose-950/30 border-rose-500/40"
                    : "bg-amber-950/30 border-amber-500/40"
                }`}
              >
                <div className="flex justify-between items-center mb-3">
                  <span className="font-mono text-xs text-slate-400">{item.video_id}</span>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold ${
                      item.classification === "VERDE"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        : item.classification === "ROJO"
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
                    <p className="text-lg font-bold">
                      {item.views_72h != null ? Number(item.views_72h).toLocaleString() : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Ratio Relativo</p>
                    <p className="text-lg font-bold text-indigo-400">
                      {item.ratio_relativo != null ? `${Number(item.ratio_relativo)}x` : "—"}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="font-semibold text-slate-400">Acción:</span> {item.action_taken}
                </p>
              </div>
            ))}
          </div>
        )
      )}
        </main>
      </div>
    </div>
  );
}
