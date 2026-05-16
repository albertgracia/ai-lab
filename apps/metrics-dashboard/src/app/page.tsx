import { Suspense } from "react";
import Link from "next/link";
import { GpuTelemetry } from "@/components/gpu-telemetry";
import { ClusterHealth } from "@/components/cluster-health";
import { RuntimeStatus } from "@/components/runtime-status";
import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { SectionHeading } from "@/components/section-heading";
import { getTargets } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function Home() {
  const targets = await getTargets();
  const upTargets = targets.filter((target) => target.health === "up").length;

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="grid gap-6 lg:grid-cols-[1.55fr_0.9fr]">
          <div className="lab-panel relative overflow-hidden rounded-[2rem] p-8 sm:p-10">
            <div className="absolute right-8 top-8 hidden rounded-full border border-cyan-300/20 px-3 py-1 font-mono text-[0.65rem] uppercase tracking-[0.24em] text-cyan-200/70 sm:block">
              Prometheus Live
            </div>
            <p className="font-mono text-[0.7rem] font-bold uppercase tracking-[0.38em] text-cyan-200">Telemetry Command Surface</p>
            <h2 className="mt-5 max-w-3xl text-5xl font-bold leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">
              Operación viva del runtime, GPUs e infraestructura AI-LAB.
            </h2>
            <p className="mt-6 max-w-3xl text-base leading-7 text-zinc-400">
              Portal SSR local para datos live de Prometheus y Live API. Grafana queda como profundidad técnica; esta web resume el estado operativo navegable.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/gpus" className="rounded-2xl bg-cyan-200 px-5 py-3 text-sm font-bold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.18)] hover:bg-cyan-100">Ver GPUs</Link>
              <Link href="/runtime" className="rounded-2xl border border-purple-300/30 bg-purple-300/5 px-5 py-3 text-sm font-bold text-purple-100 hover:border-purple-300/60">Ver Runtime</Link>
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
          <SectionHeading eyebrow="GPU mesh" title="GPU Telemetry" description="Lectura rápida de temperatura, VRAM, potencia y clocks por nodo." />
          <Suspense fallback={<p className="text-zinc-500 italic">Cargando GPUs...</p>}>
            <GpuTelemetry />
          </Suspense>
        </section>

        <Suspense fallback={<p className="text-zinc-500 italic">Cargando runtime...</p>}>
          <RuntimeStatus />
        </Suspense>

        <section className="lab-panel rounded-[2rem] p-6">
          <SectionHeading eyebrow="Scrape matrix" title="Prometheus Targets" description="Estado de exporters, sensores GPU, gateway, Docker y túneles." />
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {targets.map((target) => (
              <div key={`${target.job}-${target.instance}`} className="rounded-2xl border border-zinc-800/80 bg-black/30 p-3 transition hover:border-cyan-300/30">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-bold text-zinc-200">{target.job}</p>
                  <span className={target.health === "up" ? "font-mono text-xs font-bold text-emerald-300" : "font-mono text-xs font-bold text-red-300"}>{target.health}</span>
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
