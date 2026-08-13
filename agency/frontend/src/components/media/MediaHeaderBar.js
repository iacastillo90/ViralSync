"use client";

import { Search, Grid, List, Sparkles, Filter, ArrowUpDown, Film, Image as ImageIcon } from "lucide-react";

/**
 * MediaHeaderBar
 * Barra de herramientas estilo macOS Finder para la vista de Galería de Media y Assets.
 * Proporciona controles de ventana macOS (🔴 🟡 🟢), buscador reactivo, filtro por formato (Videos vs Imágenes), filtro por tipo de producto/servicio, ordenamiento y selector de vista (Iconos vs Lista).
 */
export function MediaHeaderBar({
  searchQuery,
  setSearchQuery,
  viewMode,
  setViewMode,
  mediaTypeFilter,
  setMediaTypeFilter,
  selectedCategory,
  setSelectedCategory,
  selectedSort,
  setSelectedSort,
  selectedCount = 0,
  products = [],
  onBulkDownload,
  onBulkDelete,
}) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur-md space-y-4">
      {/* Fila Superior: Controles de Ventana macOS + Título Módulo + Acciones Masivas */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        {/* Controles de Ventana macOS (🔴 🟡 🟢) + Título */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-950/80 px-2.5 py-1.5 rounded-full border border-slate-800/80">
            <span className="w-3 h-3 rounded-full bg-rose-500/90 shadow-sm shadow-rose-500/30"></span>
            <span className="w-3 h-3 rounded-full bg-amber-500/90 shadow-sm shadow-amber-500/30"></span>
            <span className="w-3 h-3 rounded-full bg-emerald-500/90 shadow-sm shadow-emerald-500/30"></span>
          </div>

          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Galería Multimedia y Assets de Marca</span>
            </h2>
            <p className="text-[11px] text-slate-400">
              Explora y audita todos los videos renderizados y fotos de productos por lote
            </p>
          </div>
        </div>

        {/* Acciones Masivas cuando hay elementos seleccionados */}
        {selectedCount > 0 && (
          <div className="flex items-center gap-2 bg-indigo-950/80 border border-indigo-500/40 px-3 py-1.5 rounded-xl animate-fadeIn">
            <span className="text-xs font-mono font-bold text-indigo-300">
              {selectedCount} seleccionados
            </span>
            <div className="h-4 w-px bg-indigo-500/30"></div>
            {onBulkDownload && (
              <button
                onClick={onBulkDownload}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] px-2.5 py-1 rounded-lg shadow transition-all"
              >
                Descargar Lote
              </button>
            )}
            {onBulkDelete && (
              <button
                onClick={onBulkDelete}
                className="bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px] px-2.5 py-1 rounded-lg shadow transition-all"
              >
                Eliminar
              </button>
            )}
          </div>
        )}
      </div>

      {/* Fila Inferior: Buscador + Filtros por Formato + Filtro por Producto/Servicio + Ordenamiento + Toggle Grid/List */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Buscador Reactivo Estilo Mac */}
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar archivos por nombre de producto o título..."
            className="w-full bg-slate-950/90 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30 transition-all"
          />
        </div>

        {/* Grupo de Filtros y Selector Grid/List */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filtro por Formato Media (Todos, Videos, Fotos) */}
          <div className="flex items-center bg-slate-950/90 border border-slate-800 p-1 rounded-xl">
            <button
              onClick={() => setMediaTypeFilter("all")}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                mediaTypeFilter === "all"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              ✨ Todos
            </button>
            <button
              onClick={() => setMediaTypeFilter("video")}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 ${
                mediaTypeFilter === "video"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Film className="w-3 h-3" /> Videos
            </button>
            <button
              onClick={() => setMediaTypeFilter("image")}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1 ${
                mediaTypeFilter === "image"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <ImageIcon className="w-3 h-3" /> Fotos
            </button>
          </div>

          {/* Filtro por Producto/Servicio */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 px-2.5 py-1.5 rounded-xl">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900 text-slate-200">✨ Todos los Ofertas</option>
              <option value="product" className="bg-slate-900 text-slate-200">📦 Solo Productos</option>
              <option value="service" className="bg-slate-900 text-slate-200">🛠️ Solo Servicios</option>
              {products.length > 0 && <option disabled className="bg-slate-950 text-slate-500">──────────</option>}
              {products.map((p) => (
                <option key={p.id} value={p.name} className="bg-slate-900 text-slate-200">
                  {p.is_service ? `🛠️ ${p.name}` : `📦 ${p.name}`}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Ordenamiento */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 px-2.5 py-1.5 rounded-xl">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedSort}
              onChange={(e) => setSelectedSort(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="newest" className="bg-slate-900 text-slate-200">📅 Más recientes</option>
              <option value="oldest" className="bg-slate-900 text-slate-200">⏳ Más antiguos</option>
              <option value="title" className="bg-slate-900 text-slate-200">🔤 Por Nombre A-Z</option>
            </select>
          </div>

          {/* Alternador de Vista macOS Finder (Iconos vs Lista) */}
          <div className="flex items-center bg-slate-950/90 border border-slate-800 p-1 rounded-xl">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === "grid"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Vista de Cuadrícula (Iconos Mac)"
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded-lg transition-all ${
                viewMode === "list"
                  ? "bg-indigo-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Vista de Lista (Tabla Lineal Mac)"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
