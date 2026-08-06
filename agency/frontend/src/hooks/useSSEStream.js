import { useEffect, useRef } from "react";
import { useAgentStore } from "@/stores/useAgentStore";

export function useSSEStream(tenantId) {
  const { setNodeState, addLog, setCheckpointPaused } = useAgentStore();
  const retryCountRef = useRef(0);
  const maxRetries = 5;

  useEffect(() => {
    if (!tenantId) return;

    let eventSource = null;
    let timeoutId = null;

    const connectSSE = () => {
      const sseBaseUrl =
        process.env.NEXT_PUBLIC_SSE_URL || "http://localhost:8000/realtime/sse";
      const sseUrl = `${sseBaseUrl}/${tenantId}`;
      eventSource = new EventSource(sseUrl);

      eventSource.onopen = () => {
        retryCountRef.current = 0;
        addLog(`Conexión SSE establecida con tenant '${tenantId}'`);
      };

      eventSource.addEventListener("node_change", (e) => {
        try {
          const data = JSON.parse(e.data);
          setNodeState(data.node, data.status);
          if (data.message) addLog(`[${data.node}] ${data.message}`);
        } catch (err) {
          console.error("Error parseando evento SSE node_change", err);
        }
      });

      eventSource.addEventListener("log_entry", (e) => {
        try {
          const data = JSON.parse(e.data);
          addLog(`[${data.module || "LangGraph"}] ${data.message}`);
        } catch (err) {
          console.error("Error parseando evento SSE log_entry", err);
        }
      });

      eventSource.addEventListener("checkpoint_paused", (e) => {
        try {
          const data = JSON.parse(e.data);
          setCheckpointPaused(data.node, true);
          addLog(`[PAUSA] Grafo detenido en checkpoint manual '${data.node}'`);
        } catch (err) {
          console.error("Error parseando evento SSE checkpoint_paused", err);
        }
      });

      eventSource.onerror = (err) => {
        console.warn("Parpadeo de red en SSE. Reconectando...", err);
        if (eventSource) eventSource.close();

        if (retryCountRef.current < maxRetries) {
          const timeout = Math.pow(2, retryCountRef.current) * 1000;
          retryCountRef.current += 1;
          addLog(`Reconectando SSE en ${timeout / 1000}s (Intento ${retryCountRef.current}/${maxRetries})...`);
          timeoutId = setTimeout(connectSSE, timeout);
        } else {
          addLog("Límite de reconexiones SSE alcanzado. Por favor recarga la página.");
        }
      };
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [tenantId, setNodeState, addLog, setCheckpointPaused]);
}
