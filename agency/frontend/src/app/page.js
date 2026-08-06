"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Video,
  FileText,
  Users,
  BarChart3,
  Brain,
  MessageSquare,
  ShieldCheck,
  Zap,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

export default function AgencyDashboard() {
  const [activeTab, setActiveTab] = useState("pipeline");
  const [selectedTenant, setSelectedTenant] = useState("tenant-demo-001");
  const [graphState, setGraphState] = useState({
    currentNode: "human_approval_idea",
    status: "paused",
    ideaApproval: "pending",
    publishApproval: "pending",
  });

  const [ideas, setIdeas] = useState([
    {
      id: "idea-101",
      texto: "3 Errores fatales en Negocios B2B que te están costando clientes y dinero",
      gancho: "Si trabajas en Negocios B2B, deja de hacer esto inmediatamente...",
      rum_score: 0.444,
      threshold: 0.050,
      universalidad: 0.85,
      intensidad: 0.90,
      claridad: 0.95,
      shareability: 0.80,
      distribucion: 0.85,
      alineacion: 0.90,
      passes_5_50: true,
      status: "pending",
    },
  ]);

  const [script, setScript] = useState({
    gancho_0_5s: "¡Detente! Si quieres escalar tu SaaS B2B, necesitas esto.",
    contexto_5_30s: "La mayoría comete el error de enfocarse en alcance frío sin entender la retención del algoritmo...",
    moraleja_30_50s: "La clave está en automatizar la calificación de leads con respuestas inmediatas.",
    cta_50_60s: "Comenta la palabra 'CONSULTA' abajo y te enviaré la guía completa por mensaje directo.",
    keyword: "CONSULTA",
  });

  const [leads, setLeads] = useState([
    {
      id: "lead-001",
      video_id: "video-55",
      keyword: "CONSULTA",
      ig_user_id: "user_ig_9921",
      mensaje_original: "Hola! Quiero la CONSULTA por favor",
      origen: "comment",
      calificado_at: "Hace 12 min",
      handled: false,
    },
    {
      id: "lead-002",
      video_id: "video-55",
      keyword: "CONSULTA",
      ig_user_id: "user_ig_4412",
      mensaje_original: "Me interesa la CONSULTA para mi negocio",
      origen: "dm",
      calificado_at: "Hace 35 min",
      handled: true,
    },
  ]);

  const [logs, setLogs] = useState([
    "[SYSTEM] Inicializando StateGraph para tenant-demo-001...",
    "[IDEATION] Búsqueda realizada en SearXNG: 'tendencias reels viral Negocios B2B'",
    "[FILTRO 5/50] Idea ID 101 aprobada por filtro binario.",
    "[RUM SCORER] Score RUM calculado: 0.444 (Umbral nicho: 0.050) -> PASS",
    "[LANGGRAPH] Pausado en checkpoint humano 'human_approval_idea' (interrupt_before). Esperando aprobación...",
  ]);

  const handleApproveIdea = () => {
    setGraphState((prev) => ({
      ...prev,
      currentNode: "scriptwriting",
      ideaApproval: "approved",
    }));
    setLogs((prev) => [
      ...prev,
      "[CHECKPOINT] Idea aprobada por el operador humano.",
      "[SCRIPTWRITING] Crew de guionismo activado. Inyectando personaje de marca RAG...",
      "[SCRIPTWRITING] Guion de 4 bloques generado con keyword 'CONSULTA'.",
      "[VIDEO_EDIT] Tarea de Celery 'video_edit_task' encolada en serie (--concurrency=1)...",
      "[VIDEO_EDIT] Trimming silencios -> Subtítulos Whisper -> SFX interrupts -> OK",
      "[LANGGRAPH] Pausado en checkpoint humano 'human_approval_publish' (interrupt_before).",
    ]);
    setActiveTab("publish_approval");
  };

  const handleApprovePublish = () => {
    setGraphState((prev) => ({
      ...prev,
      currentNode: "publish",
      publishApproval: "approved",
    }));
    setLogs((prev) => [
      ...prev,
      "[CHECKPOINT] Publicación aprobada por el operador humano.",
      "[PUBLISH] Invocando Instagram Graph API oficial POST /media_publish...",
      "[PUBLISH] Reel publicado exitosamente. Post ID: ig_reel_8839102",
      "[METRICS_LOOP] Tarea programada a 72h para clasificación Rojo/Amarillo/Verde.",
    ]);
    setActiveTab("pipeline");
  };

  const handleTakeoverLead = (leadId) => {
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, handled: true } : l))
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#080c14] text-slate-100">
      {/* Header Bar */}
      <header className="border-b border-slate-800/80 bg-[#0d1320]/80 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              AGENCY AI ENGINE
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              LangGraph Multi-Tenant System
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
            <Users className="w-4 h-4 text-cyan-400" />
            <select
              value={selectedTenant}
              onChange={(e) => setSelectedTenant(e.target.value)}
              className="bg-transparent text-sm text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="tenant-demo-001">Cliente Demo B2B SaaS</option>
              <option value="tenant-ecom-002">E-Commerce Brand</option>
            </select>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>Gateway LiteLLM Active</span>
          </div>

          <div className="text-right text-xs">
            <div className="text-slate-400">Presupuesto LLM</div>
            <div className="font-semibold text-cyan-400 font-mono">$1.42 / $20.00 USD</div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 border-r border-slate-800/80 bg-[#0a0f1b] p-4 flex flex-col space-y-2">
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "pipeline"
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Orquestador Grafo</span>
          </button>

          <button
            onClick={() => setActiveTab("idea_approval")}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "idea_approval"
                ? "bg-purple-500/10 text-purple-400 border border-purple-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <div className="flex items-center space-x-3">
              <Sparkles className="w-4 h-4" />
              <span>Aprobación Idea (RUM)</span>
            </div>
            {graphState.ideaApproval === "pending" && (
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                1
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("publish_approval")}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "publish_approval"
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <div className="flex items-center space-x-3">
              <Video className="w-4 h-4" />
              <span>Aprobar Publicación</span>
            </div>
            {graphState.ideaApproval === "approved" && graphState.publishApproval === "pending" && (
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                1
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("leads")}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "leads"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <div className="flex items-center space-x-3">
              <MessageSquare className="w-4 h-4" />
              <span>Leads Inbound</span>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              {leads.filter((l) => !l.handled).length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("metrics")}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "metrics"
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Métricas 72h</span>
          </button>

          <button
            onClick={() => setActiveTab("brain")}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeTab === "brain"
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <Brain className="w-4 h-4" />
            <span>Cerebro RAG & Nicho</span>
          </button>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* TAB 1: PIPELINE / GRAFO */}
          {activeTab === "pipeline" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">LangGraph Execution Flow</h2>
                  <p className="text-sm text-slate-400">
                    Visualización del pipeline persistido por tenant en PostgreSQL
                  </p>
                </div>
                <button
                  onClick={() => {
                    setGraphState({
                      currentNode: "ideation",
                      status: "running",
                      ideaApproval: "pending",
                      publishApproval: "pending",
                    });
                    setLogs((prev) => [
                      ...prev,
                      "[MANUAL_TRIGGER] Reiniciando pipeline desde nodo 'ideation'...",
                    ]);
                  }}
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-purple-600 rounded-xl font-medium text-sm flex items-center space-x-2 hover:opacity-90 transition-all shadow-lg shadow-cyan-500/20"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Ejecutar Grafo</span>
                </button>
              </div>

              {/* Node Step Map */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-800">
                <div className="grid grid-cols-6 gap-4 relative">
                  {[
                    { id: "ideation", label: "1. Ideación", sub: "SearXNG + 4 Cuadrantes" },
                    { id: "human_approval_idea", label: "2. Checkpoint Idea", sub: "RUM + Filtro 5/50", interrupt: true },
                    { id: "scriptwriting", label: "3. Guionismo", sub: "4 Bloques + PPP" },
                    { id: "video_edit", label: "4. Edición Video", sub: "Celery + Whisper + SFX" },
                    { id: "human_approval_publish", label: "5. Checkpoint Pub", sub: "Revisión Humana", interrupt: true },
                    { id: "publish", label: "6. Publicación", sub: "Instagram Graph API" },
                  ].map((step, idx) => {
                    const isActive = graphState.currentNode === step.id;
                    return (
                      <div
                        key={step.id}
                        className={`p-4 rounded-xl border flex flex-col space-y-2 transition-all ${
                          isActive
                            ? "bg-cyan-950/40 border-cyan-500 glow-cyan scale-105"
                            : "bg-slate-900/40 border-slate-800 opacity-80"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-cyan-400">PASO 0{idx + 1}</span>
                          {step.interrupt && (
                            <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              PAUSA
                            </span>
                          )}
                        </div>
                        <div className="font-semibold text-sm">{step.label}</div>
                        <div className="text-[11px] text-slate-400">{step.sub}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Live Logs SSE Feed */}
              <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-cyan-400" />
                    <h3 className="font-semibold text-sm font-mono">Stream de Eventos SSE (Tiempo Real)</h3>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">thread_id = {selectedTenant}</span>
                </div>
                <div className="bg-black/60 rounded-xl p-4 font-mono text-xs text-emerald-400 space-y-1.5 h-48 overflow-y-auto border border-slate-900">
                  {logs.map((log, idx) => (
                    <div key={idx} className="leading-relaxed">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: APROBACIÓN DE IDEA */}
          {activeTab === "idea_approval" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">Checkpoint Humano: Evaluación de Idea</h2>
                <p className="text-sm text-slate-400">
                  Filtro 5/50 superado. Evaluación del scoring RUM (Relevancia Universal de Mercado) vs Umbral de Nicho.
                </p>
              </div>

              {ideas.map((idea) => (
                <div key={idea.id} className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        Idea Candidata #1
                      </span>
                      <h3 className="text-xl font-bold mt-2 text-white">{idea.texto}</h3>
                      <p className="text-sm text-slate-300 italic mt-1">Gancho: "{idea.gancho}"</p>
                    </div>

                    <div className="text-right">
                      <div className="text-xs text-slate-400">RUM Score Calculado</div>
                      <div className="text-2xl font-extrabold text-cyan-400 font-mono">{idea.rum_score}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Umbral Nicho: <span className="text-slate-200">{idea.threshold}</span> (PASS)
                      </div>
                    </div>
                  </div>

                  {/* RUM Variables Breakdown */}
                  <div className="grid grid-cols-6 gap-4">
                    {[
                      { label: "Universalidad (U)", val: idea.universalidad },
                      { label: "Intensidad (I)", val: idea.intensidad },
                      { label: "Claridad (C)", val: idea.claridad },
                      { label: "Shareability (S)", val: idea.shareability },
                      { label: "Distribución (D)", val: idea.distribucion },
                      { label: "Alineación (A)", val: idea.alineacion },
                    ].map((item, idx) => (
                      <div key={idx} className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                        <div className="text-[11px] text-slate-400">{item.label}</div>
                        <div className="text-lg font-bold font-mono text-cyan-300 mt-1">{item.val}</div>
                        <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-cyan-500 to-purple-500 h-full"
                            style={{ width: `${item.val * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center justify-end space-x-4 pt-2">
                    <button
                      onClick={() => alert("Idea rechazada. El grafo generará un nuevo batch de ideación.")}
                      className="px-5 py-2.5 rounded-xl border border-rose-500/40 text-rose-400 font-medium text-sm hover:bg-rose-500/10 flex items-center space-x-2 transition-all"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Rechazar Idea</span>
                    </button>
                    <button
                      onClick={handleApproveIdea}
                      className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-purple-600 rounded-xl font-medium text-sm flex items-center space-x-2 hover:opacity-90 shadow-lg shadow-cyan-500/20 transition-all"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Aprobar Idea & Generar Guion</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: APROBACIÓN DE PUBLICACIÓN */}
          {activeTab === "publish_approval" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">Checkpoint Humano: Publicar en Instagram</h2>
                <p className="text-sm text-slate-400">
                  Previsualización del video editado (MoviePy/Whisper/SFX) y revisión del guion en 4 bloques.
                </p>
              </div>

              <div className="grid grid-cols-12 gap-6">
                {/* Video Player Preview Mock */}
                <div className="col-span-5 glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col items-center justify-center space-y-4 min-h-[420px]">
                  <div className="w-full aspect-[9/16] bg-slate-950 rounded-xl border border-slate-800 relative flex flex-col items-center justify-center overflow-hidden glow-purple">
                    <Video className="w-12 h-12 text-slate-600 animate-pulse" />
                    <span className="text-xs text-slate-400 mt-2 font-mono">edited_video_render.mp4</span>
                    <span className="absolute bottom-4 px-3 py-1 bg-black/80 rounded-full text-[10px] font-mono text-cyan-400 border border-cyan-500/30">
                      Subtítulos Whisper + SFX Overlay
                    </span>
                  </div>
                </div>

                {/* 4 Block Script Reader */}
                <div className="col-span-7 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
                  <h3 className="font-bold text-lg border-b border-slate-800 pb-3 flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-cyan-400" />
                    <span>Estructura de Guion (4 Bloques)</span>
                  </h3>

                  <div className="space-y-3 text-sm">
                    <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                      <div className="text-xs font-mono text-cyan-400 font-semibold mb-1">0_5s — GANCHO</div>
                      <p className="text-slate-200">{script.gancho_0_5s}</p>
                    </div>

                    <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                      <div className="text-xs font-mono text-purple-400 font-semibold mb-1">5_30s — CONTEXTO (Retención)</div>
                      <p className="text-slate-200">{script.contexto_5_30s}</p>
                    </div>

                    <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                      <div className="text-xs font-mono text-emerald-400 font-semibold mb-1">30_50s — MORALEJA (Solución)</div>
                      <p className="text-slate-200">{script.moraleja_30_50s}</p>
                    </div>

                    <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
                      <div className="text-xs font-mono text-amber-400 font-semibold mb-1">50_60s — CTA (Palabra Clave)</div>
                      <p className="text-slate-200">{script.cta_50_60s}</p>
                      <span className="inline-block mt-2 px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded text-xs font-mono border border-amber-500/30">
                        Keyword Atribución: {script.keyword}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-end space-x-4 pt-4 border-t border-slate-800">
                    <button
                      onClick={handleApprovePublish}
                      className="w-full py-3 bg-gradient-to-r from-emerald-500 to-cyan-600 rounded-xl font-bold text-sm flex items-center justify-center space-x-2 hover:opacity-90 shadow-lg shadow-emerald-500/20 transition-all"
                    >
                      <CheckCircle2 className="w-5 h-5" />
                      <span>Aprobar & Publicar en Instagram Graph API</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: LEADS INBOUND */}
          {activeTab === "leads" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">Captura Inbound de Leads (Meta Webhooks)</h2>
                <p className="text-sm text-slate-400">
                  DMs y comentarios capturados en tiempo real. Calificados por el agente ligero con atribución completa al video de origen.
                </p>
              </div>

              <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/60 text-xs font-mono text-slate-400">
                      <th className="p-4">Usuario IG</th>
                      <th className="p-4">Mensaje Capturado</th>
                      <th className="p-4">Origen</th>
                      <th className="p-4">Keyword</th>
                      <th className="p-4">Video Origen</th>
                      <th className="p-4">Estado</th>
                      <th className="p-4 text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-sm">
                    {leads.map((lead) => (
                      <tr key={lead.id} className="hover:bg-slate-900/30 transition-colors">
                        <td className="p-4 font-mono text-cyan-300 font-semibold">{lead.ig_user_id}</td>
                        <td className="p-4 text-slate-200">"{lead.mensaje_original}"</td>
                        <td className="p-4">
                          <span className="px-2 py-0.5 rounded text-xs font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            {lead.origen.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-4 font-mono text-amber-400">{lead.keyword}</td>
                        <td className="p-4 font-mono text-slate-400">{lead.video_id}</td>
                        <td className="p-4">
                          {lead.handled ? (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              Tomado por Humano
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
                              Pendiente
                            </span>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          {!lead.handled && (
                            <button
                              onClick={() => handleTakeoverLead(lead.id)}
                              className="px-3 py-1.5 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded-lg text-xs font-medium hover:bg-cyan-500/30 transition-all"
                            >
                              Tomar Conversación
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

          {/* TAB 5: MÉTRICAS 72H */}
          {activeTab === "metrics" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">Clasificación 80/20 Post-Publicación (72 Horas)</h2>
                <p className="text-sm text-slate-400">
                  Evaluación relativa basada en ratio visitas/seguidores. Alimenta automáticamente la ideación del mes siguiente.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div className="glass-panel rounded-2xl p-6 border border-rose-500/30 bg-rose-950/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-lg bg-rose-500/20 text-rose-300 text-xs font-bold font-mono">
                      ROJO (&lt; 1.0×)
                    </span>
                    <TrendingUp className="w-4 h-4 text-rose-400" />
                  </div>
                  <h3 className="text-lg font-bold">Vistas bajo Seguidores</h3>
                  <p className="text-xs text-slate-300">
                    Se descarta la idea y estructura definitivamente. No se reintenta.
                  </p>
                </div>

                <div className="glass-panel rounded-2xl p-6 border border-amber-500/30 bg-amber-950/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 text-xs font-bold font-mono">
                      AMARILLO (1.0× - 10×)
                    </span>
                    <TrendingUp className="w-4 h-4 text-amber-400" />
                  </div>
                  <h3 className="text-lg font-bold">Desempeño Moderado</h3>
                  <p className="text-xs text-slate-300">
                    Se reintenta el mes subsiguiente en 1-2 formatos cambiando el ángulo.
                  </p>
                </div>

                <div className="glass-panel rounded-2xl p-6 border border-emerald-500/30 bg-emerald-950/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold font-mono">
                      VERDE (&gt; 10×)
                    </span>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-bold">Super Viralidad</h3>
                  <p className="text-xs text-slate-300">
                    Se multiplica en 2-3 variaciones de formato. Prioridad máxima en el batch de ideación.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: CEREBRO RAG */}
          {activeTab === "brain" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">Cerebro de Marketing & RAG Qdrant</h2>
                <p className="text-sm text-slate-400">
                  Parámetros del personaje de marca y mapa de mercado persistidos por tenant.
                </p>
              </div>

              <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
                <h3 className="font-bold text-lg">Personaje de Marca (Contexto RAG)</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div className="text-xs text-slate-400 font-mono">3 Atributos de Tono</div>
                    <div className="font-bold text-cyan-400 mt-1">Autoridad, Innovación, Pragmatismo</div>
                  </div>
                  <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div className="text-xs text-slate-400 font-mono">Elemento Visual Recurrente</div>
                    <div className="font-bold text-purple-400 mt-1">Iluminación Neón Azul/Violeta</div>
                  </div>
                  <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div className="text-xs text-slate-400 font-mono">Objeto de Identidad</div>
                    <div className="font-bold text-emerald-400 mt-1">Micrófono Dinámico Rode</div>
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
