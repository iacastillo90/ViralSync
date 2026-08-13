"use client";

import { useState, useMemo } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { VideosHeaderBar } from "@/components/videos/VideosHeaderBar";
import { VideosMacGridView } from "@/components/videos/VideosMacGridView";
import { VideosMacListView } from "@/components/videos/VideosMacListView";
import {
  Video,
  Loader2,
  FolderOpen,
  ArrowLeft,
  Folder,
  Calendar,
  Wrench,
  Package,
  X,
  CheckCircle2,
  AlertCircle,
  Play,
  Download,
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
 * PublishApprovalView
 * Vista principal de Aprobación de Publicación de Videos con interfaz estilo macOS Finder,
 * jerarquía de 2 niveles (Carpetas por Ejecución/Lote -> Videos 9:16), vista Iconos/Lista y reproductor modal.
 */
export function PublishApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();
  const { data: scriptsData, loading: loadingScripts, error: errorScripts, refresh } = useTenantResource("scripts", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);

  // Estados de interfaz macOS Finder
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedSort, setSelectedSort] = useState("newest");
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);

  // Modales
  const [previewVideo, setPreviewVideo] = useState(null);
  const [notification, setNotification] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const rawScripts = Array.isArray(scriptsData) ? scriptsData : [];
  const products = Array.isArray(productsData) ? productsData : [];

  // Mapear guiones/videos con datos de productos
  const localVideos = useMemo(() => {
    return rawScripts.map((s) => {
      let pName = s.product_name || s.service_name || s.category;
      let isService = Boolean(s.service_name || s.is_service);

      if (!pName && products.length > 0) {
        const prod = products.find((p) => p.id === s.product_id) || products[0];
        if (prod) {
          pName = prod.name;
          isService = Boolean(prod.is_service);
        }
      }

      return {
        ...s,
        product_name: pName || "Producto de Campaña",
        is_service: isService,
        title: s.title || s.gancho_0_5s || "Reel 9:16 Renderizado",
      };
    });
  }, [rawScripts, products]);

  // Agrupar carpetas por idea_id / Lote de Ideación en Nivel 1
  const folderList = useMemo(() => {
    const map = {};

    const ideaOriginalTimeMap = {};
    localVideos.forEach((v) => {
      if (v.idea_id) {
        const vTime = new Date(v.created_at || Date.now()).getTime();
        if (!ideaOriginalTimeMap[v.idea_id] || vTime < ideaOriginalTimeMap[v.idea_id]) {
          ideaOriginalTimeMap[v.idea_id] = vTime;
        }
      }
    });

    localVideos.forEach((vid) => {
      const pName = vid.product_name || "Producto de Campaña";
      const isService = Boolean(vid.is_service);
      const vidTime = new Date(vid.created_at || Date.now()).getTime();

      let matchedKey = null;
      if (vid.idea_id) {
        matchedKey = `idea_${vid.idea_id}`;
      } else {
        matchedKey = Object.keys(map).find((key) => {
          const item = map[key];
          return item.productName === pName && Math.abs(vidTime - item.timestamp) < 120000;
        });
        if (!matchedKey) {
          matchedKey = `batch_${pName}_${vidTime}`;
        }
      }

      if (!map[matchedKey]) {
        map[matchedKey] = {
          key: matchedKey,
          productName: pName,
          name: pName,
          isService,
          timestamp: vid.idea_id ? (ideaOriginalTimeMap[vid.idea_id] || vidTime) : vidTime,
          createdAt: vid.created_at,
          items: [],
        };
      }

      map[matchedKey].items.push(vid);
    });

    let folders = Object.values(map);

    // 1. Filtro por Tipo o Nombre
    if (selectedCategory === "product") {
      folders = folders.filter((f) => !f.isService);
    } else if (selectedCategory === "service") {
      folders = folders.filter((f) => f.isService);
    } else if (selectedCategory !== "all") {
      folders = folders.filter((f) => f.productName === selectedCategory);
    }

    // 2. Búsqueda
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      folders = folders.filter(
        (f) =>
          f.productName.toLowerCase().includes(q) ||
          f.items.some((v) => (v.title || "").toLowerCase().includes(q) || (v.cta_50_60s || "").toLowerCase().includes(q))
      );
    }

    // 3. Ordenamiento
    if (selectedSort === "newest") {
      folders.sort((a, b) => b.timestamp - a.timestamp);
    } else if (selectedSort === "oldest") {
      folders.sort((a, b) => a.timestamp - b.timestamp);
    } else if (selectedSort === "title") {
      folders.sort((a, b) => a.productName.localeCompare(b.productName));
    }

    return folders;
  }, [localVideos, selectedCategory, searchQuery, selectedSort]);

  // Filtrar videos pertenecientes a la carpeta activa
  const filteredVideos = useMemo(() => {
    let result = [];
    if (activeFolder) {
      const folderObj = folderList.find((f) => f.key === activeFolder || f.productName === activeFolder);
      if (folderObj) {
        result = [...folderObj.items];
      } else {
        result = localVideos.filter((v) => v.product_name === activeFolder);
      }
    } else {
      result = [...localVideos];
    }

    if (selectedSort === "newest") {
      result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (selectedSort === "oldest") {
      result.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    }

    return result;
  }, [localVideos, folderList, activeFolder, selectedSort]);

  // Selección múltiple
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  };

  // Decisión de aprobación individual
  const handleDecision = async (vid, approved) => {
    setIsProcessing(true);
    addLog(`Publicación de video ${vid.id} ${approved ? "APROBADA" : "RECHAZADA"}`);
    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/publish/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            script_id: vid.id,
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );

      setNotification({
        type: approved ? "success" : "error",
        title: approved ? "¡Publicación Aprobada!" : "Publicación Rechazada",
        message: approved
          ? "El video ha sido aprobado para su publicación automática en Instagram Reels."
          : "La publicación ha sido descartada de la cola.",
      });
      refresh();
    } catch (err) {
      setNotification({
        type: "error",
        title: "Error en la Transacción",
        message: err.message || "No se pudo actualizar el estado de aprobación.",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Acciones Masivas
  const handleBulkApprove = async () => {
    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await fetchWithTenant(
          `/tenants/${tenantId}/publish/approve`,
          { method: "POST", body: JSON.stringify({ script_id: id, status: "approved" }) },
          tenantId
        );
      }
      setNotification({
        type: "success",
        title: "Aprobación Masiva",
        message: `Se han aprobado ${selectedIds.length} publicaciones con éxito.`,
      });
      setSelectedIds([]);
      refresh();
    } catch (err) {
      setNotification({ type: "error", title: "Error Masivo", message: err.message });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBulkReject = async () => {
    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await fetchWithTenant(
          `/tenants/${tenantId}/publish/approve`,
          { method: "POST", body: JSON.stringify({ script_id: id, status: "rejected" }) },
          tenantId
        );
      }
      setNotification({
        type: "error",
        title: "Rechazo Masivo",
        message: `Se han descartado ${selectedIds.length} publicaciones de la cola.`,
      });
      setSelectedIds([]);
      refresh();
    } catch (err) {
      setNotification({ type: "error", title: "Error Masivo", message: err.message });
    } finally {
      setIsProcessing(false);
    }
  };

  const currentFolderObj = folderList.find((f) => f.key === activeFolder);

  return (
    <div className="space-y-6">
      {/* 1. Barra de Herramientas Estilo macOS Finder */}
      <VideosHeaderBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        viewMode={viewMode}
        setViewMode={setViewMode}
        selectedCategory={selectedCategory}
        setSelectedCategory={setSelectedCategory}
        selectedSort={selectedSort}
        setSelectedSort={setSelectedSort}
        selectedCount={selectedIds.length}
        products={products}
        onBulkApprove={handleBulkApprove}
        onBulkReject={handleBulkReject}
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
            {filteredVideos.length} {filteredVideos.length === 1 ? "video" : "videos"} en esta carpeta
          </span>
        </div>
      )}

      {/* 3. Contenido Principal */}
      {loadingScripts ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-16 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Cargando cola de publicación de videos...</p>
        </div>
      ) : errorScripts ? (
        <div className="bg-rose-950/40 border border-rose-500/30 text-rose-300 rounded-2xl p-6 text-sm">
          Error al cargar los videos: {errorScripts.message}
        </div>
      ) : (
        <div>
          {!activeFolder ? (
            /* NIVEL 1: NAVEGACIÓN POR CARPETAS */
            folderList.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
                <Video className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-sm font-bold text-slate-300">No hay carpetas de video</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Genera o aprueba guiones virales para crear publicaciones de video automáticamente.
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
                          {count} {count === 1 ? "video" : "videos"}
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
                      <th className="px-3 py-2.5 font-semibold text-center">Videos</th>
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
                            {folder.items.length} {folder.items.length === 1 ? "video" : "videos"}
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
            /* NIVEL 2: VISTA DE VIDEOS EN CARPETA ACTIVA */
            viewMode === "grid" ? (
              <VideosMacGridView
                videos={filteredVideos}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onPlayVideo={(v) => setPreviewVideo(v)}
                onApprove={(v) => handleDecision(v, true)}
                onReject={(v) => handleDecision(v, false)}
              />
            ) : (
              <VideosMacListView
                videos={filteredVideos}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                onPlayVideo={(v) => setPreviewVideo(v)}
                onApprove={(v) => handleDecision(v, true)}
                onReject={(v) => handleDecision(v, false)}
              />
            )
          )}
        </div>
      )}

      {/* Modal de Previsualización y Reproducción de Video */}
      {previewVideo && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-4 animate-fadeIn relative">
            <button
              onClick={() => setPreviewVideo(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Video className="w-5 h-5 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100 truncate pr-6">
                {previewVideo.title || "Reproductor de Video 9:16"}
              </h3>
            </div>

            <div className="relative aspect-[9/16] max-h-[60vh] bg-slate-950 rounded-xl overflow-hidden border border-slate-800 mx-auto">
              {previewVideo.video_url ? (
                <video
                  src={previewVideo.video_url}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-center p-6 text-slate-400 text-xs">
                  Video renderizado listo para publicación
                </div>
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  handleDecision(previewVideo, true);
                  setPreviewVideo(null);
                }}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-xl text-xs transition-all flex items-center justify-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" /> Aprobar Publicación
              </button>
              <button
                onClick={() => setPreviewVideo(null)}
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