const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchWithTenant(endpoint, options = {}, tenantId) {
  let token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  
  if (!tenantId || tenantId === "nuevo" || tenantId === "null" || tenantId === "undefined") {
    tenantId = typeof window !== "undefined" ? localStorage.getItem("tenantId") : null;
  }
  if (tenantId === "nuevo" || tenantId === "null" || tenantId === "undefined") {
    tenantId = null;
  }
  if (!tenantId) {
    console.warn("No tenantId provided or found in localStorage. Request may fail if endpoint requires it.");
  }

  const defaultHeaders = {
    "Content-Type": "application/json",
    ...(tenantId && { "X-Tenant-ID": tenantId }),
  };

  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  if (!response.ok) {
    throw new Error(`HTTP Error ${response.status} en endpoint ${endpoint}`);
  }
  return response.json();
}

