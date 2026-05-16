import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getWatchdog, getHealth } from "@/lib/api";

export async function ClusterHealth() {
  const [health, watchdog] = await Promise.all([getHealth(), getWatchdog()]);
  if (!health) return <p className="text-zinc-500 italic">Esperando datos...</p>;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Health Score</p>
            <p className={`text-3xl font-black ${health.score >= 80 ? "text-emerald-400" : health.score >= 50 ? "text-yellow-400" : "text-red-400"}`}>
              {health.score}
            </p>
            <p className="text-xs text-zinc-500">{health.level}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Requests</p>
            <p className="text-3xl font-black text-white">{health.requestsTotal.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Sesiones Activas</p>
            <p className="text-3xl font-black text-emerald-400">{health.activeSessions}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Nodos / GPUs</p>
            <p className="text-3xl font-black text-cyan-400">{health.onlineNodes}/{health.totalNodes}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Streams</p>
            <p className="text-3xl font-black text-cyan-400">{health.streamsTotal}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Errores</p>
            <p className={`text-3xl font-black ${health.errorsTotal > 0 ? "text-red-400" : "text-emerald-400"}`}>{health.errorsTotal}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Routing</p>
            <p className="text-3xl font-black text-yellow-400">{health.totalRoutes}</p>
          </CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-4">
            <p className="text-xs text-zinc-500">Latencia Media</p>
            <p className="text-3xl font-black text-purple-400">-- ms</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-orange-400">Runtime Watchdog</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {watchdog?.checks && Object.entries(watchdog.checks).map(([key, val]) => (
              <div key={key} className="rounded-lg border border-zinc-800 p-3 text-center">
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
        <Card className="border-zinc-800 bg-zinc-950">
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
