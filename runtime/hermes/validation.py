from runtime.hermes.models import (
    HermesRegistry, ValidationResult, ValidationError, ValidationWarning,
)


def validate_all(registry: HermesRegistry) -> ValidationResult:
    result = ValidationResult(valid=True)

    _validate_capability_domains(registry, result)
    _validate_capability_mcp(registry, result)
    _validate_operator_capabilities(registry, result)
    _validate_operator_domains(registry, result)
    _validate_hooks_disabled(registry, result)
    _validate_mcp_servers_status(registry, result)
    _validate_hook_modes(registry, result)

    if result.errors:
        result.valid = False

    return result


def _validate_capability_domains(registry: HermesRegistry, result: ValidationResult) -> None:
    valid_domains = {"ai-lab", "marketplace", "observability", "gitnexus", "windows"}
    for cap in registry.capabilities:
        for domain in cap.domains:
            if domain not in valid_domains:
                result.errors.append(ValidationError(
                    field="domains",
                    message=f"Capability '{cap.id}' references unknown domain '{domain}'",
                    source=f"capabilities/{cap.id}",
                ))


def _validate_capability_mcp(registry: HermesRegistry, result: ValidationResult) -> None:
    mcp_ids = {s.id for s in registry.mcp_servers}
    for cap in registry.capabilities:
        for mcp_id in cap.required_mcp:
            if mcp_id not in mcp_ids:
                result.warnings.append(ValidationWarning(
                    field="required_mcp",
                    message=f"Capability '{cap.id}' requires MCP '{mcp_id}' which is not in registry",
                    source=f"capabilities/{cap.id}",
                ))
        for mcp_id in cap.optional_mcp:
            if mcp_id not in mcp_ids:
                result.warnings.append(ValidationWarning(
                    field="optional_mcp",
                    message=f"Capability '{cap.id}' optionally requires MCP '{mcp_id}' which is not in registry",
                    source=f"capabilities/{cap.id}",
                ))


def _validate_operator_capabilities(registry: HermesRegistry, result: ValidationResult) -> None:
    cap_ids = {c.id for c in registry.capabilities}
    for op in registry.operators:
        for cap_id in op.capabilities:
            if cap_id not in cap_ids:
                result.errors.append(ValidationError(
                    field="capabilities",
                    message=f"Operator '{op.id}' references capability '{cap_id}' which does not exist",
                    source=f"operators/{op.id}",
                ))


def _validate_operator_domains(registry: HermesRegistry, result: ValidationResult) -> None:
    valid_domains = {"ai-lab", "marketplace", "observability", "gitnexus", "windows"}
    for op in registry.operators:
        for domain in op.domains:
            if domain not in valid_domains:
                result.errors.append(ValidationError(
                    field="domains",
                    message=f"Operator '{op.id}' references unknown domain '{domain}'",
                    source=f"operators/{op.id}",
                ))


def _validate_hooks_disabled(registry: HermesRegistry, result: ValidationResult) -> None:
    for hook in registry.hooks:
        if hook.enabled:
            result.errors.append(ValidationError(
                field="enabled",
                message=f"Hook '{hook.id}' is enabled but enforcement must be disabled",
                source=f"hooks/{hook.id}",
            ))


def _validate_mcp_servers_status(registry: HermesRegistry, result: ValidationResult) -> None:
    for server in registry.mcp_servers:
        if server.status not in ("active", "degraded", "planned", "deprecated"):
            result.warnings.append(ValidationWarning(
                field="status",
                message=f"MCP server '{server.id}' has unknown status '{server.status}'",
                source=f"mcp/{server.id}",
            ))


def _validate_hook_modes(registry: HermesRegistry, result: ValidationResult) -> None:
    for hook in registry.hooks:
        if hook.mode != "declarative_only":
            result.warnings.append(ValidationWarning(
                field="mode",
                message=f"Hook '{hook.id}' mode is '{hook.mode}', expected 'declarative_only'",
                source=f"hooks/{hook.id}",
            ))
