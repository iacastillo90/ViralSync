"use client";

import { useState, useEffect } from "react";
import { useTenantStore } from "@/stores/useTenantStore";
import { useAgentStore } from "@/stores/useAgentStore";
import { useRealtimeNotifications } from "@/hooks/useRealtimeNotifications";
import { NotificationPanel } from "@/components/notifications/NotificationPanel";
import { Sparkles, DollarSign, Building2, Bell } from "lucide-react";

export function Header() {
  const { activeTenant, availableTenants, setActiveTenant, setAvailableTenants } = useTenantStore();
  const { setTenantId } = useAgentStore();
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);

  const { notifications, unreadCount, markAllAsRead, clearAll } = useRealtimeNotifications(activeTenant?.id);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    fetch(`${apiBase}/tenants`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setAvailableTenants(data);
          let savedTenantId = typeof window !== "undefined" ? localStorage.getItem("tenantId") : null;
          let match = data.find((t) => t.id === savedTenantId && t.id !== "nuevo") || data[0];
          if (match) {
            setActiveTenant(match);
            setTenantId(match.id);
            localStorage.setItem("tenantId", match.id);
          }
        }
      })
      .catch((err) => console.error("Error cargando tenants en Header:", err));
  }, [setAvailableTenants, setActiveTenant, setTenantId]);


  const formatCurrency = (val, fallback = 0) => {
    const num = Number(val ?? fallback);
    return isNaN(num) ? "0.00" : num.toFixed(2);
  };

  return (
    <header className="flex justify-between items-center px-6 py-4 bg-slate-900 border-b border-slate-800 text-slate-100">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-600 p-2 rounded-xl text-white shadow-lg shadow-indigo-500/20">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight">ViralSync</span>
          <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full ml-2">
            v1.0 SaaS
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {/* Presupuesto LLM en Tiempo Real */}
        <div className="flex items-center gap-2 bg-slate-950 px-3.5 py-1.5 rounded-lg border border-slate-800 text-xs">
          <DollarSign className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Gasto LLM:</span>
          <span className="font-mono font-semibold text-emerald-300">
            {activeTenant
              ? `$${formatCurrency(activeTenant.current_llm_spend_usd, 0)} / $${formatCurrency(activeTenant.monthly_llm_budget_usd, 20)}`
              : "—"}
          </span>
        </div>

        {/* Selector Multi-Tenant */}
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <Building2 className="w-4 h-4 text-indigo-400" />
          <select
            value={activeTenant?.id ?? ""}
            disabled={availableTenants.length === 0}
            onChange={(e) => {
              const selected = availableTenants.find((t) => t.id === e.target.value);
              if (selected) {
                setActiveTenant(selected);
                setTenantId(selected.id);
                localStorage.setItem("tenantId", selected.id);
              }
            }}
            className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
          >
            {availableTenants.length === 0 ? (
              <option value="" className="bg-slate-900 text-slate-200">
                Sin tenant activo
              </option>
            ) : (
              availableTenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id} className="bg-slate-900 text-slate-200">
                  {tenant.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Campana de Notificaciones SSE */}
        <button
          onClick={() => setIsNotificationOpen(true)}
          className="relative p-2 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-slate-300 transition-colors"
          title="Notificaciones en Tiempo Real"
        >
          <Bell className="w-4 h-4 text-indigo-400" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 text-white text-[9px] font-mono font-bold rounded-full flex items-center justify-center animate-pulse">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      </div>

      <NotificationPanel
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
        notifications={notifications}
        unreadCount={unreadCount}
        onMarkAllRead={markAllAsRead}
        onClearAll={clearAll}
        tenantId={activeTenant?.id}
      />
    </header>
  );
}
