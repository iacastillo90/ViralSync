"use client";

import { useState, useEffect, useMemo } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { IdeationHeaderBar } from "@/components/ideation/IdeationHeaderBar";
import { IdeationMacGridView } from "@/components/ideation/IdeationMacGridView";
import { IdeationMacListView } from "@/components/ideation/IdeationMacListView";
import { EditIdeaModal } from "@/components/ideation/EditIdeaModal";
import { Sparkles, Loader2, FolderOpen, ArrowLeft, Folder } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

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

  // Agrupar ideas en carpetas por producto/lote
  const folderList = useMemo(() => {
    const map = {};
    localIdeas.forEach((idea) => {
      const cat = idea.category || idea.product_name || "General";
      if (!map[cat]) {
        map[cat] = {
          key: cat,
          name: cat,
          items: [],
        };
      }
      map[cat].items.push(idea);
    });
    return Object.values(map);
  }, [localIdeas]);

  // Filtrar y ordenar ideas según la carpeta activa y controles Finder
  const filteredIdeas = useMemo(() => {
    let result = [...localIdeas];

    // Filtrar por carpeta activa si se está dentro de una
    if (activeFolder) {
      result = result.filter(
        (item) => (item.category || item.product_name || "General") === activeFolder
      );
    }

    // Búsqueda por texto
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (item) =>
          (item.angle || "").toLowerCase().includes(q) ||
          (item.hook || "").toLowerCase().includes(q) ||
          (item.title || "").toLowerCase().includes(q) ||
          (item.core_message || "").toLowerCase().includes(q) ||
          (item.texto || "").toLowerCase().includes(q)
      );
    }

    // Filtro por Categoría / Producto
    if (selectedCategory !== "all") {
      result = result.filter(
        (item) => (item.category || item.product_name) === selectedCategory
      );
    }

    // Filtro por Campaña
    if (selectedCampaign !== "all") {
      result = result.filter((item) => item.campaign_name === selectedCampaign);
    }

    // Ordenamiento
    if (selectedSort === "newest") {
      result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    } else if (selectedSort === "oldest") {
      result.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    } else if (selectedSort === "title") {
      result.sort((a, b) =>
        (a.angle || a.title || "").localeCompare(b.angle || b.title || "")
      );
    }

    return result;
  }, [localIdeas, activeFolder, searchQuery, selectedCategory, selectedCampaign, selectedSort]);

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

  // Aprobar Idea y Generar Guion
  const handleApproveIdea = async (idea) => {
    if (!idea || !idea.id) return;
    if (queuedIds.includes(idea.id) || idea.approval_status === "approved") return;

    addLog(`Idea APROBADA por usuario: ${idea.id}`);
    setQueuedIds((prev) => [...prev, idea.id]);
    setIsWritingScript(true);
    setApprovedIdeaTitle(idea.angle || idea.hook || idea.title || "Concepto");

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

      setTimeout(() => {
        setIsWritingScript(false);
        router.push(`/tenants/${tenantId}/guiones?ideaId=${idea.id}`);
      }, 8000);
    } catch (err) {
      alert(`Error al aprobar idea: ${err.message}`);
      setIsWritingScript(false);
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
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {folderList.map((folder) => {
                const count = folder.items.length;
                const isService = folder.items.some((i) => i.service_name || i.is_service);
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

                    <div className="flex items-center gap-3 py-1">
                      <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all">
                        <Folder className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                          {folder.name}
                        </h3>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {isService ? "🛠️ Servicio" : "📦 Producto"}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
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

      {/* Modal Bloqueante de Generación de Guion */}
      {isWritingScript && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full shadow-2xl p-6 text-center">
            <div className="w-12 h-12 bg-indigo-500/20 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-3 animate-spin">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-100 mb-1">Redactando Guion Viral...</h3>
            <p className="text-slate-400 mb-4 text-xs">
              Estructurando narrativa para "<strong>{approvedIdeaTitle}</strong>"
            </p>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-indigo-500 h-full animate-pulse w-3/4 rounded-full"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}