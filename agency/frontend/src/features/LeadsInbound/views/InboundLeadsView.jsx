"use client";

import { useState, useEffect } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { LeadsTable } from "../components/LeadsTable";
import { MessageSquare } from "lucide-react";

export function InboundLeadsView({ tenantId }) {
  const { addLog } = useAgentStore();
  const [leads, setLeads] = useState([
    {
      id: "lead-001",
      tenant_id: tenantId,
      video_id: "video-55",
      keyword: "CONSULTA",
      ig_user_id: "user_ig_9921",
      mensaje_original: "Hola! Quiero la CONSULTA por favor",
      origen: "comment",
      calificado_at: "2026-08-06T01:45:00Z",
      handled_by_human_at: null,
    },
  ]);

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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
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
            <LeadsTable leads={leads} onTakeover={handleTakeover} />
          </div>
        </main>
      </div>
    </div>
  );
}
