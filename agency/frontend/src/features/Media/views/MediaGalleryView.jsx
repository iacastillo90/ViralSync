"use client";

import { useState, useEffect } from "react";
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
  Folder,
  ArrowLeft,
} from "lucide-react";

export function MediaGalleryView({ tenantId }) {
  const { data: mediaItems, loading, error, refresh } = useTenantResource("media", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);

  // Polling automático cada 4 segundos para detectar nuevos videos renderizados
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 4000);
    return () => clearInterval(interval);
  }, [refresh]);
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all"); // "all", "video", "image"
  const [selectedMedia, setSelectedMedia] = useState(null); // for video modal player
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [activeFolder, setActiveFolder] = useState(null);

  const rawItems = items.length > 0 ? items : (Array.isArray(mediaItems) ? mediaItems : []);
  const products = Array.isArray(productsData) ? productsData : [];

  // Formateador de fecha y hora pequeña
  const formatDate = (isoString) => {
    if (!isoString) return "";
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
  };

  // Emparejar cada archivo multimedia (foto o video) con su producto correspondiente por orden de creación de campaña
  const findProductForMedia = (itemCreatedAt) => {
    if (!products || products.length === 0) return null;
    if (!itemCreatedAt) return products[0];

    const itemTime = new Date(itemCreatedAt).getTime();
    const sortedProducts = [...products].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );

    let matched = sortedProducts[0];
    for (const prod of sortedProducts) {
      const prodTime = new Date(prod.created_at).getTime();
      // Asignar al último producto creado antes o cercano al archivo multimedia
      if (prodTime <= itemTime + 15000) {
        matched = prod;
      }
    }
    return matched;
  };

  // Agrupar archivos en carpetas unificadas por Nombre de Producto (1 sola carpeta por producto con todos sus Reels versionados)
  const groupedMediaMap = rawItems.reduce((acc, item) => {
    const matchedProduct = findProductForMedia(item.created_at);
    const productName = matchedProduct ? matchedProduct.name : "Archivos de Producto";
    const folderKey = `prod_${productName.replace(/\s+/g, "_").toLowerCase()}`;
    const itemFormattedDate = formatDate(item.created_at);

    if (!acc[folderKey]) {
      acc[folderKey] = {
        key: folderKey,
        name: productName,
        createdAt: itemFormattedDate,
        rawTime: item.created_at ? new Date(item.created_at).getTime() : 0,
        items: [],
      };
    } else {
      if (item.created_at) {
        const itemTime = new Date(item.created_at).getTime();
        if (itemTime > acc[folderKey].rawTime) {
          acc[folderKey].rawTime = itemTime;
          acc[folderKey].createdAt = itemFormattedDate;
        }
      }
    }

    if (item.type === "image") {
      const alreadyHasImage = acc[folderKey].items.some(
        (i) => i.type === "image" && i.filename === item.filename
      );
      if (!alreadyHasImage) {
        acc[folderKey].items.push(item);
      }
    } else {
      acc[folderKey].items.push(item);
    }

    return acc;
  }, {});

  // Ordenar carpetas y elementos por fecha de creación descendente (los más recientes primero)
  const folderList = Object.values(groupedMediaMap).sort((a, b) => b.rawTime - a.rawTime);
  folderList.forEach((folder) => {
    folder.items.sort(
      (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    );
  });

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
          {loading && rawItems.length === 0 && (
            <div className="flex flex-col items-center justify-center p-12 bg-slate-900/50 border border-slate-800/80 rounded-2xl">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mb-3" />
              <p className="text-sm font-medium text-slate-300">Cargando galería multimedia desde MinIO...</p>
            </div>
          )}

          {/* Estado Vacío */}
          {!loading && rawItems.length === 0 && (
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

          {!activeFolder ? (
            /* VISTA DE CARPETAS DE GALERÍA (FOLDER VIEW) */
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Carpetas de Multimedia por Producto ({folderList.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {folderList.map((folder) => {
                  const videosCount = folder.items.filter((i) => i.type === "video").length;
                  const imagesCount = folder.items.filter((i) => i.type === "image").length;
                  return (
                    <div
                      key={folder.key}
                      onClick={() => setActiveFolder(folder.key)}
                      className="bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-xl hover:shadow-indigo-500/10 group flex items-start gap-4"
                    >
                      <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all">
                        <Folder className="w-6 h-6" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                          {folder.name}
                        </h3>
                        <div className="flex flex-col gap-0.5 mt-1.5">
                          <span className="text-xs text-slate-400 font-medium">
                            {videosCount > 0 && `${videosCount} ${videosCount === 1 ? "Video" : "Videos"}`}
                            {videosCount > 0 && imagesCount > 0 && ", "}
                            {imagesCount > 0 && `${imagesCount} ${imagesCount === 1 ? "Foto" : "Fotos"}`}
                          </span>
                          {folder.createdAt && (
                            <span className="text-[11px] text-indigo-400/80 font-mono">
                              🕒 {folder.createdAt}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* VISTA DE ARCHIVOS DENTRO DE LA CARPETA SELECCIONADA */
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                <button
                  onClick={() => setActiveFolder(null)}
                  className="flex items-center gap-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" /> Volver a Carpetas
                </button>
                <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
                  <FolderOpen className="w-4 h-4 text-indigo-400" /> Carpeta activa: <strong>{groupedMediaMap[activeFolder]?.name}</strong>
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {(groupedMediaMap[activeFolder]?.items || [])
                  .filter((item) => filter === "all" || item.type === filter)
                  .map((item) => (
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
                    <span className="font-mono text-indigo-300 font-semibold flex items-center gap-1">
                      🕒 {formatDate(item.created_at)}
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
            </div>
          )}

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
