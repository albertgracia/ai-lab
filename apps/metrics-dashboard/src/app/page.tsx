import { Suspense } from "react";
import Link from "next/link";
import { GpuTelemetry } from "@/components/gpu-telemetry";
import { ClusterHealth } from "@/components/cluster-health";
import { RuntimeStatus } from "@/components/runtime-status";
import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { getTargets } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function Home() {
  const targets = await getTargets();
  const upTargets = targets.filter((target) => target.health === "up").length;

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-3xl border border-cyan-400/20 bg-zinc-950/70 p-8 shadow-2xl shadow-cyan-950/10">
            <p className="text-xs font-bold uppercase tracking-[0.35em] text-cyan-300">Telemetry Command Surface</p>
            <h2 className="mt-4 max-w-3xl text-4xl font-black leading-tight text-white sm:text-5xl">
              Operación viva del runtime, GPUs e infraestructura AI-LAB.
            </h2>
            <p className="mt-5 max-w-3xl text-zinc-400">
              Portal SSR local para datos live de Prometheus y Live API. Grafana queda como profundidad técnica; esta web resume el estado operativo navegable.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/gpus" className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-black text-zinc-950 hover:bg-cyan-200">Ver GPUs</Link>
              <Link href="/runtime" className="rounded-xl border border-zinc-700 px-5 py-3 text-sm font-black text-zinc-200 hover:border-purple-400 hover:text-purple-300">Ver Runtime</Link>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <MetricCard label="Prometheus Targets" value={`${upTargets}/${targets.length}`} hint="targets activos" tone={upTargets === targets.length ? "emerald" : "yellow"} />
            <MetricCard label="SSR Timestamp" value={new Date().toISOString().slice(11, 19)} hint="UTC · no-store" tone="cyan" />
          </div>
        </section>

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

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/70 p-6">
          <h2 className="text-lg font-black text-white">Prometheus Targets</h2>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {targets.map((target) => (
              <div key={`${target.job}-${target.instance}`} className="rounded-xl border border-zinc-800 bg-black/30 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-bold text-zinc-200">{target.job}</p>
                  <span className={target.health === "up" ? "text-xs font-black text-emerald-300" : "text-xs font-black text-red-300"}>{target.health}</span>
                </div>
                <p className="mt-1 truncate font-mono text-xs text-zinc-500">{target.instance}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </MetricsShell>
  );
}
