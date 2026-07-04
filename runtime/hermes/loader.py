import os
import json
import yaml

from runtime.hermes.models import (
    HermesRegistry, Capability, MCPServer, MCPTool,
    Operator, Hook, SoulIdentity, SoulTruthModel,
    SoulProtocol, SoulBoundaries, SoulDomain,
)

HERMES_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        return yaml.safe_load(content) or {}
    except yaml.YAMLError:
        stripped = _extract_yaml_block(content)
        return yaml.safe_load(stripped) or {}


def _load_yaml_list(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        return yaml.safe_load(content) or []
    except yaml.YAMLError:
        stripped = _extract_yaml_block(content)
        return yaml.safe_load(stripped) or []


def _extract_yaml_block(content: str) -> str:
    lines = content.splitlines()
    in_block = False
    block_lines = []
    for line in lines:
        if line.strip().startswith("```yaml"):
            in_block = True
            continue
        if line.strip().startswith("```") and in_block:
            in_block = False
            continue
        if in_block:
            block_lines.append(line)
    return "\n".join(block_lines)


def load_soul() -> dict[str, object]:
    soul_dir = os.path.join(HERMES_DIR, "soul")
    result = {}

    identity_path = os.path.join(soul_dir, "identity.yaml")
    if os.path.exists(identity_path):
        result["identity"] = _load_yaml(identity_path)

    truth_path = os.path.join(soul_dir, "truth_model.yaml")
    if os.path.exists(truth_path):
        result["truth_model"] = _load_yaml(truth_path)

    protocols_path = os.path.join(soul_dir, "protocols.yaml")
    if os.path.exists(protocols_path):
        result["protocols"] = _load_yaml(protocols_path)

    boundaries_path = os.path.join(soul_dir, "boundaries.yaml")
    if os.path.exists(boundaries_path):
        result["boundaries"] = _load_yaml(boundaries_path)

    domains_path = os.path.join(soul_dir, "domains.yaml")
    if os.path.exists(domains_path):
        result["domains"] = _load_yaml(domains_path)

    return result


def load_capabilities() -> list[Capability]:
    caps_dir = os.path.join(HERMES_DIR, "capabilities")
    schema_path = os.path.join(caps_dir, "capability.schema.json")
    schema = _load_json_schema(schema_path)

    capabilities = []
    for fname in sorted(os.listdir(caps_dir)):
        if not fname.endswith(".yaml") or fname == "capability.schema.json":
            continue
        fpath = os.path.join(caps_dir, fname)
        data = _load_yaml(fpath)
        capabilities.append(Capability(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            purpose=data.get("purpose", ""),
            domains=data.get("domains", []),
            required_mcp=data.get("required_mcp", []),
            optional_mcp=data.get("optional_mcp", []),
            permissions=data.get("permissions", {}),
            forbidden_actions=data.get("forbidden_actions", []),
            evidence_requirements=data.get("evidence_requirements", {}),
            reports=data.get("reports", []),
            dependencies=data.get("dependencies", []),
            raw=data,
        ))
    return capabilities


def _load_json_schema(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_mcp_servers() -> list[MCPServer]:
    mcp_dir = os.path.join(HERMES_DIR, "mcp")

    servers = []
    for fname in sorted(os.listdir(mcp_dir)):
        if not fname.endswith(".yaml") or fname == "registry.yaml":
            continue
        fpath = os.path.join(mcp_dir, fname)
        data = _load_yaml(fpath)

        tools_raw = data.get("tools", [])
        tools = [
            MCPTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                read_only=t.get("read_only", True),
            )
            for t in tools_raw
        ]

        servers.append(MCPServer(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", ""),
            protocol=data.get("protocol", ""),
            tools=tools,
            status=data.get("status", "planned"),
            priority=data.get("priority", 50),
            auth=data.get("auth", {}),
            raw=data,
        ))
    return servers


def load_operators() -> list[Operator]:
    ops_dir = os.path.join(HERMES_DIR, "operators")

    operators = []
    for fname in sorted(os.listdir(ops_dir)):
        if not fname.endswith(".yaml"):
            continue
        fpath = os.path.join(ops_dir, fname)
        data = _load_yaml(fpath)

        operators.append(Operator(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            domains=data.get("domains", []),
            execution_mode=data.get("execution_mode", "readonly"),
            required_mcp=data.get("required_mcp", []),
            priority=data.get("priority", 50),
            authorization_required=data.get("authorization_required", False),
            raw=data,
        ))
    return operators


def load_hooks() -> list[Hook]:
    hooks_dir = os.path.join(HERMES_DIR, "hooks", "lifecycle")

    hooks = []
    if not os.path.isdir(hooks_dir):
        return hooks

    for fname in sorted(os.listdir(hooks_dir)):
        if not fname.endswith(".yaml"):
            continue
        fpath = os.path.join(hooks_dir, fname)
        data = _load_yaml(fpath)

        hooks.append(Hook(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            lifecycle_event=data.get("lifecycle_event", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", False),
            mode=data.get("mode", "declarative_only"),
            timeout_ms=data.get("timeout_ms", 5000),
            failure_policy=data.get("failure_policy", "log"),
            raw=data,
        ))
    return hooks


def load_all() -> HermesRegistry:
    registry = HermesRegistry()

    soul_raw = load_soul()
    if soul_raw:
        pass

    registry.capabilities = load_capabilities()
    registry.mcp_servers = load_mcp_servers()
    registry.operators = load_operators()
    registry.hooks = load_hooks()

    return registry
