import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = async () => {
  const services = [
    {
      name: "AI-LAB Docs",
      status: "online",
      category: "documentation",
      url: "/",
      description: "Portal privado de documentación y operaciones AI-LAB.",
    },
    {
      name: "Live Status",
      status: "online",
      category: "telemetry",
      url: "/status/live",
      description: "Vista viva de telemetría operacional.",
    },
    {
      name: "Historical Telemetry",
      status: "online",
      category: "telemetry",
      url: "/status/history",
      description: "Histórico GPU/VRAM del laboratorio.",
    },
    {
      name: "Operations Center",
      status: "online",
      category: "ops",
      url: "/ops",
      description: "Centro de mando operacional del laboratorio.",
    },
    {
      name: "Runbooks",
      status: "online",
      category: "recovery",
      url: "/runbooks",
      description: "Procedimientos de recuperación, diagnóstico y operación.",
    },
    {
      name: "Incident Log",
      status: "online",
      category: "operations",
      url: "/incidents",
      description: "Registro de incidencias, cambios y fixes operativos.",
    },
    {
      name: "Infrastructure Inventory",
      status: "online",
      category: "infrastructure",
      url: "/infra",
      description: "Inventario de nodos, GPUs y servicios del AI-LAB.",
    },
    {
      name: "Architecture Map",
      status: "online",
      category: "blueprint",
      url: "/architecture",
      description: "Mapa de arquitectura operacional del AI-LAB.",
    },
    {
      name: "Private Blog",
      status: "online",
      category: "knowledge",
      url: "/blog",
      description: "Blog técnico interno del laboratorio.",
    }
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        services,
      },
      null,
      2
    ),
    {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    }
  );
};
