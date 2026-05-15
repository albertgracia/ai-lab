export async function onRequest(context) {
    const url = "https://blog-ai-lab.labrazahome.com/api/status.json";
    try {
        const resp = await fetch(url, {
            headers: {
                "CF-Access-Client-Id": "3093bf6c93d1c8dbb6ab65db21941ac0.access",
                "CF-Access-Client-Secret": "e54c05bb3496e0ff55c55b6af63c456aa6b7d5171a74f42aeebd3facefe30a1c"
            }
        });
        if (!resp.ok) {
            return new Response(JSON.stringify({error: "API error", status: resp.status}), {
                status: 502, headers: {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            });
        }
        const data = await resp.json();
        return new Response(JSON.stringify(data), {
            headers: {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        });
    } catch (e) {
        return new Response(JSON.stringify({error: e.message}), {status: 502, headers: {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}});
    }
}