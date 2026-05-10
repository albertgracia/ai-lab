// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import starlight from "@astrojs/starlight";

export default defineConfig({
  vite: {
    plugins: [tailwindcss()],
  },

  integrations: [
    starlight({
      title: "AI-LAB Docs",
    }),
  ],
});
