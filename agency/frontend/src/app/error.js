"use client";

import { useEffect } from "react";

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-[#080c14] px-6 text-center text-slate-100">
      <h1 className="text-2xl font-bold">Algo salió mal</h1>
      <p className="text-slate-400">
        Ocurrió un error inesperado al cargar esta página.
      </p>
      <button
        onClick={reset}
        className="mt-2 rounded-xl bg-indigo-600 px-6 py-2.5 font-semibold text-white shadow-lg shadow-indigo-500/20 transition-colors hover:bg-indigo-500"
      >
        Reintentar
      </button>
    </div>
  );
}
