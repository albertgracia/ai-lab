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
    starlight({ title: "AI-LAB Docs" }),
    mermaid(),
    react(),
  ],
});
