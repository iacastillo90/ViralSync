"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { IdeationHeaderBar } from "@/components/ideation/IdeationHeaderBar";
import { IdeationMacGridView } from "@/components/ideation/IdeationMacGridView";
import { IdeationMacListView } from "@/components/ideation/IdeationMacListView";
import { EditIdeaModal } from "@/components/ideation/EditIdeaModal";
import { Sparkles, Loader2, FolderOpen, ArrowLeft, Folder, Calendar, Wrench, Package } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

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
 * IdeaApprovalView
 * Vista principal de Ideación con interfaz estilo macOS Finder,
 * edición dinámica con calculador de tiempos, selección múltiple y vistas conmutables.
 */
export function IdeaApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();
  const { data, loading, error, refresh } = useTenantResource("ideas", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);

  // Estados de interfaz y filtrado estilo macOS Finder
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedCampaign, setSelectedCampaign] = useState("all");
  const [selectedSort, setSelectedSort] = useState("newest");
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeFolder, setActiveFolder] = useState(null);

  // Estado del Modal de Edición de Idea
  const [editingIdea, setEditingIdea] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Estados de aprobación y flujo de guion
  const [queuedIds, setQueuedIds] = useState([]);
  const [isWritingScript, setIsWritingScript] = useState(false);
  const [approvedIdeaTitle, setApprovedIdeaTitle] = useState("");
  const [progressStep, setProgressStep] = useState(0); // 0-4
  const progressTimerRef = useRef(null);

  const router = useRouter();
  const searchParams = useSearchParams();
  const urlProduct = searchParams ? searchParams.get("product") : null;

  // Lista local editable de ideas
  const [localIdeas, setLocalIdeas] = useState([]);

  useEffect(() => {
    if (Array.isArray(data)) {
      const products = Array.isArray(productsData) ? productsData : [];
      const enriched = data.map((item) => {
        let pName = item.product_name || item.service_name || item.category;
        if (!pName && products.length > 0) {
          pName = products[0].name || products[0].title;
        }
        if (!pName && urlProduct) {
          pName = urlProduct;
        }
        return {
          ...item,
          product_name: pName || "Producto de Campaña",
        };
      });
      setLocalIdeas(enriched);
    }
  }, [data, productsData, urlProduct]);

  // Polling silencioso cada 5s para sincronización de lote
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Extraer categorías/productos únicos para el filtro
  const categoriesList = useMemo(() => {
    const cats = new Set();
    localIdeas.forEach((item) => {
      const name = item.category || item.product_name;
      if (name) cats.add(name);
    });
    return Array.from(cats);
  }, [localIdeas]);

  // Extraer campañas únicas
  const campaignsList = useMemo(() => {
    const camps = new Set();
    localIdeas.forEach((item) => {
      if (item.campaign_name) camps.add(item.campaign_name);
    });
    return Array.from(camps);
  }, [localIdeas]);

  // Agrupar, filtrar y ordenar carpetas por tipo (Producto vs Servicio), búsqueda y fecha
  const folderList = useMemo(() => {
    const map = {};
    localIdeas.forEach((idea) => {
      const pName = idea.product_name || idea.service_name || idea.category || "Producto de Campaña";
      const isService = Boolean(idea.service_name || idea.is_service);
      const ideaTime = new Date(idea.created_at || Date.now()).getTime();

      // Buscar si existe una carpeta para este producto dentro de una ventana de 2 minutos (batch)
      let matchedKey = Object.keys(map).find((key) => {
        const item = map[key];
        return item.productName === pName && Math.abs(ideaTime - item.timestamp) < 120000;
      });

      if (!matchedKey) {
        matchedKey = `batch_${pName}_${ideaTime}`;
        map[matchedKey] = {
          key: matchedKey,
          productName: pName,
          name: pName,
          isService: isService,
          timestamp: ideaTime,
          createdAt: idea.created_at,
          items: [],
        };
      }

      map[matchedKey].items.push(idea);
    });

    let folders = Object.values(map);

    // 1. Filtro por Tipo (Producto vs Servicio) o Nombre
    if (selectedCategory === "product") {
      folders = folders.filter((f) => !f.isService);
    } else if (selectedCategory === "service") {
      folders = folders.filter((f) => f.isService);
    } else if (selectedCategory !== "all") {
      folders = folders.filter((f) => f.productName === selectedCategory);
    }

    // 2. Filtro por Búsqueda en el nombre del producto/servicio o propuestas
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      folders = folders.filter(
        (f) =>
          f.productName.toLowerCase().includes(q) ||
          f.items.some(
            (i) =>
              (i.gancho || "").toLowerCase().includes(q) ||
              (i.texto || "").toLowerCase().includes(q)
          )
      );
    }

    // 3. Ordenamiento Dinámico de Carpetas (Más recientes, Más antiguos, Por Nombre A-Z)
    if (selectedSort === "newest") {
      folders.sort((a, b) => b.timestamp - a.timestamp);
    } else if (selectedSort === "oldest") {
      folders.sort((a, b) => a.timestamp - b.timestamp);
    } else if (selectedSort === "title") {
      folders.sort((a, b) => a.productName.localeCompare(b.productName));
    }

    return folders;
  }, [localIdeas, selectedCategory, searchQuery, selectedSort]);

  // Filtrar las ideaciones que pertenecen a la carpeta activa
  const filteredIdeas = useMemo(() => {
    let result = [];

    if (activeFolder) {
      const folderObj = folderList.find(
        (f) => f.key === activeFolder || f.productName === activeFolder || f.name === activeFolder
      );
      if (folderObj) {
        result = [...folderObj.items];
      } else {
        result = localIdeas.filter(
          (item) => (item.product_name || item.service_name || item.category) === activeFolder
        );
      }
    } else {
      result = [...localIdeas];
    }

    // Ordenamiento secundario de propuestas dentro de la carpeta
    if (selectedSort === "newest") {
      result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (selectedSort === "oldest") {
      result.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    }

    return result;
  }, [localIdeas, folderList, activeFolder, selectedSort]);

  // Controladores de Selección Múltiple
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.length === filteredIdeas.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredIdeas.map((item) => item.id));
    }
  };

  // Acciones Masivas (Bulk Actions)
  const handleBulkDelete = () => {
    if (!confirm(`¿Eliminar las ${selectedIds.length} ideas seleccionadas?`)) return;
    setLocalIdeas((prev) => prev.filter((item) => !selectedIds.includes(item.id)));
    setSelectedIds([]);
  };

  const handleBulkDownload = () => {
    const selectedData = localIdeas.filter((item) => selectedIds.includes(item.id));
    const jsonStr = JSON.stringify(selectedData, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ideas_viralsync_${tenantId}.json`;
    a.click();
  };

  // Eliminación Individual
  const handleDeleteIdea = (id) => {
    if (!confirm("¿Eliminar este concepto de ideación?")) return;
    setLocalIdeas((prev) => prev.filter((item) => item.id !== id));
    setSelectedIds((prev) => prev.filter((item) => item !== id));
  };

  // Descarga Individual
  const handleDownloadIdea = (idea) => {
    const jsonStr = JSON.stringify(idea, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `idea_${idea.id || "concepto"}.json`;
    a.click();
  };

  // Abrir Modal de Edición
  const handleOpenEdit = (idea) => {
    setEditingIdea(idea);
    setIsEditModalOpen(true);
  };

  // Guardar Idea Editada (con Recálculo de Tiempo)
  const handleSaveEditedIdea = (updatedIdea) => {
    setLocalIdeas((prev) =>
      prev.map((item) => (item.id === updatedIdea.id ? updatedIdea : item))
    );
    addLog(`Idea ${updatedIdea.id} editada y recalculada a ~${updatedIdea.estimated_duration}s`);
  };

  // Pasos del progreso de generación de guión
  const PROGRESS_STEPS = [
    { label: "Analizando tendencias del nicho...", icon: "🔍" },
    { label: "Estructurando narrativa 4 bloques...", icon: "📝" },
    { label: "Optimizando ganchos virales...", icon: "⚡" },
    { label: "Calculando score de impacto...", icon: "📊" },
    { label: "¡Guión listo! Abriendo carpeta...", icon: "✅" },
  ];

  // Aprobar Idea y Generar Guión con progreso real
  const handleApproveIdea = async (idea) => {
    if (!idea || !idea.id) return;
    if (queuedIds.includes(idea.id) || idea.approval_status === "approved") return;

    addLog(`Idea APROBADA por usuario: ${idea.id}`);
    setQueuedIds((prev) => [...prev, idea.id]);
    setIsWritingScript(true);
    setApprovedIdeaTitle(idea.angle || idea.hook || idea.title || "Concepto");
    setProgressStep(0);

    // Avanzar pasos de UI mientras el backend procesa
    let step = 0;
    const intervals = [1800, 3200, 5000, 7000];
    const timers = [];
    intervals.forEach((delay, idx) => {
      timers.push(setTimeout(() => setProgressStep(idx + 1), delay));
    });

    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/ideas/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            idea_id: idea.id,
            status: "approved",
          }),
        },
        tenantId
      );

      // Paso final: navegar a la carpeta de guión
      setTimeout(() => {
        timers.forEach(clearTimeout);
        setProgressStep(4);
        setTimeout(() => {
          setIsWritingScript(false);
          router.push(`/tenants/${tenantId}/guiones?ideaId=${idea.id}`);
        }, 1000);
      }, 8000);
    } catch (err) {
      timers.forEach(clearTimeout);
      setIsWritingScript(false);
      setProgressStep(0);
      alert(`Error al aprobar idea: ${err.message}`);
    }
  };


  return (
    <div className="space-y-6">
      {/* 1. Barra de Herramientas Estilo macOS Finder */}
      <IdeationHeaderBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        viewMode={viewMode}
        setViewMode={setViewMode}
        selectedCategory={selectedCategory}
        setSelectedCategory={setSelectedCategory}
        selectedCampaign={selectedCampaign}
        setSelectedCampaign={setSelectedCampaign}
        selectedSort={selectedSort}
        setSelectedSort={setSelectedSort}
        categories={categoriesList}
        campaigns={campaignsList}
        selectedCount={selectedIds.length}
        totalCount={filteredIdeas.length}
        isAllSelected={selectedIds.length > 0 && selectedIds.length === filteredIdeas.length}
        onToggleSelectAll={handleToggleSelectAll}
        onBulkDelete={handleBulkDelete}
        onBulkDownload={handleBulkDownload}
      />

      {/* 2. NIVEL 1: Si no se ha ingresado a ninguna carpeta, mostrar la cuadrícula de Carpetas */}
      {!activeFolder ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              📁 Carpetas de Productos y Servicios ({folderList.length})
            </h2>
            <span className="text-[11px] text-slate-500 font-medium">
              Haz clic en una carpeta para abrir y explorar sus propuestas de ideación
            </span>
          </div>

          {loading && localIdeas.length === 0 ? (
            <div className="flex items-center justify-center gap-3 text-xs text-slate-400 py-12">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-400" /> Cargando catálogo de ideación...
            </div>
          ) : folderList.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <Folder className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-sm font-bold text-slate-300">No hay carpetas de ideación</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Genera propuestas desde el formulario inicial para ver carpetas organizadas por producto o servicio.
              </p>
            </div>
          ) : viewMode === "grid" ? (
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
                        {count} {count === 1 ? "propuesta" : "propuestas"}
                      </span>
                    </div>

                    <div className="flex items-start gap-3 py-1">
                      <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all shrink-0">
                        <Folder className="w-6 h-6" />
                      </div>
                      <div className="space-y-1.5 flex-1 min-w-0">
                        {/* 1. Nombre Limpio del Producto / Servicio */}
                        <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors leading-snug truncate">
                          {folder.productName || folder.name}
                        </h3>

                        {/* 2. Fecha y Hora Completa Formateada (Abajo en letra pequeña) */}
                        <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500 shrink-0" />
                          <span>{formatDateTime(folder.createdAt)}</span>
                        </div>

                        {/* 3. Insignia Dinámica de Producto o Servicio */}
                        <div className="pt-0.5">
                          <span
                            className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border ${
                              isService
                                ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                                : "bg-indigo-950/60 text-indigo-300 border-indigo-500/30"
                            }`}
                          >
                            {isService ? (
                              <Wrench className="w-3 h-3 text-amber-400" />
                            ) : (
                              <Package className="w-3 h-3 text-indigo-400" />
                            )}
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
            /* VISTA EN LISTA LINEAL COMPACTA PARA CARPETAS MAC */
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 font-medium select-none">
                  <tr>
                    <th className="px-4 py-2.5 font-semibold">Carpeta / Producto o Servicio</th>
                    <th className="px-3 py-2.5 font-semibold">Tipo</th>
                    <th className="px-3 py-2.5 font-semibold text-center">Propuestas</th>
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
                            {isService ? (
                              <Wrench className="w-3 h-3 text-amber-400" />
                            ) : (
                              <Package className="w-3 h-3 text-indigo-400" />
                            )}
                            <span>{isService ? "Servicio" : "Producto"}</span>
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-center whitespace-nowrap font-mono font-bold text-indigo-300">
                          {folder.items.length} {folder.items.length === 1 ? "propuesta" : "propuestas"}
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
            <span className="text-slate-300 font-semibold flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-indigo-400" /> Carpeta Activa: <strong className="text-indigo-300">{activeFolder}</strong> ({filteredIdeas.length} propuestas)
            </span>
          </div>

          {/* Renderizado de las ideaciones dentro de la carpeta activa */}
          {viewMode === "grid" ? (
            <IdeationMacGridView
              ideas={filteredIdeas}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onEdit={handleOpenEdit}
              onDelete={handleDeleteIdea}
              onDownload={handleDownloadIdea}
              onApprove={handleApproveIdea}
              onSelectFolder={(folderName) => setActiveFolder(folderName)}
            />
          ) : (
            <IdeationMacListView
              ideas={filteredIdeas}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onEdit={handleOpenEdit}
              onDelete={handleDeleteIdea}
              onDownload={handleDownloadIdea}
              onApprove={handleApproveIdea}
              onSelectFolder={(folderName) => setActiveFolder(folderName)}
            />
          )}
        </div>
      )}

      {/* 4. Modal Interactivo de Edición y Recálculo Dinámico de Tiempo */}
      <EditIdeaModal
        idea={editingIdea}
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveEditedIdea}
      />

      {/* Modal de Progreso de Generación de Guión */}
      {isWritingScript && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl max-w-md w-full shadow-2xl p-7 space-y-5">
            {/* Icono animado */}
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 bg-indigo-500/20 border border-indigo-500/40 text-indigo-400 rounded-full flex items-center justify-center text-2xl animate-pulse">
                {PROGRESS_STEPS[progressStep]?.icon}
              </div>
              <h3 className="text-base font-bold text-slate-100 text-center">
                Generando Guión Viral
              </h3>
              <p className="text-xs text-slate-400 text-center">
                Para: <strong className="text-indigo-300">{approvedIdeaTitle}</strong>
              </p>
            </div>

            {/* Pasos de progreso */}
            <div className="space-y-2.5">
              {PROGRESS_STEPS.map((step, idx) => (
                <div key={idx} className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all ${
                  idx < progressStep
                    ? "bg-emerald-950/60 border border-emerald-500/30"
                    : idx === progressStep
                    ? "bg-indigo-950/70 border border-indigo-500/40"
                    : "opacity-40"
                }`}>
                  <span className="text-base shrink-0">{step.icon}</span>
                  <span className={`text-xs font-medium ${
                    idx < progressStep ? "text-emerald-300" :
                    idx === progressStep ? "text-indigo-200" : "text-slate-500"
                  }`}>
                    {step.label}
                  </span>
                  {idx < progressStep && (
                    <span className="ml-auto text-emerald-400 text-[10px] font-bold">✓</span>
                  )}
                  {idx === progressStep && (
                    <Loader2 className="ml-auto w-3.5 h-3.5 text-indigo-400 animate-spin shrink-0" />
                  )}
                </div>
              ))}
            </div>

            {/* Barra de progreso */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full transition-all duration-700"
                style={{ width: `${Math.round((progressStep / (PROGRESS_STEPS.length - 1)) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}