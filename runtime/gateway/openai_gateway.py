import json
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
import time

from runtime.router.capability_router import choose_model

from runtime.telemetry.gateway_metrics import (
    register_request,
    register_stream,
    register_error,
    register_latency,
    get_metrics,
)

from runtime.distributed.execution_coordinator import (
    register_execution,
)

from runtime.telemetry.runtime_api import (
    runtime_snapshot,
)

from runtime.distributed.runtime_topology import (
    get_topology,
)

from runtime.telemetry.runtime_api import (
    runtime_snapshot,
)

from runtime.distributed.execution_coordinator import (
    register_execution,
)


from runtime.gateway.stream_sanitizer import relay_stream
from runtime.gateway.gateway_metrics import (
    load_metrics,
    record_request,
    record_error,
)
from collections import defaultdict
import threading

RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60
_rate_limit_data: dict = defaultdict(list)
_rate_limit_lock = threading.Lock()


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    with _rate_limit_lock:
        timestamps = _rate_limit_data[client_ip]
        timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        _rate_limit_data[client_ip] = timestamps
        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            return False
        timestamps.append(now)
        return True



HOST = "0.0.0.0"
PORT = 8008

BACKENDS = [
    {"name": "rx9070", "url": "http://192.168.1.50:1234/v1", "enabled": True},
    {"name": "nas-n5", "url": "http://192.168.1.200:12345/v1", "enabled": False},
    {"name": "rx7900xt", "url": "http://192.168.1.60:1234/v1", "enabled": False},
]

PRIMARY_BACKEND = "rx9070"


def get_active_backend():
    for backend in BACKENDS:
        if backend["enabled"]:
            return backend

    return BACKENDS[0]

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
        client_ip = self.client_address[0]
        if not check_rate_limit(client_ip):
            self._send_json(429, {"error": "rate_limit_exceeded", "message": "Too many requests. Try again later."})
            return
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "ai-lab-openai-gateway",
                    "backend": get_active_backend()["url"],
                    "mode": "stream-aware sanitized",
                    "time": int(time.time()),
                },
            )
            return

        
        
        if self.path == "/metrics":
            metrics = load_metrics()
            prom_text = (
                "# HELP ailab_requests_total Total requests\n"
                "# TYPE ailab_requests_total counter\n"
                f"ailab_requests_total {metrics.get('requests_total', 0)}\n"
                "# HELP ailab_streams_total Total streaming requests\n"
                "# TYPE ailab_streams_total counter\n"
                f"ailab_streams_total {metrics.get('streams_total', 0)}\n"
                "# HELP ailab_errors_total Total errors\n"
                "# TYPE ailab_errors_total counter\n"
                f"ailab_errors_total {metrics.get('errors_total', 0)}\n"
                "# HELP ailab_last_latency_ms Last request latency\n"
                "# TYPE ailab_last_latency_ms gauge\n"
                f"ailab_last_latency_ms {metrics.get('last_latency_ms', 0) or 0}\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(prom_text.encode("utf-8"))
            return

        if self.path == "/runtime/topology":
            self._send_json(
                200,
                get_topology()
            )
            return

        if self.path == "/runtime/status":

            self._send_json(
                200,
                runtime_snapshot()
            )
            return

        if self.path == "/gateway/metrics":

            self._send_json(
                200,
                load_metrics(),
            )
            return

        if self.path == "/v1/models":
            start_time = time.time()

            try:
                response = requests.get(
                    f"{get_active_backend()['url']}/models",
                    headers=backend_headers(),
                    timeout=30,
                )

                latency_ms = int(
                    (time.time() - start_time) * 1000
                )

                record_request(
                    self.path,
                    model=None,
                    latency_ms=latency_ms,
                    stream=False,
                )

                self._send_json(
                    response.status_code,
                    response.json(),
                )

            except Exception as exc:
                record_error(
                    self.path,
                    exc,
                )

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
        client_ip = self.client_address[0]
        if not check_rate_limit(client_ip):
            self._send_json(429, {"error": "rate_limit_exceeded", "message": "Too many requests. Try again later."})
            return
        if self.path != "/v1/chat/completions":
            self._send_json(
                404,
                {
                    "error": "not_found",
                    "path": self.path,
                },
            )
            return

        start_time = time.time()

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

            requested_model = payload.get(
                "model",
                "default"
            )

            task_type = "reasoning"

            if "code" in str(payload).lower():
                task_type = "coding"

            selected_model = choose_model(
                task_type
            )

            payload["model"] = selected_model

            stream_enabled = bool(
                payload.get("stream", False)
            )

            response = requests.post(
                f"{get_active_backend()['url']}/chat/completions",
                headers=backend_headers(),
                json=payload,
                stream=stream_enabled,
                timeout=600,
            )

            latency_ms = int(
                (time.time() - start_time) * 1000
            )

            record_request(
                self.path,
                model=payload.get("model"),
                latency_ms=latency_ms,
                stream=stream_enabled,
            )

            if stream_enabled:
                register_stream()
                self._send_sse_headers()

                relay_stream(
                    response,
                    self,
                )

                return

            data = response.json()

            data = sanitize_completion_response(data)

            self._send_json(
                response.status_code,
                data,
            )

        except requests.exceptions.RequestException as exc:
            record_error(
                self.path,
                exc,
            )

            self._send_json(
                502,
                {
                    "error": "backend_unreachable",
                    "detail": str(exc),
                },
            )

        except Exception as exc:
            record_error(
                self.path,
                exc,
            )

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
    backend = get_active_backend()
    print(f"Backend:   {backend['name']} @ {backend['url']}")
    print("Mode:      stream-aware sanitized + metrics")
    print()

    server.serve_forever()


if __name__ == "__main__":
    run()
