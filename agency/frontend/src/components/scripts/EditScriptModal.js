"use client";

import { useState, useEffect } from "react";
import { X, Sparkles, Check, Calculator } from "lucide-react";

/**
 * EditScriptModal
 * Componente atómico de modal para editar la narrativa en 4 bloques de un guion
 * y recalcular dinámicamente el tiempo de locución y el formato recomendado de video en tiempo real.
 */
export function EditScriptModal({ script, isOpen, onClose, onSave }) {
  const [gancho, setGancho] = useState("");
  const [contexto, setContexto] = useState("");
  const [moraleja, setMoraleja] = useState("");
  const [cta, setCta] = useState("");
  const [productName, setProductName] = useState("");

  // Cargar datos del guion al abrir
  useEffect(() => {
    if (script) {
      setGancho(script.gancho_0_5s || script.gancho || script.title || "");
      setContexto(script.contexto_5_30s || script.contexto || script.core_message || "");
      setMoraleja(script.moraleja_30_50s || script.moraleja || "");
      setCta(script.cta_50_60s || script.cta || "");
      setProductName(script.product_name || script.service_name || script.category || "Producto General");
    }
  }, [script]);

  if (!isOpen || !script) return null;

  // 🧮 CÁLCULO DINÁMICO DE TIEMPO EN TIEMPO REAL
  const fullText = `${gancho} ${contexto} ${moraleja} ${cta}`.trim();
  const wordCount = fullText.split(/\s+/).filter(Boolean).length;

  // Promedio de locución humana en español: 2.5 palabras por segundo (150 palabras/min)
  const estimatedSpeechSeconds = (wordCount / 2.5).toFixed(1);
  const speechSecNum = parseFloat(estimatedSpeechSeconds);

  // Determinar la duración recomendada estricta (15s, 30s, 45s, 60s) con margen de silencio
  let recommendedTargetSeconds = 30;
  let silencePadding = 3;

  if (speechSecNum <= 13) {
    recommendedTargetSeconds = 15;
    silencePadding = 2;
  } else if (speechSecNum <= 27) {
    recommendedTargetSeconds = 30;
    silencePadding = 3;
  } else if (speechSecNum <= 41) {
    recommendedTargetSeconds = 45;
    silencePadding = 4;
  } else {
    recommendedTargetSeconds = 60;
    silencePadding = 5;
  }

  const handleFormSubmit = (e) => {
    e.preventDefault();
    onSave({
      ...script,
      gancho_0_5s: gancho,
      gancho,
      title: gancho,
      contexto_5_30s: contexto,
      contexto: contexto,
      moraleja_30_50s: moraleja,
      moraleja,
      cta_50_60s: cta,
      cta,
      product_name: productName,
      target_duration: recommendedTargetSeconds,
      word_count: wordCount,
      speech_duration_seconds: speechSecNum,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-fadeIn">
        {/* Cabecera del Modal */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/90 flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" /> Editar Guion & Recalcular Duración
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Ajusta los 4 bloques narrativos. La duración de locución se recalcula en tiempo real.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 bg-slate-800 p-1.5 rounded-xl border border-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Formulario de Edición de los 4 Bloques */}
        <form onSubmit={handleFormSubmit} className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Panel de Recálculo Dinámico de Tiempo */}
          <div className="bg-slate-950 border border-indigo-500/40 p-4 rounded-xl space-y-2">
            <div className="flex justify-between items-center">
              <h4 className="font-bold text-indigo-300 flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-indigo-400" /> Calculador de Locución en Vivo
              </h4>
              <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded font-mono font-bold">
                {wordCount} palabras
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">⏱️ Tiempo de Voz Estimado</div>
                <div className="font-mono text-slate-100 font-bold text-sm mt-0.5">
                  ~{estimatedSpeechSeconds} seg
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">🎬 Formato Objetivo</div>
                <div className="font-mono text-amber-400 font-bold text-sm mt-0.5">
                  {recommendedTargetSeconds}s ({silencePadding}s margen)
                </div>
              </div>
            </div>
          </div>

          {/* Producto / Servicio */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Producto / Servicio:</label>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Bloque 1: Gancho Viral (0-5s) */}
          <div>
            <label className="block font-semibold text-indigo-400 mb-1">🪝 Bloque 1: Gancho Viral (0-5s):</label>
            <textarea
              rows={2}
              value={gancho}
              onChange={(e) => setGancho(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Bloque 2: Contexto & Problema (5-30s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">💡 Bloque 2: Contexto & Desarrollo (5-30s):</label>
            <textarea
              rows={3}
              value={contexto}
              onChange={(e) => setContexto(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Bloque 3: Moraleja & Solución (30-50s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">✨ Bloque 3: Moraleja / Solución (30-50s):</label>
            <textarea
              rows={2}
              value={moraleja}
              onChange={(e) => setMoraleja(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Bloque 4: Llamado a la Acción (CTA) */}
          <div>
            <label className="block font-semibold text-emerald-400 mb-1">📣 Bloque 4: Llamado a la Acción (CTA):</label>
            <input
              type="text"
              value={cta}
              onChange={(e) => setCta(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Botones de Acción */}
          <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-lg flex items-center gap-1.5 transition-all"
            >
              <Check className="w-4 h-4" /> Guardar & Recalcular
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
