"use client";

import { useState, useEffect } from "react";
import { fetchWithTenant } from "@/services/apiConfig";
import { Users, MessageSquare, Send, Award, CheckCircle2, ChevronRight, User, Sparkles } from "lucide-react";

export function LeadsKanbanView({ tenantId }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [replyingLead, setReplyingLead] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const loadLeads = async () => {
    if (!tenantId) return;
    try {
      setLoading(true);
      const data = await fetchWithTenant(`/tenants/${tenantId}/leads`, {}, tenantId);
      if (Array.isArray(data)) setLeads(data);
    } catch (err) {
      console.error("Error cargando leads CRM:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
  }, [tenantId]);

  const handleStageChange = async (leadId, newStage) => {
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/leads/${leadId}/stage`,
        {
          method: "PATCH",
          body: JSON.stringify({ stage: newStage }),
        },
        tenantId
      );
      setLeads((prev) =>
        prev.map((l) => (l.id === leadId ? { ...l, qualification_status: newStage } : l))
      );
    } catch (err) {
      console.error("Error actualizando etapa:", err);
    }
  };

  const handleSendDM = async (e) => {
    e.preventDefault();
    if (!replyingLead || !replyText.trim()) return;
    try {
      setSending(true);
      await fetchWithTenant(
        `/tenants/${tenantId}/leads/${replyingLead.id}/reply-dm`,
        {
          method: "POST",
          body: JSON.stringify({ message_text: replyText }),
        },
        tenantId
      );
      alert(`¡Mensaje DM enviado con éxito a @${replyingLead.instagram_handle || 'lead'}!`);
      setReplyingLead(null);
      setReplyText("");
    } catch (err) {
      alert(`Error enviando DM: ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const columns = [
    { id: "nuevo", title: "Nuevos Leads", color: "border-indigo-500/40 text-indigo-400" },
    { id: "contactado", title: "Contactados DM", color: "border-amber-500/40 text-amber-400" },
    { id: "cualificado", title: "Cualificados RAG", color: "border-purple-500/40 text-purple-400" },
    { id: "cerrado", title: "Citas / Venta", color: "border-emerald-500/40 text-emerald-400" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-3xl shadow-xl">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600/20 p-3 rounded-2xl border border-indigo-500/30 text-indigo-400">
            <Users className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Tablero Kanban CRM Inbound Leads</h1>
            <p className="text-xs text-slate-400">
              Gestiona el embudo de conversión de clientes captados autónomamente por comentarios y DMs.
            </p>
          </div>
        </div>

        <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-xs font-mono px-3 py-1.5 rounded-full font-bold flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" /> Bot DM Activo
        </span>
      </div>

      {/* Tablero Kanban */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 font-mono text-xs">Cargando embudo CRM...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {columns.map((col) => {
            const colLeads = leads.filter(
              (l) => (l.qualification_status || "nuevo").toLowerCase() === col.id
            );

            return (
              <div key={col.id} className="bg-slate-900/90 border border-slate-800 rounded-3xl p-4 space-y-4 shadow-xl flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <h3 className={`text-xs font-bold font-mono uppercase tracking-wider ${col.color}`}>
                      {col.title}
                    </h3>
                    <span className="bg-slate-950 text-slate-400 border border-slate-800 text-[10px] font-mono px-2 py-0.5 rounded-full">
                      {colLeads.length}
                    </span>
                  </div>

                  <div className="space-y-3 min-h-[300px]">
                    {colLeads.length === 0 ? (
                      <p className="text-[11px] text-slate-600 text-center py-8 italic">Sin leads en esta etapa</p>
                    ) : (
                      colLeads.map((lead) => (
                        <div
                          key={lead.id}
                          className="bg-slate-950 border border-slate-800 hover:border-indigo-500/40 p-4 rounded-2xl space-y-3 shadow-md transition-all"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex items-center gap-2">
                              <div className="w-7 h-7 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-xs">
                                <User className="w-3.5 h-3.5" />
                              </div>
                              <div>
                                <h4 className="text-xs font-bold text-slate-200">
                                  @{lead.instagram_handle || "lead_anonimo"}
                                </h4>
                                <span className="text-[9px] text-slate-500 font-mono">
                                  Score: {lead.intent_score || 85}/100
                                </span>
                              </div>
                            </div>

                            <span className="bg-amber-950/60 border border-amber-500/30 text-amber-300 text-[9px] font-mono px-1.5 py-0.5 rounded">
                              {lead.first_keyword || "REEL"}
                            </span>
                          </div>

                          {lead.last_comment && (
                            <p className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded-xl border border-slate-850 italic">
                              "{lead.last_comment}"
                            </p>
                          )}

                          <div className="pt-2 border-t border-slate-900 flex justify-between items-center gap-1">
                            <button
                              onClick={() => setReplyingLead(lead)}
                              className="text-[10px] bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-500/30 px-2 py-1 rounded-lg font-bold flex items-center gap-1 transition-all"
                            >
                              <MessageSquare className="w-3 h-3" /> DM
                            </button>

                            <select
                              value={lead.qualification_status || col.id}
                              onChange={(e) => handleStageChange(lead.id, e.target.value)}
                              className="bg-slate-900 text-[10px] text-slate-300 border border-slate-800 rounded px-1.5 py-1 outline-none"
                            >
                              <option value="nuevo">Nuevo</option>
                              <option value="contactado">Contactado</option>
                              <option value="cualificado">Cualificado</option>
                              <option value="cerrado">Cerrado</option>
                            </select>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal Respuesta DM */}
      {replyingLead && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-indigo-400" /> Responder DM a @{replyingLead.instagram_handle}
            </h3>

            <form onSubmit={handleSendDM} className="space-y-4">
              <div>
                <label className="text-xs font-mono text-slate-400 block mb-1">Mensaje Directo:</label>
                <textarea
                  rows={4}
                  required
                  placeholder="Hola! Te envío la auditoría gratuita solicitada..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setReplyingLead(null)}
                  className="flex-1 py-2.5 bg-slate-800 text-slate-300 rounded-xl text-xs font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={sending}
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" /> {sending ? "Enviando..." : "Enviar DM"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
