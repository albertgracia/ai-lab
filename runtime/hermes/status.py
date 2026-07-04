import json
import os

from runtime.hermes.loader import load_all, load_soul
from runtime.hermes.validation import validate_all, build_capability_dependency_graph
from runtime.hermes.models import StatusReport, HermesRegistry


def _soul_files_exist() -> bool:
    soul_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soul")
    required = ["identity.yaml", "truth_model.yaml", "protocols.yaml", "boundaries.yaml", "domains.yaml"]
    for fname in required:
        if not os.path.exists(os.path.join(soul_dir, fname)):
            return False
    return True


def build_status_report(registry: HermesRegistry | None = None) -> StatusReport:
    if registry is None:
        registry = load_all()

    validation = validate_all(registry)
    dep_graph = build_capability_dependency_graph(registry)

    cap_errors = [e for e in validation.errors if e.source.startswith("capabilities/")]
    cap_warnings = [w for w in validation.warnings if w.source.startswith("capabilities/")]

    cap_validation = {
        "total": len(registry.capabilities),
        "errors": len(cap_errors),
        "warnings": len(cap_warnings),
        "critical_present": True,
    }

    dep_info = {
        "nodes": dep_graph.nodes,
        "edges": dep_graph.edges,
        "cycles_detected": dep_graph.cycles_detected,
        "cycles": dep_graph.cycles,
    }

    return StatusReport(
        registries_loaded=True,
        soul_loaded=_soul_files_exist(),
        capabilities_count=len(registry.capabilities),
        operators_count=len(registry.operators),
        hooks_count=len(registry.hooks),
        mcp_servers_count=len(registry.mcp_servers),
        enforcement_active=False,
        errors=[{"field": e.field, "message": e.message, "source": e.source} for e in validation.errors],
        warnings=[{"field": w.field, "message": w.message, "source": w.source} for w in validation.warnings],
        capability_validation=cap_validation,
        capability_dependency_graph=dep_info,
        capability_cycles_detected=dep_graph.cycles_detected,
    )


def status_json(registry: HermesRegistry | None = None) -> str:
    report = build_status_report(registry)
    return json.dumps({
        "registries_loaded": report.registries_loaded,
        "soul_loaded": report.soul_loaded,
        "capabilities_count": report.capabilities_count,
        "operators_count": report.operators_count,
        "hooks_count": report.hooks_count,
        "mcp_servers_count": report.mcp_servers_count,
        "enforcement_active": report.enforcement_active,
        "errors": report.errors,
        "warnings": report.warnings,
        "capability_validation": report.capability_validation,
        "capability_dependency_graph": report.capability_dependency_graph,
        "capability_cycles_detected": report.capability_cycles_detected,
    }, indent=2, ensure_ascii=False)


def cli_main() -> None:
    print(status_json())


if __name__ == "__main__":
    cli_main()
