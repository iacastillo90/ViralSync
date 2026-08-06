"use client";

import { useAgentStore } from "@/stores/useAgentStore";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Video, CheckCircle, XCircle } from "lucide-react";

export function PublishApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();

  const handleDecision = async (approved) => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    addLog(`Publicación de video ${approved ? "APROBADA" : "RECHAZADA"}`);
    await fetch(`${apiBase}/tenants/${tenantId}/publish/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: approved ? "approved" : "rejected",
      }),
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar tenantId={tenantId} />
        <main className="flex-1 p-6 space-y-6">
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Video className="w-5 h-5 text-indigo-400" /> Checkpoint: Aprobación de Publicación
              </h1>
              <p className="text-xs text-slate-400">
                Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
              </p>
            </div>
          </div>

          <div className="max-w-2xl bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-full font-semibold">
              Video Editado & Subtitulado Listo
            </span>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <p className="text-xs text-slate-400">URI de Video en S3/R2:</p>
              <p className="text-sm font-mono text-indigo-400 break-all">
                s3://viralsync-media-dev/{tenantId}/edited_output.mp4
              </p>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => handleDecision(true)}
                className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all"
              >
                <CheckCircle className="w-4 h-4" /> Aprobar Publicación en Instagram
              </button>
              <button
                onClick={() => handleDecision(false)}
                className="flex-1 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium py-2.5 rounded-lg transition-all"
              >
                <XCircle className="w-4 h-4" /> Rechazar
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
