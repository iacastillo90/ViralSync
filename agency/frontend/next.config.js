// Fail fast on PRODUCTION BUILDS only: without the API/SSE URLs the client
// would silently fall back to localhost and ship broken. Use the Next.js build
// phase so the runtime `next start` (which already inlined NEXT_PUBLIC_* at
// build time) is not blocked. Dev builds (`next dev`) keep working.
//
// Local smoke-test builds: `next build` always runs with NODE_ENV=production,
// and localhost URLs are forbidden by default. If you need a LOCAL test build
// (CI gate, prerender check) with localhost endpoints, set the explicit
// opt-out `NEXT_PUBLIC_ALLOW_LOCALHOST=true`. Production runs never set it.
const { PHASE_PRODUCTION_BUILD } = require("next/constants");

module.exports = (phase) => {
  if (phase === PHASE_PRODUCTION_BUILD) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const sseUrl = process.env.NEXT_PUBLIC_SSE_URL;
    if (!apiUrl || !sseUrl) {
      throw new Error(
        "NEXT_PUBLIC_API_URL and NEXT_PUBLIC_SSE_URL are REQUIRED for production builds. Set them in the build environment (e.g. NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1 NEXT_PUBLIC_SSE_URL=https://api.yourdomain.com/realtime/sse npm run build)."
      );
    }
    const allowLocalhost = process.env.NEXT_PUBLIC_ALLOW_LOCALHOST === "true";
    const localRef =
      apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1") || sseUrl.includes("localhost") || sseUrl.includes("127.0.0.1");
    if (localRef && !allowLocalhost) {
      throw new Error(
        "NEXT_PUBLIC_API_URL and NEXT_PUBLIC_SSE_URL must point to a real deployed backend in production builds; localhost/127.0.0.1 values are forbidden (they would silently hit the client's own machine). For a LOCAL smoke build set NEXT_PUBLIC_ALLOW_LOCALHOST=true."
      );
    }
  }
  return {
    reactStrictMode: true,
  };
};