import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getGpuData } from "@/lib/api";

function GpuBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono">{value.toFixed(1)}{label.includes("°") ? "°C" : label.includes("W") ? "W" : label.includes("MHz") ? " MHz" : "%"}</span>
      </div>
      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export async function GpuTelemetry() {
  const gpus = await getGpuData();
  if (gpus.length === 0) return <p className="text-zinc-500 italic">Esperando datos GPU...</p>;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {gpus.map((gpu) => {
        const maxTemp = Math.max(gpu.temp, gpu.memTemp, gpu.hotSpot);
        const healthColor = maxTemp > 80 ? "text-red-400" : maxTemp > 60 ? "text-yellow-400" : "text-emerald-400";
        return (
          <Card key={gpu.name} className="border-zinc-800 bg-zinc-950">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-mono text-cyan-400">{gpu.name.replace(/_/g, " ")}</CardTitle>
                <Badge variant="outline" className={healthColor + " border-current"}>
                  {maxTemp}°C
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <GpuBar label="GPU Core" value={gpu.temp} max={100} color="bg-gradient-to-r from-emerald-500 to-emerald-400" />
              <GpuBar label="GPU Memory" value={gpu.memTemp} max={100} color="bg-gradient-to-r from-cyan-500 to-cyan-400" />
              <GpuBar label="Hot Spot" value={gpu.hotSpot} max={110} color="bg-gradient-to-r from-orange-500 to-red-400" />
              <div className="pt-2 border-t border-zinc-800">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">VRAM</span>
                  <span className="font-mono">{gpu.vramUsed.toFixed(0)} / {gpu.vramTotal.toFixed(0)} MB</span>
                </div>
                <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-1000"
                    style={{ width: `${gpu.vramTotal > 0 ? (gpu.vramUsed / gpu.vramTotal) * 100 : 0}%` }} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2 text-center text-xs">
                <div className="rounded bg-zinc-900 p-2">
                  <p className="text-zinc-500">Power</p>
                  <p className="font-mono text-yellow-400 font-bold">{gpu.power.toFixed(0)}W</p>
                </div>
                <div className="rounded bg-zinc-900 p-2">
                  <p className="text-zinc-500">Core Clock</p>
                  <p className="font-mono text-cyan-400 font-bold">{gpu.coreClock.toFixed(0)} MHz</p>
                </div>
                <div className="rounded bg-zinc-900 p-2">
                  <p className="text-zinc-500">Mem Clock</p>
                  <p className="font-mono text-purple-400 font-bold">{gpu.memClock.toFixed(0)} MHz</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
