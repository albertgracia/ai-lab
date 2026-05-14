import json
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from runtime.gateway.stream_sanitizer import relay_stream


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

    if "temperature" not in payload:
        payload["temperature"] = 0.2

    if (
        "max_tokens" not in payload
        or payload.get("max_tokens", 0) < 1024
    ):
        payload["max_tokens"] = 2048

    return payload


def sanitize_completion_response(data):
    choices = data.get("choices", [])

    for choice in choices:
        message = choice.get("message", {})

        if "reasoning_content" in message:
            message.pop("reasoning_content", None)

        content = message.get("content", "")

        message["content"] = sanitize_text(content)

        if not message["content"]:
            message["content"] = (
                "Respuesta generada, pero el contenido final "
                "llegó vacío desde el modelo."
            )

    return data


def backend_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer lm-studio",
    }


class GatewayHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(
            "%s - - [%s] %s"
            % (
                self.client_address[0],
                self.log_date_time_string(),
                format % args,
            )
        )

    def _send_json(self, status, data):
        body = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/event-stream; charset=utf-8",
        )
        self.send_header(
            "Cache-Control",
            "no-cache",
        )
        self.send_header(
            "Connection",
            "keep-alive",
        )
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "backend": LMSTUDIO_BASE_URL,
                    "mode": "stream-aware sanitized",
                    "time": int(time.time()),
                },
            )
            return

        if self.path == "/v1/models":
            try:
                response = requests.get(
                    f"{LMSTUDIO_BASE_URL}/models",
                    headers=backend_headers(),
                    timeout=30,
                )

                self._send_json(
                    response.status_code,
                    response.json(),
                )

            except Exception as exc:
                self._send_json(
                    502,
                    {
                        "error": "gateway_models_proxy_failed",
                        "detail": str(exc),
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
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            raw_body = self.rfile.read(content_length)

            payload = json.loads(
                raw_body.decode("utf-8")
            )

            payload = inject_agent_context(payload)

            stream_enabled = bool(
                payload.get("stream", False)
            )

            response = requests.post(
                f"{LMSTUDIO_BASE_URL}/chat/completions",
                headers=backend_headers(),
                json=payload,
                stream=stream_enabled,
                timeout=600,
            )

            if stream_enabled:
                self._send_sse_headers()

                relay_stream(response, self)

                return

            data = response.json()

            data = sanitize_completion_response(data)

            self._send_json(
                response.status_code,
                data,
            )

        except requests.exceptions.RequestException as exc:
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
    print("Mode:      stream-aware sanitized")
    print()

    server.serve_forever()


if __name__ == "__main__":
    run()
