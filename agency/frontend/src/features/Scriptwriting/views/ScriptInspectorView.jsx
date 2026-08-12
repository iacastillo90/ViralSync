import { useState, useEffect } from "react";
import { useTenantResource } from "@/hooks/useTenantResource";
import { Script4BlockReader } from "../components/Script4BlockReader";
import { FileText, Folder, FolderOpen, PlayCircle, Loader2, ArrowLeft, Video } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { fetchWithTenant } from "@/services/apiConfig";

export function ScriptInspectorView({ tenantId }) {
  const { data, loading, error, refresh } = useTenantResource("scripts", tenantId);
  const { data: productsData } = useTenantResource("products", tenantId);
  const searchParams = useSearchParams();
  const ideaIdParam = searchParams ? searchParams.get("ideaId") : null;

  const scripts = Array.isArray(data) ? data : [];
  const products = Array.isArray(productsData) ? productsData : [];

  // Polling automático cada 4 segundos para detectar nuevos guiones recien escritos
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
    }, 4000);
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

  // Asignar cada guion al producto correspondiente por fecha
  const findMatchingProduct = (itemCreatedAt) => {
    if (!products || products.length === 0) return null;
    if (!itemCreatedAt) return products[0];

    const itemTime = new Date(itemCreatedAt).getTime();
    let bestProduct = null;
    let minDiff = Infinity;

    for (const prod of products) {
      const prodTime = new Date(prod.created_at).getTime();
      const diff = itemTime - prodTime;
      if (diff >= -10000 && diff < minDiff) {
        minDiff = diff;
        bestProduct = prod;
      }
    }
    return bestProduct || products[0];
  };

  // Agrupar guiones en carpetas independientes por lote de generación (batch por timestamp)
  const groupedScriptsMap = scripts.reduce((acc, s) => {
    const scriptTime = new Date(s.created_at || Date.now()).getTime();

    // Buscar si ya existe un lote creado dentro de un margen de 30 segundos
    let matchedBatchKey = Object.keys(acc).find((key) => {
      const batchTime = acc[key].timestamp;
      return Math.abs(scriptTime - batchTime) < 30000;
    });

    const matchedProduct = findMatchingProduct(s.created_at);
    const productName = matchedProduct ? matchedProduct.name : "Guiones de Producto";

    if (!matchedBatchKey) {
      matchedBatchKey = `batch_${s.id || scriptTime}`;
      acc[matchedBatchKey] = {
        key: matchedBatchKey,
        name: productName,
        timestamp: scriptTime,
        createdAt: formatDate(s.created_at),
        items: [],
      };
    }

    acc[matchedBatchKey].items.push(s);
    return acc;
  }, {});

  const folderList = Object.values(groupedScriptsMap);

  const [activeFolder, setActiveFolder] = useState(ideaIdParam && folderList.length > 0 ? folderList[0].key : null);
  const [selectedScriptForVideo, setSelectedScriptForVideo] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [isVideoLoading, setIsVideoLoading] = useState(false);

  const handleOpenVideoModal = async (script) => {
    setSelectedScriptForVideo(script);
    setIsVideoLoading(true);
    setVideoUrl(null);

    try {
      // Intentar obtener el video desde la API de media / videos
      const res = await fetchWithTenant(`/tenants/${tenantId}/media`, {}, tenantId);
      if (Array.isArray(res) && res.length > 0) {
        const scriptTime = new Date(script.created_at || Date.now()).getTime();
        const videos = res.filter((m) => m.type === "video" || m.object_key?.endsWith(".mp4") || m.url?.includes(".mp4"));
        
        // Ordenar videos del más reciente al más antiguo
        videos.sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());

        // Encontrar el video creado alrededor o después del guion
        let matchedVideo = videos.find((v) => {
          const vTime = new Date(v.created_at || 0).getTime();
          return vTime >= scriptTime - 30000;
        });

        if (!matchedVideo && videos.length > 0) {
          matchedVideo = videos[0]; // fallback al video más reciente
        }

        if (matchedVideo && matchedVideo.url) {
          setVideoUrl(matchedVideo.url);
        }
      }
    } catch (err) {
      console.error("Error obteniendo video:", err);
    } finally {
      setIsVideoLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" /> Inspector de Guiones en 4 Bloques
          </h1>
          <p className="text-xs text-slate-400">
            Tenant: <span className="font-mono text-indigo-400">{tenantId}</span>
          </p>
        </div>
        <button
          onClick={refresh}
          className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition-colors"
        >
          Refrescar Guiones
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-3 text-sm text-slate-400 py-10">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" /> Cargando carpetas de guiones…
        </div>
      ) : error ? (
        <div className="text-sm text-rose-300 bg-rose-950/40 border border-rose-500/30 rounded-lg p-3">
          Error al cargar guiones: {error.message}
        </div>
      ) : scripts.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
          <Folder className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-slate-300 font-semibold">Sin guiones todavía</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Aprueba una idea en la pestaña de Ideación RUM para que el Guionista Viral genere la estructura narrativa.
          </p>
        </div>
      ) : !activeFolder ? (
        /* VISTA DE CARPETAS (FOLDER VIEW) */
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Carpetas de Guiones ({folderList.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {folderList.map((folder) => {
              const count = folder.items.length;
              return (
                <div
                  key={folder.key}
                  onClick={() => setActiveFolder(folder.key)}
                  className="bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-xl hover:shadow-indigo-500/10 group flex items-start gap-4"
                >
                  <div className="bg-indigo-600/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white p-3 rounded-xl transition-all">
                    <Folder className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                      {folder.name}
                    </h3>
                    <div className="flex flex-col gap-0.5 mt-1.5">
                      <span className="text-xs text-slate-400 font-medium">
                        {count} {count === 1 ? "guion generado" : "guiones generados"}
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
        /* VISTA DENTRO DE LA CARPETA SELECCIONADA / GUION AISLADO */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setActiveFolder(null)}
              className="flex items-center gap-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Volver a Carpetas
            </button>
            <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
              <FolderOpen className="w-4 h-4 text-indigo-400" /> Carpeta activa: <strong>{groupedScriptsMap[activeFolder]?.name}</strong>
            </span>
          </div>

          <div className="space-y-6">
            {(groupedScriptsMap[activeFolder]?.items || []).map((scriptItem) => (
              <div key={scriptItem.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                    Estructura Narrativa del Video
                  </h2>
                  <button
                    onClick={() => handleOpenVideoModal(scriptItem)}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-600/30"
                  >
                    <PlayCircle className="w-4 h-4" /> Ver Video Renderizado
                  </button>
                </div>
                <Script4BlockReader script={scriptItem} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal de Reproducción / Estado del Video */}
      {selectedScriptForVideo && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-800">
                <h3 className="font-bold text-slate-100 flex items-center gap-2">
                  <Video className="w-5 h-5 text-indigo-400" /> Estado del Video Final
                </h3>
                <button
                  onClick={() => setSelectedScriptForVideo(null)}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  ✕ Cerrar
                </button>
              </div>

              {isVideoLoading ? (
                <div className="py-12 text-center space-y-3">
                  <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
                  <p className="text-sm text-slate-300">Consultando estado del renderizado...</p>
                </div>
              ) : videoUrl ? (
                <div className="space-y-4">
                  <div className="aspect-[9/16] bg-black rounded-xl overflow-hidden max-h-[420px] mx-auto border border-slate-800 shadow-2xl flex items-center justify-center">
                    <video controls autoPlay src={videoUrl} className="w-full h-full object-contain" />
                  </div>
                  <a
                    href={videoUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="block text-center text-xs text-indigo-400 hover:underline font-medium"
                  >
                    Abrir video en ventana completa &rarr;
                  </a>
                </div>
              ) : (
                <div className="py-10 text-center space-y-4">
                  <div className="w-14 h-14 bg-indigo-600/20 text-indigo-400 rounded-full flex items-center justify-center mx-auto animate-pulse">
                    <Video className="w-7 h-7" />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-slate-100">Trabajando en el Video...</h4>
                    <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1">
                      El Renderizador Local de Emergencia está uniendo la voz artificial, los textos y los fondos. El proceso toma ~1-2 minutos.
                    </p>
                  </div>
                  <div className="pt-2">
                    <button
                      onClick={() => handleOpenVideoModal(selectedScriptForVideo)}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-4 py-2 rounded-xl transition-all border border-slate-700"
                    >
                      Comprobar de Nuevo
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}