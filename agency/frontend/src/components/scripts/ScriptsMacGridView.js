"use client";

import {
  FileText,
  Edit3,
  Trash2,
  Download,
  Video,
  Clock,
  CheckSquare,
  Square,
  Package,
  Wrench,
  Calendar,
  Globe,
} from "lucide-react";

/**
 * Formateador de fecha y hora pequeña (DD/MM/YYYY HH:mm)
 */
function formatDateTime(isoString) {
  if (!isoString) return "Fecha N/A";
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (e) {
    return isoString;
  }
}

/**
 * Helper para detectar el idioma del guion y retornar bandera e insignia
 */
function getLanguageInfo(script) {
  const kw = (script.keyword || "").toUpperCase();
  const hook = script.gancho_0_5s || script.title || "";

  if (kw.includes("LANG:DE") || kw.includes("GERMAN") || hook.includes("[Alemán") || hook.includes("[German")) {
    return { label: "Alemán", flag: "🇩🇪", badgeClass: "bg-amber-950/80 text-amber-300 border-amber-500/40" };
  }
  if (kw.includes("LANG:EN") || kw.includes("ENGLISH") || hook.includes("[Inglés") || hook.includes("[English")) {
    return { label: "Inglés", flag: "🇺🇸", badgeClass: "bg-blue-950/80 text-blue-300 border-blue-500/40" };
  }
  if (kw.includes("LANG:FR") || kw.includes("FRENCH") || hook.includes("[Francés") || hook.includes("[French")) {
    return { label: "Francés", flag: "🇫🇷", badgeClass: "bg-purple-950/80 text-purple-300 border-purple-500/40" };
  }
  if (kw.includes("LANG:PT") || kw.includes("PORTUGUESE") || hook.includes("[Portugués") || hook.includes("[Portuguese")) {
    return { label: "Portugués", flag: "🇧🇷", badgeClass: "bg-emerald-950/80 text-emerald-300 border-emerald-500/40" };
  }
  return { label: "Español (Original)", flag: "🇪🇸", badgeClass: "bg-indigo-950/80 text-indigo-300 border-indigo-500/40" };
}

/**
 * ScriptsMacGridView
 * Componente atómico de vista en cuadrícula (Grid Iconos) estilo macOS Finder para Guiones.
 * Despliega los guiones en tarjetas estructuradas en 4 bloques narrativos (Gancho, Contexto, Moraleja, CTA).
 */
export function ScriptsMacGridView({
  scripts = [],
  selectedIds = [],
  onToggleSelect,
  onEdit,
  onDelete,
  onDownload,
  onTranslate,
  onViewPrompts,
  onRenderVideo,
  onSelectFolder,
}) {
  if (scripts.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-12 text-center space-y-3">
        <FileText className="w-12 h-12 text-slate-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-300">No se encontraron guiones</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          No hay guiones virales registrados que coincidan con los filtros aplicados.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      {scripts.map((script) => {
        const isSelected = selectedIds.includes(script.id);
        const title = script.title || script.gancho_0_5s || "Guion Viral 9:16";
        const productName =
          script.product_name ||
          script.service_name ||
          script.category ||
          "Producto de Campaña";

        const isService = Boolean(script.service_name || script.is_service);
        const createdAtFormatted = formatDateTime(script.created_at);
        const targetDuration = script.target_duration || script.estimated_duration || 30;
        const langInfo = getLanguageInfo(script);

        return (
          <div
            key={script.id}
            className={`group bg-slate-900/95 border rounded-2xl p-5 shadow-xl backdrop-blur-md flex flex-col justify-between transition-all relative overflow-hidden space-y-3 ${
              isSelected
                ? "border-indigo-500 ring-2 ring-indigo-500/30 bg-slate-900"
                : "border-slate-800/80 hover:border-slate-700 hover:shadow-2xl"
            }`}
          >
            {/* Cabecera Ventana macOS (Puntos 🔴 🟡 🟢 + Insignia de Idioma + Checkbox) */}
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 group-hover:bg-rose-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 group-hover:bg-amber-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 group-hover:bg-emerald-500 transition-colors"></span>
              </div>

              {/* Insignia de Idioma */}
              <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold flex items-center gap-1 shadow-sm ${langInfo.badgeClass}`}>
                <span>{langInfo.flag}</span>
                <span>{langInfo.label}</span>
              </span>

              {/* Checkbox de Selección */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleSelect(script.id);
                }}
                className="text-slate-400 hover:text-indigo-400 transition-colors"
                title="Seleccionar guion"
              >
                {isSelected ? (
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600 group-hover:text-slate-400" />
                )}
              </button>
            </div>

            {/* Insignias de Producto/Servicio, Duración y Fecha/Hora */}
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectFolder) onSelectFolder(productName);
                  }}
                  className="bg-indigo-950/70 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-lg text-[10px] font-bold font-mono uppercase flex items-center gap-1.5 truncate max-w-[70%] hover:bg-indigo-900/80 hover:border-indigo-400 cursor-pointer transition-colors"
                >
                  {isService ? (
                    <Wrench className="w-3 h-3 text-amber-400 shrink-0" />
                  ) : (
                    <Package className="w-3 h-3 text-indigo-400 shrink-0" />
                  )}
                  <span className="truncate">{productName}</span>
                </span>

                <span className="bg-amber-950/40 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-md text-[10px] font-mono flex items-center gap-1 shrink-0 font-bold">
                  <Clock className="w-3 h-3 text-amber-400" /> ~{targetDuration}s
                </span>
              </div>

              <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400">
                <Calendar className="w-3 h-3 text-slate-500" />
                <span>{createdAtFormatted}</span>
              </div>
            </div>

            {/* Estructura Narrativa en 4 Bloques (Gancho, Contexto, Moraleja, CTA) */}
            <div className="space-y-2 py-1 flex-1 text-xs">
              {/* Bloque 1: Gancho Viral (0-5s) */}
              <div className="bg-indigo-950/60 border border-indigo-500/40 p-2.5 rounded-xl space-y-0.5">
                <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider block">
                  🪝 Bloque 1: Gancho Viral (0-5s)
                </span>
                <p className="text-slate-100 font-semibold leading-snug">
                  "{script.gancho_0_5s || title}"
                </p>
              </div>

              {/* Bloque 2: Contexto & Problema (5-30s) */}
              {script.contexto_5_30s && (
                <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded-xl space-y-0.5">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    💡 Bloque 2: Contexto & Desarrollo (5-30s)
                  </span>
                  <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-3">
                    {script.contexto_5_30s}
                  </p>
                </div>
              )}

              {/* Bloque 3: Moraleja & Solución (30-50s) */}
              {script.moraleja_30_50s && (
                <div className="bg-slate-950/60 border border-slate-800 p-2.5 rounded-xl space-y-0.5">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    ✨ Bloque 3: Moraleja / Solución (30-50s)
                  </span>
                  <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-2">
                    {script.moraleja_30_50s}
                  </p>
                </div>
              )}

              {/* Bloque 4: Llamado a la Acción / CTA (50-60s) */}
              {script.cta_50_60s && (
                <div className="bg-emerald-950/40 border border-emerald-500/30 p-2.5 rounded-xl space-y-0.5">
                  <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider block">
                    📣 Bloque 4: Llamado a la Acción (CTA)
                  </span>
                  <p className="text-emerald-200 text-[11px] font-medium leading-snug">
                    {script.cta_50_60s}
                  </p>
                </div>
              )}
            </div>

            {/* Pie de la Tarjeta Mac: Acciones Rápidas */}
            <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between gap-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onEdit(script)}
                  title="Editar guion y recalcular tiempo"
                  className="p-1.5 bg-slate-950 hover:bg-indigo-950 text-slate-300 hover:text-indigo-300 border border-slate-800 rounded-lg text-xs transition-colors flex items-center gap-1 font-bold"
                >
                  <Edit3 className="w-3.5 h-3.5" /> Editar
                </button>
                <button
                  onClick={() => onDownload(script)}
                  title="Descargar Guion en TXT/JSON"
                  className="p-1.5 bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-slate-100 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDelete(script.id)}
                  title="Eliminar guion"
                  className="p-1.5 bg-slate-950 hover:bg-rose-950 text-slate-400 hover:text-rose-300 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Botones de Acción Principal: Prompts IA, Traducir & Renderizar Video */}
              <div className="flex items-center gap-1.5">
                {onViewPrompts && (
                  <button
                    onClick={() => onViewPrompts(script)}
                    className="bg-slate-950 hover:bg-indigo-950 text-indigo-300 border border-slate-800 hover:border-indigo-500/50 text-[11px] font-bold px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-all"
                    title="Ver desglose de Prompts de Video IA por escenas de 5s"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Prompts IA
                  </button>
                )}

                {onTranslate && (
                  <button
                    onClick={() => onTranslate(script)}
                    className="bg-slate-950 hover:bg-indigo-950 text-indigo-300 border border-slate-800 hover:border-indigo-500/50 text-[11px] font-bold px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-all"
                    title="Traducir guion a otro idioma (Inglés, Portugués, Francés, Alemán)"
                  >
                    <Globe className="w-3.5 h-3.5 text-indigo-400" /> Traducir
                  </button>
                )}

                {onRenderVideo && (
                  <button
                    onClick={() => onRenderVideo(script)}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-md transition-all"
                  >
                    <Video className="w-3.5 h-3.5" /> Renderizar
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
