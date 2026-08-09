"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTenantStore } from "@/stores/useTenantStore";
import { useAgentStore } from "@/stores/useAgentStore";
import {
  Layers,
  Sparkles,
  FileText,
  MessageSquare,
  BarChart3,
  Brain,
  Film,
  ShieldCheck,
} from "lucide-react";

export function Sidebar({ tenantId }) {
  const pathname = usePathname();
  const { activeTenant } = useTenantStore();
  const { tenantId: storeTenantId } = useAgentStore();

  const effectiveTenantId =
    tenantId && tenantId !== "nuevo"
      ? tenantId
      : activeTenant?.id || storeTenantId || "nuevo";

  const navItems = [
    {
      label: "Pipeline Monitor",
      icon: Layers,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/pipeline`,
    },
    {
      label: "Ideación RUM",
      icon: Sparkles,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/aprobaciones/ideas`,
    },
    {
      label: "Guiones 4 Bloques",
      icon: FileText,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/guiones`,
    },
    {
      label: "Leads Inbound",
      icon: MessageSquare,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/leads`,
    },
    {
      label: "Métricas 72h",
      icon: BarChart3,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/metricas`,
    },
    {
      label: "Cerebro RAG",
      icon: Brain,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/cerebro`,
    },
    {
      label: "Videos & Media MinIO",
      icon: Film,
      href: effectiveTenantId === "nuevo" ? "/tenants/nuevo" : `/tenants/${effectiveTenantId}/media`,
    },
    { label: "Admin Sistema", icon: ShieldCheck, href: "/admin/sistema" },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 text-slate-300 min-h-screen flex flex-col justify-between">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wider text-slate-500 px-3 mb-3 font-semibold">
          Navegación DDD
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                  : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </div>

      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-400">
        <p className="font-semibold text-slate-300 mb-1 truncate">
          {activeTenant?.name ? activeTenant.name : "Aislamiento Activo"}
        </p>
        <p className="truncate font-mono text-indigo-400">
          {effectiveTenantId === "nuevo" ? "Sin Tenant Configurado" : effectiveTenantId}
        </p>
      </div>
    </aside>
  );
}
