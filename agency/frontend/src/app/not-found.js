import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#080c14] px-6 text-center text-slate-100">
      <h1 className="text-6xl font-bold text-indigo-400">404</h1>
      <h2 className="text-2xl font-semibold">Página no encontrada</h2>
      <p className="text-slate-400">
        La página que buscas no existe o fue movida.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-xl bg-indigo-600 px-6 py-2.5 font-semibold text-white shadow-lg shadow-indigo-500/20 transition-colors hover:bg-indigo-500"
      >
        Volver al inicio
      </Link>
    </div>
  );
}
