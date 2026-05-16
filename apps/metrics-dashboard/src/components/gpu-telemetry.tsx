import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GpuData } from "@/lib/api";

function formatMetric(value: number, unit: string) {
  if (unit === "%") return `${value.toFixed(0)}%`;
  if (unit === "°C") return `${value.toFixed(0)}°C`;
  if (unit === "W") return `${value.toFixed(0)}W`;
  if (unit === "MHz") return `${value.toFixed(0)} MHz`;
  if (unit === "MB") return `${value.toFixed(0)} MB`;
  return value.toFixed(0);
}

function GpuBar({ label, value, max, color, unit }: { label: string; value: number; max: number; color: string; unit: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono text-zinc-200">{formatMetric(value, unit)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function GpuTelemetry({ gpus }: { gpus: GpuData[] }) {
  if (gpus.length === 0) return <p className="text-zinc-500 italic">Esperando datos GPU...</p>;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {gpus.map((gpu) => {
        const maxTemp = Math.max(gpu.temp, gpu.memTemp, gpu.hotSpot);
        const healthColor = maxTemp > 80 ? "text-red-400" : maxTemp > 60 ? "text-yellow-400" : "text-emerald-400";
        return (
          <Card key={gpu.name} className="lab-panel overflow-hidden rounded-[2rem] border-zinc-800/80">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-zinc-500">Inference node</p>
                  <CardTitle className="mt-1 text-xl font-bold tracking-[-0.04em] text-cyan-100">{gpu.name.replace(/_/g, " ")}</CardTitle>
                </div>
                <Badge variant="outline" className={`${healthColor} h-7 border-current bg-black/20 px-3 font-mono`}>
                  {maxTemp.toFixed(0)}°C
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-2xl border border-zinc-800 bg-black/25 p-3">
                  <p className="text-zinc-500">Temp</p>
                  <p className={`mt-1 font-mono text-lg font-bold ${healthColor}`}>{formatMetric(gpu.temp, "°C")}</p>
                </div>
                <div className="rounded-2xl border border-zinc-800 bg-black/25 p-3">
                  <p className="text-zinc-500">VRAM</p>
                  <p className="mt-1 font-mono text-lg font-bold text-purple-300">{formatMetric(gpu.vramUsed, "MB")}</p>
                </div>
                <div className="rounded-2xl border border-zinc-800 bg-black/25 p-3">
                  <p className="text-zinc-500">Power</p>
                  <p className="mt-1 font-mono text-lg font-bold text-yellow-300">{formatMetric(gpu.power, "W")}</p>
                </div>
              </div>
              <GpuBar label="GPU Core" value={gpu.temp} max={100} unit="°C" color="bg-gradient-to-r from-emerald-500 to-emerald-400" />
              <GpuBar label="GPU Memory" value={gpu.memTemp} max={100} unit="°C" color="bg-gradient-to-r from-cyan-500 to-cyan-400" />
              <GpuBar label="Hot Spot" value={gpu.hotSpot} max={110} unit="°C" color="bg-gradient-to-r from-orange-500 to-red-400" />
              <div className="pt-2 border-t border-zinc-800">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">VRAM usage</span>
                  <span className="font-mono text-zinc-200">{formatMetric(gpu.vramUsed, "MB")} / {formatMetric(gpu.vramTotal, "MB")}</span>
                </div>
                <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-1000"
                    style={{ width: `${gpu.vramTotal > 0 ? (gpu.vramUsed / gpu.vramTotal) * 100 : 0}%` }} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-2 text-center text-xs">
                <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3">
                  <p className="text-zinc-500">Power</p>
                  <p className="font-mono text-yellow-400 font-bold">{formatMetric(gpu.power, "W")}</p>
                </div>
                <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3">
                  <p className="text-zinc-500">Core Clock</p>
                  <p className="font-mono text-cyan-400 font-bold">{formatMetric(gpu.coreClock, "MHz")}</p>
                </div>
                <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3">
                  <p className="text-zinc-500">Mem Clock</p>
                  <p className="font-mono text-purple-400 font-bold">{formatMetric(gpu.memClock, "MHz")}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
