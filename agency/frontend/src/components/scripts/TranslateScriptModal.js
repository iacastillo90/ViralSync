"use client";

import { useState } from "react";
import { X, Globe, Loader2, Check } from "lucide-react";

/**
 * TranslateScriptModal
 * Componente atómico de modal para traducir guiones a múltiples idiomas (Inglés, Portugués, Francés, Alemán)
 * utilizando el servicio de traducción de IA del backend.
 */
export function TranslateScriptModal({ script, isOpen, onClose, onTranslate, isTranslating }) {
  const [selectedLang, setSelectedLang] = useState("en");

  if (!isOpen || !script) return null;

  const languages = [
    { code: "en", label: "Inglés (English)", flag: "🇺🇸" },
    { code: "pt", label: "Portugués (Português)", flag: "🇧🇷" },
    { code: "fr", label: "Francés (Français)", flag: "🇫🇷" },
    { code: "de", label: "Alemán (Deutsch)", flag: "🇩🇪" },
    { code: "es", label: "Español (Re-adaptar)", flag: "🇪🇸" },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    onTranslate(script, selectedLang);
  };

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden animate-fadeIn space-y-4 p-6">
        {/* Cabecera del Modal */}
        <div className="flex justify-between items-center pb-3 border-b border-slate-800">
          <h3 className="font-bold text-slate-100 flex items-center gap-2 text-base">
            <Globe className="w-5 h-5 text-indigo-400" /> Traducir Guion Multilingüe
          </h3>
          <button
            onClick={onClose}
            disabled={isTranslating}
            className="text-slate-400 hover:text-slate-100 bg-slate-800 p-1.5 rounded-xl border border-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          La Inteligencia Artificial adaptará culturalmente los 4 bloques narrativos (Gancho, Contexto, Moraleja y CTA) al idioma de tu público objetivo:
        </p>

        {/* Selección de Idiomas */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-2 text-xs font-semibold">
            {languages.map((lang) => (
              <label
                key={lang.code}
                className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                  selectedLang === lang.code
                    ? "bg-indigo-950/70 border-indigo-500 text-indigo-200 shadow-md ring-1 ring-indigo-500/30"
                    : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">{lang.flag}</span>
                  <span>{lang.label}</span>
                </div>
                <input
                  type="radio"
                  name="language"
                  value={lang.code}
                  checked={selectedLang === lang.code}
                  onChange={(e) => setSelectedLang(e.target.value)}
                  className="accent-indigo-500"
                />
              </label>
            ))}
          </div>

          {/* Botones de Acción */}
          <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isTranslating}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isTranslating}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs shadow-lg flex items-center gap-1.5 transition-all disabled:opacity-50"
            >
              {isTranslating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" /> Traduciendo...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" /> Traducir Ahora
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
