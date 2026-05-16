import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { HealthData, WatchdogData } from "@/lib/api";

export function ClusterHealth({
  health,
  watchdog,
  latencyMs,
}: {
  health: HealthData | null;
  watchdog: WatchdogData | null;
  latencyMs?: number | null;
}) {
  if (!health) return <p className="text-zinc-500 italic">Esperando datos...</p>;
  const freshness = new Date().toISOString().slice(11, 19);
  const latency = typeof latencyMs === "number" && Number.isFinite(latencyMs) ? `${latencyMs.toFixed(0)} ms` : "-- ms";

  return (
    <div className="space-y-6">
      <Card className="lab-panel overflow-hidden rounded-[2rem] border-zinc-800/80">
        <CardHeader className="flex flex-row items-start justify-between gap-4 pb-4">
          <div>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-zinc-500">Live snapshot</p>
            <CardTitle className="mt-1 text-sm text-cyan-300">Cluster Health</CardTitle>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-cyan-300/30 bg-cyan-300/10 text-cyan-100">{freshness} UTC</Badge>
            <Badge variant="outline" className={health.score >= 80 ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-100" : health.score >= 50 ? "border-yellow-300/30 bg-yellow-300/10 text-yellow-100" : "border-red-300/30 bg-red-300/10 text-red-100"}>
              score {health.score}
            </Badge>
            <Badge variant="outline" className="border-zinc-700 bg-black/30 text-zinc-200">
              {health.level}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-zinc-500">Health Score</p>
              <p className={`mt-2 text-4xl font-bold tracking-[-0.05em] ${health.score >= 80 ? "text-emerald-300" : health.score >= 50 ? "text-yellow-300" : "text-red-300"}`}>
                {health.score}
              </p>
              <p className="text-xs text-zinc-500">{health.level}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-zinc-500">Requests</p>
              <p className="mt-2 text-4xl font-bold tracking-[-0.05em] text-white">{health.requestsTotal.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Sesiones Activas</p>
              <p className="text-3xl font-black text-emerald-400">{health.activeSessions}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Latencia</p>
              <p className="text-3xl font-black text-purple-400">{latency}</p>
              <p className="mt-1 text-[11px] uppercase tracking-[0.2em] text-zinc-600">gateway live</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Nodos / GPUs</p>
              <p className="text-3xl font-black text-cyan-400">{health.onlineNodes}/{health.totalNodes}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Streams</p>
              <p className="text-3xl font-black text-cyan-400">{health.streamsTotal}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Errores</p>
              <p className={`text-3xl font-black ${health.errorsTotal > 0 ? "text-red-400" : "text-emerald-400"}`}>{health.errorsTotal}</p>
            </CardContent>
          </Card>
          <Card className="border-zinc-800/90 bg-zinc-950/80">
            <CardContent className="p-4">
              <p className="text-xs text-zinc-500">Routing</p>
              <p className="text-3xl font-black text-yellow-400">{health.totalRoutes}</p>
            </CardContent>
          </Card>
        </CardContent>
      </Card>

      <Card className="lab-panel rounded-[2rem] border-zinc-800/80">
        <CardHeader className="pb-3">
          <CardTitle className="font-mono text-xs uppercase tracking-[0.24em] text-orange-300">Runtime Watchdog</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {watchdog?.checks && Object.entries(watchdog.checks).map(([key, val]) => (
              <div key={key} className="rounded-2xl border border-zinc-800/80 bg-black/25 p-3 text-center">
                <p className="text-xs text-zinc-500 mb-1">{key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</p>
                <p className={`text-lg font-bold ${val ? "text-emerald-400" : "text-red-400"}`}>
                  {val ? "ok" : "fail"}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {health.reasons.length > 0 && (
        <Card className="lab-panel rounded-[2rem] border-zinc-800/80">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-cyan-400">Health Factors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              {health.reasons.map((r, i) => (
                <div key={i} className="text-zinc-300">• {r}</div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
