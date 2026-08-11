import React, { useState } from "react";

/**
 * BatchIngestView.jsx
 * Vista de Carga Masiva de Productos e Ingesta Multi-Media conectada a
 * POST /api/v1/tenants/{tenant_id}/products/batch
 */
export default function BatchIngestView({ tenantId = "default_tenant" }) {
  const [products, setProducts] = useState([
    { product_name: "", description: "", product_image_url: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleFieldChange = (index, field, value) => {
    const updated = [...products];
    updated[index][field] = value;
    setProducts(updated);
  };

  const addRow = () => {
    setProducts((prev) => [
      ...prev,
      { product_name: "", description: "", product_image_url: "" },
    ]);
  };

  const removeRow = (index) => {
    if (products.length <= 1) return;
    setProducts((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    const validProducts = products.filter((p) => p.product_name.trim() !== "");
    if (validProducts.length === 0) {
      setMessage({ type: "error", text: "Ingresa al menos un nombre de producto válido." });
      setLoading(false);
      return;
    }

    try:
      const res = await fetch(`/api/v1/tenants/${tenantId}/products/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ products: validProducts }),
      });
      const data = await res.json();

      if (res.ok) {
        setMessage({
          type: "success",
          text: `Procesados ${data.ingested_count} productos exitosamente.`,
        });
        setProducts([{ product_name: "", description: "", product_image_url: "" }]);
      } else {
        setMessage({ type: "error", text: data.detail || "Error en ingesta masiva." });
      }
    } catch (err) {
      setMessage({ type: "error", text: `Error de conexión: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-3xl p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-xl space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100">
            Ingesta Masiva de Productos y Medios
          </h2>
          <p className="text-xs text-slate-400">
            Carga múltiples registros de producto con presignado MinIO/S3 y notificación SSE en vivo.
          </p>
        </div>
        <button
          type="button"
          onClick={addRow}
          className="text-xs font-semibold px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
        >
          + Agregar Producto
        </button>
      </div>

      {message && (
        <div
          className={`p-3 rounded-lg text-xs font-medium ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
          }`}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {products.map((item, idx) => (
          <div
            key={idx}
            className="p-4 bg-slate-950/80 border border-slate-800 rounded-lg space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400">
                Producto #{idx + 1}
              </span>
              {products.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeRow(idx)}
                  className="text-xs text-rose-400 hover:text-rose-300"
                >
                  Eliminar
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Nombre del Producto *"
                value={item.product_name}
                onChange={(e) => handleFieldChange(idx, "product_name", e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-indigo-500"
                required
              />
              <input
                type="text"
                placeholder="URL de Imagen (Opcional)"
                value={item.product_image_url}
                onChange={(e) => handleFieldChange(idx, "product_image_url", e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <textarea
              placeholder="Descripción / Propuesta de Valor *"
              value={item.description}
              onChange={(e) => handleFieldChange(idx, "description", e.target.value)}
              rows={2}
              className="w-full text-xs p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>
        ))}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 text-xs font-bold uppercase tracking-wider bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg transition"
        >
          {loading ? "Procesando Ingesta..." : "Ejecutar Ingesta Masiva"}
        </button>
      </form>
    </div>
  );
}
