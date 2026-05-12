import type { APIRoute } from "astro";

export const prerender = false;

export const GET: APIRoute = async () => {
  const incidents = [
    {
      id: "INC-2026-05-12-001",
      type: "fix",
      severity: "medium",
      status: "resolved",
      title: "Historical telemetry route served placeholder",
      date: "2026-05-12",
      affected: ["/status/history"],
      summary:
        "Astro was serving src/pages/status/history/index.astro instead of src/pages/status/history.astro, causing the private history page to show a placeholder.",
      resolution:
        "Moved the working Historical Telemetry implementation into src/pages/status/history/index.astro and fixed relative imports.",
    },
    {
      id: "CHG-2026-05-12-002",
      type: "change",
      severity: "low",
      status: "completed",
      title: "Operations Center service dashboard added",
      date: "2026-05-12",
      affected: ["/ops", "/api/services.json"],
      summary:
        "Added operational service dashboard with service state cards and AI-LAB command center layout.",
      resolution:
        "Implemented services API and OpsServiceCard component.",
    },
    {
      id: "CHG-2026-05-12-003",
      type: "change",
      severity: "low",
      status: "completed",
      title: "Operational runbooks added",
      date: "2026-05-12",
      affected: ["/runbooks"],
      summary:
        "Created initial recovery procedures for Cloudflare Tunnel, Astro build and telemetry.",
      resolution:
        "Added runbook index and first three recovery pages.",
    }
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        incidents,
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
