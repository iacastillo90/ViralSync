"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAgentStore } from "@/stores/useAgentStore";
import {
  BarChart3,
  TrendingUp,
  Brain,
  Sparkles,
  Zap,
  Users,
  Video as VideoIcon,
  CheckCircle2,
  Share2,
  Award,
} from "lucide-react";
import { useState, useEffect } from "react";

export default function AnalyticsPage() {
  const { tenantId } = useAgentStore();
  const activeTenantId = tenantId || "92c96882-9eb6-4f50-b7b6-316c3eb6e9a5";

  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const res = await fetch(`${baseUrl}/tenants/${activeTenantId}/metrics`);
        if (res.ok) {
          const data = await res.json();
          setAnalyticsData(data);
        }
      } catch (err) {
        console.error("Error cargando analíticas:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [activeTenantId]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={activeTenantId} />
        <main className="flex-1 p-6 space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2 text-slate-100">
                <BarChart3 className="w-5 h-5 text-indigo-400" /> Analítica IA 360 & Aprendizaje RAG 72h
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Monitoreo de Viralidad post-difusión, Retención y Retroalimentación Vectorial en Qdrant
              </p>
            </div>
          </div>

          {/* Tarjetas Principales de KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> Viral Score Promedio
              </span>
              <p className="text-2xl font-extrabold text-emerald-400 font-mono">0.84 / 1.00</p>
              <span className="text-[10px] text-slate-400">+18% vs mes anterior</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block flex items-center gap-1">
                <Users className="w-3.5 h-3.5 text-indigo-400" /> Leads Capturados por DM
              </span>
              <p className="text-2xl font-extrabold text-indigo-400 font-mono">48 Leads</p>
              <span className="text-[10px] text-slate-400">Conversión por comentario "AUDIO"</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Motor IA Activo
              </span>
              <p className="text-sm font-bold text-amber-300 font-mono pt-1">NVIDIA Cosmos 9:16</p>
              <span className="text-[10px] text-slate-400">Generación 3D cinemática I2V</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-1">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block flex items-center gap-1">
                <Brain className="w-3.5 h-3.5 text-purple-400" /> Patrones RAG Indexados
              </span>
              <p className="text-2xl font-extrabold text-purple-400 font-mono">14 Patrones</p>
              <span className="text-[10px] text-slate-400">Almacenados en Qdrant</span>
            </div>
          </div>

          {/* Sección de Cierre de Bucle RAG */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" /> Patrones Ganadores Indexados en la Memoria Vectorial (Qdrant)
            </h2>
            <p className="text-xs text-slate-400">
              Estos elementos narrativos superaron el umbral de viralidad a las 72h y fueron inyectados en la memoria RAG para optimizar los futuros guiones de tu agencia:
            </p>

            <div className="space-y-3 pt-2">
              {[
                {
                  gancho: "¿Te gustaría un audio profesional sin ruido de fondo en tus videos?",
                  score: "0.89 (Viral High-Performer)",
                  niche: "Audio & Podcast",
                  reason: "Alta tasa de retención en los primeros 3 segundos con gancho de dolor directo."
                },
                {
                  gancho: "El micrófono que ignora a tu teclado mecánico (y a tu mamá gritando)",
                  score: "0.82 (Viral High-Performer)",
                  niche: "Gaming & Content Creation",
                  reason: "Uso de humor y situación cotidiana relatable para creadores de contenido."
                }
              ].map((p, idx) => (
                <div key={idx} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-200">"{p.gancho}"</span>
                    <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-[10px] font-mono px-2 py-0.5 rounded font-bold">
                      {p.score}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{p.reason}</p>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
