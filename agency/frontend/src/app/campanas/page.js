"use client";

import { useState, useEffect } from "react";
import { useTenantStore } from "@/stores/useTenantStore";
import { fetchWithTenant } from "@/services/apiConfig";
import { Layers, Plus, Target, CheckCircle2, Clock, Sparkles, FolderOpen, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function CampaignsPage() {
  const { activeTenant } = useTenantStore();
  const tenantId = activeTenant?.id;

  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [targetReels, setTargetReels] = useState(8);
  const [creating, setCreating] = useState(false);

  const loadCampaigns = async () => {
    if (!tenantId) return;
    try {
      setLoading(true);
      const data = await fetchWithTenant(`/tenants/${tenantId}/campaigns`, {}, tenantId);
      if (Array.isArray(data)) setCampaigns(data);
    } catch (err) {
      console.error("Error cargando campañas:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, [tenantId]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim() || !tenantId) return;
    try {
      setCreating(true);
      await fetchWithTenant(
        `/tenants/${tenantId}/campaigns`,
        {
          method: "POST",
          body: JSON.stringify({
            name: name.strip ? name.strip() : name.trim(),
            objective,
            target_reels_count: parseInt(targetReels, 10) || 8,
          }),
        },
        tenantId
      );
      setName("");
      setObjective("");
      setShowModal(false);
      loadCampaigns();
    } catch (err) {
      alert(`Error creando campaña: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-3xl shadow-xl">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600/20 p-3 rounded-2xl border border-indigo-500/30 text-indigo-400">
            <Layers className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Modo Campaña (Agrupación Comercial)</h1>
            <p className="text-xs text-slate-400">
              Organiza ideaciones, guiones y videos bajo un mismo objetivo de negocio.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 transition-all"
        >
          <Plus className="w-4 h-4" /> Nueva Campaña
        </button>
      </div>

      {/* Grid de Campañas */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 font-mono text-xs">Cargando campañas activas...</div>
      ) : campaigns.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl p-12 text-center space-y-3">
          <Target className="w-12 h-12 text-slate-700 mx-auto" />
          <h3 className="text-sm font-bold text-slate-200">No hay campañas registradas</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Crea tu primera campaña para agrupar 8 Reels con un objetivo estratégico (Lanzamiento, Promoción, Autoridad).
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="bg-slate-900 border border-slate-800 hover:border-indigo-500/40 p-6 rounded-3xl space-y-4 shadow-xl flex flex-col justify-between transition-all"
            >
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono font-bold px-2.5 py-1 rounded-full">
                    {c.status === "active" ? "Campaña Activa" : c.status}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    Objetivo: {c.target_reels_count} Reels
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-100">{c.name}</h3>
                {c.objective && <p className="text-xs text-slate-400 line-clamp-2">{c.objective}</p>}
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-500">
                  {c.created_at ? new Date(c.created_at).toLocaleDateString("es-ES") : "Reciente"}
                </span>
                {tenantId && (
                  <Link
                    href={`/tenants/${tenantId}/aprobaciones/ideas?campaignId=${c.id}`}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-bold flex items-center gap-1"
                  >
                    Ver Ideaciones <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Nueva Campaña */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" /> Crear Nueva Campaña
            </h3>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Nombre de la Campaña
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Lanzamiento Black Friday 2026"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Objetivo Estratégico
                </label>
                <textarea
                  rows={2}
                  placeholder="Ej: Posicionar la oferta de consultoría B2B y captar 50 leads calificados por DM..."
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  Meta de Reels Aprobados
                </label>
                <select
                  value={targetReels}
                  onChange={(e) => setTargetReels(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="4">4 Reels (1 por semana)</option>
                  <option value="8">8 Reels (2 por semana - Recomendado)</option>
                  <option value="12">12 Reels (3 por semana)</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold py-2.5 rounded-xl transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
                >
                  {creating ? "Guardando..." : "Crear Campaña"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
