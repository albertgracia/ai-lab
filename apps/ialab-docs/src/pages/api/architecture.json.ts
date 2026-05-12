import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = async () => {
  const layers = [
    {
      name: "Edge",
      description: "Entrada externa y acceso seguro.",
      components: ["Cloudflare DNS", "Cloudflare Tunnel", "Zero Trust / Private Access"],
    },
    {
      name: "Routing",
      description: "Reverse proxy y publicación de servicios internos.",
      components: ["Traefik", "Local routing", "Private domains"],
    },
    {
      name: "Application",
      description: "Portal documental y operacional.",
      components: ["Astro", "React Components", "Tailwind UI"],
    },
    {
      name: "Operational APIs",
      description: "APIs internas para estado, histórico e inventario.",
      components: [
        "/api/status.json",
        "/api/history.json",
        "/api/services.json",
        "/api/incidents.json",
        "/api/infra.json",
      ],
    },
    {
      name: "Observability",
      description: "Vistas operacionales del laboratorio.",
      components: ["/status", "/status/live", "/status/history", "/ops"],
    },
    {
      name: "Knowledge Base",
      description: "Documentación técnica, runbooks y memoria operacional.",
      components: ["/runbooks", "/incidents", "/infra", "/blog"],
    },
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        architecture: "AI-LAB Operational Architecture",
        layers,
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
