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

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
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
      .then((payload) => setData(payload))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [endpoint, tenantId]);

  return { data, loading, error };
}