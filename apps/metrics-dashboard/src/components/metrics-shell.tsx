import Link from "next/link";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/gpus", label: "GPUs" },
  { href: "/runtime", label: "Runtime" },
];

export function MetricsShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_36%),linear-gradient(135deg,#020617,#09090b_45%,#000)] text-zinc-100">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-8 rounded-3xl border border-cyan-400/20 bg-black/40 p-4 shadow-2xl shadow-cyan-950/20 backdrop-blur">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <Link href="/" className="group">
              <p className="text-xs font-bold uppercase tracking-[0.35em] text-cyan-300">AI-LAB Metrics</p>
              <h1 className="mt-1 text-3xl font-black tracking-tight text-white group-hover:text-cyan-200 sm:text-4xl">
                Live Telemetry Portal
              </h1>
            </Link>
            <nav className="flex flex-wrap gap-2">
              {nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-full border border-zinc-700 bg-zinc-950/80 px-4 py-2 text-sm font-bold text-zinc-300 transition hover:border-cyan-400 hover:text-cyan-300"
                >
                  {item.label}
                </Link>
              ))}
              <a
                href="https://ai-lab.labrazahome.com"
                className="rounded-full border border-zinc-700 bg-zinc-950/80 px-4 py-2 text-sm font-bold text-zinc-500 transition hover:border-zinc-500 hover:text-zinc-200"
              >
                Docs
              </a>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="mt-10 border-t border-zinc-800 py-6 text-center text-xs text-zinc-600">
          <p>AI-LAB Cognitive Operations Runtime · Next.js SSR · Prometheus · Live API</p>
          <p className="mt-1">metricas.labrazahome.com</p>
        </footer>
      </div>
    </div>
  );
}
