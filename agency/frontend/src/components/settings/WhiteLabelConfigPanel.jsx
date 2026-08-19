"use client";

import { useState, useEffect } from "react";
import { fetchWithTenant } from "@/services/apiConfig";
import { ShieldCheck, Palette, Image as ImageIcon, Save, Check } from "lucide-react";

export function WhiteLabelConfigPanel({ tenantId }) {
  const [agencyName, setAgencyName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#4F46E5");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (!tenantId) return;
    const loadBranding = async () => {
      try {
        setLoading(true);
        const data = await fetchWithTenant(`/tenants/${tenantId}/branding`, {}, tenantId);
        if (data) {
          setAgencyName(data.agency_name || "");
          setLogoUrl(data.logo_url || "");
          setPrimaryColor(data.primary_color || "#4F46E5");
        }
      } catch (err) {
        console.error("Error cargando marca blanca:", err);
      } finally {
        setLoading(false);
      }
    };
    loadBranding();
  }, [tenantId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!tenantId) return;
    try {
      setSaving(true);
      await fetchWithTenant(
        `/tenants/${tenantId}/branding`,
        {
          method: "PUT",
          body: JSON.stringify({
            agency_name: agencyName,
            logo_url: logoUrl,
            primary_color: primaryColor,
          }),
        },
        tenantId
      );
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert(`Error guardando marca blanca: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6 shadow-xl max-w-2xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Marca Blanca de Agencia (White-Label)</h3>
            <p className="text-xs text-slate-400">
              Personaliza el logo, nombre comercial y color primario que se mostrará en los reportes PDF.
            </p>
          </div>
        </div>

        {savedSuccess && (
          <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-xs font-mono px-3 py-1 rounded-full font-bold flex items-center gap-1">
            <Check className="w-3.5 h-3.5" /> Guardado
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-center py-6 text-xs text-slate-500 font-mono">Cargando configuración de marca...</div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-1">Nombre Comercial de la Agencia</label>
            <input
              type="text"
              required
              placeholder="Ej: ViralSync Marketing Studio"
              value={agencyName}
              onChange={(e) => setAgencyName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-1">URL del Logo (PNG / SVG)</label>
            <input
              type="url"
              placeholder="https://tuagencia.com/logo.png"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-1">Color Primario Corporativo</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="w-10 h-10 bg-slate-950 border border-slate-800 rounded-xl cursor-pointer p-1"
              />
              <input
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="w-32 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-100 outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all"
            >
              <Save className="w-4 h-4" /> {saving ? "Guardando..." : "Guardar Marca Blanca"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
