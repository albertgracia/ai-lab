import type { APIRoute } from "astro";

export const prerender = true;

export const GET: APIRoute = async () => {
  const models = [
    {
      name: "LM Studio Local API",
      provider: "local",
      runtime: "LM Studio",
      status: "online",
      endpoint: "http://192.168.1.200:1234/v1",
      capabilities: ["chat", "openai-compatible-api", "local-inference"],
      notes: "Endpoint local compatible con API estilo OpenAI.",
    },
    {
      name: "Ollama Runtime",
      provider: "local",
      runtime: "Ollama",
      status: "planned",
      endpoint: "http://192.168.1.30:11434",
      capabilities: ["chat", "embeddings", "local-inference"],
      notes: "Runtime local para modelos ligeros y automatización.",
    },
    {
      name: "AI-LAB RAG Core",
      provider: "internal",
      runtime: "Qdrant + LLM",
      status: "planned",
      endpoint: "/api/rag",
      capabilities: ["retrieval", "knowledge-search", "document-reasoning"],
      notes: "Capa futura de búsqueda semántica y documentación operativa.",
    }
  ];

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        environment: "local-private",
        models,
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
