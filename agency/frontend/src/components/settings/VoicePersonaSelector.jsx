"use client";

import { useState, useEffect } from "react";
import { fetchWithTenant } from "@/services/apiConfig";
import { Mic, Check, Volume2, Sparkles, UserCheck } from "lucide-react";

export function VoicePersonaSelector({ tenantId, currentVoiceCode, onSelectVoice }) {
  const [personas, setPersonas] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(currentVoiceCode || "es-ES-AlvaroNeural");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadVoices = async () => {
      try {
        setLoading(true);
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const res = await fetch(`${apiBase}/voice-personas`);
        if (res.ok) {
          const data = await res.json();
          setPersonas(data);
        }
      } catch (err) {
        console.error("Error cargando catálogo de voces:", err);
      } finally {
        setLoading(false);
      }
    };
    loadVoices();
  }, []);

  const handleSelect = async (persona) => {
    setSelectedVoice(persona.voice_code);
    if (!tenantId) return;
    try {
      setSaving(true);
      await fetchWithTenant(
        `/tenants/${tenantId}/voice-persona`,
        {
          method: "POST",
          body: JSON.stringify({
            voice_code: persona.voice_code,
            voice_name: persona.name,
          }),
        },
        tenantId
      );
      if (onSelectVoice) onSelectVoice(persona);
    } catch (err) {
      console.error("Error guardando voz de marca:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-5 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
            <Mic className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              Voice Persona (Locutor IA de Marca)
            </h3>
            <p className="text-xs text-slate-400">
              Selecciona la identidad y tono de voz oficial para la locución de tus Reels.
            </p>
          </div>
        </div>

        {saving && (
          <span className="text-xs text-indigo-400 font-mono animate-pulse">Guardando preferencia...</span>
        )}
      </div>

      {loading ? (
        <div className="text-center py-8 space-y-2">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-mono">Cargando catálogo de voces...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {personas.map((p) => {
            const isSelected = selectedVoice === p.voice_code;
            return (
              <div
                key={p.id}
                onClick={() => handleSelect(p)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer space-y-2 flex flex-col justify-between ${
                  isSelected
                    ? "bg-indigo-950/60 border-indigo-500 shadow-lg shadow-indigo-600/20"
                    : "bg-slate-950 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="space-y-1.5">
                  <div className="flex justify-between items-start">
                    <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono px-2 py-0.5 rounded-full font-bold">
                      {p.style}
                    </span>
                    {isSelected && (
                      <span className="bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Check className="w-3 h-3" /> Activa
                      </span>
                    )}
                  </div>

                  <h4 className="text-sm font-bold text-slate-100">{p.name}</h4>
                  <p className="text-xs text-slate-400 italic">"{p.preview_sample}"</p>
                </div>

                <div className="pt-2 border-t border-slate-900 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                  <span>Nicho: {p.recommended_niche}</span>
                  <span className="text-indigo-400">{p.voice_code}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
