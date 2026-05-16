import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRuntime } from "@/lib/api";

export async function RuntimeStatus() {
  const runtime = await getRuntime();
  if (!runtime) return <p className="text-zinc-500 italic">Esperando datos...</p>;

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm text-emerald-400">Autonomous Runtime</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-5">
          <div className="rounded-xl border border-zinc-800 p-4 text-center">
            <p className="text-xs text-zinc-500">Optimizer</p>
            <p className="text-2xl font-bold text-emerald-400">active</p>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4 text-center">
            <p className="text-xs text-zinc-500">Confidence</p>
            <p className="text-2xl font-bold text-cyan-400">{runtime.confidence.toFixed(2)}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4 text-center">
            <p className="text-xs text-zinc-500">Recommendations</p>
            <p className="text-2xl font-bold text-yellow-400">{runtime.recommendations}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4 text-center">
            <p className="text-xs text-zinc-500">Session Affinity</p>
            <p className="text-2xl font-bold text-purple-400">{runtime.sessionAffinity}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 p-4 text-center">
            <p className="text-xs text-zinc-500">History Actions</p>
            <p className="text-2xl font-bold text-yellow-400">{runtime.historyActions}</p>
          </div>
        </div>
        {runtime.pendingActions > 0 && (
          <div className="mt-4 rounded-xl border border-orange-500/50 bg-zinc-900 p-3 text-orange-300 text-sm text-center">
            {runtime.pendingActions} accione{runtime.pendingActions > 1 ? "s" : ""} pendiente{runtime.pendingActions > 1 ? "s" : ""} de aprobación
          </div>
        )}
      </CardContent>
    </Card>
  );
}
