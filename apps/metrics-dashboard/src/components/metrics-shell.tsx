import Link from "next/link";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/ops", label: "Ops" },
  { href: "/gpus", label: "GPUs" },
  { href: "/runtime", label: "Runtime" },
];

export function MetricsShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="lab-grid min-h-screen overflow-hidden bg-[radial-gradient(circle_at_12%_8%,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_88%_18%,rgba(168,85,247,0.13),transparent_28%),linear-gradient(135deg,#020617,#09090b_46%,#000)] text-zinc-100">
      <div className="pointer-events-none fixed inset-x-0 top-0 h-24 bg-gradient-to-b from-cyan-300/10 to-transparent" />
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="lab-panel mb-8 rounded-[2rem] p-4 backdrop-blur-xl">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <Link href="/" className="group flex items-center gap-4">
              <div className="grid h-16 w-16 place-items-center rounded-2xl border border-cyan-300/20 bg-black/35 p-2 shadow-[0_0_36px_rgba(34,211,238,0.18)]">
                <img
                  src="https://ai-lab.labrazahome.com/images/ai-lab-logo.png"
                  alt="AI-LAB"
                  className="h-full w-full object-contain transition group-hover:scale-105"
                />
              </div>
              <div>
                <p className="text-[0.65rem] font-bold uppercase tracking-[0.42em] text-cyan-200">AI-LAB Metrics</p>
                <h1 className="mt-1 text-3xl font-bold tracking-[-0.04em] text-white group-hover:text-cyan-100 sm:text-4xl">
                  Telemetry Control
                </h1>
              </div>
            </Link>
            <nav className="flex flex-wrap gap-2 rounded-2xl border border-white/5 bg-black/30 p-1.5">
              {nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-xl border border-transparent px-4 py-2 text-sm font-bold text-zinc-300 transition hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-cyan-100"
                >
                  {item.label}
                </Link>
              ))}
              <a
                href="https://ai-lab.labrazahome.com"
                className="rounded-xl border border-transparent px-4 py-2 text-sm font-bold text-zinc-500 transition hover:border-zinc-500/40 hover:bg-zinc-900 hover:text-zinc-200"
              >
                Docs
              </a>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="mt-10 border-t border-zinc-800/80 py-6 text-center font-mono text-xs text-zinc-600">
          <p>AI-LAB Cognitive Operations Runtime · Next.js SSR · Prometheus · Live API</p>
          <p className="mt-1">metricas.labrazahome.com</p>
        </footer>
      </div>
    </div>
  );
}
