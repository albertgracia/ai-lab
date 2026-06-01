from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "mcp" / "runtime-mcp"

EXPECTED_TOOLS = {
    "ailab_status",
    "ailab_runtime_health",
    "ailab_route_preview",
    "ailab_operator_summary",
    "ailab_incidents_active",
    "ailab_slo_status",
    "ailab_health_latency",
    "ailab_memory_search",
}

FORBIDDEN_PATTERNS = {
    "AILAB_MCP_TOKEN=",
    "Authorization: Bearer ",
    "BEGIN RSA",
    "BEGIN OPENSSH",
    "private_key",
    "PASSWORD=",
    "SECRET=",
    "API_KEY=",
}

FORBIDDEN_MUTABLE_CALLS = {
    "os.system",
    "subprocess.run",
    "subprocess.Popen",
    "shutil.rmtree",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_snapshot_files_exist() -> None:
    assert (SNAPSHOT / "server.py").is_file()
    assert (SNAPSHOT / "lan_server.py").is_file()
    assert (SNAPSHOT / "README.md").is_file()
    assert (SNAPSHOT / "SYNC-POLICY.md").is_file()


def test_snapshot_python_files_parse() -> None:
    for path in (SNAPSHOT / "server.py", SNAPSHOT / "lan_server.py"):
        ast.parse(read_text(path), filename=str(path))


def test_expected_tools_are_present_in_snapshot() -> None:
    combined = "\n".join(
        read_text(path)
        for path in (SNAPSHOT / "server.py", SNAPSHOT / "lan_server.py")
    )
    missing = sorted(tool for tool in EXPECTED_TOOLS if tool not in combined)
    assert not missing, f"Missing expected MCP tools: {missing}"


def test_no_secret_values_are_versioned() -> None:
    for path in SNAPSHOT.rglob("*"):
        if not path.is_file():
            continue
        text = read_text(path)
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in text, f"Forbidden secret-like pattern {pattern!r} in {path}"


def test_no_obvious_mutable_shell_operations() -> None:
    for path in (SNAPSHOT / "server.py", SNAPSHOT / "lan_server.py"):
        text = read_text(path)
        for pattern in FORBIDDEN_MUTABLE_CALLS:
            assert pattern not in text, f"Forbidden mutable operation {pattern!r} in {path}"
