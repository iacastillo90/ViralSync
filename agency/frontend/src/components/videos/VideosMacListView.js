"use client";

import { Video, Play, Download, CheckCircle, XCircle, CheckSquare, Square, Package, Wrench, Calendar } from "lucide-react";

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
 * VideosMacListView
 * Componente de vista en lista detallada lineal estilo macOS Finder para Videos.
 * Muestra las publicaciones en filas compactas de 1 línea con detalles de producto, duración, estado y acciones rápidas.
 */
export function VideosMacListView({
  videos = [],
  selectedIds = [],
  onToggleSelect,
  onPlayVideo,
  onApprove,
  onReject,
  onDownload,
}) {
  if (videos.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-2">
        <Video className="w-8 h-8 text-slate-600 mx-auto" />
        <p className="text-xs text-slate-400">No hay videos en el listado.</p>
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
              <th className="px-4 py-2.5 font-semibold">Video / Publicación</th>
              <th className="px-3 py-2.5 font-semibold">Producto / Servicio</th>
              <th className="px-3 py-2.5 font-semibold text-center">Estado</th>
              <th className="px-3 py-2.5 font-semibold text-center">Duración</th>
              <th className="px-3 py-2.5 font-semibold">Fecha y Hora</th>
              <th className="px-4 py-2.5 font-semibold text-right">Acciones Rápidas</th>
            </tr>
          </thead>

          {/* Cuerpo de Filas Delgadas estilo Finder */}
          <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
            {videos.map((vid) => {
              const isSelected = selectedIds.includes(vid.id);
              const title = vid.title || vid.cta_50_60s || "Reel 9:16 Renderizado";
              const productName = vid.product_name || vid.service_name || vid.category || "Producto de Campaña";
              const isService = Boolean(vid.service_name || vid.is_service);
              const isApproved = vid.status === "approved" || vid.approved;
              // Insignia de variante (FASE-4): distingue la fila `videos` elegida por provider.
              const variantLabel =
                vid.source === "json2video"
                  ? "☁️ Json2Video"
                  : vid.source === "local"
                  ? "🎬 Local"
                  : vid.video_url
                  ? "🎬 Local"
                  : "⏳ Sin render";
              const variantCls =
                vid.source === "json2video"
                  ? "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                  : vid.source === "local"
                  ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/40"
                  : "bg-slate-950/60 text-slate-400 border-slate-600/40";

              return (
                <tr
                  key={vid.id}
                  className={`hover:bg-slate-900/80 transition-colors group ${
                    isSelected ? "bg-indigo-950/30 text-indigo-200" : "text-slate-300"
                  }`}
                >
                  {/* Casilla de Selección */}
                  <td className="px-3 py-2.5 text-center">
                    <button
                      onClick={() => onToggleSelect(vid.id)}
                      className="text-slate-500 hover:text-indigo-400 transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-700 group-hover:text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Título / Publicación */}
                  <td className="px-4 py-2.5 font-medium max-w-md truncate">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onPlayVideo(vid)}
                        className="p-1 rounded bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all shrink-0"
                        title="Reproducir Video"
                      >
                        <Play className="w-3 h-3 fill-current" />
                      </button>
                      <span className="truncate group-hover:text-indigo-300 transition-colors font-semibold">
                        "{title}"
                      </span>
                    </div>
                  </td>

                  {/* Producto o Servicio Dinámico */}
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
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

                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold inline-flex items-center gap-1 ${variantCls}`}
                      >
                        {variantLabel}
                      </span>
                    </div>
                  </td>

                  {/* Estado */}
                  <td className="px-3 py-2.5 text-center whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold ${
                        isApproved
                          ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                          : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                      }`}
                    >
                      {isApproved ? "✓ Aprobado" : "⏳ Pendiente"}
                    </span>
                  </td>

                  {/* Duración */}
                  <td className="px-3 py-2.5 text-center font-mono text-[11px] text-slate-400 whitespace-nowrap">
                    {vid.duration || 30}s
                  </td>

                  {/* Fecha y Hora */}
                  <td className="px-3 py-2.5 whitespace-nowrap text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(vid.created_at)}</span>
                    </div>
                  </td>

                  {/* Acciones Rápidas */}
                  <td className="px-4 py-2.5 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => onApprove(vid)}
                        className="px-2.5 py-1 rounded bg-emerald-600/90 hover:bg-emerald-500 text-white font-bold text-[10px] shadow transition-all flex items-center gap-1"
                      >
                        <CheckCircle className="w-3 h-3" />
                        <span>Aprobar</span>
                      </button>

                      <button
                        onClick={() => onReject(vid)}
                        className="p-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-500/30 transition-all"
                        title="Rechazar"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                      </button>

                      {vid.video_url && (
                        <a
                          href={vid.video_url}
                          download={`video_${vid.id}.mp4`}
                          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
                          title="Descargar MP4"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
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
