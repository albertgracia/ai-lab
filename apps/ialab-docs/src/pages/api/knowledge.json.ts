import type { APIRoute } from "astro";

export const prerender = true;

export const GET: APIRoute = async () => {
  const sections = [
    {
      title: "Operations Center",
      category: "operations",
      href: "/ops",
      description: "Centro operacional principal del AI-LAB.",
    },

    {
      title: "Infrastructure Inventory",
      category: "infrastructure",
      href: "/infra",
      description: "Inventario de nodos, GPUs y servicios.",
    },

    {
      title: "Architecture Map",
      category: "architecture",
      href: "/architecture",
      description: "Mapa operacional y flujo del laboratorio.",
    },

    {
      title: "Runbooks",
      category: "recovery",
      href: "/runbooks",
      description: "Procedimientos de recuperación y operación.",
    },

    {
      title: "Incident Log",
      category: "operations",
      href: "/incidents",
      description: "Histórico de incidencias y cambios.",
    },

    {
      title: "Live Status",
      category: "telemetry",
      href: "/status/live",
      description: "Estado vivo del laboratorio.",
    },

    {
      title: "Historical Telemetry",
      category: "telemetry",
      href: "/status/history",
      description: "Histórico GPU/VRAM y observabilidad.",
    },

    {
      title: "Model Registry",
      category: "operations",
      href: "/models",
      description: "Inventario de runtimes, endpoints y capacidades IA.",
    },

    {
      title: "Private Technical Blog",
      category: "knowledge",
      href: "/blog",
      description: "Documentación y artículos técnicos internos.",
    }
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        sections,
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
