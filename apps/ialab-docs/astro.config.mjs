// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import starlight from "@astrojs/starlight";
import mermaid from "astro-mermaid";
import react from "@astrojs/react";

const isPublicBuild = process.env.AILAB_PUBLIC_BUILD === 'true';

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
            { label: "Grounding + RAG", link: "/grounding-y-rag" },
            { label: "Codebase Structure", link: "/codebase-structural-cognition" },
            { label: "AnythingLLM Role", link: "/architecture/anythingllm-role" },
            { label: "AnythingLLM Enterprise", link: "/architecture/anythingllm-enterprise" },
            { label: "Marketplace Digital Twin", link: "/architecture/marketplace-digital-twin" },
            { label: "Health Layer (37A)", link: "/architecture/cognitive-health-layer" },
            { label: "Event Bus", link: "/event_bus" },
            { label: "Schemas", items: [{ autogenerate: { directory: "schemas" } }] },
          ],
        },
        {
          label: "Operations",
          collapsed: false,
          items: [
            { label: "Runtime Reference", collapsed: false, items: [{ autogenerate: { directory: "runtime" } }] },
            { label: "Runtime Flow", link: "/runtime_flow" },
            { label: "Truth Layers", link: "/runtime-truth-layers" },
            { label: "Analytics Engine", link: "/runtime-analytics-engine" },
            { label: "Cloudflare Redirects", link: "/cloudflare-pages-redirects" },
            { label: "Cloudflare Zero Trust", link: "/cloudflare-zero-trust" },
            { label: "v1 RC Tests", link: "/plan-pruebas-runtime-v1-rc" },
            { label: "Experiments", items: [{ autogenerate: { directory: "experiments" } }] },
            { label: "Roadmap", items: [{ autogenerate: { directory: "roadmap" } }] },
            { label: "Memory System", items: [{ autogenerate: { directory: "memory" } }] },
            { label: "Agentic", items: [{ autogenerate: { directory: "agentic" } }] },
            ...(isPublicBuild ? [] : [
              { label: "Runbooks", link: "/runbooks" },
            ]),
          ],
        },
        {
          label: "Observability",
          collapsed: false,
          items: [
            { label: "Dashboards + Metrics", collapsed: false, items: [{ autogenerate: { directory: "observability" } }] },
            { label: "Sensor Domains", link: "/observability/sensor-domains" },
          ],
        },
        {
          label: "Governance",
          collapsed: false,
          items: [
            { label: "Policies", collapsed: false, items: [{ autogenerate: { directory: "governance" } }] },
            { label: "ADR Log", items: [{ autogenerate: { directory: "adrs" } }] },
          ],
        },
        {
          label: "Audits",
          collapsed: false,
          items: [
            { label: "Index", link: "/audits/" },
          ],
        },
        ...(isPublicBuild ? [] : [
          {
            label: "Incidents",
            collapsed: false,
            items: [
              { label: "Index", link: "/incidents/" },
            ],
          },
          {
            label: "Historical",
            collapsed: false,
            items: [{ autogenerate: { directory: "historical" } }],
          },
        ]),
        {
          label: "Hermes Enterprise",
          collapsed: false,
          items: [
            { label: "Overview", link: "/hermes/" },
            { label: "Architecture", link: "/hermes/architecture" },
            { label: "SOUL", link: "/hermes/soul" },
            { label: "Capability Registry", link: "/hermes/capability-registry" },
            { label: "Operator Registry", link: "/hermes/operator-registry" },
            { label: "Hook Registry", link: "/hermes/hook-registry" },
            { label: "MCP Registry", link: "/hermes/mcp-registry" },
            { label: "Dynamic Governance", link: "/hermes/dynamic-governance" },
            { label: "Status Endpoint", link: "/hermes/status-endpoint" },
            { label: "Roadmap", link: "/hermes/roadmap" },
          ],
        },
      ],
    }),
    mermaid(),
    react(),
  ],
});
