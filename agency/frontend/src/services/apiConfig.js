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
    const error = new Error(`HTTP Error ${response.status} en endpoint ${endpoint}`);
    error.status = response.status;
    if (response.status === 429) {
      error.retryAfter = response.headers.get("Retry-After") || "60";
    }
    throw error;
  }
  return response.json();
}

export async function getPresignedUploadUrl(tenantId, filename) {
  return fetchWithTenant(`/${tenantId}/ingestion/presigned-upload-url`, {
    method: "POST",
    body: JSON.stringify({ filename }),
  }, tenantId);
}

export async function uploadFileWithPresignedUrl(tenantId, file) {
  const { upload_url, object_key } = await getPresignedUploadUrl(tenantId, file.name);
  const putResponse = await fetch(upload_url, {
    method: "PUT",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
  if (!putResponse.ok) {
    throw new Error(`Error al subir archivo a S3/MinIO (${putResponse.status})`);
  }
  return { object_key, filename: file.name };
}


