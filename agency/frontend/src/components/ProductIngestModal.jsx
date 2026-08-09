"use client";

import { useState } from "react";
import { Upload, Sparkles, Image as ImageIcon, CheckCircle2, Box, Layers } from "lucide-react";
import { useAgentStore } from "@/stores/useAgentStore";

export default function ProductIngestModal({ onIngested }) {
  const { tenantId, addLog } = useAgentStore();
  const [productName, setProductName] = useState("");
  const [description, setDescription] = useState("");
  const [businessType, setBusinessType] = useState("auto");
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [ingestedResult, setIngestedResult] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!productName || !description) return;

    setLoading(true);
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    const formData = new FormData();
    formData.append("product_name", productName);
    formData.append("description", description);
    formData.append("business_type", businessType);
    if (selectedFile) {
      formData.append("file", selectedFile);
    }

    try {
      addLog(`Subiendo foto y registrando producto '${productName}' en MinIO...`);
      const res = await fetch(`${apiBase}/tenants/${tenantId}/product-ingest`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      setIngestedResult(data);
      addLog(`Producto ingestado exitosamente en MinIO: ${data.product_image_url}`);

      // Iniciar el flujo de LangGraph automáticamente
      await fetch(`${apiBase}/tenants/${tenantId}/graph/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_reideation: true }),
      });

      if (onIngested) onIngested(data);
    } catch (err) {
      addLog(`Error al ingestar producto: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl my-6">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="bg-indigo-600/20 text-indigo-400 p-2.5 rounded-xl border border-indigo-500/30">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">Crear Reel con IA (Ingesta de Producto)</h2>
          <p className="text-xs text-slate-400">
            Sube la foto y descripción de tu producto. La IA guardará la imagen en MinIO y generará el video adaptado.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
              Nombre del Producto o Servicio
            </label>
            <input
              type="text"
              required
              placeholder="Ej: Suplemento Nootrópico AlphaMind"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
              Tipo de Oferta
            </label>
            <select
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="auto">✨ Detección Automática por IA</option>
              <option value="PRODUCTO_FISICO">📦 Producto Físico (Image-to-Video)</option>
              <option value="SERVICIO_INTANGIBLE">💼 Servicio Intangible (Text-to-Video)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
            Descripción y Promesa de Valor
          </label>
          <textarea
            required
            rows={3}
            placeholder="Describe las características principales, dolor del cliente que resuelve y beneficios clave..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Zona de Carga de Foto de Producto */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
            Foto del Producto (Almacenada en MinIO para Image-to-Video)
          </label>
          <div className="flex items-center gap-4">
            <label className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl p-4 cursor-pointer bg-slate-950/50 transition-all">
              <Upload className="w-6 h-6 text-indigo-400 mb-1" />
              <span className="text-xs text-slate-300 font-medium">
                {selectedFile ? selectedFile.name : "Haz clic para subir la foto del producto"}
              </span>
              <span className="text-[10px] text-slate-500">JPG, PNG o WEBP (Formato recomendado 9:16 o 1:1)</span>
              <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </label>

            {previewUrl && (
              <div className="relative w-20 h-20 rounded-xl overflow-hidden border border-slate-700 bg-slate-950 shrink-0">
                <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
              </div>
            )}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
        >
          {loading ? (
            <span>Procesando e iniciando IA...</span>
          ) : (
            <>
              <Sparkles className="w-4 h-4" /> Generar Reel con IA (Image-to-Video)
            </>
          )}
        </button>

        {ingestedResult && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <div>
                <strong>¡Producto guardado en MinIO!</strong> Clasificado como{" "}
                <span className="font-mono bg-emerald-900/60 px-2 py-0.5 rounded text-emerald-200">
                  {typeof ingestedResult.classification === "object"
                    ? ingestedResult.classification?.business_type || "PRODUCTO_FISICO"
                    : ingestedResult.classification || "PRODUCTO_FISICO"}
                </span>{" "}
                (
                {typeof ingestedResult.classification === "object"
                  ? ingestedResult.classification?.visual_mode || "IMAGE_TO_VIDEO"
                  : "IMAGE_TO_VIDEO"}
                ).
              </div>
            </div>
            {tenantId && (
              <a
                href={`/tenants/${tenantId}/media`}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg font-medium text-xs transition-all shrink-0 flex items-center gap-1 shadow-md shadow-indigo-600/30"
              >
                Ver en Galería MinIO &rarr;
              </a>
            )}
          </div>
        )}
      </form>
    </div>
  );
}
