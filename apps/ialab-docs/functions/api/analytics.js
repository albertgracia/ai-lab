export async function onRequest(context) {
    return new Response(JSON.stringify({test: "Function works!", time: Date.now()}), {
        headers: {"Content-Type": "application/json"}
    });
}