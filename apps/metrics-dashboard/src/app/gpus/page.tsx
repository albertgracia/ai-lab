import { MetricsShell } from "@/components/metrics-shell";
import { GpuTelemetry } from "@/components/gpu-telemetry";
import { MetricCard } from "@/components/metric-card";
import { TelemetryChart } from "@/components/telemetry-chart";
import { getGpuData, getGpuHistory } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function GpusPage() {
  const [gpus, history] = await Promise.all([getGpuData(), getGpuHistory(1)]);
  const totalVram = gpus.reduce((sum, gpu) => sum + gpu.vramTotal, 0);
  const usedVram = gpus.reduce((sum, gpu) => sum + gpu.vramUsed, 0);
  const totalPower = gpus.reduce((sum, gpu) => sum + gpu.power, 0);
  const maxTemp = Math.max(0, ...gpus.flatMap((gpu) => [gpu.temp, gpu.memTemp, gpu.hotSpot]));

  return (
    <MetricsShell>
      <div className="space-y-8">
        <section className="rounded-3xl border border-cyan-400/20 bg-zinc-950/70 p-8">
          <p className="text-xs font-bold uppercase tracking-[0.35em] text-cyan-300">GPU Telemetry</p>
          <h2 className="mt-3 text-4xl font-black text-white">RX9070 + RX7900XT</h2>
          <p className="mt-3 max-w-3xl text-zinc-400">
            Sensores PowerShell/LibreHWMonitor en `:9183` combinados con windows_exporter para VRAM, procesos y capacidad de inferencia.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="GPUs" value={gpus.length} hint="nodos con telemetría" tone="cyan" />
          <MetricCard label="VRAM Pool" value={`${usedVram.toFixed(0)} / ${totalVram.toFixed(0)} MB`} hint="uso dedicado actual" tone="purple" />
          <MetricCard label="Power" value={`${totalPower.toFixed(0)} W`} hint="paquete combinado" tone="yellow" />
          <MetricCard label="Max Temp" value={`${maxTemp.toFixed(0)} °C`} hint="core/memory/hotspot" tone={maxTemp > 80 ? "red" : maxTemp > 60 ? "yellow" : "emerald"} />
        </section>

        <GpuTelemetry />

        <section className="rounded-3xl border border-zinc-800 bg-zinc-950/80 p-6">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-zinc-500">Última hora</p>
              <h3 className="text-2xl font-black text-white">Temperatura y potencia</h3>
            </div>
            <p className="font-mono text-xs text-zinc-500">Prometheus query_range · step 60s</p>
          </div>
          <TelemetryChart data={history} labels={["RX9070 temp", "RX7900XT temp", "RX9070 power", "RX7900XT power"]} />
        </section>
      </div>
    </MetricsShell>
  );
}
