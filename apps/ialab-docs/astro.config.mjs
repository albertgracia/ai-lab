// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import starlight from "@astrojs/starlight";
import mermaid from "astro-mermaid";
import react from "@astrojs/react";

export default defineConfig({
  site: "https://ai-lab.labrazahome.com",

  server: {
    host: true,
    allowedHosts: ["blog-ai-lab.labrazahome.com"],
  },

  vite: {
    plugins: [tailwindcss()],
  },

  integrations: [
    starlight({
      title: "AI-LAB Docs",
      sidebar: [
        { label: "Home", link: "/" },
        {
          label: "Architecture",
          collapsed: false,
          items: [
            { label: "Core Documents", collapsed: false, items: [{ autogenerate: { directory: "architecture" } }] },
            { label: "Overview", link: "/arquitectura-ai-lab" },
            { label: "Public-Private", link: "/arquitectura-publico-privado" },
            { label: "Phase 8", link: "/architecture_phase8" },
            { label: "Topology", link: "/topologia-ai-lab" },
            { label: "Topology Layer", link: "/topology_layer" },
            { label: "Distributed Inference", link: "/inferencia-distribuida" },
            { label: "Cognitive Routing", link: "/routing-cognitivo" },
            { label: "Grounding + RAG", link: "/grounding-y-rag" },
            { label: "Codebase Structure", link: "/codebase-structural-cognition" },
            { label: "Event Bus", link: "/event_bus" },
            { label: "Schemas", items: [{ autogenerate: { directory: "schemas" } }] },
            { label: "Codebase", items: [{ autogenerate: { directory: "codebase" } }] },
          ],
        },
        {
          label: "Operations",
          collapsed: false,
          items: [
            { label: "Runtime Reference", collapsed: false, items: [{ autogenerate: { directory: "runtime" } }] },
            { label: "Runtime Overview", link: "/runtime-ai-lab" },
            { label: "Runtime Flow", link: "/runtime_flow" },
            { label: "SSE Runtime", link: "/sse_runtime" },
            { label: "Truth Layers", link: "/runtime-truth-layers" },
            { label: "Analytics Engine", link: "/runtime-analytics-engine" },
            { label: "Analytics Fix", link: "/runtime-analytics-correccion" },
            { label: "Runbook: Cloudflare", link: "/runbook-cloudflare-pages" },
            { label: "Runbook: F19 Alerts", link: "/runbook-fase-19-5-operational-alerts-baseline" },
            { label: "Runbook: F19 Observability", link: "/runbook-fase-19-route-family-observability" },
            { label: "Runbook: F20 Router", link: "/runbook-fase-20-router-qwen" },
            { label: "Runbook: F29 SLO", link: "/runbook-fase-29.4-slo-enforcement" },
            { label: "CI/CD Automation", link: "/automatizacion-ci-cd" },
            { label: "Cloudflare Deployment", link: "/implementacion-astro-cloudflare-github" },
            { label: "Cloudflare Redirects", link: "/cloudflare-pages-redirects" },
            { label: "OpenWebUI", link: "/openwebui-conexion-router" },
            { label: "Private Operation", link: "/operacion-privada-ai-lab" },
            { label: "LMStudio Failover", link: "/router-lmstudio-failover" },
            { label: "LMStudio Fix", link: "/fix-model-unloaded-lmstudio" },
            { label: "OpenCode Patch", link: "/parche-opencode-router-gateway" },
            { label: "v1 RC Tests", link: "/plan-pruebas-runtime-v1-rc" },
            { label: "Systemd Services", link: "/servicios-persistentes-systemd" },
            { label: "Storage", link: "/almacenamiento-ai-lab" },
            { label: "Internal Routes", link: "/rutas-internas-ai-lab" },
            { label: "Experiments", items: [{ autogenerate: { directory: "experiments" } }] },
            { label: "Roadmap", items: [{ autogenerate: { directory: "roadmap" } }] },
            { label: "Memory System", items: [{ autogenerate: { directory: "memory" } }] },
            { label: "Agentic", items: [{ autogenerate: { directory: "agentic" } }] },
          ],
        },
        {
          label: "Observability",
          collapsed: false,
          items: [
            { label: "Dashboards + Metrics", collapsed: false, items: [{ autogenerate: { directory: "observability" } }] },
            { label: "Platform", link: "/observabilidad-plataforma-ai-lab" },
            { label: "Definitive Guide", link: "/observabilidad-ai-lab-definitiva" },
            { label: "Live State", link: "/observabilidad-y-estado-vivo" },
            { label: "Observability Map", link: "/mapa-observabilidad-ai-lab" },
            { label: "GPU Telemetry", link: "/telemetria-gpu-restauracion" },
            { label: "Complete Report", link: "/informe-completo-ai-lab" },
            { label: "Operational Report", link: "/informe-operacional-exhaustivo" },
          ],
        },
        {
          label: "Governance",
          collapsed: false,
          items: [
            { label: "Policies", collapsed: false, items: [{ autogenerate: { directory: "governance" } }] },
            { label: "ADR Log", items: [{ autogenerate: { directory: "adrs" } }] },
            { label: "Cloudflare Zero Trust", link: "/cloudflare-zero-trust" },
          ],
        },
        {
          label: "Historical",
          collapsed: false,
          items: [{ autogenerate: { directory: "historical" } }],
        },
      ],
    }),
    mermaid(),
    react(),
  ],
});
