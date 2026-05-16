const PROMETHEUS = "http://192.168.1.40:9090/api/v1";
const AI_LAB_API = "http://127.0.0.1:8084";

async function prometheusQuery(query: string): Promise<any> {
  try {
    const res = await fetch(`${PROMETHEUS}/query?query=${encodeURIComponent(query)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });
    return await res.json();
  } catch { return null; }
}

async function aiLabApi(path: string): Promise<any> {
  try {
    const res = await fetch(`${AI_LAB_API}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });
    return await res.json();
  } catch { return null; }
}

export interface GpuData {
  name: string;
  temp: number;
  memTemp: number;
  hotSpot: number;
  vramTotal: number;
  vramUsed: number;
  vramFree: number;
  power: number;
  coreClock: number;
  memClock: number;
  load3d: number;
  loadCore: number;
}

export interface WatchdogData {
  status: string;
  checks: Record<string, boolean>;
}

export interface RuntimeData {
  recommendations: number;
  confidence: number;
  pendingActions: number;
  sessionAffinity: number;
  historyActions: number;
}

export interface HealthData {
  score: number;
  level: string;
  reasons: string[];
  requestsTotal: number;
  streamsTotal: number;
  errorsTotal: number;
  onlineNodes: number;
  totalNodes: number;
  activeSessions: number;
  totalRoutes: number;
  gpuCount: number;
}

export async function getGpuData(): Promise<GpuData[]> {
  const result = await prometheusQuery(
    'gpu_temperature_celsius{instance=~".*:9183"}'
  );
  if (!result?.data?.result) return [];

  const gpus: Record<string, any> = {};
  for (const r of result.data.result) {
    const inst = r.metric.instance;
    const gpu = r.metric.gpu;
    const sensor = r.metric.sensor;
    if (!gpus[gpu]) gpus[gpu] = {};
    gpus[gpu].name = gpu;
    if (sensor === "GPU_Core") gpus[gpu].temp = Number(r.value[1]);
    if (sensor === "GPU_Memory") gpus[gpu].memTemp = Number(r.value[1]);
    if (sensor === "GPU_Hot_Spot") gpus[gpu].hotSpot = Number(r.value[1]);
  }

  const loadResult = await prometheusQuery(
    'gpu_load_percent{instance=~".*:9183",sensor=~"D3D_3D|GPU_Core"}'
  );
  if (loadResult?.data?.result) {
    for (const r of loadResult.data.result) {
      const gpu = r.metric.gpu;
      const sensor = r.metric.sensor;
      if (!gpus[gpu]) gpus[gpu] = {};
      if (sensor === "D3D_3D") gpus[gpu].load3d = Number(r.value[1]);
      if (sensor === "GPU_Core") gpus[gpu].loadCore = Number(r.value[1]);
    }
  }

  const powerResult = await prometheusQuery(
    'gpu_power_watts{instance=~".*:9183"}'
  );
  if (powerResult?.data?.result) {
    for (const r of powerResult.data.result) {
      const gpu = r.metric.gpu;
      if (!gpus[gpu]) gpus[gpu] = {};
      gpus[gpu].power = Number(r.value[1]);
    }
  }

  const clockResult = await prometheusQuery(
    'gpu_clock_mhz{instance=~".*:9183"}'
  );
  if (clockResult?.data?.result) {
    for (const r of clockResult.data.result) {
      const gpu = r.metric.gpu;
      const sensor = r.metric.sensor;
      if (!gpus[gpu]) gpus[gpu] = {};
      if (sensor === "GPU_Core") gpus[gpu].coreClock = Number(r.value[1]);
      if (sensor === "GPU_Memory") gpus[gpu].memClock = Number(r.value[1]);
    }
  }

  const vramResult = await prometheusQuery(
    'gpu_smalldata{instance=~".*:9183",sensor=~"GPU_Memory_Total|GPU_Memory_Used|GPU_Memory_Free"}'
  );
  if (vramResult?.data?.result) {
    for (const r of vramResult.data.result) {
      const gpu = r.metric.gpu;
      const sensor = r.metric.sensor;
      if (!gpus[gpu]) gpus[gpu] = {};
      if (sensor === "GPU_Memory_Total") gpus[gpu].vramTotal = Number(r.value[1]);
      if (sensor === "GPU_Memory_Used") gpus[gpu].vramUsed = Number(r.value[1]);
      if (sensor === "GPU_Memory_Free") gpus[gpu].vramFree = Number(r.value[1]);
    }
  }

  return Object.values(gpus).map((g: any) => ({
    name: g.name || "unknown",
    temp: g.temp ?? 0,
    memTemp: g.memTemp ?? 0,
    hotSpot: g.hotSpot ?? 0,
    vramTotal: g.vramTotal ?? 0,
    vramUsed: g.vramUsed ?? 0,
    vramFree: g.vramFree ?? 0,
    power: g.power ?? 0,
    coreClock: g.coreClock ?? 0,
    memClock: g.memClock ?? 0,
    load3d: g.load3d ?? 0,
    loadCore: g.loadCore ?? 0,
  }));
}

export async function getWatchdog(): Promise<WatchdogData | null> {
  return aiLabApi("/api/watchdog");
}

export async function getHealth(): Promise<HealthData | null> {
  const d = await aiLabApi("/api/analytics");
  if (!d) return null;
  return {
    score: d.health?.score || 0,
    level: d.health?.level || "--",
    reasons: d.health?.reasons || [],
    requestsTotal: d.metrics?.requests_total || 0,
    streamsTotal: d.metrics?.streams_total || 0,
    errorsTotal: d.metrics?.errors_total || 0,
    onlineNodes: d.metrics?.online_nodes || 0,
    totalNodes: d.metrics?.total_nodes || 0,
    activeSessions: d.sessions?.active_sessions || 0,
    totalRoutes: d.routing?.total_routes || 0,
    gpuCount: d.metrics?.gpu_count || 2,
  };
}

export async function getRuntime(): Promise<RuntimeData | null> {
  const [opt, conf, pending, aff, adj] = await Promise.all([
    aiLabApi("/api/runtime-optimizer"),
    aiLabApi("/api/runtime-confidence"),
    aiLabApi("/api/runtime-pending-actions"),
    aiLabApi("/api/runtime-affinity"),
    aiLabApi("/api/runtime-adjustments"),
  ]);
  let confidence = 0;
  if (conf?.models) {
    const vals = Object.values(conf.models).map((m: any) => m.confidence || 0);
    confidence = vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : 0;
  }
  return {
    recommendations: opt?.recommendations_count || 0,
    confidence,
    pendingActions: pending?.pending || 0,
    sessionAffinity: aff?.total_sessions || 0,
    historyActions: adj?.length || 0,
  };
}
