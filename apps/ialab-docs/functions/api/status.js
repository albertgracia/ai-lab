export async function onRequest(context) {
    return new Response(JSON.stringify({test: "Status function works!"}), {
        headers: {"Content-Type": "application/json"}
    });
}