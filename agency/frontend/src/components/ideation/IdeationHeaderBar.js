"use client";

import {
  Search,
  Grid,
  List,
  Trash2,
  Download,
  Filter,
  CheckSquare,
  Square,
  Sparkles,
} from "lucide-react";

/**
 * IdeationHeaderBar
 * Componente atómico de la barra superior estilo macOS Finder.
 * Proporciona controles de búsqueda, filtrado avanzado (Categoría, Producto, Campaña, Tenant),
 * alternador de vista (Iconos vs Lista compacta lineal) y acciones masivas (Bulk Actions).
 */
export function IdeationHeaderBar({
  searchQuery,
  setSearchQuery,
  viewMode,
  setViewMode,
  selectedCategory,
  setSelectedCategory,
  selectedCampaign,
  setSelectedCampaign,
  selectedSort,
  setSelectedSort,
  categories = [],
  campaigns = [],
  selectedCount = 0,
  totalCount = 0,
  isAllSelected = false,
  onToggleSelectAll,
  onBulkDelete,
  onBulkDownload,
  onNewIdeation,
}) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-md space-y-3">
      {/* 1. Fila Principal: Título, Búsqueda, Vista Finder y Botón de Acción */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-3">
        {/* Título de la Sección con Estilo Mac Finder */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-950/80 rounded-lg border border-slate-800">
            <span className="w-3 h-3 rounded-full bg-rose-500 inline-block shadow-sm"></span>
            <span className="w-3 h-3 rounded-full bg-amber-500 inline-block shadow-sm"></span>
            <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block shadow-sm"></span>
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100 flex items-center gap-2">
              📂 Explorador de Ideas & Conceptos
            </h1>
            <p className="text-[11px] text-slate-400">
              {totalCount} {totalCount === 1 ? "idea encontrada" : "ideas encontradas en el catálogo"}
            </p>
          </div>
        </div>

        {/* Campo de Búsqueda por Nombre / Palabra Clave */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por nombre o concepto..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-medium transition-colors"
          />
        </div>

        {/* Alternador de Vista Finder (Iconos Grid vs Lista Compacta) */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <div className="bg-slate-950 p-1 rounded-xl border border-slate-800 flex items-center gap-1">
            <button
              onClick={() => setViewMode("grid")}
              title="Vista de Iconos (Grid Mac)"
              className={`p-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-all font-medium ${
                viewMode === "grid"
                  ? "bg-indigo-600 text-white shadow-md font-bold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Iconos</span>
            </button>
            <button
              onClick={() => setViewMode("list")}
              title="Vista de Lista Detallada (Línea Mac)"
              className={`p-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-all font-medium ${
                viewMode === "list"
                  ? "bg-indigo-600 text-white shadow-md font-bold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <List className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Lista</span>
            </button>
          </div>

          {/* Botón para Lanzar Nueva Ideación */}
          {onNewIdeation && (
            <button
              onClick={onNewIdeation}
              className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-lg transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" /> Nueva Ideación
            </button>
          )}
        </div>
      </div>

      {/* 2. Segunda Fila: Filtros Avanzados y Acciones en Lote (Bulk Actions) */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-2 border-t border-slate-800/60 text-xs">
        {/* Controles de Selección Masiva y Filtros de Categoría */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {/* Botón Seleccionar Todo */}
          <button
            onClick={onToggleSelectAll}
            className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 px-2.5 py-1.5 rounded-xl font-medium transition-colors"
          >
            {isAllSelected ? (
              <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
            ) : (
              <Square className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span>{isAllSelected ? "Deseleccionar" : "Seleccionar Todo"}</span>
          </button>

          {/* Filtro por Categoría / Producto */}
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 px-2.5 py-1 rounded-xl">
            <Filter className="w-3 h-3 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer font-medium"
            >
              <option value="all" className="bg-slate-900">📦 Todas las Categorías</option>
              {categories.map((cat, idx) => (
                <option key={idx} value={cat} className="bg-slate-900">
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro por Campaña */}
          {campaigns.length > 0 && (
            <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 px-2.5 py-1 rounded-xl">
              <select
                value={selectedCampaign}
                onChange={(e) => setSelectedCampaign(e.target.value)}
                className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer font-medium"
              >
                <option value="all" className="bg-slate-900">🎯 Todas las Campañas</option>
                {campaigns.map((camp, idx) => (
                  <option key={idx} value={camp} className="bg-slate-900">
                    {camp}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Ordenamiento */}
          <select
            value={selectedSort}
            onChange={(e) => setSelectedSort(e.target.value)}
            className="bg-slate-950 border border-slate-800 px-2.5 py-1.5 rounded-xl text-xs text-slate-300 focus:outline-none font-medium cursor-pointer"
          >
            <option value="newest" className="bg-slate-900">📅 Más recientes</option>
            <option value="oldest" className="bg-slate-900">⏳ Más antiguos</option>
            <option value="title" className="bg-slate-900">🔤 Por Nombre (A-Z)</option>
          </select>
        </div>

        {/* Acciones Masivas cuando hay elementos seleccionados */}
        {selectedCount > 0 && (
          <div className="flex items-center gap-2 bg-indigo-950/60 border border-indigo-500/40 px-3 py-1 rounded-xl text-indigo-200 animate-fadeIn">
            <span className="font-bold font-mono text-xs">{selectedCount} selec.</span>
            <button
              onClick={onBulkDownload}
              title="Descargar Seleccionadas en JSON"
              className="p-1 hover:bg-indigo-900/80 rounded-lg text-indigo-300 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onBulkDelete}
              title="Eliminar Seleccionadas"
              className="p-1 hover:bg-rose-900/80 rounded-lg text-rose-300 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
