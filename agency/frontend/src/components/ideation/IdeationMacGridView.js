"use client";

import {
  Folder,
  Edit3,
  Trash2,
  Download,
  CheckCircle2,
  Clock,
  Sparkles,
  CheckSquare,
  Square,
  Package,
} from "lucide-react";

/**
 * IdeationMacGridView
 * Componente atómico de vista en cuadrícula (Grid Iconos) estilo macOS Finder.
 * Presenta las ideas como carpetas/documentos interactivos con controles de ventana Mac (🔴 🟡 🟢),
 * tarjetas de vista previa, selección múltiple y botones de acción rápida.
 */
export function IdeationMacGridView({
  ideas = [],
  selectedIds = [],
  onToggleSelect,
  onEdit,
  onDelete,
  onDownload,
  onApprove,
}) {
  if (ideas.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-12 text-center space-y-3">
        <Folder className="w-12 h-12 text-slate-600 mx-auto" />
        <h3 className="text-sm font-bold text-slate-300">No se encontraron ideas</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          No hay conceptos de ideación registrados que coincidan con los filtros aplicados.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {ideas.map((idea) => {
        const isSelected = selectedIds.includes(idea.id);
        const title = idea.angle || idea.hook || idea.title || "Concepto de Ideación";
        const category = idea.category || idea.product_name || "General";
        const estimatedDuration = idea.estimated_duration || 30;

        return (
          <div
            key={idea.id}
            className={`group bg-slate-900/90 border rounded-2xl p-4 shadow-xl backdrop-blur-md flex flex-col justify-between transition-all relative overflow-hidden ${
              isSelected
                ? "border-indigo-500 ring-2 ring-indigo-500/30 bg-slate-900"
                : "border-slate-800/80 hover:border-slate-700 hover:shadow-2xl"
            }`}
          >
            {/* Cabecera Estilo Ventana macOS (Puntos 🔴 🟡 🟢 + Checkbox) */}
            <div className="flex justify-between items-center pb-2.5 border-b border-slate-800/60">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 group-hover:bg-rose-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 group-hover:bg-amber-500 transition-colors"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 group-hover:bg-emerald-500 transition-colors"></span>
              </div>

              {/* Casilla de Selección Múltiple */}
              <button
                onClick={() => onToggleSelect(idea.id)}
                className="text-slate-400 hover:text-indigo-400 transition-colors"
                title="Seleccionar idea"
              >
                {isSelected ? (
                  <CheckSquare className="w-4 h-4 text-indigo-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600 group-hover:text-slate-400" />
                )}
              </button>
            </div>

            {/* Cuerpo de la Tarjeta Mac: Icono, Etiqueta y Texto del Gancho */}
            <div className="py-3 space-y-2.5 flex-1">
              <div className="flex items-start justify-between gap-2">
                <span className="bg-indigo-950/70 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-lg text-[10px] font-bold font-mono uppercase flex items-center gap-1">
                  <Package className="w-3 h-3 text-indigo-400" /> {category}
                </span>

                <span className="bg-slate-950 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-md text-[10px] font-mono flex items-center gap-1">
                  <Clock className="w-3 h-3 text-amber-400" /> ~{estimatedDuration}s
                </span>
              </div>

              <h3 className="text-xs font-bold text-slate-100 line-clamp-2 leading-snug group-hover:text-indigo-300 transition-colors">
                {title}
              </h3>

              {idea.core_message && (
                <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed">
                  {idea.core_message}
                </p>
              )}
            </div>

            {/* Pie de la Tarjeta Mac: Acciones Rápidas (Editar, Descargar, Borrar, Aprobar) */}
            <div className="pt-2.5 border-t border-slate-800/60 flex items-center justify-between gap-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onEdit(idea)}
                  title="Editar idea y recalcular tiempo"
                  className="p-1.5 bg-slate-950 hover:bg-indigo-950 text-slate-300 hover:text-indigo-300 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDownload(idea)}
                  title="Descargar en JSON"
                  className="p-1.5 bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-slate-100 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDelete(idea.id)}
                  title="Eliminar idea"
                  className="p-1.5 bg-slate-950 hover:bg-rose-950 text-slate-400 hover:text-rose-300 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {onApprove && (
                <button
                  onClick={() => onApprove(idea)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1 shadow-md transition-all"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Aprobar
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
