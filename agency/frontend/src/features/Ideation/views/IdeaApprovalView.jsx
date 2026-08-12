"use client";

import { useState, useEffect } from "react";
import { useAgentStore } from "@/stores/useAgentStore";
import { useTenantResource } from "@/hooks/useTenantResource";
import { fetchWithTenant } from "@/services/apiConfig";
import { RUMBreakdownBarChart } from "../components/RUMBreakdownBarChart";
import { Sparkles, CheckCircle, XCircle, ArrowRight, PlayCircle, Folder, FolderOpen, Loader2, ArrowLeft } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

export function IdeaApprovalView({ tenantId }) {
  const { addLog } = useAgentStore();
  const { data, loading, error, refresh } = useTenantResource("ideas", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);
  const [queuedIds, setQueuedIds] = useState([]);
  const [decisionError, setDecisionError] = useState(null);
  const [isWritingScript, setIsWritingScript] = useState(false);
  const [approvedIdeaTitle, setApprovedIdeaTitle] = useState("");
  const [activeFolder, setActiveFolder] = useState(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlProduct = searchParams ? searchParams.get("product") : null;

  const ideas = Array.isArray(data) ? data : [];
  const products = Array.isArray(productsData) ? productsData : [];

  // Polling automático cada 3 segundos para mostrar la carpeta recién creada por la IA
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  // Formateador de fecha y hora pequeña
  const formatDate = (isoString) => {
    if (!isoString) return "";
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
  };

  // Asignar cada idea al producto más cercano por fecha de creación
  const findMatchingProduct = (itemCreatedAt) => {
    if (!products || products.length === 0) return null;
    if (!itemCreatedAt) return products[0];

    const itemTime = new Date(itemCreatedAt).getTime();
    let bestProduct = null;
    let minDiff = Infinity;

    for (const prod of products) {
      const prodTime = new Date(prod.created_at).getTime();
      const diff = itemTime - prodTime;
      // El producto debió crearse antes o casi al tiempo de la idea
      if (diff >= -10000 && diff < minDiff) {
        minDiff = diff;
        bestProduct = prod;
      }
    }
    return bestProduct || products[0];
  };

  // Agrupar las ideas en carpetas independientes por lote de generación (batch por timestamp)
  const groupedIdeasMap = ideas.reduce((acc, idea) => {
    const ideaTime = new Date(idea.created_at || Date.now()).getTime();
    
    // Buscar si ya existe un lote creado dentro de un margen de 30 segundos
    let matchedBatchKey = Object.keys(acc).find((key) => {
      const batchTime = acc[key].timestamp;
      return Math.abs(ideaTime - batchTime) < 30000;
    });

    const matchedProduct = findMatchingProduct(idea.created_at);
    const productName = matchedProduct ? matchedProduct.name : "Producto General";

    if (!matchedBatchKey) {
      matchedBatchKey = `batch_${idea.id || ideaTime}`;
      acc[matchedBatchKey] = {
        key: matchedBatchKey,
        name: productName,
        timestamp: ideaTime,
        createdAt: formatDate(idea.created_at),
        items: [],
      };
    } else {
      if (ideaTime > acc[matchedBatchKey].timestamp) {
        acc[matchedBatchKey].timestamp = ideaTime;
        acc[matchedBatchKey].createdAt = formatDate(idea.created_at);
      }
    }

    acc[matchedBatchKey].items.push(idea);
    return acc;
  }, {});

  // Ordenar carpetas y sus elementos por timestamp descendente (último lote de generación primero)
  const folderList = Object.values(groupedIdeasMap).sort((a, b) => b.timestamp - a.timestamp);
  folderList.forEach((folder) => {
    folder.items.sort(
      (a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    );
  });

  const handleDecision = async (idea, approved) => {
    setDecisionError(null);
    if (!idea || !idea.id) return;
    if (queuedIds.includes(idea.id) || idea.approval_status === "approved") return;

    addLog(`Idea ${approved ? "APROBADA" : "RECHAZADA"} por usuario: ${idea.id}`);
    setQueuedIds((prev) => [...prev, idea.id]);

    if (approved) {
      setIsWritingScript(true);
      setApprovedIdeaTitle(idea.texto);
    }

    try {
      await fetchWithTenant(
        `/tenants/${tenantId}/ideas/approve`,
        {
          method: "POST",
          body: JSON.stringify({
            idea_id: idea.id,
            status: approved ? "approved" : "rejected",
          }),
        },
        tenantId
      );

      if (approved) {
        // Esperar 10 segundos para dar tiempo a Celery de escribir el guion en DB antes de redirigir
        setTimeout(() => {
          setIsWritingScript(false);
          router.push(`/tenants/${tenantId}/guiones?ideaId=${idea.id}`);
        }, 10000);
      }
    } catch (err) {
      setDecisionError(err);
      setIsWritingScript(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" /> Checkpoint: Evaluación de Ideas RUM
          </h1>
          <p className="text-xs text-slate-400">
            Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
          </p>
        </div>
        <button 
          onClick={refresh}
          className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition-colors"
        >
          Refrescar Ideas
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-3 text-sm text-slate-400 py-10">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" /> Cargando carpetas de ideas…
        </div>
      ) : error ? (
        <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
          Error al cargar ideas: {error.message}
        </div>
      ) : ideas.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
          <Folder className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-slate-300 font-semibold">No hay carpetas ni ideas pendientes</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Sube un producto nuevo en el formulario inicial para que la Inteligencia Artificial genere sus carpetas de ideación.
          </p>
        </div>
      ) : !activeFolder ? (
        /* VISTA DE CARPETAS (FOLDER VIEW) */
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Carpetas por Producto ({folderList.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {folderList.map((folder, idx) => {
              const count = folder.items.length;
              const isLatest = idx === 0;
              return (
                <div
                  key={folder.key}
                  onClick={() => setActiveFolder(folder.key)}
                  className={`bg-slate-900 border rounded-2xl p-5 cursor-pointer transition-all hover:shadow-xl group flex items-start gap-4 relative ${
                    isLatest
                      ? "border-indigo-500/70 shadow-lg shadow-indigo-500/10 hover:border-indigo-400"
                      : "border-slate-800 hover:border-indigo-500/50 hover:shadow-indigo-500/10"
                  }`}
                >
                  {isLatest && (
                    <span className="absolute -top-2.5 right-4 bg-indigo-600 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full shadow-md shadow-indigo-600/40 flex items-center gap-1">
                      ✨ NUEVO LOTE
                    </span>
                  )}
                  <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all">
                    <Folder className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                      {folder.name}
                    </h3>
                    <div className="flex flex-col gap-0.5 mt-1.5">
                      <span className="text-xs text-slate-400 font-medium">
                        {count} {count === 1 ? "idea candidata" : "ideas candidatas"}
                      </span>
                      {folder.createdAt && (
                        <span className="text-[11px] text-indigo-400/80 font-mono">
                          🕒 {folder.createdAt}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* VISTA DENTRO DE LA CARPETA SELECCIONADA */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setActiveFolder(null)}
              className="flex items-center gap-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Volver a Carpetas
            </button>
            <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
              <FolderOpen className="w-4 h-4 text-indigo-400" /> Carpeta activa: <strong>{groupedIdeasMap[activeFolder]?.name}</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {(groupedIdeasMap[activeFolder]?.items || []).map((idea) => {
              const isApproved = idea.approval_status === "approved" || queuedIds.includes(idea.id);
              const isRejected = idea.approval_status === "rejected";

              return (
                <div key={idea.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex justify-between items-start">
                    <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2.5 py-1 rounded-full font-bold">
                      Candidata RUM (Score: {idea.rum_score ?? "—"} |{" "}
                      {idea.passes_threshold === true ? "PASS" : "PENDIENTE"})
                    </span>
                    <span className="text-xs font-mono text-slate-400">{idea.approval_status}</span>
                  </div>

                  <h2 className="text-lg font-bold text-slate-100">{idea.texto}</h2>
                  <p className="text-sm text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-xs text-slate-500 block mb-1 uppercase font-semibold">Gancho Viral (0-5s):</span>
                    "{idea.gancho ?? "—"}"
                  </p>

                  <div className="flex gap-4 text-xs text-slate-300">
                    <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                      Niño 5 Años:{" "}
                      <strong className={idea.entendible_nino_5_anos === true ? "text-emerald-400" : "text-slate-400"}>
                        {idea.entendible_nino_5_anos === true ? "SI" : idea.entendible_nino_5_anos === false ? "NO" : "—"}
                      </strong>
                    </span>
                    <span className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                      Interés 50/100:{" "}
                      <strong className={idea.interesa_50_de_100 === true ? "text-emerald-400" : "text-slate-400"}>
                        {idea.interesa_50_de_100 === true ? "SI" : idea.interesa_50_de_100 === false ? "NO" : "—"}
                      </strong>
                    </span>
                  </div>

                  <RUMBreakdownBarChart metrics={idea} />

                  {isApproved ? (
                    <div className="bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 px-4 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" /> Idea Aprobada — Guion Generado
                    </div>
                  ) : isRejected ? (
                    <div className="bg-rose-950/60 border border-rose-500/40 text-rose-300 px-4 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2">
                      <XCircle className="w-4 h-4 text-rose-400" /> Idea Rechazada
                    </div>
                  ) : (
                    <div className="flex gap-3 pt-2">
                      <button
                        onClick={() => handleDecision(idea, true)}
                        className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-lg transition-all shadow-lg shadow-emerald-600/20"
                      >
                        <CheckCircle className="w-4 h-4" /> Aprobar Idea
                      </button>
                      <button
                        onClick={() => handleDecision(idea, false)}
                        className="flex-1 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-medium py-2.5 rounded-lg transition-all"
                      >
                        <XCircle className="w-4 h-4" /> Rechazar
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Modal Bloqueante de Redacción de Guion */}
      {isWritingScript && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full shadow-2xl p-6 text-center">
            <div className="w-16 h-16 bg-indigo-500/20 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-4 animate-spin">
              <Sparkles className="w-8 h-8" />
            </div>
            <h3 className="text-2xl font-bold text-slate-100 mb-2">Redactando Guion Viral...</h3>
            <p className="text-slate-300 mb-6 text-xs leading-relaxed">
              La IA está estructurando la narrativa en 4 bloques para "<strong>{approvedIdeaTitle}</strong>" y enviando la orden de renderizado.
            </p>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div className="bg-indigo-500 h-full animate-pulse w-3/4 rounded-full"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}