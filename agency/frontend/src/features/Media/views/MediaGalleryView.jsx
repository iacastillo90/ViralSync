"use client";

import { useState, useEffect, useMemo } from "react";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { MediaHeaderBar } from "@/components/media/MediaHeaderBar";
import { MediaMacGridView } from "@/components/media/MediaMacGridView";
import { MediaMacListView } from "@/components/media/MediaMacListView";
import {
  Film,
  Image as ImageIcon,
  Loader2,
  FolderOpen,
  ArrowLeft,
  Folder,
  Calendar,
  Wrench,
  Package,
  X,
  Play,
  Download,
  Trash2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

/**
 * Formateador de fecha corta (DD/MM/YYYY HH:mm)
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
 * MediaGalleryView
 * Vista principal de Galería de Media y Assets con interfaz estilo macOS Finder,
 * jerarquía de 2 niveles (Carpetas por Ejecución/Lote -> Archivos Multimedia), vista Iconos/Lista y reproductor/visor modal.
 */
export function MediaGalleryView({ tenantId }) {
  const { data: mediaItems, loading: loadingMedia, error: errorMedia, refresh: refreshMedia } = useTenantResource("media", tenantId);
  const { data: scriptsData, refresh: refreshScripts } = useTenantResource("scripts", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);

  // Función de refresco combinado
  const refresh = () => {
    if (refreshMedia) refreshMedia();
    if (refreshScripts) refreshScripts();
  };

  // Polling automático cada 12s para detectar nuevos renders de forma fluida
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 12000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Estados de interfaz macOS Finder
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"
  const [searchQuery, setSearchQuery] = useState("");
  const [mediaTypeFilter, setMediaTypeFilter] = useState("all"); // "all" | "video" | "image"
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedSort, setSelectedSort] = useState("newest");
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);

  // Modales
  const [previewItem, setPreviewItem] = useState(null);
  const [notification, setNotification] = useState(null);

  const rawItems = Array.isArray(mediaItems) ? mediaItems : [];
  const rawScripts = Array.isArray(scriptsData) ? scriptsData : [];
  const products = Array.isArray(productsData) ? productsData : [];

  // Mapear archivos con datos de productos e incluir guiones como items de video
  const localMedia = useMemo(() => {
    const items = rawItems.map((item) => {
      let pName = item.product_name || item.service_name;
      let isService = Boolean(item.service_name || item.is_service);

      if (!pName && products.length > 0) {
        const prod = products.find((p) => p.id === item.product_id) || products[0];
        if (prod) {
          pName = prod.name;
          isService = Boolean(prod.is_service);
        }
      }

      return {
        ...item,
        product_name: pName || "Producto de Campaña",
        is_service: isService,
        title: item.title || item.name || (item.media_type === "video" || item.type === "video" ? "Reel 9:16 Renderizado" : "Foto de Producto"),
      };
    });

    // Incluir guiones como entradas multimedia de video si no estan presentes
    rawScripts.forEach((s) => {
      const alreadyIncluded = items.some((m) => m.id === s.id || (m.filename && m.filename.includes(s.id)));
      if (!alreadyIncluded) {
        let pName = s.product_name || s.service_name || s.category;
        let isService = Boolean(s.service_name || s.is_service);
        if (!pName && products.length > 0) {
          const prod = products.find((p) => p.id === s.product_id) || products[0];
          if (prod) {
            pName = prod.name;
            isService = Boolean(prod.is_service);
          }
        }
        items.push({
          id: s.id,
          object_key: `script_${s.id}`,
          title: s.gancho_0_5s || "Video de Ideación",
          filename: `script_${s.id}.mp4`,
          type: "video",
          url: s.video_url || s.edited_video_uri || `http://localhost:9000/viralsync-media/${tenantId}/video_${s.id}.mp4`,
          product_name: pName || "Producto de Campaña",
          is_service: isService,
          created_at: s.created_at,
          idea_id: s.idea_id,
        });
      }
    });

    return items;
  }, [rawItems, rawScripts, products, tenantId]);

  // Agrupar carpetas por Lote / Producto en Nivel 1
  const folderList = useMemo(() => {
    const map = {};

    const itemOriginalTimeMap = {};
    localMedia.forEach((m) => {
      if (m.idea_id || m.batch_id) {
        const key = m.idea_id || m.batch_id;
        const mTime = new Date(m.created_at || Date.now()).getTime();
        if (!itemOriginalTimeMap[key] || mTime < itemOriginalTimeMap[key]) {
          itemOriginalTimeMap[key] = mTime;
        }
      }
    });

    localMedia.forEach((item) => {
      const pName = item.product_name || "Producto de Campaña";
      const isService = Boolean(item.is_service);
      const itemTime = new Date(item.created_at || Date.now()).getTime();

      let matchedKey = null;
      if (item.idea_id || item.batch_id) {
        matchedKey = `batch_${item.idea_id || item.batch_id}`;
      } else {
        matchedKey = Object.keys(map).find((key) => {
          const folderObj = map[key];
          return folderObj.productName === pName && Math.abs(itemTime - folderObj.timestamp) < 120000;
        });
        if (!matchedKey) {
          matchedKey = `batch_${pName}_${itemTime}`;
        }
      }

      if (!map[matchedKey]) {
        map[matchedKey] = {
          key: matchedKey,
          productName: pName,
          name: pName,
          isService,
          timestamp: (item.idea_id || item.batch_id) ? (itemOriginalTimeMap[item.idea_id || item.batch_id] || itemTime) : itemTime,
          createdAt: item.created_at,
          items: [],
        };
      }

      map[matchedKey].items.push(item);
    });

    let folders = Object.values(map);

    // 1. Filtro por Formato Media
    if (mediaTypeFilter === "video") {
      folders = folders.map((f) => ({
        ...f,
        items: f.items.filter((i) => i.media_type === "video" || i.url?.includes(".mp4")),
      })).filter((f) => f.items.length > 0);
    } else if (mediaTypeFilter === "image") {
      folders = folders.map((f) => ({
        ...f,
        items: f.items.filter((i) => i.media_type === "image" || !i.url?.includes(".mp4")),
      })).filter((f) => f.items.length > 0);
    }

    // 2. Filtro por Categoría / Tipo de Oferta
    if (selectedCategory === "product") {
      folders = folders.filter((f) => !f.isService);
    } else if (selectedCategory === "service") {
      folders = folders.filter((f) => f.isService);
    } else if (selectedCategory !== "all") {
      folders = folders.filter((f) => f.productName === selectedCategory);
    }

    // 3. Búsqueda
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      folders = folders.filter(
        (f) =>
          f.productName.toLowerCase().includes(q) ||
          f.items.some((i) => (i.title || "").toLowerCase().includes(q) || (i.product_name || "").toLowerCase().includes(q))
      );
    }

    // 4. Ordenamiento
    if (selectedSort === "newest") {
      folders.sort((a, b) => b.timestamp - a.timestamp);
    } else if (selectedSort === "oldest") {
      folders.sort((a, b) => a.timestamp - b.timestamp);
    } else if (selectedSort === "title") {
      folders.sort((a, b) => a.productName.localeCompare(b.productName));
    }

    return folders;
  }, [localMedia, mediaTypeFilter, selectedCategory, searchQuery, selectedSort]);

  // Filtrar los archivos pertenecientes a la carpeta activa
  const filteredMedia = useMemo(() => {
    let result = [];
    if (activeFolder) {
      const folderObj = folderList.find((f) => f.key === activeFolder || f.productName === activeFolder);
      if (folderObj) {
        result = [...folderObj.items];
      } else {
        result = localMedia.filter((m) => m.product_name === activeFolder);
      }
    } else {
      result = [...localMedia];
    }

    if (selectedSort === "newest") {
      result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (selectedSort === "oldest") {
      result.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    }

    return result;
  }, [localMedia, folderList, activeFolder, selectedSort]);

  // Selección múltiple
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  };

  // Eliminación de archivo
  const handleDeleteItem = async (id) => {
    if (!confirm("¿Eliminar este archivo multimedia?")) return;
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/media/${id}`,
        { method: "DELETE" },
        tenantId
      );
      setNotification({
        type: "success",
        title: "Archivo Eliminado",
        message: "El elemento ha sido removido de la galería multimedia.",
      });
      refresh();
    } catch (err) {
      setNotification({
        type: "error",
        title: "Error al Eliminar",
        message: err.message || "No se pudo eliminar el archivo.",
      });
    }
  };

  const currentFolderObj = folderList.find((f) => f.key === activeFolder);

  return (
    <div className="space-y-6">
      {/* 1. Barra de Herramientas Estilo macOS Finder */}
      <MediaHeaderBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        viewMode={viewMode}
        setViewMode={setViewMode}
        mediaTypeFilter={mediaTypeFilter}
        setMediaTypeFilter={setMediaTypeFilter}
        selectedCategory={selectedCategory}
        setSelectedCategory={setSelectedCategory}
        selectedSort={selectedSort}
        setSelectedSort={setSelectedSort}
        selectedCount={selectedIds.length}
        products={products}
      />

      {/* 2. Breadcrumbs Nivel 2 */}
      {activeFolder && (
        <div className="flex items-center justify-between bg-slate-900/80 border border-slate-800 p-3 rounded-2xl animate-fadeIn">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveFolder(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-all shadow"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Volver a Carpetas</span>
            </button>
            <span className="text-slate-600">/</span>
            <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-300 bg-indigo-950/60 border border-indigo-500/30 px-3 py-1.5 rounded-xl">
              <FolderOpen className="w-4 h-4 text-indigo-400" />
              <span>{currentFolderObj ? currentFolderObj.productName : activeFolder}</span>
            </div>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {filteredMedia.length} {filteredMedia.length === 1 ? "archivo" : "archivos"} en esta carpeta
          </span>
        </div>
      )}

      {/* 3. Contenido Principal */}
      {loadingMedia ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-16 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Cargando galería multimedia...</p>
        </div>
      ) : errorMedia ? (
        <div className="bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-2xl p-6 text-sm">
          Error al cargar multimedia: {errorMedia.message}
        </div>
      ) : (
        <div>
          {!activeFolder ? (
            /* NIVEL 1: NAVEGACIÓN POR CARPETAS */
            folderList.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
                <Film className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-sm font-bold text-slate-300">No hay carpetas de multimedia</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Renderiza guiones o sube imágenes de producto para generar carpetas de assets.
                </p>
              </div>
            ) : viewMode === "grid" ? (
              /* VISTA DE ICONOS NIVEL 1 */
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {folderList.map((folder) => {
                  const count = folder.items.length;
                  const isService = folder.isService;
                  return (
                    <div
                      key={folder.key}
                      onClick={() => setActiveFolder(folder.key)}
                      className="group bg-slate-900/90 border border-slate-800 hover:border-indigo-500/70 p-5 rounded-2xl cursor-pointer transition-all hover:shadow-2xl flex flex-col justify-between space-y-3 relative overflow-hidden"
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800/60">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 group-hover:bg-rose-500 transition-colors"></span>
                          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 group-hover:bg-amber-500 transition-colors"></span>
                          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 group-hover:bg-emerald-500 transition-colors"></span>
                        </div>
                        <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                          {count} {count === 1 ? "archivo" : "archivos"}
                        </span>
                      </div>

                      <div className="flex items-start gap-3 py-1">
                        <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all shrink-0">
                          <Folder className="w-6 h-6" />
                        </div>
                        <div className="space-y-1.5 flex-1 min-w-0">
                          <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors leading-snug truncate">
                            {folder.productName}
                          </h3>
                          <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-500 shrink-0" />
                            <span>{formatDateTime(folder.createdAt)}</span>
                          </div>
                          <div className="pt-0.5">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border ${
                                isService
                                  ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                                  : "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                              }`}
                            >
                              {isService ? <Wrench className="w-3 h-3 text-amber-400" /> : <Package className="w-3 h-3 text-indigo-400" />}
                              <span>{isService ? "Servicio" : "Producto"}</span>
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* VISTA DE LISTA NIVEL 1 */
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 font-medium select-none">
                    <tr>
                      <th className="px-4 py-2.5 font-semibold">Carpeta / Producto o Servicio</th>
                      <th className="px-3 py-2.5 font-semibold">Tipo</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Archivos</th>
                      <th className="px-3 py-2.5 font-semibold">Fecha y Hora</th>
                      <th className="px-4 py-2.5 font-semibold text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
                    {folderList.map((folder) => {
                      const isService = folder.isService;
                      return (
                        <tr
                          key={folder.key}
                          onClick={() => setActiveFolder(folder.key)}
                          className="hover:bg-slate-900/80 cursor-pointer transition-colors group"
                        >
                          <td className="px-4 py-2.5 font-bold text-slate-200 group-hover:text-indigo-300">
                            <div className="flex items-center gap-2">
                              <Folder className="w-4 h-4 text-indigo-400 shrink-0" />
                              <span>{folder.productName}</span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                                isService
                                  ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                                  : "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                              }`}
                            >
                              {isService ? <Wrench className="w-3 h-3 text-amber-400" /> : <Package className="w-3 h-3 text-indigo-400" />}
                              <span>{isService ? "Servicio" : "Producto"}</span>
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-center whitespace-nowrap font-mono font-bold text-indigo-300">
                            {folder.items.length} {folder.items.length === 1 ? "archivo" : "archivos"}
                          </td>
                          <td className="px-3 py-2.5 whitespace-nowrap text-[11px] font-mono text-slate-400">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-slate-500" />
                              <span>{formatDateTime(folder.createdAt)}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5 text-right whitespace-nowrap">
                            <span className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] px-3 py-1 rounded-lg shadow transition-all">
                              Abrir Carpeta →
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            /* NIVEL 2: VISTA DE ARCHIVOS MULTIMEDIA EN CARPETA ACTIVA */
            viewMode === "grid" ? (
              <MediaMacGridView
                mediaItems={filteredMedia}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onOpenPreview={(item) => setPreviewItem(item)}
                onDelete={handleDeleteItem}
              />
            ) : (
              <MediaMacListView
                mediaItems={filteredMedia}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onOpenPreview={(item) => setPreviewItem(item)}
                onDelete={handleDeleteItem}
              />
            )
          )}
        </div>
      )}

      {/* Modal de Visor / Reproductor de Media */}
      {previewItem && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-4 animate-fadeIn relative">
            <button
              onClick={() => setPreviewItem(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              {previewItem.media_type === "video" || previewItem.url?.includes(".mp4") ? (
                <Film className="w-5 h-5 text-indigo-400" />
              ) : (
                <ImageIcon className="w-5 h-5 text-emerald-400" />
              )}
              <h3 className="text-sm font-bold text-slate-100 truncate pr-6">
                {previewItem.title || "Visor Multimedia"}
              </h3>
            </div>

            <div className="relative aspect-[9/16] max-h-[60vh] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 mx-auto flex items-center justify-center">
              {previewItem.media_type === "video" || previewItem.url?.includes(".mp4") ? (
                <video
                  src={previewItem.url || previewItem.video_url}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : (
                <img
                  src={previewItem.url || previewItem.image_url}
                  alt={previewItem.title}
                  className="w-full h-full object-contain"
                />
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <a
                href={previewItem.url || previewItem.video_url || previewItem.image_url}
                download={`media_${previewItem.id}`}
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 rounded-xl text-xs transition-all flex items-center justify-center gap-1.5"
              >
                <Download className="w-4 h-4" /> Descargar Archivo
              </a>
              <button
                onClick={() => setPreviewItem(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition-all"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ventana Emergente de Notificación (OK / Error) */}
      {notification && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div
            className={`bg-slate-900 border rounded-2xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-center animate-fadeIn ${
              notification.type === "success" ? "border-emerald-500/60" : "border-rose-500/60"
            }`}
          >
            <div
              className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto ${
                notification.type === "success"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-500/40"
                  : "bg-rose-950 text-rose-400 border border-rose-500/40"
              }`}
            >
              {notification.type === "success" ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <AlertCircle className="w-6 h-6" />
              )}
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">{notification.title}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{notification.message}</p>
            </div>
            <button
              onClick={() => setNotification(null)}
              className={`w-full py-2 rounded-xl font-bold text-xs shadow-md transition-all ${
                notification.type === "success"
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                  : "bg-rose-600 hover:bg-rose-500 text-white"
              }`}
            >
              Entendido
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
