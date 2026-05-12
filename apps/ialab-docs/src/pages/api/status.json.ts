export async function GET() {
  return new Response(
    JSON.stringify({
      gpus: "2/2",
      llmNodes: "2/2",
      docker: "14",
      vram: "28 GiB",
      state: "LIVE"
    }),
    {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store"
      }
    }
  );
}
