"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen bg-[#080c14] text-slate-100 antialiased" suppressHydrationWarning>
        <div suppressHydrationWarning className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
          <h1 className="text-2xl font-bold">Error crítico</h1>
          <p className="text-slate-400">
            Ocurrió un error crítico en la aplicación.
          </p>
          <button
            onClick={reset}
            className="mt-2 rounded-xl bg-indigo-600 px-6 py-2.5 font-semibold text-white shadow-lg shadow-indigo-500/20 transition-colors hover:bg-indigo-500"
          >
            Reintentar
          </button>
        </div>
      </body>
    </html>
  );
}
