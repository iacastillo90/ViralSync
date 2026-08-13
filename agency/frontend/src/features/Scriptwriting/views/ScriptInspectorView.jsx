"use client";

import { useState, useEffect, useMemo } from "react";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { ScriptsHeaderBar } from "@/components/scripts/ScriptsHeaderBar";
import { ScriptsMacGridView } from "@/components/scripts/ScriptsMacGridView";
import { ScriptsMacListView } from "@/components/scripts/ScriptsMacListView";
import { EditScriptModal } from "@/components/scripts/EditScriptModal";
import { TranslateScriptModal } from "@/components/scripts/TranslateScriptModal";
import { Sparkles, Loader2, FolderOpen, ArrowLeft, Folder, Calendar, Wrench, Package, Video, X, CheckCircle2, AlertCircle } from "lucide-react";
import { useSearchParams } from "next/navigation";

/**
 * Formateador de fecha y hora pequeña (DD/MM/YYYY HH:mm)
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
 * ScriptInspectorView
 * Vista principal de Guiones Virales con interfaz estilo macOS Finder,
 * jerarquía de 2 niveles (Carpetas -> Guiones), edición con recálculo dinámico de tiempos y vistas conmutables.
 */
export function ScriptInspectorView({ tenantId }) {
  const { data, loading, error, refresh } = useTenantResource("scripts", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);
  const searchParams = useSearchParams();
  const ideaIdParam = searchParams ? searchParams.get("ideaId") : null;

  // Estados de interfaz macOS Finder
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedSort, setSelectedSort] = useState("newest");
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);

  // Estado para Ventana Emergente (Pop-up OK / Error)
  const [notification, setNotification] = useState(null); // { type: "success" | "error", title: string, message: string }

  // Estado del Modal de Edición de Guion
  const [editingScript, setEditingScript] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Estado del Modal de Traducción Multilingüe
  const [translatingScript, setTranslatingScript] = useState(null);
  const [isTranslateModalOpen, setIsTranslateModalOpen] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);

  // Estados de Renderizado de Video
  const [videoUrl, setVideoUrl] = useState(null);
  const [renderingScriptTitle, setRenderingScriptTitle] = useState("");
  const [isVideoLoading, setIsVideoLoading] = useState(false);

  // Lista local editable de guiones
  const [localScripts, setLocalScripts] = useState([]);

  useEffect(() => {
    if (Array.isArray(data)) {
      const products = Array.isArray(productsData) ? productsData : [];
      const enriched = data.map((s) => {
        let pName = s.product_name || s.service_name || s.category;
        if (!pName && products.length > 0) {
          pName = products[0].name || products[0].title;
        }
        return {
          ...s,
          product_name: pName || "Producto de Campaña",
        };
      });
      setLocalScripts(enriched);
    }
  }, [data, productsData]);

  // Polling silencioso cada 5s para sincronización de nuevos guiones
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Categorías/productos únicos
  const categoriesList = useMemo(() => {
    const cats = new Set();
    localScripts.forEach((item) => {
      const name = item.product_name || item.service_name || item.category;
      if (name) cats.add(name);
    });
    return Array.from(cats);
  }, [localScripts]);

  // Agrupar, filtrar y ordenar carpetas de guiones en Nivel 1
  const folderList = useMemo(() => {
    const map = {};

    // 1. Identificar la fecha original de cada lote/idea_id
    const ideaOriginalTimeMap = {};
    localScripts.forEach((s) => {
      if (s.idea_id) {
        const sTime = new Date(s.created_at || Date.now()).getTime();
        if (!ideaOriginalTimeMap[s.idea_id] || sTime < ideaOriginalTimeMap[s.idea_id]) {
          ideaOriginalTimeMap[s.idea_id] = sTime;
        }
      }
    });

    localScripts.forEach((script) => {
      const pName = script.product_name || script.service_name || script.category || "Producto de Campaña";
      const isService = Boolean(script.service_name || script.is_service);
      const scriptTime = new Date(script.created_at || Date.now()).getTime();

      // Determinar la clave de la carpeta:
      // Si el guion proviene de una idea (idea_id), su lote es único para esa ejecución de ideación.
      // Todas sus traducciones comparten el mismo idea_id y por ende la MISMA carpeta.
      let matchedKey = null;

      if (script.idea_id) {
        matchedKey = `idea_${script.idea_id}`;
      } else {
        matchedKey = Object.keys(map).find((key) => {
          const item = map[key];
          return item.productName === pName && Math.abs(scriptTime - item.timestamp) < 120000;
        });
        if (!matchedKey) {
          matchedKey = `batch_${pName}_${scriptTime}`;
        }
      }

      if (!map[matchedKey]) {
        map[matchedKey] = {
          key: matchedKey,
          productName: pName,
          name: pName,
          isService,
          timestamp: script.idea_id ? (ideaOriginalTimeMap[script.idea_id] || scriptTime) : scriptTime,
          createdAt: script.created_at,
          items: [],
        };
      }

      map[matchedKey].items.push(script);
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

    // 2. Filtro por Búsqueda por texto
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      folders = folders.filter(
        (f) =>
          f.productName.toLowerCase().includes(q) ||
          f.items.some(
            (s) =>
              (s.gancho_0_5s || "").toLowerCase().includes(q) ||
              (s.contexto_5_30s || "").toLowerCase().includes(q) ||
              (s.title || "").toLowerCase().includes(q)
          )
      );
    }

    // 3. Ordenamiento Dinámico de Carpetas
    if (selectedSort === "newest") {
      folders.sort((a, b) => b.timestamp - a.timestamp);
    } else if (selectedSort === "oldest") {
      folders.sort((a, b) => a.timestamp - b.timestamp);
    } else if (selectedSort === "title") {
      folders.sort((a, b) => a.productName.localeCompare(b.productName));
    }

    return folders;
  }, [localScripts, selectedCategory, searchQuery, selectedSort]);

  // Autoseleccionar carpeta si viene el parámetro ideaIdParam de la URL
  useEffect(() => {
    if (ideaIdParam && folderList.length > 0 && !activeFolder) {
      setActiveFolder(folderList[0].key);
    }
  }, [ideaIdParam, folderList, activeFolder]);

  // Filtrar los guiones pertencientes a la carpeta activa
  const filteredScripts = useMemo(() => {
    let result = [];
    if (activeFolder) {
      const folderObj = folderList.find(
        (f) => f.key === activeFolder || f.productName === activeFolder || f.name === activeFolder
      );
      if (folderObj) {
        result = [...folderObj.items];
      } else {
        result = localScripts.filter(
          (item) => (item.product_name || item.service_name || item.category) === activeFolder
        );
      }
    } else {
      result = [...localScripts];
    }

    // Ordenamiento secundario de guiones
    if (selectedSort === "newest") {
      result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (selectedSort === "oldest") {
      result.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    }

    return result;
  }, [localScripts, folderList, activeFolder, selectedSort]);

  // Controles de Selección Múltiple
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.length === filteredScripts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredScripts.map((item) => item.id));
    }
  };

  // Acciones Masivas
  const handleBulkDelete = () => {
    if (!confirm(`¿Eliminar los ${selectedIds.length} guiones seleccionados?`)) return;
    setLocalScripts((prev) => prev.filter((item) => !selectedIds.includes(item.id)));
    setSelectedIds([]);
  };

  const handleBulkDownload = () => {
    const selectedData = localScripts.filter((item) => selectedIds.includes(item.id));
    const jsonStr = JSON.stringify(selectedData, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `guiones_viralsync_${tenantId}.json`;
    a.click();
  };

  // Acciones Individuales
  const handleDeleteScript = (id) => {
    if (!confirm("¿Eliminar este guion viral?")) return;
    setLocalScripts((prev) => prev.filter((item) => item.id !== id));
    setSelectedIds((prev) => prev.filter((item) => item !== id));
  };

  const handleDownloadScript = (script) => {
    const fullText = `=== GUION VIRAL: ${script.product_name || "PRODUCTO"} ===\n\n` +
      `🪝 BLOQUE 1 - GANCHO (0-5s):\n${script.gancho_0_5s || script.gancho || ""}\n\n` +
      `💡 BLOQUE 2 - CONTEXTO (5-30s):\n${script.contexto_5_30s || script.contexto || ""}\n\n` +
      `✨ BLOQUE 3 - MORALEJA (30-50s):\n${script.moraleja_30_50s || script.moraleja || ""}\n\n` +
      `📣 BLOQUE 4 - CTA (50-60s):\n${script.cta_50_60s || script.cta || ""}\n`;

    const blob = new Blob([fullText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `guion_${script.id || "viral"}.txt`;
    a.click();
  };

  const handleOpenEdit = (script) => {
    setEditingScript(script);
    setIsEditModalOpen(true);
  };

  const handleSaveEditedScript = (updatedScript) => {
    setLocalScripts((prev) =>
      prev.map((item) => (item.id === updatedScript.id ? updatedScript : item))
    );
  };

  // Abrir Modal de Traducción
  const handleOpenTranslate = (script) => {
    setTranslatingScript(script);
    setIsTranslateModalOpen(true);
  };

  // Ejecutar Traducción con la API Backend del Tenant
  const handleTranslateScript = async (script, targetLang) => {
    if (!script || !script.id) return;
    setIsTranslating(true);
    try {
      const resData = await fetchWithTenant(
        `/tenants/${tenantId}/scripts/${script.id}/translate`,
        {
          method: "POST",
          body: JSON.stringify({ target_language: targetLang }),
        },
        tenantId
      );

      if (resData && (resData.id || resData.gancho_0_5s)) {
        // Agregar el nuevo guion traducido a la lista local para renderizado instantáneo
        setLocalScripts((prev) => [
          {
            ...resData,
            product_name: script.product_name || script.service_name || "Producto de Campaña",
          },
          ...prev,
        ]);
        setIsTranslateModalOpen(false);

        const langLabels = {
          en: "Inglés (English)",
          pt: "Portugués (Português)",
          fr: "Francés (Français)",
          de: "Alemán (Deutsch)",
          es: "Español",
        };
        const langName = langLabels[targetLang] || targetLang.toUpperCase();

        setNotification({
          type: "success",
          title: "¡Guion Traducido con Éxito!",
          message: `El guion de 4 bloques ha sido adaptado al idioma ${langName} y añadido a tu catálogo de guiones.`,
        });

        refresh();
      }
    } catch (err) {
      setNotification({
        type: "error",
        title: "Error al Traducir Guion",
        message: err.message || "Ocurrió un error en el motor de traducción del servidor.",
      });
    } finally {
      setIsTranslating(false);
    }
  };

  // Ordenar Renderizado de Video al Microservicio
  const handleRenderVideo = async (script) => {
    setIsVideoLoading(true);
    setRenderingScriptTitle(script.gancho_0_5s || script.title || "Guion Viral");
    try {
      const fullText = `${script.gancho_0_5s || ""} ${script.contexto_5_30s || ""} ${script.moraleja_30_50s || ""} ${script.cta_50_60s || ""}`.trim();
      const resData = await fetchWithTenant(
        `/tenants/${tenantId}/render`,
        {
          method: "POST",
          body: JSON.stringify({
            script_id: script.id,
            script_text: fullText,
            product_image_url: script.product_image_url,
            target_duration: script.target_duration || 30,
          }),
        },
        tenantId
      );
      if (resData && resData.video_url) {
        setVideoUrl(resData.video_url);
      }
    } catch (err) {
      setNotification({
        type: "error",
        title: "Error al Solicitar Renderizado",
        message: err.message || "No se pudo conectar con el servicio de renderizado de video.",
      });
    } finally {
      setIsVideoLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Barra de Herramientas Estilo macOS Finder */}
      <ScriptsHeaderBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        viewMode={viewMode}
        setViewMode={setViewMode}
        selectedCategory={selectedCategory}
        setSelectedCategory={setSelectedCategory}
        selectedSort={selectedSort}
        setSelectedSort={setSelectedSort}
        categories={categoriesList}
        selectedCount={selectedIds.length}
        totalCount={filteredScripts.length}
        isAllSelected={selectedIds.length > 0 && selectedIds.length === filteredScripts.length}
        onToggleSelectAll={handleToggleSelectAll}
        onBulkDelete={handleBulkDelete}
        onBulkDownload={handleBulkDownload}
      />

      {/* 2. NIVEL 1: Si no se ha ingresado a ninguna carpeta, mostrar la cuadrícula de Carpetas */}
      {!activeFolder ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              📁 Carpetas de Guiones por Producto ({folderList.length})
            </h2>
            <span className="text-[11px] text-slate-500 font-medium">
              Haz clic en una carpeta para inspeccionar sus guiones estructurados
            </span>
          </div>

          {loading && localScripts.length === 0 ? (
            <div className="flex items-center justify-center gap-3 text-xs text-slate-400 py-12">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-400" /> Cargando catálogo de guiones...
            </div>
          ) : folderList.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <Folder className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-sm font-bold text-slate-300">No hay carpetas de guiones</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Aprueba una propuesta en Ideación para redactar sus guiones virales automáticamente.
              </p>
            </div>
          ) : viewMode === "grid" ? (
            /* VISTA DE ICONOS EN NIVEL 1 */
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
                    {/* Estilo Mac Window Controls */}
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800/60">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 group-hover:bg-rose-500 transition-colors"></span>
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 group-hover:bg-amber-500 transition-colors"></span>
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 group-hover:bg-emerald-500 transition-colors"></span>
                      </div>
                      <span className="bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
                        {count} {count === 1 ? "guion" : "guiones"}
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
            /* VISTA DE LISTA DETALLADA EN NIVEL 1 */
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 font-medium select-none">
                  <tr>
                    <th className="px-4 py-2.5 font-semibold">Carpeta / Producto o Servicio</th>
                    <th className="px-3 py-2.5 font-semibold">Tipo</th>
                    <th className="px-3 py-2.5 font-semibold text-center">Guiones</th>
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
                          {folder.items.length} {folder.items.length === 1 ? "guion" : "guiones"}
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
          )}
        </div>
      ) : (
        /* NIVEL 2: DENTRO DE LA CARPETA SELECCIONADA */
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-950/80 border border-slate-800 px-4 py-2.5 rounded-xl text-xs shadow-md">
            <button
              onClick={() => setActiveFolder(null)}
              className="flex items-center gap-2 font-bold text-indigo-400 hover:text-indigo-300 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> ← Volver a todas las carpetas
            </button>
            <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
              <FolderOpen className="w-4 h-4 text-indigo-400" /> Carpeta activa: <strong className="text-indigo-300">{activeFolder}</strong> ({filteredScripts.length} guiones)
            </span>
          </div>

          {/* Renderizado conmutatorio de guiones (Grid de Iconos vs Lista Compacta Lineal) */}
          {viewMode === "grid" ? (
            <ScriptsMacGridView
              scripts={filteredScripts}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onEdit={handleOpenEdit}
              onDelete={handleDeleteScript}
              onDownload={handleDownloadScript}
              onTranslate={handleOpenTranslate}
              onRenderVideo={handleRenderVideo}
              onSelectFolder={(folderName) => setActiveFolder(folderName)}
            />
          ) : (
            <ScriptsMacListView
              scripts={filteredScripts}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onEdit={handleOpenEdit}
              onDelete={handleDeleteScript}
              onDownload={handleDownloadScript}
              onTranslate={handleOpenTranslate}
              onRenderVideo={handleRenderVideo}
              onSelectFolder={(folderName) => setActiveFolder(folderName)}
            />
          )}
        </div>
      )}

      {/* Modal de Traducción Multilingüe */}
      <TranslateScriptModal
        script={translatingScript}
        isOpen={isTranslateModalOpen}
        onClose={() => setIsTranslateModalOpen(false)}
        onTranslate={handleTranslateScript}
        isTranslating={isTranslating}
      />

      {/* Ventana Emergente de Notificación (Pop-up OK / Error) */}
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