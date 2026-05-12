import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = async () => {
  const nodes = [
    {
      name: "ubuntu-ialab",
      role: "AI Core Node",
      status: "online",
      ip: "192.168.1.30",
      os: "Ubuntu Server",
      services: [
        "Astro Docs",
        "Telemetry",
        "Traefik",
        "Cloudflare Tunnel",
      ],
      gpu: {
        model: "RTX 5070",
        vram: "12GB",
      },
      tags: ["ai", "ops", "telemetry"],
    },

    {
      name: "NAS-N5",
      role: "Storage / Hyper-V",
      status: "online",
      ip: "10.10.10.1",
      os: "Windows 11 Pro",
      services: [
        "Hyper-V",
        "File Server",
        "Docker",
      ],
      gpu: {
        model: "RX 7900",
        vram: "16GB",
      },
      tags: ["storage", "virtualization"],
    },

    {
      name: "UCG-Fiber",
      role: "Network Gateway",
      status: "online",
      ip: "192.168.1.1",
      os: "UniFi OS",
      services: [
        "Routing",
        "IDS/IPS",
        "VLANs",
        "VPN",
      ],
      tags: ["network", "security"],
    }
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        nodes,
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
