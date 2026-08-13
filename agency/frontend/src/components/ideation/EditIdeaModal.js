"use client";

import { useState, useEffect } from "react";
import { X, Clock, Sparkles, Check, Calculator } from "lucide-react";

/**
 * EditIdeaModal
 * Componente atómico de modal para editar una idea y recalcular dinámicamente
 * la duración del tiempo de locución y el formato recomendado (15s, 30s, 45s, 60s) en tiempo real.
 */
export function EditIdeaModal({ idea, isOpen, onClose, onSave }) {
  const [angle, setAngle] = useState("");
  const [coreMessage, setCoreMessage] = useState("");
  const [moraleja, setMoraleja] = useState("");
  const [cta, setCta] = useState("");
  const [category, setCategory] = useState("");

  // Cargar datos de la idea al abrir
  useEffect(() => {
    if (idea) {
      setAngle(idea.angle || idea.hook || idea.title || "");
      setCoreMessage(idea.core_message || idea.contexto_5_30s || "");
      setMoraleja(idea.moraleja || idea.moraleja_30_50s || "");
      setCta(idea.cta || idea.cta_50_60s || "");
      setCategory(idea.category || idea.product_name || "General");
    }
  }, [idea]);

  if (!isOpen || !idea) return null;

  // 🧮 CÁLCULO DINÁMICO DE TIEMPO EN TIEMPO REAL
  const fullText = `${angle} ${coreMessage} ${moraleja} ${cta}`.trim();
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
      ...idea,
      angle,
      hook: angle,
      title: angle,
      core_message: coreMessage,
      contexto_5_30s: coreMessage,
      moraleja,
      moraleja_30_50s: moraleja,
      cta,
      cta_50_60s: cta,
      category,
      product_name: category,
      estimated_duration: recommendedTargetSeconds,
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
              <Sparkles className="w-4 h-4 text-indigo-400" /> Editar Idea & Recalcular Tiempo
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Modifica los textos del concepto. La duración estimada se recalcula automáticamente.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 bg-slate-800 p-1.5 rounded-xl border border-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Formulario de Edición */}
        <form onSubmit={handleFormSubmit} className="p-5 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Panel de Recálculo Dinámico de Tiempo */}
          <div className="bg-slate-950 border border-indigo-500/40 p-4 rounded-xl space-y-2">
            <div className="flex justify-between items-center">
              <h4 className="font-bold text-indigo-300 flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-indigo-400" /> Calculador de Tiempo en Vivo
              </h4>
              <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded font-mono font-bold">
                {wordCount} palabras
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">⏱️ Locución de Voz</div>
                <div className="font-mono text-slate-100 font-bold text-sm mt-0.5">
                  ~{estimatedSpeechSeconds} seg
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-2.5 rounded-lg text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">🎬 Formato de Video</div>
                <div className="font-mono text-amber-400 font-bold text-sm mt-0.5">
                  {recommendedTargetSeconds}s ({silencePadding}s silencio)
                </div>
              </div>
            </div>
          </div>

          {/* Categoría / Producto */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Categoría / Producto:</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Gancho / Ángulo (0-5s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">🪝 Gancho Inicial (Angle/Hook):</label>
            <textarea
              rows={2}
              value={angle}
              onChange={(e) => setAngle(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Mensaje Central / Contexto (5-30s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">💡 Mensaje Central / Contexto:</label>
            <textarea
              rows={3}
              value={coreMessage}
              onChange={(e) => setCoreMessage(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Moraleja / Solución (30-50s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">✨ Moraleja / Solución propuesta:</label>
            <textarea
              rows={2}
              value={moraleja}
              onChange={(e) => setMoraleja(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-medium"
            />
          </div>

          {/* Llamado a la Acción (CTA 50-60s) */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">📣 Llamado a la Acción (CTA):</label>
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
