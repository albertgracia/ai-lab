import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RuntimeData } from "@/lib/api";

export function RuntimeStatus({ runtime }: { runtime: RuntimeData | null }) {
  if (!runtime) return <p className="text-zinc-500 italic">Esperando datos...</p>;
  const pendingTone = runtime.pendingActions > 0 ? "border-orange-500/50 bg-orange-500/10 text-orange-200" : "border-emerald-500/50 bg-emerald-500/10 text-emerald-200";

  return (
    <Card className="lab-panel rounded-[2rem] border-zinc-800/80">
      <CardHeader className="pb-4">
        <CardTitle className="text-sm text-emerald-300">Autonomous Runtime</CardTitle>
        <p className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-zinc-500">supervised optimizer · policy gated</p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">Optimizer</p>
            <p className="text-2xl font-bold text-emerald-400">active</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">Confidence</p>
            <p className="text-2xl font-bold text-cyan-400">{runtime.confidence.toFixed(2)}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">Recommendations</p>
            <p className="text-2xl font-bold text-yellow-400">{runtime.recommendations}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">Session Affinity</p>
            <p className="text-2xl font-bold text-purple-400">{runtime.sessionAffinity}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">History Actions</p>
            <p className="text-2xl font-bold text-yellow-400">{runtime.historyActions}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-black/25 p-4 text-center">
            <p className="text-xs text-zinc-500">Active Streams</p>
            <p className="text-2xl font-bold text-emerald-400">{runtime.activeStreams}</p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-zinc-800/80 bg-black/20 p-4">
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-zinc-500">Requests</p>
            <p className="mt-2 text-2xl font-bold text-white">{runtime.requestsTotal.toLocaleString()}</p>
          </div>
          <div className="rounded-2xl border border-zinc-800/80 bg-black/20 p-4">
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-zinc-500">Routing / min</p>
            <p className="mt-2 text-2xl font-bold text-yellow-300">{runtime.routingPerMinute.toFixed(2)}</p>
          </div>
          <div className={`rounded-2xl border p-4 text-center ${pendingTone}`}>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em]">Approval queue</p>
            <p className="mt-2 text-2xl font-bold">{runtime.pendingActions}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
