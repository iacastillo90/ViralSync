"use client";

import { UserCheck } from "lucide-react";

export function LeadsTable({ leads, onTakeover }) {
  return (
    <div className="overflow-x-auto bg-slate-950 rounded-xl border border-slate-800">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs">
          <tr>
            <th className="p-3">ID Lead</th>
            <th className="p-3">User IG</th>
            <th className="p-3">Keyword</th>
            <th className="p-3">Mensaje Original</th>
            <th className="p-3">Estado Bot</th>
            <th className="p-3">Acción Operador</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {leads.map((lead) => (
            <tr key={lead.id} className="hover:bg-slate-900/50">
              <td className="p-3 font-mono text-xs text-slate-400">{lead.id}</td>
              <td className="p-3 font-medium text-slate-200">{lead.ig_user_id}</td>
              <td className="p-3 font-mono text-indigo-400 font-semibold">{lead.keyword}</td>
              <td className="p-3 text-slate-300">{lead.mensaje_original}</td>
              <td className="p-3">
                {lead.handled_by_human_at ? (
                  <span className="bg-amber-950/60 text-amber-400 border border-amber-500/40 px-2.5 py-1 rounded-full text-xs font-semibold">
                    Operador Asignado
                  </span>
                ) : (
                  <span className="bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full text-xs font-semibold">
                    Bot Activo
                  </span>
                )}
              </td>
              <td className="p-3">
                {!lead.handled_by_human_at && (
                  <button
                    onClick={() => onTakeover(lead.id)}
                    className="flex items-center gap-1.5 bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  >
                    <UserCheck className="w-3.5 h-3.5" /> Asumir Control Humano
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
