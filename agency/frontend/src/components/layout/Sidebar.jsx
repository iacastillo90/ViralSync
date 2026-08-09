"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Layers,
  Sparkles,
  FileText,
  MessageSquare,
  BarChart3,
  Brain,
  ShieldCheck,
} from "lucide-react";

// tenantId is required; always passed by call sites (no demo fallback).
export function Sidebar({ tenantId }) {
  const pathname = usePathname();

  const navItems = [
    { label: "Pipeline Monitor", icon: Layers, href: `/tenants/${tenantId}/pipeline` },
    { label: "Ideación RUM", icon: Sparkles, href: `/tenants/${tenantId}/aprobaciones/ideas` },
    { label: "Guiones 4 Bloques", icon: FileText, href: `/tenants/${tenantId}/guiones` },
    { label: "Leads Inbound", icon: MessageSquare, href: `/tenants/${tenantId}/leads` },
    { label: "Métricas 72h", icon: BarChart3, href: `/tenants/${tenantId}/metricas` },
    { label: "Cerebro RAG", icon: Brain, href: `/tenants/${tenantId}/cerebro` },
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
              key={item.href}
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
        <p className="font-semibold text-slate-300 mb-1">Aislamiento Activo</p>
        <p className="truncate font-mono text-indigo-400">{tenantId}</p>
      </div>
    </aside>
  );
}
