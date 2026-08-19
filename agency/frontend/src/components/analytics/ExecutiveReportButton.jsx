"use client";

import { useState } from "react";
import { FileDown, Loader2, CheckCircle, ShieldCheck } from "lucide-react";
import { getTenantHeader } from "@/services/apiConfig";

export function ExecutiveReportButton({ tenantId, className = "" }) {
  const [loading, setLoading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handleDownload = async () => {
    if (!tenantId || loading) return;

    try {
      setLoading(true);
      setDownloaded(false);

      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const headers = getTenantHeader(tenantId);

      const res = await fetch(`${apiBase}/tenants/${tenantId}/reports/monthly-pdf?download=true`, {
        headers,
      });

      if (!res.ok) {
        throw new Error(`Error en el servidor al generar el PDF (código ${res.status})`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Reporte_Ejecutivo_${tenantId.slice(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      setDownloaded(true);
      setTimeout(() => setDownloaded(false), 3000);
    } catch (err) {
      console.error("Error descargando reporte PDF:", err);
      alert(`No se pudo descargar el reporte PDF: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className={`bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all disabled:opacity-50 ${className}`}
      title="Descargar Reporte Ejecutivo en PDF (Marca Blanca)"
    >
      {loading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-indigo-200" />
          <span>Generando PDF...</span>
        </>
      ) : downloaded ? (
        <>
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          <span>PDF Descargado</span>
        </>
      ) : (
        <>
          <FileDown className="w-4 h-4 text-indigo-200" />
          <span>Reporte Ejecutivo PDF</span>
        </>
      )}
    </button>
  );
}
