import { MetricsShell } from "@/components/metrics-shell";
import { MetricCard } from "@/components/metric-card";
import { SectionHeading } from "@/components/section-heading";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const AI_LAB_API = "http://127.0.0.1:8084";

async function aiLabApi(path: string) {
  try {
    const res = await fetch(`${AI_LAB_API}${path}`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    return await res.json();
  } catch { return null; }
}

function Pill({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-zinc-700/40 bg-black/30 px-4 py-2">
      <span className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-zinc-500">{label}</span>
      <span className={ok === undefined ? "font-mono text-sm text-white" : ok ? "font-mono text-sm font-bold text-emerald-300" : "font-mono text-sm font-bold text-red-300"}>
        {value}
      </span>
    </div>
  );
}

async function getControlData() {
  const [runtime, status, policies, routes, governance] = await Promise.all([
    aiLabApi("/api/control/runtime").catch(() => null),
    aiLabApi("/api/control/status").catch(() => null),
    aiLabApi("/api/control/policies").catch(() => null),
    aiLabApi("/api/control/routes").catch(() => []),
    aiLabApi("/api/control/recover").catch(() => null),
  ]);
  return { runtime, status, policies, routes: (Array.isArray(routes) ? routes : []).slice(0, 5), governance };
}

function GovernanceBadge({ state }: { state?: string }) {
  const colors: Record<string, string> = {
    NORMAL: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    ELEVATED: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    DEGRADED: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    LOCKDOWN: "bg-red-500/20 text-red-300 border-red-500/30",
  };
  const s = state || "NORMAL";
  return (
    <span className={`inline-block rounded-full border px-3 py-1 font-mono text-[0.65rem] font-bold uppercase tracking-[0.24em] ${colors[s] || colors.NORMAL}`}>
      {s}
    </span>
  );
}

export default async function ControlPage() {
  const { runtime, status, policies, routes, governance } = await getControlData();

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="lab-panel rounded-[2rem] p-8 sm:p-10">
          <p className="font-mono text-[0.7rem] font-bold uppercase tracking-[0.38em] text-cyan-200">Control Plane</p>
          <h2 className="mt-4 max-w-3xl text-5xl font-bold leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">
            Runtime Operational Control
          </h2>
          <div className="mt-6 flex items-center gap-4">
            <GovernanceBadge state={runtime?.governance} />
            {status?.uptime_hours != null && (
              <span className="font-mono text-sm text-zinc-400">{status.uptime_hours}h uptime</span>
            )}
          </div>
        </section>

        <SectionHeading eyebrow="state" title="Runtime Overview" />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Mode" value={runtime?.mode || "?"} hint="current mode" />
          <MetricCard label="Health" value={runtime?.health || "?"} hint={`score ${runtime?.health_score ?? "?"}`} />
          <MetricCard label="Nodes Online" value={String(runtime?.nodes_online ?? "?")} hint={`${status?.nodes_offline ?? "?"} offline`} />
          <MetricCard label="Router Latency" value={`${runtime?.router_latency_ms ?? "?"} ms`} hint="last request" />
        </div>

        <SectionHeading eyebrow="policy" title="Active Policies" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Pill label="Execute Policy" value={policies?.execute_policy || "?"} />
          <Pill label="Tool Fastpath" value={policies?.tool_fastpath ? "active" : "off"} ok={policies?.tool_fastpath} />
          <Pill label="Governance" value={policies?.governance_state || "?"} />
        </div>

        <SectionHeading eyebrow="infra" title="Infrastructure" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Pill label="Qdrant" value={status?.qdrant || "?"} ok={status?.qdrant === "healthy"} />
          <Pill label="Semantic Recall" value={status?.semantic_recall ? "enabled" : "off"} ok={status?.semantic_recall} />
          <Pill label="Uptime" value={`${status?.uptime_hours ?? "?"}h`} />
        </div>

        <SectionHeading eyebrow="routing" title="Recent Routing Decisions" />
        <div className="overflow-x-auto rounded-2xl border border-zinc-700/30 bg-black/30">
          <table className="w-full font-mono text-xs">
            <thead>
              <tr className="border-b border-zinc-700/30 text-zinc-500">
                <th className="px-4 py-2 text-left">Model</th>
                <th className="px-4 py-2 text-left">Node</th>
                <th className="px-4 py-2 text-left">Task</th>
                <th className="px-4 py-2 text-right">Latency</th>
                <th className="px-4 py-2 text-center">OK</th>
              </tr>
            </thead>
            <tbody>
              {(routes as any[])?.map((r, i) => (
                <tr key={i} className="border-b border-zinc-800/50 text-zinc-300">
                  <td className="px-4 py-2">{r.selected_model?.slice(0, 30)}</td>
                  <td className="px-4 py-2 text-zinc-500">{r.node}</td>
                  <td className="px-4 py-2">{r.task_type}</td>
                  <td className="px-4 py-2 text-right">{r.latency_ms}ms</td>
                  <td className="px-4 py-2 text-center">{r.success ? "✓" : "✗"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {governance?.recommended_actions?.length > 0 && (
          <>
            <SectionHeading eyebrow="actions" title="Recommended Actions" />
            <ul className="list-inside list-disc space-y-1 text-sm text-zinc-400">
              {governance.recommended_actions.map((a: string, i: number) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </MetricsShell>
  );
}
