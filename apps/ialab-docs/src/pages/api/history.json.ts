import fs from "fs/promises";
import path from "path";

const HISTORY_ROOT = "/opt/ai-lab-data/snapshots/history";

async function listJsonFiles(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });

  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      files.push(...await listJsonFiles(fullPath));
    }

    if (entry.isFile() && entry.name.endsWith(".json")) {
      files.push(fullPath);
    }
  }

  return files;
}

function extractTimestamp(filePath: string) {
  const parts = filePath.split(path.sep);
  const day = parts[parts.length - 2];
  const file = parts[parts.length - 1];

  const time = file
    .replace("system_snapshot_", "")
    .replace(".json", "")
    .replaceAll("-", ":");

  return `${day}T${time}`;
}

export async function GET() {
  try {
    const files = await listJsonFiles(HISTORY_ROOT);

    const latestFiles = files
      .sort()
      .slice(-120);

    const snapshots = [];

    for (const file of latestFiles) {
      try {
        const raw = await fs.readFile(file, "utf-8");
        const data = JSON.parse(raw);

        const gpu = Array.isArray(data.gpu) ? data.gpu : [];
        const docker = Array.isArray(data.docker?.containers)
          ? data.docker.containers
          : [];
        const llm = Array.isArray(data.llm?.lmstudio_nodes)
          ? data.llm.lmstudio_nodes
          : [];

        snapshots.push({
          timestamp: extractTimestamp(file),
          gpu: gpu.map((node: any) => ({
            node: node.node,
            host: node.host,
            usage: node.gpu_usage?.max_gpu_usage_percent ?? null,
            vram_used: node.vram?.vram_used_gib ?? null,
            vram_total: node.vram?.vram_total_gib ?? null,
            vram_free: node.vram?.vram_free_gib_estimated ?? null,
            online: !(node.gpu_usage?.error || node.vram?.error),
          })),
          docker_running: docker.filter((c: any) => c.State === "running").length,
          docker_total: docker.length,
          llm_online: llm.filter((n: any) => n.online).length,
          llm_total: llm.length,
        });
      } catch {
        // Ignorar snapshots corruptos o incompletos
      }
    }

    return new Response(
      JSON.stringify({
        count: snapshots.length,
        snapshots,
      }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({
        error: "history_unavailable",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}
