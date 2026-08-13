"use client";

import { Film, Play, Download, Trash2, Image as ImageIcon, CheckSquare, Square, Package, Wrench, Calendar } from "lucide-react";

/**
 * Formateador de fecha corta
 */
function formatDate(isoString) {
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
 * MediaMacListView
 * Componente de vista en lista detallada lineal estilo macOS Finder para Galería de Media.
 * Muestra los archivos multimedia en filas compactas de 1 línea con formato, producto, fecha/hora y acciones rápidas.
 */
export function MediaMacListView({
  mediaItems = [],
  selectedIds = [],
  onToggleSelect,
  onOpenPreview,
  onDelete,
  onDownload,
}) {
  if (mediaItems.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-2">
        <Film className="w-8 h-8 text-slate-600 mx-auto" />
        <p className="text-xs text-slate-400">No hay archivos multimedia en el listado.</p>
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
              <th className="px-4 py-2.5 font-semibold">Archivo / Asset</th>
              <th className="px-3 py-2.5 font-semibold">Formato</th>
              <th className="px-3 py-2.5 font-semibold">Producto / Servicio</th>
              <th className="px-3 py-2.5 font-semibold">Fecha y Hora</th>
              <th className="px-4 py-2.5 font-semibold text-right">Acciones Rápidas</th>
            </tr>
          </thead>

          {/* Cuerpo de Filas Delgadas estilo Finder */}
          <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
            {mediaItems.map((item) => {
              const isSelected = selectedIds.includes(item.id);
              const isVideo = item.media_type === "video" || item.url?.includes(".mp4") || item.type === "video";
              const title = item.title || item.name || (isVideo ? "Reel 9:16 Renderizado" : "Imagen de Producto");
              const productName = item.product_name || item.service_name || "Producto de Campaña";
              const isService = Boolean(item.service_name || item.is_service);

              return (
                <tr
                  key={item.id}
                  className={`hover:bg-slate-900/80 transition-colors group ${
                    isSelected ? "bg-indigo-950/30 text-indigo-200" : "text-slate-300"
                  }`}
                >
                  {/* Casilla de Selección */}
                  <td className="px-3 py-2.5 text-center">
                    <button
                      onClick={() => onToggleSelect(item.id)}
                      className="text-slate-500 hover:text-indigo-400 transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-700 group-hover:text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Título / Asset */}
                  <td className="px-4 py-2.5 font-medium max-w-md truncate">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onOpenPreview(item)}
                        className="p-1 rounded bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all shrink-0"
                        title="Ver Preview"
                      >
                        {isVideo ? <Play className="w-3 h-3 fill-current" /> : <ImageIcon className="w-3 h-3" />}
                      </button>
                      <span className="truncate group-hover:text-indigo-300 transition-colors font-semibold">
                        "{title}"
                      </span>
                    </div>
                  </td>

                  {/* Formato */}
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold inline-flex items-center gap-1 ${
                        isVideo
                          ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/40"
                          : "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                      }`}
                    >
                      {isVideo ? <Film className="w-3 h-3 text-indigo-400" /> : <ImageIcon className="w-3 h-3 text-emerald-400" />}
                      <span>{isVideo ? "Video MP4" : "Imagen JPG"}</span>
                    </span>
                  </td>

                  {/* Producto o Servicio Dinámico */}
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold inline-flex items-center gap-1 ${
                        isService
                          ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                          : "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                      }`}
                    >
                      {isService ? <Wrench className="w-3 h-3 text-amber-400" /> : <Package className="w-3 h-3 text-indigo-400" />}
                      <span>{productName}</span>
                    </span>
                  </td>

                  {/* Fecha y Hora */}
                  <td className="px-3 py-2.5 whitespace-nowrap text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                  </td>

                  {/* Acciones Rápidas */}
                  <td className="px-4 py-2.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onOpenPreview(item)}
                        className="px-2.5 py-1 rounded bg-indigo-600/90 hover:bg-indigo-500 text-white font-bold text-[10px] shadow transition-all flex items-center gap-1"
                      >
                        <span>{isVideo ? "Reproducir" : "Ver"}</span>
                      </button>

                      {onDownload && (
                        <a
                          href={item.url || item.video_url || item.image_url}
                          download={`media_${item.id}`}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
                          title="Descargar"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                      )}

                      {onDelete && (
                        <button
                          onClick={() => onDelete(item.id)}
                          className="p-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-500/30 transition-all"
                          title="Eliminar"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
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
