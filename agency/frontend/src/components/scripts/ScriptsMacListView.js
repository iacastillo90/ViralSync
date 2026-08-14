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
  Play,
  Sparkles,
} from "lucide-react";

/**
 * Formateador de fecha y hora (DD/MM/YYYY HH:mm)
 */
function formatDateTime(isoString) {
  if (!isoString) return "Reciente";
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
  return { label: "Español", flag: "🇪🇸", badgeClass: "bg-indigo-950/80 text-indigo-300 border-indigo-500/40" };
}

/**
 * ScriptsMacListView
 * Componente atómico de vista en lista detallada lineal estilo macOS Finder para Guiones.
 * Muestra los guiones en filas delgadas de 1 línea, una debajo de otra de forma limpia.
 */
export function ScriptsMacListView({
  scripts = [],
  selectedIds = [],
  onToggleSelect,
  onEdit,
  onDelete,
  onDownload,
  onTranslate,
  onViewPrompts,
  onRenderVideo,
  onViewVideos,
  onSelectFolder,
}) {
  if (scripts.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-2">
        <FileText className="w-8 h-8 text-slate-600 mx-auto" />
        <p className="text-xs text-slate-400">No hay guiones en el listado.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          {/* Cabecera de Columnas Estilo macOS Finder */}
          <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 font-medium select-none">
            <tr>
              <th className="w-10 px-3 py-2.5 text-center">
                <span className="sr-only">Selección</span>
              </th>
              <th className="px-4 py-2.5 font-semibold">Gancho / Título del Guion</th>
              <th className="px-3 py-2.5 font-semibold">Idioma</th>
              <th className="px-3 py-2.5 font-semibold">Producto / Servicio</th>
              <th className="px-3 py-2.5 font-semibold text-center">Duración Est.</th>
              <th className="px-3 py-2.5 font-semibold">Fecha y Hora</th>
              <th className="px-4 py-2.5 font-semibold text-right">Acciones Rápidas</th>
            </tr>
          </thead>

          {/* Cuerpo de Filas Delgadas estilo Finder */}
          <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
            {scripts.map((script) => {
              const isSelected = selectedIds.includes(script.id);
              const title = script.gancho_0_5s || script.title || "Guion Viral 9:16";
              const productName =
                script.product_name ||
                script.service_name ||
                script.category ||
                "Producto de Campaña";

              const isService = Boolean(script.service_name || script.is_service);
              const targetDuration = script.target_duration || script.estimated_duration || 30;
              const dateStr = formatDateTime(script.created_at);
              const langInfo = getLanguageInfo(script);

              return (
                <tr
                  key={script.id}
                  className={`hover:bg-slate-900/80 transition-colors group ${
                    isSelected ? "bg-indigo-950/30 text-indigo-200" : "text-slate-300"
                  }`}
                >
                  {/* Casilla de Selección */}
                  <td className="px-3 py-2.5 text-center">
                    <button
                      onClick={() => onToggleSelect(script.id)}
                      className="text-slate-500 hover:text-indigo-400 transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-700 group-hover:text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Título / Gancho Principal */}
                  <td className="px-4 py-2.5 font-medium max-w-md truncate">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      <span className="truncate group-hover:text-indigo-300 transition-colors font-semibold">
                        "{title}"
                      </span>
                    </div>
                  </td>

                  {/* Insignia de Idioma */}
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold inline-flex items-center gap-1 shadow-sm ${langInfo.badgeClass}`}>
                      <span>{langInfo.flag}</span>
                      <span>{langInfo.label}</span>
                    </span>
                  </td>

                  {/* Producto o Servicio Dinámico */}
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span
                      onClick={() => onSelectFolder && onSelectFolder(productName)}
                      title={`Ver todos los guiones de ${productName}`}
                      className="bg-slate-900 hover:bg-indigo-950 border border-slate-800 hover:border-indigo-500/50 px-2 py-0.5 rounded text-[11px] font-mono text-indigo-300 inline-flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      {isService ? (
                        <Wrench className="w-3 h-3 text-amber-400" />
                      ) : (
                        <Package className="w-3 h-3 text-indigo-400" />
                      )}
                      <span>{productName}</span>
                    </span>
                  </td>

                  {/* Duración Estimada */}
                  <td className="px-3 py-2.5 text-center whitespace-nowrap">
                    <span className="bg-amber-950/40 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-mono font-bold inline-flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-400" /> ~{targetDuration}s
                    </span>
                  </td>

                  {/* Fecha y Hora de Creación */}
                  <td className="px-3 py-2.5 whitespace-nowrap text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      <span>{dateStr}</span>
                    </div>
                  </td>

                  {/* Botones de Acción en Línea */}
                  <td className="px-4 py-2.5 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => onEdit(script)}
                        title="Editar y recalcular tiempo"
                        className="p-1 bg-slate-900 hover:bg-indigo-950 text-slate-400 hover:text-indigo-300 border border-slate-800 rounded-md transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDownload(script)}
                        title="Descargar Guion en TXT/JSON"
                        className="p-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-md transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDelete(script.id)}
                        title="Eliminar guion"
                        className="p-1 bg-slate-900 hover:bg-rose-950 text-slate-400 hover:text-rose-300 border border-slate-800 rounded-md transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      {onViewPrompts && (
                        <button
                          onClick={() => onViewPrompts(script)}
                          title="Ver prompts de video IA desglosados por escenas de 5s"
                          className="bg-slate-900 hover:bg-indigo-950 text-indigo-300 border border-slate-800 hover:border-indigo-500/50 text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1 transition-all ml-1"
                        >
                          <Sparkles className="w-3 h-3 text-amber-400" /> Prompts IA
                        </button>
                      )}

                      {onTranslate && (
                        <button
                          onClick={() => onTranslate(script)}
                          title="Traducir guion a otro idioma"
                          className="bg-slate-900 hover:bg-indigo-950 text-indigo-300 border border-slate-800 hover:border-indigo-500/50 text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1 transition-all ml-1"
                        >
                          <Globe className="w-3 h-3 text-indigo-400" /> Traducir
                        </button>
                      )}

                      {onViewVideos && (
                        <button
                          onClick={() => onViewVideos(script)}
                          title="Ver versiones de video renderizadas (Cloud json2video / Local MoviePy)"
                          className="bg-slate-900 hover:bg-emerald-950 text-emerald-300 border border-slate-800 hover:border-emerald-500/50 text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1 transition-all ml-1"
                        >
                          <Play className="w-3 h-3 text-emerald-400" /> Ver video
                        </button>
                      )}

                      {onRenderVideo && (
                        <button
                          onClick={() => onRenderVideo(script)}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold px-2.5 py-1 rounded-md flex items-center gap-1 shadow transition-all ml-1"
                        >
                          <Video className="w-3 h-3" /> Renderizar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
