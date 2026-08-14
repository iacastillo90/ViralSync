"use client";

import { useEffect, useState } from "react";
import { fetchWithTenant } from "@/services/apiConfig";

/**
 * useTenantResource
 *
 * Shared tri-state fetch wrapper over fetchWithTenant (design D6 / REQ-FEAT-4).
 * Endpoint is the short resource name ("ideas", "scripts", "brain", "metrics")
 * and the hook builds `/tenants/${tenantId}/${endpoint}`.
 *
 * Returns { data, loading, error }:
 *  - data:    raw parsed payload (null while loading / on error)
 *  - loading: true while a request is in flight
 *  - error:   Error on rejection (401/403/404/5xx/network), null otherwise
 *
 * Consumers guard the shape: array views use Array.isArray(data), the brain
 * view consumes the object directly. AbortController + ignore-AbortError
 * follows the InboundLeadsView pattern (no state updates on unmount).
 */
export function useTenantResource(endpoint, tenantId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [trigger, setTrigger] = useState(0);

  const refresh = () => setTrigger((prev) => prev + 1);

  useEffect(() => {
    const controller = new AbortController();
    // Solo activamos estado de carga inicial si data es null,
    // evitando el parpadeo constante y desmontaje de la interfaz al refrescar en segundo plano.
    if (data === null) {
      setLoading(true);
    }
    setError(null);

    if (
      !tenantId ||
      tenantId === "null" ||
      tenantId === "undefined" ||
      tenantId === "nuevo"
    ) {
      setError(new Error("Sin tenant activo"));
      setLoading(false);
      return undefined;
    }

    fetchWithTenant(
      `/tenants/${tenantId}/${endpoint}`,
      { signal: controller.signal },
      tenantId
    )
      .then((payload) => {
        if (payload) setData(payload);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.warn(`[useTenantResource] Reintento en /${endpoint}:`, err.message);
          setError(err);
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [endpoint, tenantId, trigger]);

  return { data, loading, error, refresh };
}