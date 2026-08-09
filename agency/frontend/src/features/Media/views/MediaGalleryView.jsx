"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import {
  Film,
  Play,
  Download,
  Trash2,
  Image as ImageIcon,
  CheckCircle2,
  X,
  Sparkles,
  RefreshCw,
  FolderOpen,
} from "lucide-react";

export function MediaGalleryView({ tenantId }) {
  const { data: mediaItems, loading, error } = useTenantResource("media", tenantId);
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all"); // "all", "video", "image"
  const [selectedMedia, setSelectedMedia] = useState(null); // for video modal player
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  // Update local list when hook data arrives
  const displayItems = (items.length > 0 ? items : (Array.isArray(mediaItems) ? mediaItems : []))
    .filter((item) => filter === "all" || item.type === filter);

  const handleDownload = (item) => {
    // Force download of the file
    const link = document.createElement("a");
    link.href = item.url;
    link.download = item.filename || "media_file";
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setToastMessage(`Descargando ${item.filename}...`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleDelete = async (itemId) => {
    setDeletingId(itemId);
    try {
      await fetchWithTenant(`/tenants/${tenantId}/media/${itemId}`, { method: "DELETE" }, tenantId);
      const updated = (items.length > 0 ? items : (Array.isArray(mediaItems) ? mediaItems : []))
        .filter((m) => m.id !== itemId);
      setItems(updated);
      setToastMessage("Archivo eliminado de MinIO exitosamente.");
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      console.error("Error al borrar elemento multimedia:", err);
    } finally {
      setDeletingId(null);
      setDeleteConfirmId(null);
    }
  };

  return (
    <div className="space-y-6">
          {/* Header de la Vista */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Film className="w-5 h-5 text-indigo-400" /> Galería de Videos & Multimedia (MinIO S3)
              </h1>
              <p className="text-xs text-slate-400">
                Visualiza, reproduce, descarga y gestiona todos los reels producidos y fotos de productos guardadas en MinIO Storage.
              </p>
            </div>

            {/* Filtros de Tipo */}
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl">
              <button
                onClick={() => setFilter("all")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  filter === "all" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Todos
              </button>
              <button
                onClick={() => setFilter("video")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                  filter === "video" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Film className="w-3.5 h-3.5" /> Videos MP4
              </button>
              <button
                onClick={() => setFilter("image")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                  filter === "image" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5" /> Imágenes
              </button>
            </div>
          </div>

          {/* Toast Notification */}
          {toastMessage && (
            <div className="p-3 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-300 text-xs flex items-center gap-2 animate-fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{toastMessage}</span>
            </div>
          )}

          {/* Estado de Carga */}
          {loading && items.length === 0 && (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/50 border border-slate-800/80 rounded-2xl">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mb-3" />
              <p className="text-sm font-medium text-slate-300">Cargando galería multimedia desde MinIO...</p>
            </div>
          )}

          {/* Estado Vacío */}
          {!loading && displayItems.length === 0 && (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center">
              <FolderOpen className="w-12 h-12 text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-slate-300">Sin archivos multimedia aún</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">
                Sube la foto de tu producto en el panel principal o genera un Reel con IA para ver tus videos aquí.
              </p>
              <a
                href="/"
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-medium transition-all shadow-lg shadow-indigo-600/30 flex items-center gap-1.5"
              >
                <Sparkles className="w-4 h-4" /> Crear Nuevo Reel
              </a>
            </div>
          )}

          {/* Grid de Archivos Multimedia */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {displayItems.map((item) => (
              <div
                key={item.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-slate-700 transition-all flex flex-col group shadow-lg"
              >
                {/* Previsualización del Media */}
                <div className="relative aspect-video bg-slate-950 flex items-center justify-center overflow-hidden">
                  {item.type === "video" ? (
                    <div className="relative w-full h-full flex items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950">
                      <video
                        src={item.url}
                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                        preload="metadata"
                      />
                      <button
                        onClick={() => setSelectedMedia(item)}
                        className="absolute bg-indigo-600/90 hover:bg-indigo-500 text-white p-3 rounded-full shadow-xl shadow-indigo-600/50 backdrop-blur-sm transition-all hover:scale-110"
                        title="Reproducir Video"
                      >
                        <Play className="w-6 h-6 fill-current ml-0.5" />
                      </button>
                      <span className="absolute top-2 left-2 bg-indigo-950/80 border border-indigo-500/30 text-indigo-300 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full backdrop-blur-sm flex items-center gap-1">
                        <Film className="w-3 h-3" /> VIDEO MP4
                      </span>
                    </div>
                  ) : (
                    <div className="relative w-full h-full">
                      <img
                        src={item.url}
                        alt={item.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                      <span className="absolute top-2 left-2 bg-slate-950/80 border border-slate-700 text-slate-300 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full backdrop-blur-sm flex items-center gap-1">
                        <ImageIcon className="w-3 h-3" /> FOTO PRODUCTO
                      </span>
                    </div>
                  )}
                </div>

                {/* Información del Objeto */}
                <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <h3 className="font-semibold text-sm text-slate-200 line-clamp-1 group-hover:text-indigo-400 transition-colors">
                      {item.title || item.filename}
                    </h3>
                    <p className="text-[11px] font-mono text-slate-500 truncate mt-0.5">
                      {item.object_key}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-2.5">
                    <span>{(item.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                    <span className="font-mono text-slate-500">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Acciones: Ver / Descargar / Borrar */}
                  <div className="flex items-center gap-2 pt-1">
                    {item.type === "video" && (
                      <button
                        onClick={() => setSelectedMedia(item)}
                        className="flex-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 py-1.5 px-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1 transition-all"
                      >
                        <Play className="w-3.5 h-3.5" /> Ver
                      </button>
                    )}

                    <button
                      onClick={() => handleDownload(item)}
                      className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 py-1.5 px-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1 transition-all"
                      title="Descargar archivo"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-400" /> Descargar
                    </button>

                    <button
                      onClick={() => setDeleteConfirmId(item.id)}
                      className="p-1.5 bg-red-950/40 hover:bg-red-900/60 text-red-400 border border-red-500/20 rounded-lg text-xs transition-all"
                      title="Eliminar de MinIO"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Modal Reproductor de Video MP4 */}
          {selectedMedia && (
            <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-5 space-y-4 shadow-2xl relative">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Film className="w-5 h-5 text-indigo-400" />
                    <h3 className="font-bold text-base text-slate-100">{selectedMedia.title}</h3>
                  </div>
                  <button
                    onClick={() => setSelectedMedia(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="aspect-video bg-black rounded-xl overflow-hidden shadow-inner flex items-center justify-center">
                  <video
                    controls
                    autoPlay
                    src={selectedMedia.url}
                    className="w-full h-full object-contain"
                  />
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800">
                  <span className="font-mono text-slate-500">Key: {selectedMedia.object_key}</span>
                  <button
                    onClick={() => handleDownload(selectedMedia)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-3.5 py-1.5 rounded-lg font-medium flex items-center gap-1.5 transition-all shadow-md shadow-emerald-600/30"
                  >
                    <Download className="w-4 h-4" /> Descargar Video MP4
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Modal de Confirmación de Borrado */}
          {deleteConfirmId && (
            <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
                <div className="flex items-center gap-3 text-red-400">
                  <Trash2 className="w-6 h-6" />
                  <h3 className="font-bold text-lg text-slate-100">¿Eliminar archivo de MinIO?</h3>
                </div>
                <p className="text-xs text-slate-400">
                  Esta acción eliminará permanentemente el archivo del bucket de MinIO Storage. Esta operación no se puede deshacer.
                </p>
                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => setDeleteConfirmId(null)}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:bg-slate-800 transition-all"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => handleDelete(deleteConfirmId)}
                    disabled={deletingId === deleteConfirmId}
                    className="px-4 py-2 rounded-xl text-xs font-medium bg-red-600 hover:bg-red-500 text-white transition-all shadow-lg shadow-red-600/30 disabled:opacity-50"
                  >
                    {deletingId === deleteConfirmId ? "Eliminando..." : "Sí, Eliminar de MinIO"}
                  </button>
                </div>
              </div>
            </div>
          )}
    </div>
  );
}
