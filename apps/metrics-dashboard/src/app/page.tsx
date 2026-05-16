import { Suspense } from "react";
import { GpuTelemetry } from "@/components/gpu-telemetry";
import { ClusterHealth } from "@/components/cluster-health";
import { RuntimeStatus } from "@/components/runtime-status";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function Home() {
  return (
    <div className="min-h-screen bg-black">
      <div className="mx-auto max-w-7xl px-4 py-8 space-y-8">
        <header className="border-b border-zinc-800 pb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-cyan-400">AI-LAB METRICS</p>
              <h1 className="mt-2 text-4xl font-black text-white">Telemetry Dashboard</h1>
              <p className="mt-1 text-sm text-zinc-400">
                Datos en vivo de <span className="text-cyan-400">Prometheus</span> ·{" "}
                <span className="text-emerald-400">GPU</span> ·{" "}
                <span className="text-purple-400">Runtime</span>
              </p>
            </div>
            <div className="text-right text-xs text-zinc-600">
              <p>Última actualización: servidor</p>
              <p className="font-mono">SSR · {new Date().toISOString().slice(0, 19).replace("T", " ")} UTC</p>
            </div>
          </div>
        </header>

        <Suspense fallback={<p className="text-zinc-500 italic">Cargando health...</p>}>
          <ClusterHealth />
        </Suspense>

        <section>
          <h2 className="text-lg font-bold text-cyan-400 mb-4">GPU Telemetry</h2>
          <Suspense fallback={<p className="text-zinc-500 italic">Cargando GPUs...</p>}>
            <GpuTelemetry />
          </Suspense>
        </section>

        <Suspense fallback={<p className="text-zinc-500 italic">Cargando runtime...</p>}>
          <RuntimeStatus />
        </Suspense>

        <footer className="border-t border-zinc-800 pt-6 text-center text-xs text-zinc-600">
          <p>AI-LAB Cognitive Operations Runtime · metricas.labrazahome.com</p>
          <p className="mt-1">Datos servidos desde Prometheus + Live API via Next.js SSR</p>
        </footer>
      </div>
    </div>
  );
}
