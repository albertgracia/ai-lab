import Link from "next/link";
import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { SectionHeading } from "@/components/section-heading";
import { getGpuData, getHealth, getRuntime, getTargets, getWatchdog } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function StatusPill({ ok }: { ok: boolean }) {
  return (
    <span className={ok ? "font-mono text-xs font-bold text-emerald-300" : "font-mono text-xs font-bold text-red-300"}>
      {ok ? "ok" : "fail"}
    </span>
  );
}

export default async function OpsPage() {
  const [health, watchdog, runtime, targets, gpus] = await Promise.all([
    getHealth(),
    getWatchdog(),
    getRuntime(),
    getTargets(),
    getGpuData(),
  ]);

  const upTargets = targets.filter((target) => target.health === "up").length;
  const maxGpuTemp = Math.max(0, ...gpus.flatMap((gpu) => [gpu.temp, gpu.memTemp, gpu.hotSpot]));
  const totalPower = gpus.reduce((sum, gpu) => sum + gpu.power, 0);
  const pendingActions = runtime?.pendingActions || 0;

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="lab-panel rounded-[2rem] p-8 sm:p-10">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="font-mono text-[0.7rem] font-bold uppercase tracking-[0.38em] text-cyan-200">AI-LAB Command Center</p>
              <h2 className="mt-4 max-w-4xl text-5xl font-bold leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">
                Operations Center live, servido desde Next.js SSR.
              </h2>
              <p className="mt-5 max-w-3xl text-base leading-7 text-zinc-400">
                Clon operativo del antiguo `/ops` de Astro: health score, métricas de inferencia, watchdog, runtime autónomo y estado del cluster en una superficie live.
              </p>
            </div>
            <div className="min-w-40 rounded-[2rem] border border-cyan-300/20 bg-black/30 p-6 text-center">
              <p className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-zinc-500">Health Score</p>
              <p className={(health?.score || 0) >= 80 ? "mt-2 text-6xl font-bold tracking-[-0.08em] text-emerald-300" : "mt-2 text-6xl font-bold tracking-[-0.08em] text-yellow-300"}>
                {health?.score || 0}
              </p>
              <p className="font-mono text-xs text-zinc-500">{health?.level || "--"}</p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="GPU Cluster" value={`${gpus.length} GPUs`} hint={`max ${maxGpuTemp.toFixed(0)} C · ${totalPower.toFixed(0)} W`} tone="cyan" />
          <MetricCard label="Requests" value={(health?.requestsTotal || 0).toLocaleString()} hint={`${runtime?.requestsPerMinute.toFixed(2) || "0.00"} req/min`} tone="zinc" />
          <MetricCard label="Active Sessions" value={health?.activeSessions || 0} hint={`${runtime?.activeStreams || 0} active streams`} tone="emerald" />
          <MetricCard label="Prometheus" value={`${upTargets}/${targets.length}`} hint="targets up" tone={upTargets === targets.length ? "emerald" : "yellow"} />
          <MetricCard label="Latency" value={`${runtime?.latencyMs.toFixed(0) || 0} ms`} hint="gateway last latency" tone={(runtime?.latencyMs || 0) > 2000 ? "red" : "purple"} />
          <MetricCard label="Routing" value={health?.totalRoutes || 0} hint={`${runtime?.routingPerMinute.toFixed(2) || "0.00"} decisions/min`} tone="yellow" />
          <MetricCard label="Errors" value={health?.errorsTotal || 0} hint={`${runtime?.errorsPerMinute.toFixed(2) || "0.00"} errors/min`} tone={(health?.errorsTotal || 0) > 0 ? "red" : "emerald"} />
          <MetricCard label="Pending Actions" value={pendingActions} hint="human approval queue" tone={pendingActions > 0 ? "yellow" : "emerald"} />
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="lab-panel rounded-[2rem] p-6">
            <SectionHeading eyebrow="Runtime watchdog" title="Service Checks" description="Estado directo desde Live API." />
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(watchdog?.checks || {}).map(([key, ok]) => (
                <div key={key} className="rounded-2xl border border-zinc-800/80 bg-black/25 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-bold capitalize text-zinc-200">{key.replace(/_/g, " ")}</p>
                    <StatusPill ok={Boolean(ok)} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="lab-panel rounded-[2rem] p-6">
            <SectionHeading eyebrow="Autonomous runtime" title="Supervised Optimizer" description="FASE 12 supervised learning queue." />
            <div className="grid gap-3 sm:grid-cols-2">
              <MetricCard label="Optimizer" value="active" hint="policy gated" tone="emerald" />
              <MetricCard label="Confidence" value={runtime?.confidence.toFixed(2) || "0.00"} hint="avg model confidence" tone="cyan" />
              <MetricCard label="Recommendations" value={runtime?.recommendations || 0} hint="recent optimizer recs" tone="yellow" />
              <MetricCard label="History Actions" value={runtime?.historyActions || 0} hint="adjustment log" tone="purple" />
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="lab-panel rounded-[2rem] p-6">
            <SectionHeading eyebrow="Health factors" title="Operational Reasons" description="Factores calculados por analytics engine." />
            <div className="space-y-2 text-sm text-zinc-300">
              {health?.reasons?.length ? health.reasons.map((reason) => (
                <div key={reason} className="rounded-2xl border border-zinc-800 bg-black/25 p-3">{reason}</div>
              )) : <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/5 p-3 text-emerald-300">Sin problemas activos</div>}
            </div>
          </div>

          <div className="lab-panel rounded-[2rem] p-6">
            <SectionHeading eyebrow="Quick access" title="Operational Surfaces" description="Entradas principales del portal live." />
            <div className="grid gap-3 sm:grid-cols-2">
              <Link href="/" className="rounded-2xl border border-cyan-300/20 bg-cyan-300/5 p-4 text-sm font-bold text-cyan-100 hover:border-cyan-300/50">Overview</Link>
              <Link href="/gpus" className="rounded-2xl border border-cyan-300/20 bg-cyan-300/5 p-4 text-sm font-bold text-cyan-100 hover:border-cyan-300/50">GPU Telemetry</Link>
              <Link href="/runtime" className="rounded-2xl border border-purple-300/20 bg-purple-300/5 p-4 text-sm font-bold text-purple-100 hover:border-purple-300/50">Runtime</Link>
              <a href="https://ai-lab.labrazahome.com" className="rounded-2xl border border-zinc-700 bg-black/25 p-4 text-sm font-bold text-zinc-300 hover:border-zinc-500">Docs</a>
            </div>
          </div>
        </section>
      </div>
    </MetricsShell>
  );
}
