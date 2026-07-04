import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from runtime.hermes.enterprise_status import build_enterprise_status


class HermesStatusHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:
        if self.path == "/hermes/status":
            self._handle_status()
        elif self.path == "/health":
            self._handle_health()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not_found", "path": self.path}).encode())

    def _handle_status(self) -> None:
        data = build_enterprise_status()
        body = json.dumps(data, indent=2, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_health(self) -> None:
        body = json.dumps({"status": "ok", "service": "hermes-enterprise-status"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(host: str = "127.0.0.1", port: int = 8095) -> None:
    server = HTTPServer((host, port), HermesStatusHandler)
    print(f"Hermes Enterprise Status endpoint: http://{host}:{port}/hermes/status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8095
    serve(host, port)
