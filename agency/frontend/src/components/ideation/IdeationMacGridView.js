"use client";

import {
  Folder,
  Edit3,
  Trash2,
  Download,
  CheckCircle2,
  Clock,
  CheckSquare,
  Square,
  Package,
  Wrench,
  Calendar,
} from "lucide-react";

/**
 * Formateador de fecha y hora pequeña (DD/MM/YYYY HH:mm)
 */
function formatDateTime(isoString) {
  if (!isoString) return "Fecha N/A";
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
 * IdeationMacGridView
 * Componente atómico de vista en cuadrícula (Grid Iconos) estilo macOS Finder.
 * Muestra el nombre dinámico del Producto o Servicio del formulario, la fecha/hora de creación,
 * y controla el botón de aprobación para evitar aprobaciones masivas accidentales.
 */
export function IdeationMacGridView({
  ideas = [],
  selectedIds = [],
  onToggleSelect,
  onEdit,
  onDelete,
  onDownload,
  onApprove,
  onSelectFolder,
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

  // Ocultar botón "Aprobar" si hay más de 1 idea en pantalla para evitar aprobaciones masivas no deseadas
  const showApproveButton = ideas.length === 1;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {ideas.map((idea) => {
        const isSelected = selectedIds.includes(idea.id);
        const title =
          idea.gancho ||
          idea.angle ||
          idea.hook ||
          idea.texto ||
          idea.title ||
          idea.enfoque ||
          `Ángulo Viral #${idea.id ? String(idea.id).slice(0, 5) : "1"}`;
        const productName =
          idea.product_name ||
          idea.service_name ||
          idea.category ||
          idea.matched_product_name ||
          "Producto de Campaña";

        const isService = Boolean(idea.service_name || idea.is_service);
        const createdAtFormatted = formatDateTime(idea.created_at);
        const estimatedDuration = idea.estimated_duration || 30;

        return (
          <div
            key={idea.id}
            onClick={() => onSelectFolder && onSelectFolder(productName)}
            title={`Hacer clic para ver todas las ideaciones de ${productName}`}
            className={`group bg-slate-900/90 border rounded-2xl p-4 shadow-xl backdrop-blur-md flex flex-col justify-between transition-all relative overflow-hidden cursor-pointer ${
              isSelected
                ? "border-indigo-500 ring-2 ring-indigo-500/30 bg-slate-900"
                : "border-slate-800/80 hover:border-indigo-500/60 hover:shadow-2xl"
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
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleSelect(idea.id);
                }}
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

            {/* Cuerpo de la Tarjeta Mac: Nombre Dinámico de Producto/Servicio, Datetime y Duración */}
            <div className="py-3 space-y-2.5 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectFolder) onSelectFolder(productName);
                  }}
                  className="bg-indigo-950/70 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-lg text-[10px] font-bold font-mono uppercase flex items-center gap-1 truncate max-w-[65%] hover:bg-indigo-900/80 hover:border-indigo-400 transition-colors"
                >
                  {isService ? (
                    <Wrench className="w-3 h-3 text-amber-400 shrink-0" />
                  ) : (
                    <Package className="w-3 h-3 text-indigo-400 shrink-0" />
                  )}
                  <span className="truncate">{productName}</span>
                </span>

                <span className="bg-slate-950 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-md text-[10px] font-mono flex items-center gap-1 shrink-0">
                  <Clock className="w-3 h-3 text-amber-400" /> ~{estimatedDuration}s
                </span>
              </div>

              {/* Fecha y Hora de Creación (Datetime) */}
              <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400 pt-0.5">
                <Calendar className="w-3 h-3 text-slate-500" />
                <span>{createdAtFormatted}</span>
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

            {/* Pie de la Tarjeta Mac: Acciones Rápidas (Editar, Descargar, Borrar y Aprobar Condicional) */}
            <div className="pt-2.5 border-t border-slate-800/60 flex items-center justify-between gap-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(idea);
                  }}
                  title="Editar idea y recalcular tiempo"
                  className="p-1.5 bg-slate-950 hover:bg-indigo-950 text-slate-300 hover:text-indigo-300 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDownload(idea);
                  }}
                  title="Descargar en JSON"
                  className="p-1.5 bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-slate-100 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(idea.id);
                  }}
                  title="Eliminar idea"
                  className="p-1.5 bg-slate-950 hover:bg-rose-950 text-slate-400 hover:text-rose-300 border border-slate-800 rounded-lg text-xs transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Botón Aprobar solo cuando showApproveButton es verdadero (1 sola idea) */}
              {onApprove && showApproveButton && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onApprove(idea);
                  }}
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
