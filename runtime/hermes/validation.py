from runtime.hermes.models import (
    HermesRegistry, ValidationResult, ValidationError, ValidationWarning,
    CapabilityDependencyGraph,
)


def validate_all(registry: HermesRegistry) -> ValidationResult:
    result = ValidationResult(valid=True)

    _validate_capability_ids_unique(registry, result)
    _validate_capability_required_fields(registry, result)
    _validate_capability_domains(registry, result)
    _validate_capability_mcp(registry, result)
    _validate_capability_dependencies_exist(registry, result)
    _validate_capability_inputs_outputs(registry, result)
    _validate_capability_permissions(registry, result)
    _validate_capability_forbidden_actions(registry, result)
    _validate_capability_evidence(registry, result)
    _validate_critical_capabilities(registry, result)

    _validate_operator_ids_unique(registry, result)
    _validate_operator_capabilities(registry, result)
    _validate_operator_domains(registry, result)
    _validate_operator_mcp(registry, result)
    _validate_operator_execution_mode(registry, result)
    _validate_operator_protocols(registry, result)
    _validate_operator_reports(registry, result)
    _validate_operator_forbidden_actions(registry, result)
    _validate_operator_success_criteria(registry, result)
    _validate_operator_truth_model(registry, result)
    _validate_hooks_disabled(registry, result)
    _validate_mcp_servers_status(registry, result)
    _validate_hook_modes(registry, result)

    if result.errors:
        result.valid = False

    return result


def build_capability_dependency_graph(registry: HermesRegistry) -> CapabilityDependencyGraph:
    cap_ids = {c.id for c in registry.capabilities}
    nodes = sorted(cap_ids)
    edges = []
    cycles = []
    cycles_detected = False

    for cap in registry.capabilities:
        for dep in cap.dependencies:
            if dep in cap_ids:
                edges.append({"from": cap.id, "to": dep})

    adj = {c: [] for c in cap_ids}
    for cap in registry.capabilities:
        for dep in cap.dependencies:
            if dep in cap_ids:
                adj[cap.id].append(dep)

    visited = set()
    rec_stack = set()
    parent_map: dict[str, str | None] = {}

    def _dfs(node: str) -> None:
        nonlocal cycles_detected
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                parent_map[neighbor] = node
                _dfs(neighbor)
            elif neighbor in rec_stack:
                cycles_detected = True
                path = []
                cur: str | None = node
                while cur is not None and cur != neighbor:
                    path.append(cur)
                    cur = parent_map.get(cur)
                path.append(neighbor)
                path.reverse()
                cycles.append(path)
        rec_stack.discard(node)

    for c in sorted(cap_ids):
        if c not in visited:
            _dfs(c)

    return CapabilityDependencyGraph(
        nodes=nodes, edges=edges,
        cycles_detected=cycles_detected, cycles=cycles,
    )


def _validate_capability_ids_unique(registry: HermesRegistry, result: ValidationResult) -> None:
    seen: set[str] = set()
    for cap in registry.capabilities:
        if cap.id in seen:
            result.errors.append(ValidationError(
                field="id",
                message=f"Duplicate capability ID '{cap.id}'",
                source=f"capabilities/{cap.id}",
            ))
        seen.add(cap.id)


def _validate_capability_required_fields(registry: HermesRegistry, result: ValidationResult) -> None:
    for cap in registry.capabilities:
        if not cap.purpose:
            result.warnings.append(ValidationWarning(
                field="purpose",
                message=f"Capability '{cap.id}' has empty purpose",
                source=f"capabilities/{cap.id}",
            ))
        if not cap.domains:
            result.errors.append(ValidationError(
                field="domains",
                message=f"Capability '{cap.id}' has no domains declared",
                source=f"capabilities/{cap.id}",
            ))
        if not cap.required_mcp and not cap.optional_mcp:
            result.warnings.append(ValidationWarning(
                field="required_mcp",
                message=f"Capability '{cap.id}' has no MCP servers (required or optional)",
                source=f"capabilities/{cap.id}",
            ))


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


def _validate_capability_dependencies_exist(registry: HermesRegistry, result: ValidationResult) -> None:
    cap_ids = {c.id for c in registry.capabilities}
    for cap in registry.capabilities:
        for dep in cap.dependencies:
            if dep not in cap_ids:
                result.errors.append(ValidationError(
                    field="dependencies",
                    message=f"Capability '{cap.id}' depends on '{dep}' which does not exist",
                    source=f"capabilities/{cap.id}",
                ))


def _validate_capability_inputs_outputs(registry: HermesRegistry, result: ValidationResult) -> None:
    for cap in registry.capabilities:
        raw = cap.raw
        inputs = raw.get("inputs", {})
        outputs = raw.get("outputs", {})
        if not isinstance(inputs, dict) or len(inputs) == 0:
            result.warnings.append(ValidationWarning(
                field="inputs",
                message=f"Capability '{cap.id}' has no inputs declared",
                source=f"capabilities/{cap.id}",
            ))
        if not isinstance(outputs, dict) or len(outputs) == 0:
            result.warnings.append(ValidationWarning(
                field="outputs",
                message=f"Capability '{cap.id}' has no outputs declared",
                source=f"capabilities/{cap.id}",
            ))


def _validate_capability_permissions(registry: HermesRegistry, result: ValidationResult) -> None:
    for cap in registry.capabilities:
        perms = cap.permissions
        if not isinstance(perms, dict):
            result.errors.append(ValidationError(
                field="permissions",
                message=f"Capability '{cap.id}' permissions is not a dict",
                source=f"capabilities/{cap.id}",
            ))
            continue
        if "read_only" not in perms:
            result.warnings.append(ValidationWarning(
                field="permissions.read_only",
                message=f"Capability '{cap.id}' missing read_only in permissions",
                source=f"capabilities/{cap.id}",
            ))
        if "governance_levels" not in perms:
            result.warnings.append(ValidationWarning(
                field="permissions.governance_levels",
                message=f"Capability '{cap.id}' missing governance_levels in permissions",
                source=f"capabilities/{cap.id}",
            ))


def _validate_capability_forbidden_actions(registry: HermesRegistry, result: ValidationResult) -> None:
    for cap in registry.capabilities:
        if not cap.forbidden_actions:
            result.warnings.append(ValidationWarning(
                field="forbidden_actions",
                message=f"Capability '{cap.id}' has no forbidden actions declared",
                source=f"capabilities/{cap.id}",
            ))


def _validate_capability_evidence(registry: HermesRegistry, result: ValidationResult) -> None:
    for cap in registry.capabilities:
        ev = cap.evidence_requirements
        if not isinstance(ev, dict):
            result.warnings.append(ValidationWarning(
                field="evidence_requirements",
                message=f"Capability '{cap.id}' missing evidence_requirements",
                source=f"capabilities/{cap.id}",
            ))
            continue
        if "min_confidence" not in ev:
            result.warnings.append(ValidationWarning(
                field="evidence_requirements.min_confidence",
                message=f"Capability '{cap.id}' missing min_confidence in evidence_requirements",
                source=f"capabilities/{cap.id}",
            ))
        if "require_citations" not in ev:
            result.warnings.append(ValidationWarning(
                field="evidence_requirements.require_citations",
                message=f"Capability '{cap.id}' missing require_citations in evidence_requirements",
                source=f"capabilities/{cap.id}",
            ))


def _validate_critical_capabilities(registry: HermesRegistry, result: ValidationResult) -> None:
    critical_ids = {
        "ai-lab-runtime", "gitnexus-analysis", "observability",
        "marketplace-operator", "deployment-review", "incident-response",
    }
    loaded_ids = {c.id for c in registry.capabilities}
    for cid in critical_ids:
        if cid not in loaded_ids:
            result.errors.append(ValidationError(
                field="critical",
                message=f"Critical capability '{cid}' is missing from registry",
                source="capabilities/",
            ))


def _validate_operator_ids_unique(registry: HermesRegistry, result: ValidationResult) -> None:
    seen: set[str] = set()
    for op in registry.operators:
        if op.id in seen:
            result.errors.append(ValidationError(
                field="id",
                message=f"Duplicate operator ID '{op.id}'",
                source=f"operators/{op.id}",
            ))
        seen.add(op.id)


def _validate_operator_capabilities(registry: HermesRegistry, result: ValidationResult) -> None:
    cap_ids = {c.id for c in registry.capabilities}
    for op in registry.operators:
        if not op.capabilities:
            result.errors.append(ValidationError(
                field="capabilities",
                message=f"Operator '{op.id}' has no capabilities declared",
                source=f"operators/{op.id}",
            ))
            continue
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
        if not op.domains:
            result.errors.append(ValidationError(
                field="domains",
                message=f"Operator '{op.id}' has no domains declared",
                source=f"operators/{op.id}",
            ))
            continue
        for domain in op.domains:
            if domain not in valid_domains:
                result.errors.append(ValidationError(
                    field="domains",
                    message=f"Operator '{op.id}' references unknown domain '{domain}'",
                    source=f"operators/{op.id}",
                ))


def _validate_operator_mcp(registry: HermesRegistry, result: ValidationResult) -> None:
    mcp_ids = {s.id for s in registry.mcp_servers}
    for op in registry.operators:
        for mcp_id in op.required_mcp:
            if mcp_id not in mcp_ids:
                result.warnings.append(ValidationWarning(
                    field="required_mcp",
                    message=f"Operator '{op.id}' requires MCP '{mcp_id}' which is not in registry",
                    source=f"operators/{op.id}",
                ))


def _validate_operator_execution_mode(registry: HermesRegistry, result: ValidationResult) -> None:
    valid_modes = {"readonly", "advisory", "execute"}
    for op in registry.operators:
        if op.execution_mode not in valid_modes:
            result.errors.append(ValidationError(
                field="execution_mode",
                message=f"Operator '{op.id}' has invalid execution_mode '{op.execution_mode}'",
                source=f"operators/{op.id}",
            ))
        if op.execution_mode == "readonly" and op.authorization_required:
            result.warnings.append(ValidationWarning(
                field="authorization_required",
                message=f"Operator '{op.id}' is readonly but requires authorization",
                source=f"operators/{op.id}",
            ))
        if op.execution_mode == "execute" and not op.authorization_required:
            result.warnings.append(ValidationWarning(
                field="authorization_required",
                message=f"Operator '{op.id}' is execute mode but does not require authorization",
                source=f"operators/{op.id}",
            ))


def _validate_operator_protocols(registry: HermesRegistry, result: ValidationResult) -> None:
    valid_protocols = {
        "gitnexus_first", "mcp_first", "evidence_first",
        "backup_before_write", "no_restart_without_authorization",
        "no_pass_without_validation",
    }
    for op in registry.operators:
        for proto in op.required_protocols:
            if proto not in valid_protocols:
                result.warnings.append(ValidationWarning(
                    field="required_protocols",
                    message=f"Operator '{op.id}' references unknown protocol '{proto}'",
                    source=f"operators/{op.id}",
                ))


def _validate_operator_reports(registry: HermesRegistry, result: ValidationResult) -> None:
    for op in registry.operators:
        if not op.reports:
            result.warnings.append(ValidationWarning(
                field="reports",
                message=f"Operator '{op.id}' has no reports declared",
                source=f"operators/{op.id}",
            ))
        else:
            for r in op.reports:
                if not isinstance(r.get("type"), str):
                    result.warnings.append(ValidationWarning(
                        field="reports.type",
                        message=f"Operator '{op.id}' has report without type",
                        source=f"operators/{op.id}",
                    ))


def _validate_operator_forbidden_actions(registry: HermesRegistry, result: ValidationResult) -> None:
    for op in registry.operators:
        if not op.forbidden_actions:
            result.warnings.append(ValidationWarning(
                field="forbidden_actions",
                message=f"Operator '{op.id}' has no forbidden actions declared",
                source=f"operators/{op.id}",
            ))


def _validate_operator_success_criteria(registry: HermesRegistry, result: ValidationResult) -> None:
    for op in registry.operators:
        if not op.success_criteria:
            result.warnings.append(ValidationWarning(
                field="success_criteria",
                message=f"Operator '{op.id}' has no success_criteria declared",
                source=f"operators/{op.id}",
            ))
        if not op.failure_conditions:
            result.warnings.append(ValidationWarning(
                field="failure_conditions",
                message=f"Operator '{op.id}' has no failure_conditions declared",
                source=f"operators/{op.id}",
            ))


def _validate_operator_truth_model(registry: HermesRegistry, result: ValidationResult) -> None:
    for op in registry.operators:
        tm = op.truth_model
        if not isinstance(tm, dict):
            result.warnings.append(ValidationWarning(
                field="truth_model",
                message=f"Operator '{op.id}' missing truth_model",
                source=f"operators/{op.id}",
            ))
            continue
        if "min_confidence" not in tm:
            result.warnings.append(ValidationWarning(
                field="truth_model.min_confidence",
                message=f"Operator '{op.id}' missing min_confidence in truth_model",
                source=f"operators/{op.id}",
            ))
        if "require_citations" not in tm:
            result.warnings.append(ValidationWarning(
                field="truth_model.require_citations",
                message=f"Operator '{op.id}' missing require_citations in truth_model",
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
