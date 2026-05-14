import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from pathlib import Path


HOST = "0.0.0.0"
PORT = 8008

LMSTUDIO_BASE_URL = "http://192.168.1.50:1234/v1"

AGENT_PROMPT_FILE = Path("/opt/ai-lab/.agent/OPENCODE_PROMPT.md")


def load_agent_prompt():
    if not AGENT_PROMPT_FILE.exists():
        return (
            "Eres AI-LAB, un runtime cognitivo privado. "
            "Responde siempre en español, de forma clara, segura y operativa."
        )

    return AGENT_PROMPT_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def sanitize_text(value):
    if not isinstance(value, str):
        return value

    return (
        value
        .replace("\ufffd", "")
        .replace("\x00", "")
        .strip()
    )


def inject_agent_context(payload):
    messages = payload.get("messages", [])

    system_prompt = load_agent_prompt()

    injected = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    for msg in messages:
        injected.append(msg)

    payload["messages"] = injected

    payload["stream"] = False

    if "max_tokens" not in payload or payload.get("max_tokens", 0) < 1024:
        payload["max_tokens"] = 2048

    if "temperature" not in payload:
        payload["temperature"] = 0.2

    return payload


def proxy_json(method, path, payload=None):
    url = f"{LMSTUDIO_BASE_URL}{path}"

    data = None

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer lm-studio",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    with urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8", errors="ignore")
        return response.status, json.loads(raw)


def sanitize_completion_response(data):
    choices = data.get("choices", [])

    for choice in choices:
        message = choice.get("message", {})

        if "reasoning_content" in message:
            message.pop("reasoning_content", None)

        content = message.get("content", "")

        message["content"] = sanitize_text(content)

        if not message["content"]:
            message["content"] = "Respuesta generada, pero el contenido final llegó vacío desde el modelo."

    return data


class GatewayHandler(BaseHTTPRequestHandler):

    def _send_json(self, status, data):
        body = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            try:
                status, data = proxy_json(
                    "GET",
                    "/models",
                )

                self._send_json(status, data)

            except Exception as exc:
                self._send_json(
                    502,
                    {
                        "error": "gateway_models_proxy_failed",
                        "detail": str(exc),
                    },
                )

            return

        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "backend": LMSTUDIO_BASE_URL,
                    "time": int(time.time()),
                },
            )

            return

        self._send_json(
            404,
            {
                "error": "not_found",
                "path": self.path,
            },
        )

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json(
                404,
                {
                    "error": "not_found",
                    "path": self.path,
                },
            )

            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(content_length)

            payload = json.loads(
                raw_body.decode("utf-8")
            )

            payload = inject_agent_context(payload)

            status, data = proxy_json(
                "POST",
                "/chat/completions",
                payload,
            )

            data = sanitize_completion_response(data)

            self._send_json(status, data)

        except HTTPError as exc:
            self._send_json(
                exc.code,
                {
                    "error": "backend_http_error",
                    "detail": str(exc),
                },
            )

        except URLError as exc:
            self._send_json(
                502,
                {
                    "error": "backend_unreachable",
                    "detail": str(exc),
                },
            )

        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": "gateway_error",
                    "detail": str(exc),
                },
            )


def run():
    server = HTTPServer(
        (HOST, PORT),
        GatewayHandler,
    )

    print("AI-LAB OPENAI GATEWAY")
    print("=====================")
    print(f"Listening: http://{HOST}:{PORT}")
    print(f"Backend:   {LMSTUDIO_BASE_URL}")
    print("Mode:      non-stream sanitized")
    print()

    server.serve_forever()


if __name__ == "__main__":
    run()
