"use client";

import {
  FileText,
  Edit3,
  Trash2,
  Download,
  CheckCircle2,
  Clock,
  CheckSquare,
  Square,
  Package,
} from "lucide-react";

/**
 * IdeationMacListView
 * Componente atómico de vista en lista detallada lineal estilo macOS Finder.
 * Muestra las ideas en filas delgadas de 1 línea, una debajo de otra de forma limpia,
 * ideal para escanear rápidamente múltiples conceptos con baja ocupación vertical.
 */
export function IdeationMacListView({
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
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-2">
        <FileText className="w-8 h-8 text-slate-600 mx-auto" />
        <p className="text-xs text-slate-400">No hay ideas en el listado.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          {/* Cabecera de Columnas Estilo macOS Finder */}
          <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 font-medium select-none">
            <tr>
              <th className="w-10 px-3 py-2 text-center">
                <span className="sr-only">Selección</span>
              </th>
              <th className="px-4 py-2 font-semibold">Concepto / Gancho de Ideación</th>
              <th className="px-3 py-2 font-semibold">Categoría / Producto</th>
              <th className="px-3 py-2 font-semibold text-center">Duración Est.</th>
              <th className="px-3 py-2 font-semibold">Fecha</th>
              <th className="px-4 py-2 font-semibold text-right">Acciones Rápidas</th>
            </tr>
          </thead>

          {/* Cuerpo de Filas Delgadas estilo Finder */}
          <tbody className="divide-y divide-slate-800/40 bg-slate-950/40">
            {ideas.map((idea) => {
              const isSelected = selectedIds.includes(idea.id);
              const title = idea.angle || idea.hook || idea.title || "Concepto de Ideación";
              const category = idea.category || idea.product_name || "General";
              const estimatedDuration = idea.estimated_duration || 30;
              const dateStr = idea.created_at
                ? new Date(idea.created_at).toLocaleDateString("es-ES")
                : "Reciente";

              return (
                <tr
                  key={idea.id}
                  className={`hover:bg-slate-900/80 transition-colors group ${
                    isSelected ? "bg-indigo-950/30 text-indigo-200" : "text-slate-300"
                  }`}
                >
                  {/* Casilla de Selección */}
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => onToggleSelect(idea.id)}
                      className="text-slate-500 hover:text-indigo-400 transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-700 group-hover:text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Título / Gancho Principal */}
                  <td className="px-4 py-2 font-medium max-w-md truncate">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      <span className="truncate group-hover:text-indigo-300 transition-colors">
                        {title}
                      </span>
                    </div>
                  </td>

                  {/* Categoría o Producto */}
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-[11px] font-mono text-slate-300 inline-flex items-center gap-1">
                      <Package className="w-3 h-3 text-slate-400" /> {category}
                    </span>
                  </td>

                  {/* Duración Estimada */}
                  <td className="px-3 py-2 text-center whitespace-nowrap">
                    <span className="bg-amber-950/40 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-mono inline-flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-400" /> ~{estimatedDuration}s
                    </span>
                  </td>

                  {/* Fecha */}
                  <td className="px-3 py-2 whitespace-nowrap text-[11px] font-mono text-slate-400">
                    {dateStr}
                  </td>

                  {/* Botones de Acción en Línea */}
                  <td className="px-4 py-2 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => onEdit(idea)}
                        title="Editar y recalcular tiempo"
                        className="p-1 bg-slate-900 hover:bg-indigo-950 text-slate-400 hover:text-indigo-300 border border-slate-800 rounded-md transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDownload(idea)}
                        title="Descargar JSON"
                        className="p-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-md transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDelete(idea.id)}
                        title="Eliminar idea"
                        className="p-1 bg-slate-900 hover:bg-rose-950 text-slate-400 hover:text-rose-300 border border-slate-800 rounded-md transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      {onApprove && (
                        <button
                          onClick={() => onApprove(idea)}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1 shadow transition-all ml-1"
                        >
                          <CheckCircle2 className="w-3 h-3" /> Aprobar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
