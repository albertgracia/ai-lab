import type { APIRoute } from "astro";
import { infraInventory } from "../../lib/infraInventory";

export const prerender = true;

export const GET: APIRoute = async () => {
  return new Response(JSON.stringify(infraInventory, null, 2), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
};
