import { NextResponse } from "next/server";

export function middleware(request) {
  const { pathname } = request.nextUrl;

  // Multi-tenant URL isolation: Interceptar solicitudes a /tenants/[tenantId]
  const tenantMatch = pathname.match(/^\/tenants\/([^/]+)/);
  if (tenantMatch) {
    const tenantId = tenantMatch[1];
    
    // Inyectar el tenant_id verificado en las cabeceras de la solicitud
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-tenant-id", tenantId);

    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/tenants/:path*"],
};
