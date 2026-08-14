"use client";

import { Bell, X, CheckCheck, Trash2, Video, AlertCircle, Info, CheckCircle2 } from "lucide-react";
import Link from "next/link";

export function NotificationPanel({ isOpen, onClose, notifications, unreadCount, onMarkAllRead, onClearAll, tenantId }) {
  if (!isOpen) return null;

  const getIcon = (type) => {
    switch (type) {
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />;
      case "info":
      default:
        return <Video className="w-4 h-4 text-indigo-400 shrink-0" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-sm bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header Drawer */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-indigo-400" />
            <h3 className="font-bold text-sm text-slate-100">Notificaciones</h3>
            {unreadCount > 0 && (
              <span className="bg-indigo-600 text-white text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Acciones */}
        <div className="px-4 py-2 border-b border-slate-800/60 bg-slate-950 flex justify-between text-[11px] font-mono">
          <button
            onClick={onMarkAllRead}
            className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <CheckCheck className="w-3.5 h-3.5" /> Marcar leídas
          </button>
          <button
            onClick={onClearAll}
            className="text-slate-500 hover:text-rose-400 flex items-center gap-1"
          >
            <Trash2 className="w-3.5 h-3.5" /> Limpiar
          </button>
        </div>

        {/* Lista de Notificaciones */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {notifications.length === 0 ? (
            <div className="text-center py-12 space-y-2">
              <Bell className="w-8 h-8 text-slate-700 mx-auto" />
              <p className="text-xs text-slate-500">Sin notificaciones por ahora</p>
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`p-3.5 rounded-2xl border text-xs space-y-1.5 transition-all ${
                  n.unread
                    ? "bg-slate-950 border-indigo-500/30"
                    : "bg-slate-900/60 border-slate-800/80 opacity-75"
                }`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex items-center gap-2">
                    {getIcon(n.type)}
                    <span className="font-bold text-slate-200">{n.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 shrink-0">
                    {n.timestamp}
                  </span>
                </div>
                <p className="text-slate-400 leading-relaxed text-[11px] pl-6">
                  {n.message}
                </p>
                {n.scriptId && (
                  <div className="pl-6 pt-1">
                    <Link
                      href={`/tenants/${tenantId}/guiones`}
                      onClick={onClose}
                      className="text-[10px] font-mono font-bold text-indigo-400 hover:underline flex items-center gap-1"
                    >
                      Ver en Guiones →
                    </Link>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
