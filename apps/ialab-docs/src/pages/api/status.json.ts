import fs from "fs/promises";

export async function GET() {
  try {
    const raw = await fs.readFile(
      "/opt/ai-lab/runtime/state/system_snapshot.json",
      "utf-8"
    );

    return new Response(raw, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({
        error: "snapshot_unavailable",
      }),
      {
        status: 500,
      }
    );
  }
}
