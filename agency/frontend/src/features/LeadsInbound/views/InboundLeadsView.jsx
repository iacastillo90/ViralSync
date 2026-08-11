"use client";

import { useState, useEffect } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { fetchWithTenant } from "@/services/apiConfig";
import { LeadsTable } from "../components/LeadsTable";
import { MessageSquare } from "lucide-react";

export function InboundLeadsView({ tenantId }) {
  const { addLog } = useAgentStore();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setError(null);
    if (!tenantId) {
      setError(new Error("Sin tenant activo"));
      setLoading(false);
      return;
    }
    fetchWithTenant(`/tenants/${tenantId}/leads`, { signal: c.signal }, tenantId)
      .then((d) => setLeads(Array.isArray(d) ? d : []))
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      })
      .finally(() => setLoading(false));
    return () => c.abort();
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;

    const sseBaseUrl = process.env.NEXT_PUBLIC_SSE_URL || "http://localhost:8000/realtime/sse";
    const sseUrl = `${sseBaseUrl}/${tenantId}`;
    const eventSource = new EventSource(sseUrl);


    eventSource.addEventListener("lead_captured", (e) => {
      try {
        const newLead = JSON.parse(e.data);
        addLog(`⚡ Evento SSE lead_captured recibido: ${newLead.keyword || "Lead"}`);
        setLeads((prev) => [
          {
            id: newLead.id || `lead_${Date.now()}`,
            ig_user_id: newLead.ig_user_id || "Lead SSE",
            keyword: newLead.keyword || "CONSULTA",
            mensaje_original: newLead.mensaje_original || newLead.message || "Lead en vivo",
            created_at: new Date().toISOString(),
          },
          ...prev,
        ]);
      } catch (err) {
        console.error("Error al procesar SSE lead_captured", err);
      }
    });

    return () => {
      eventSource.close();
    };
  }, [tenantId, addLog]);


  const handleTakeover = async (leadId) => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    addLog(`Operador asumiendo control de lead '${leadId}'`);
    await fetch(`${apiBase}/tenants/${tenantId}/leads/${leadId}/takeover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_id: "admin_uuid_443", action: "pause_bot" }),
    });
    setLeads(
      leads.map((l) =>
        l.id === leadId
          ? { ...l, handled_by_human_at: new Date().toISOString() }
          : l
      )
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" /> Leads Inbound & Atribución CTA
          </h1>
          <p className="text-xs text-slate-400">
            Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
          </p>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Leads Calificados por Keyword
        </h2>
        {loading ? (
          <p className="text-sm text-slate-400">Cargando…</p>
        ) : error ? (
          <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
            Error al cargar leads: {error.message}
          </div>
        ) : leads.length === 0 ? (
          <p className="text-sm text-slate-400">No hay leads aún</p>
        ) : (
          <LeadsTable leads={leads} onTakeover={handleTakeover} />
        )}
      </div>
    </div>
  );
}
