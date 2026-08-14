"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAgentStore } from "@/stores/useAgentStore";
import {
  Calendar as CalendarIcon,
  Clock,
  CheckCircle2,
  AlertCircle,
  Video as VideoIcon,
  Sparkles,
  Share2,
  Filter,
  Plus,
  Play,
  Instagram,
  Send,
  ArrowRight,
} from "lucide-react";
import { useState, useEffect } from "react";

export default function CalendarioPage() {
  const { tenantId } = useAgentStore();
  const activeTenantId = tenantId || "92c96882-9eb6-4f50-b7b6-316c3eb6e9a5";

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedVideoForSchedule, setSelectedVideoForSchedule] = useState(null);
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("15:00");
  const [schedulePlatform, setSchedulePlatform] = useState("instagram_reels");
  const [isScheduling, setIsScheduling] = useState(false);
  const [notification, setNotification] = useState("");

  const fetchCalendarData = async () => {
    try {
      setLoading(true);
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${baseUrl}/tenants/${activeTenantId}/calendar`);
      if (!res.ok) throw new Error("Error cargando el calendario editorial");
      const data = await res.json();
      setItems(data);
    } catch (err) {
      console.error("Error al obtener calendario:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendarData();
  }, [activeTenantId]);

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedVideoForSchedule || !scheduleDate) {
      alert("Por favor selecciona una fecha válida para agendar.");
      return;
    }

    setIsScheduling(true);
    try {
      const scheduledIso = new Date(`${scheduleDate}T${scheduleTime}:00Z`).toISOString();
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

      const res = await fetch(`${baseUrl}/tenants/${activeTenantId}/calendar/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: selectedVideoForSchedule.video_id,
          scheduled_at: scheduledIso,
          platform: schedulePlatform,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error agendando publicación");

      setNotification(`¡Éxito! Publicación agendada para el ${scheduleDate} a las ${scheduleTime} UTC.`);
      setSelectedVideoForSchedule(null);
      fetchCalendarData();

      setTimeout(() => setNotification(""), 5000);
    } catch (err) {
      alert(`Error al agendar: ${err.message}`);
    } finally {
      setIsScheduling(false);
    }
  };

  const filteredItems = items.filter((item) => {
    if (statusFilter === "all") return true;
    if (statusFilter === "scheduled") return item.publish_approval_status === "approved" && item.scheduled_at;
    if (statusFilter === "pending") return item.publish_approval_status === "pending";
    if (statusFilter === "published") return item.publish_approval_status === "published";
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={activeTenantId} />
        <main className="flex-1 p-6 space-y-6">
          {/* Header de la Vista */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2 text-slate-100">
                <CalendarIcon className="w-5 h-5 text-indigo-400" /> Calendario Editorial Multi-Canal
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Planificación, Programación Autónoma y Control de Difusión en Instagram Reels, TikTok y Shorts
              </p>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-slate-400">Filtrar por Estado:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-indigo-500"
              >
                <option value="all">Todas las publicaciones ({items.length})</option>
                <option value="scheduled">Programadas / Aprobadas</option>
                <option value="pending">Pendientes de Aprobar</option>
                <option value="published">Publicadas en Redes</option>
              </select>
            </div>
          </div>

          {/* Notificación Flotante de Éxito */}
          {notification && (
            <div className="bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 p-4 rounded-xl text-xs flex items-center justify-between animate-fade-in">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{notification}</span>
              </div>
            </div>
          )}

          {/* Estado de Carga */}
          {loading ? (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/50 border border-slate-800 rounded-2xl">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3"></div>
              <p className="text-xs text-slate-400 font-mono">Cargando parrilla de publicaciones del tenant...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredItems.map((item) => {
                const isScheduled = item.scheduled_at || item.publish_approval_status === "approved";
                const isPublished = item.publish_approval_status === "published";

                return (
                  <div
                    key={item.video_id}
                    className="bg-slate-900 border border-slate-800 hover:border-indigo-500/40 rounded-2xl p-5 space-y-4 transition-all shadow-lg flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      <div className="flex justify-between items-start gap-2">
                        <span
                          className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border uppercase ${
                            isPublished
                              ? "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                              : isScheduled
                              ? "bg-indigo-950 text-indigo-300 border-indigo-500/40"
                              : "bg-amber-950 text-amber-300 border-amber-500/40"
                          }`}
                        >
                          {isPublished ? "Publicado" : isScheduled ? "Programado" : "Pendiente"}
                        </span>

                        <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
                          {item.provider}
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-slate-100 line-clamp-2">{item.title}</h3>

                      {item.gancho && (
                        <p className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded-xl border border-slate-850 italic line-clamp-2">
                          "{item.gancho}"
                        </p>
                      )}

                      {/* Video Player Preview / Thumbnail */}
                      <div className="relative aspect-[9/16] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 group max-h-56 flex items-center justify-center">
                        {item.edited_video_uri ? (
                          <video
                            src={item.edited_video_uri}
                            className="w-full h-full object-cover"
                            controls={false}
                          />
                        ) : (
                          <div className="flex flex-col items-center text-slate-500">
                            <VideoIcon className="w-8 h-8 mb-1" />
                            <span className="text-[10px]">Video en Proceso</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-slate-850 space-y-3">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-indigo-400" />
                          {item.scheduled_at
                            ? new Date(item.scheduled_at).toLocaleDateString("es-ES", {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "Sin fecha agendada"}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase">{item.platform}</span>
                      </div>

                      <button
                        onClick={() => {
                          setSelectedVideoForSchedule(item);
                          setScheduleDate(new Date().toISOString().split("T")[0]);
                        }}
                        className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
                      >
                        <CalendarIcon className="w-3.5 h-3.5" /> Programar Fecha & Hora
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Modal Interactivo para Programar Fecha & Hora */}
          {selectedVideoForSchedule && (
            <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden p-6 space-y-5">
                <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    <CalendarIcon className="w-5 h-5 text-indigo-400" /> Programar Difusión
                  </h3>
                  <button
                    onClick={() => setSelectedVideoForSchedule(null)}
                    className="text-xs text-slate-400 hover:text-slate-100"
                  >
                    ✕
                  </button>
                </div>

                <form onSubmit={handleScheduleSubmit} className="space-y-4">
                  <div>
                    <label className="text-xs font-mono text-slate-400 block mb-1">Título del Reel:</label>
                    <p className="text-xs text-slate-200 font-bold bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                      {selectedVideoForSchedule.title}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-mono text-slate-400 block mb-1">Fecha de Publicación:</label>
                      <input
                        type="date"
                        value={scheduleDate}
                        onChange={(e) => setScheduleDate(e.target.value)}
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-mono text-slate-400 block mb-1">Hora (UTC):</label>
                      <input
                        type="time"
                        value={scheduleTime}
                        onChange={(e) => setScheduleTime(e.target.value)}
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-mono text-slate-400 block mb-1">Plataforma Objetivo:</label>
                    <select
                      value={schedulePlatform}
                      onChange={(e) => setSchedulePlatform(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                    >
                      <option value="instagram_reels">Instagram Reels API</option>
                      <option value="tiktok">TikTok Content Posting API</option>
                      <option value="youtube_shorts">YouTube Shorts API</option>
                    </select>
                  </div>

                  <div className="pt-3 flex gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedVideoForSchedule(null)}
                      className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold"
                    >
                      Cancelar
                    </button>

                    <button
                      type="submit"
                      disabled={isScheduling}
                      className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
                    >
                      {isScheduling ? "Agendando..." : "Confirmar Agenda"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
