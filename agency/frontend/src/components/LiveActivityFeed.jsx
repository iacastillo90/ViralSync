import React, { useEffect, useState } from "react";

/**
 * LiveActivityFeed.jsx
 * Componente en tiempo real que se suscribe a Server-Sent Events (SSE) por tenant
 * y muestra notificaciones activas para lead_captured, rum_metrics_evaluated,
 * audit_event_logged y product_media_ingested.
 */
export default function LiveActivityFeed({ tenantId = "default_tenant" }) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("connecting");

  useEffect(() => {
    if (!tenantId) return;

    const sseBaseUrl = process.env.NEXT_PUBLIC_SSE_URL || "http://localhost:8000/realtime/sse";
    const sseUrl = `${sseBaseUrl}/${tenantId}`;
    const eventSource = new EventSource(sseUrl);


    eventSource.onopen = () => {
      setStatus("connected");
    };

    eventSource.onerror = () => {
      setStatus("disconnected");
    };

    const handleEvent = (type) => (e) => {
      try {
        const data = JSON.parse(e.data);
        setEvents((prev) => [
          {
            id: Date.now() + Math.random(),
            type,
            data,
            timestamp: new Date().toLocaleTimeString(),
          },
          ...prev.slice(0, 49),
        ]);
      } catch (err) {
        console.error("Error parsing SSE event payload", err);
      }
    };

    const eventTypes = [
      "lead_captured",
      "rum_metrics_evaluated",
      "audit_event_logged",
      "product_media_ingested",
      "node_progress",
      "ingest_complete",
    ];

    eventTypes.forEach((evt) => {
      eventSource.addEventListener(evt, handleEvent(evt));
    });

    return () => {
      eventSource.close();
    };
  }, [tenantId]);

  const getBadgeStyle = (type) => {
    switch (type) {
      case "lead_captured":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      case "rum_metrics_evaluated":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "audit_event_logged":
        return "bg-amber-500/20 text-amber-400 border-amber-500/30";
      case "product_media_ingested":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <div className="w-full max-w-xl p-4 bg-slate-900/90 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          Feed de Eventos en Tiempo Real
        </h3>
        <span
          className={`text-xs px-2 py-0.5 rounded-full border ${
            status === "connected"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
          }`}
        >
          {status}
        </span>
      </div>

      <div className="mt-3 space-y-2 max-h-80 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-6">
            Esperando eventos SSE en vivo...
          </p>
        ) : (
          events.map((item) => (
            <div
              key={item.id}
              className="p-3 bg-slate-950/60 border border-slate-850 rounded-lg flex items-start justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <span
                  className={`inline-block font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${getBadgeStyle(
                    item.type
                  )}`}
                >
                  {item.type}
                </span>
                <p className="text-slate-300 font-medium">
                  {JSON.stringify(item.data)}
                </p>
              </div>
              <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap">
                {item.timestamp}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
