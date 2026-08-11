import "./globals.css";

export const metadata = {
  title: "Agencia Multiagente de Marketing | Dashboard",
  description: "Sistema Multiagente de Automatización de Contenido e Inbound Marketing",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen bg-[#080c14] text-slate-100 antialiased selection:bg-cyan-500 selection:text-white" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
