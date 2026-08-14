"use client";

import { Video, Play, Download, CheckCircle, XCircle, CheckSquare, Square, Package, Wrench } from "lucide-react";

/**
 * VideosMacGridView
 * Componente de vista en cuadrícula (Grid Iconos) estilo macOS Finder para Videos.
 * Despliega tarjetas de video con controles de ventana, miniatura 9:16 o reproductor, insignias de producto/servicio y acciones de aprobación/rechazo.
 */
export function VideosMacGridView({
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
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-12 text-center space-y-3">
        <Video className="w-12 h-12 text-slate-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-300">No se encontraron videos</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          No hay publicaciones de video registradas que coincidan con los filtros aplicados.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {videos.map((vid) => {
        const isSelected = selectedIds.includes(vid.id);
        const title = vid.title || vid.cta_50_60s || "Reel 9:16 Renderizado";
        const productName = vid.product_name || vid.service_name || vid.category || "Producto de Campaña";
        const isService = Boolean(vid.service_name || vid.is_service);
        const isApproved = vid.status === "approved" || vid.approved;
        const isRejected = vid.status === "rejected";
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
          <div
            key={vid.id}
            className={`group bg-slate-900/95 border rounded-2xl p-4 shadow-xl backdrop-blur-md flex flex-col justify-between transition-all relative overflow-hidden space-y-3 ${
              isSelected
                ? "border-indigo-500 ring-2 ring-indigo-500/30 bg-slate-900"
                : "border-slate-800/80 hover:border-slate-700 hover:shadow-2xl"
            }`}
          >
            {/* Cabecera Ventana macOS (🔴 🟡 🟢 + Checkbox) */}
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 group-hover:bg-rose-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 group-hover:bg-amber-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 group-hover:bg-emerald-500 transition-colors"></span>
              </div>

              {/* Insignia de Estado */}
              <span
                className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold ${
                  isApproved
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                    : isRejected
                    ? "bg-rose-950/80 text-rose-300 border-rose-500/40"
                    : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                }`}
              >
                {isApproved ? "✓ Aprobado" : isRejected ? "✗ Rechazado" : "⏳ Pendiente"}
              </span>

              {/* Checkbox de Selección */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleSelect(vid.id);
                }}
                className="text-slate-400 hover:text-indigo-400 transition-colors"
              >
                {isSelected ? (
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600 group-hover:text-slate-400" />
                )}
              </button>
            </div>

            {/* Contenedor del Preview de Video (Aspecto 9:16) */}
            <div className="relative aspect-[9/16] bg-slate-950 rounded-xl overflow-hidden border border-slate-800/80 group-hover:border-indigo-500/40 transition-all flex items-center justify-center">
              {vid.video_url ? (
                <video
                  src={vid.video_url}
                  poster={vid.thumbnail_url || vid.product_image_url}
                  className="w-full h-full object-cover"
                  muted
                  loop
                  playsInline
                />
              ) : (
                <div className="p-4 text-center space-y-2">
                  <Video className="w-10 h-10 text-indigo-400 mx-auto opacity-70" />
                  <p className="text-[11px] font-medium text-slate-400">Preview Renderizado 9:16</p>
                </div>
              )}

              {/* Overlay Botón Play Reproductor */}
              <button
                onClick={() => onPlayVideo(vid)}
                className="absolute inset-0 bg-slate-950/40 hover:bg-slate-950/20 backdrop-blur-[2px] transition-all flex items-center justify-center group/btn"
              >
                <div className="w-12 h-12 rounded-full bg-indigo-600/90 text-white flex items-center justify-center shadow-lg group-hover/btn:scale-110 group-hover/btn:bg-indigo-500 transition-all">
                  <Play className="w-5 h-5 ml-0.5 fill-current" />
                </div>
              </button>
            </div>

            {/* Metadatos y Producto */}
            <div className="space-y-1.5 pt-1">
              <h3 className="text-xs font-bold text-slate-100 line-clamp-2 leading-snug">
                "{title}"
              </h3>

              <div className="flex items-center justify-between gap-2 pt-1">
                <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      isService
                        ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                        : "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                    }`}
                  >
                    {isService ? <Wrench className="w-3 h-3 text-amber-400" /> : <Package className="w-3 h-3 text-indigo-400" />}
                    <span>{productName}</span>
                  </span>

                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded border shrink-0 ${variantCls}`}
                  >
                    {variantLabel}
                  </span>
                </div>

                <span className="text-[10px] font-mono text-slate-500 shrink-0">
                  {vid.duration || 30}s
                </span>
              </div>
            </div>

            {/* Botones de Acción Inmediata (Aprobar / Rechazar / Descargar) */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60">
              <button
                onClick={() => onApprove(vid)}
                className="flex-1 py-1.5 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center justify-center gap-1 shadow transition-all"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Aprobar</span>
              </button>

              <button
                onClick={() => onReject(vid)}
                className="py-1.5 px-2.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-500/30 font-bold text-[11px] flex items-center justify-center transition-all"
                title="Rechazar publicación"
              >
                <XCircle className="w-3.5 h-3.5" />
              </button>

              {vid.video_url && (
                <a
                  href={vid.video_url}
                  download={`video_${vid.id}.mp4`}
                  className="py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[11px] flex items-center justify-center transition-all"
                  title="Descargar MP4"
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
