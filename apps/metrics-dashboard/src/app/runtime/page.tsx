import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { RuntimeStatus } from "@/components/runtime-status";
import { SectionHeading } from "@/components/section-heading";
import { TelemetryChart } from "@/components/telemetry-chart";
import { getRuntime, getRuntimeHistory } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function RuntimePage() {
  const [runtime, history] = await Promise.all([getRuntime(), getRuntimeHistory(1)]);

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="lab-panel rounded-[2rem] p-8 sm:p-10">
          <p className="font-mono text-[0.7rem] font-bold uppercase tracking-[0.38em] text-purple-200">Cognitive Runtime</p>
          <h2 className="mt-4 max-w-4xl text-5xl font-bold leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">Gateway, router y aprendizaje supervisado</h2>
          <p className="mt-5 max-w-3xl text-base leading-7 text-zinc-400">
            Vista operacional del runtime OpenAI-compatible: inferencias, decisiones de routing, latencia, failovers y cola autónoma supervisada.
          </p>
        </section>

        {runtime && (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Requests" value={runtime.requestsTotal.toLocaleString()} hint={`${runtime.requestsPerMinute.toFixed(2)} req/min`} tone="cyan" />
            <MetricCard label="Routing" value={`${runtime.routingPerMinute.toFixed(2)}/min`} hint="decisiones recientes" tone="yellow" />
            <MetricCard label="Latency" value={`${runtime.latencyMs.toFixed(0)} ms`} hint="última latencia gateway" tone={runtime.latencyMs > 2000 ? "red" : "emerald"} />
            <MetricCard label="Failovers" value={runtime.failovers.toLocaleString()} hint="vida del gateway" tone={runtime.failovers > 0 ? "yellow" : "emerald"} />
            <MetricCard label="Confidence" value={runtime.confidence.toFixed(2)} hint="avg model confidence" tone="purple" />
            <MetricCard label="Pending Actions" value={runtime.pendingActions.toLocaleString()} hint="human approval queue" tone={runtime.pendingActions > 0 ? "yellow" : "emerald"} />
          </section>
        )}

        <RuntimeStatus runtime={runtime} />

        <section className="lab-panel rounded-[2rem] p-6">
          <SectionHeading eyebrow="Última hora" title="Actividad del runtime" description="Prometheus query_range · step 60s" />
          <TelemetryChart data={history} labels={["requests/min", "routing/min", "errors/min", "latency ms"]} />
        </section>
      </div>
    </MetricsShell>
  );
}
