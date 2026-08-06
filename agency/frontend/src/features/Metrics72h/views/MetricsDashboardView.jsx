"use client";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { MetricClassificationCard } from "../components/MetricClassificationCard";
import { BarChart3 } from "lucide-react";

export function MetricsDashboardView({ tenantId }) {
  const mockMetrics = [
    {
      video_id: "video-55",
      published_at: "2026-08-03T10:00:00Z",
      metrics_72h: {
        views: 150000,
        followers_at_posting: 10000,
        ratio: 15.0,
        leads_generated: 142,
      },
      classification: "VERDE",
      action_taken: "Encolado para 3 variaciones en próximo batch.",
    },
    {
      video_id: "video-56",
      published_at: "2026-08-03T14:00:00Z",
      metrics_72h: {
        views: 4500,
        followers_at_posting: 10000,
        ratio: 0.45,
        leads_generated: 2,
      },
      classification: "ROJO",
      action_taken: "Idea descartada.",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-400" /> Clasificación 80/20 & Métricas 72h
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {mockMetrics.map((item) => (
              <MetricClassificationCard key={item.video_id} item={item} />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
