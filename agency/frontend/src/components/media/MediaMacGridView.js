"use client";

import { Film, Play, Download, Trash2, Image as ImageIcon, CheckSquare, Square, Package, Wrench } from "lucide-react";

/**
 * MediaMacGridView
 * Componente de vista en cuadrícula (Grid Iconos) estilo macOS Finder para Galería de Media.
 * Despliega archivos multimedia (videos 9:16 e imágenes de producto) en tarjetas con vista previa y acciones de reproductor/descarga.
 */
export function MediaMacGridView({
  mediaItems = [],
  selectedIds = [],
  onToggleSelect,
  onOpenPreview,
  onDelete,
  onDownload,
}) {
  if (mediaItems.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-12 text-center space-y-3">
        <Film className="w-12 h-12 text-slate-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-300">No se encontraron archivos multimedia</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          No hay videos renderizados o imágenes guardadas en este lote.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
      {mediaItems.map((item) => {
        const isSelected = selectedIds.includes(item.id);
        const isVideo = item.media_type === "video" || item.url?.includes(".mp4") || item.type === "video";
        const title = item.title || item.name || (isVideo ? "Reel 9:16 Renderizado" : "Imagen de Producto");
        const productName = item.product_name || item.service_name || "Producto de Campaña";
        const isService = Boolean(item.service_name || item.is_service);

        return (
          <div
            key={item.id}
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

              {/* Insignia de Formato */}
              <span
                className={`px-2 py-0.5 rounded border text-[10px] font-mono font-bold flex items-center gap-1 ${
                  isVideo
                    ? "bg-indigo-950/80 text-indigo-300 border-indigo-500/40"
                    : "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                }`}
              >
                {isVideo ? <Film className="w-3 h-3 text-indigo-400" /> : <ImageIcon className="w-3 h-3 text-emerald-400" />}
                <span>{isVideo ? "Video 9:16" : "Imagen"}</span>
              </span>

              {/* Checkbox de Selección */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleSelect(item.id);
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

            {/* Contenedor de Preview */}
            <div className="relative aspect-[9/16] bg-slate-950 rounded-xl overflow-hidden border border-slate-800/80 group-hover:border-indigo-500/40 transition-all flex items-center justify-center">
              {isVideo ? (
                <video
                  src={item.url || item.video_url}
                  poster={item.thumbnail_url}
                  className="w-full h-full object-cover"
                  muted
                  loop
                  playsInline
                />
              ) : (
                <img
                  src={item.url || item.image_url}
                  alt={title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              )}

              {/* Overlay Interactivo */}
              <button
                onClick={() => onOpenPreview(item)}
                className="absolute inset-0 bg-slate-950/40 hover:bg-slate-950/20 backdrop-blur-[2px] transition-all flex items-center justify-center group/btn"
              >
                <div className="w-12 h-12 rounded-full bg-indigo-600/90 text-white flex items-center justify-center shadow-lg group-hover/btn:scale-110 group-hover/btn:bg-indigo-500 transition-all">
                  {isVideo ? <Play className="w-5 h-5 ml-0.5 fill-current" /> : <ImageIcon className="w-5 h-5" />}
                </div>
              </button>
            </div>

            {/* Título y Producto */}
            <div className="space-y-1.5 pt-1">
              <h3 className="text-xs font-bold text-slate-100 line-clamp-2 leading-snug">
                "{title}"
              </h3>

              <div className="flex items-center justify-between pt-1">
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
              </div>
            </div>

            {/* Botones de Acción Inmediata (Ver / Descargar / Eliminar) */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60">
              <button
                onClick={() => onOpenPreview(item)}
                className="flex-1 py-1.5 rounded-lg bg-indigo-600/90 hover:bg-indigo-500 text-white font-bold text-[11px] flex items-center justify-center gap-1 shadow transition-all"
              >
                <span>{isVideo ? "Reproducir" : "Ver Imagen"}</span>
              </button>

              {onDownload && (
                <a
                  href={item.url || item.video_url || item.image_url}
                  download={`media_${item.id}`}
                  className="py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[11px] flex items-center justify-center transition-all"
                  title="Descargar archivo"
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              )}

              {onDelete && (
                <button
                  onClick={() => onDelete(item.id)}
                  className="py-1.5 px-2.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-500/30 font-bold text-[11px] flex items-center justify-center transition-all"
                  title="Eliminar archivo"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
