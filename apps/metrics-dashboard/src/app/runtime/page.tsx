import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { RuntimeStatus } from "@/components/runtime-status";
import { TelemetryChart } from "@/components/telemetry-chart";
import { getRuntime, getRuntimeHistory } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function RuntimePage() {
  const [runtime, history] = await Promise.all([getRuntime(), getRuntimeHistory(1)]);

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="rounded-3xl border border-purple-400/20 bg-zinc-950/70 p-8">
          <p className="text-xs font-bold uppercase tracking-[0.35em] text-purple-300">Cognitive Runtime</p>
          <h2 className="mt-3 text-4xl font-black text-white">Gateway, router y aprendizaje supervisado</h2>
          <p className="mt-3 max-w-3xl text-zinc-400">
            Vista operacional del runtime OpenAI-compatible: inferencias, decisiones de routing, latencia, failovers y cola autónoma supervisada.
          </p>
        </section>

        {runtime && (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Requests" value={runtime.requestsTotal.toLocaleString()} hint={`${runtime.requestsPerMinute.toFixed(2)} req/min`} tone="cyan" />
            <MetricCard label="Routing" value={`${runtime.routingPerMinute.toFixed(2)}/min`} hint="decisiones recientes" tone="yellow" />
            <MetricCard label="Latency" value={`${runtime.latencyMs.toFixed(0)} ms`} hint="última latencia gateway" tone={runtime.latencyMs > 2000 ? "red" : "emerald"} />
            <MetricCard label="Failovers" value={runtime.failovers.toLocaleString()} hint="vida del gateway" tone={runtime.failovers > 0 ? "yellow" : "emerald"} />
          </section>
        )}

        <RuntimeStatus />

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/80 p-6">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">Última hora</p>
              <h3 className="text-2xl font-black text-white">Actividad del runtime</h3>
            </div>
            <p className="font-mono text-xs text-zinc-500">Prometheus query_range · step 60s</p>
          </div>
          <TelemetryChart data={history} labels={["requests/min", "routing/min", "errors/min", "latency ms"]} />
        </section>
      </div>
    </MetricsShell>
  );
}
