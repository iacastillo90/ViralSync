"use client";

import { useState, useEffect } from "react";

export function useRealtimeNotifications(tenantId) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!tenantId) return;

    const sseBase = process.env.NEXT_PUBLIC_SSE_URL || "http://localhost:8000/realtime/sse";
    const sseUrl = `${sseBase}/${tenantId}`;
    const eventSource = new EventSource(sseUrl);

    const addNotification = (notif) => {
      setNotifications((prev) => [
        {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          unread: true,
          ...notif,
        },
        ...prev.slice(0, 49), // Conservar máximo 50
      ]);
      setUnreadCount((c) => c + 1);
    };

    eventSource.addEventListener("video_render_started", (e) => {
      try {
        const data = JSON.parse(e.data);
        addNotification({
          type: "info",
          title: "🎬 Generando Video IA",
          message: `Iniciando post-producción visual para: "${data.title || "Reel 9:16"}"`,
        });
      } catch (err) {}
    });

    eventSource.addEventListener("video_render_completed", (e) => {
      try {
        const data = JSON.parse(e.data);
        addNotification({
          type: "success",
          title: "✅ Video Renderizado Listo",
          message: `El Reel ha sido generado con éxito (${data.provider || "NVIDIA NIM / MoviePy"}).`,
          scriptId: data.script_id,
        });
      } catch (err) {}
    });

    eventSource.addEventListener("video_render_failed", (e) => {
      try {
        const data = JSON.parse(e.data);
        addNotification({
          type: "error",
          title: "❌ Error de Renderizado",
          message: data.error || "El proceso de video falló.",
        });
      } catch (err) {}
    });

    eventSource.addEventListener("graph_error", (e) => {
      try {
        const data = JSON.parse(e.data);
        addNotification({
          type: "error",
          title: "⚠️ Error en la Agencia",
          message: data.message || "Fallo en el flujo LangGraph.",
        });
      } catch (err) {}
    });

    return () => {
      eventSource.close();
    };
  }, [tenantId]);

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
    setUnreadCount(0);
  };

  const clearAll = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  return { notifications, unreadCount, markAllAsRead, clearAll };
}
