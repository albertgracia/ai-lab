from runtime.modes.registry import describe_mode, list_modes
from runtime.security.capability_guard import explain_capability
from runtime.policies.execution_policy import explain_command
from runtime.audit.audit_logger import audit_event


def main():
    print("== MODES ==")
    for mode in list_modes():
        print(describe_mode(mode))

    print("\n== CAPABILITIES ==")
    tests = [
        ("plan", "write"),
        ("readonly", "logs"),
        ("build", "write"),
        ("build", "deploy"),
        ("execute", "deploy"),
    ]

    for mode, capability in tests:
        result = explain_capability(mode, capability)
        print(result)

    print("\n== COMMAND POLICY ==")
    commands = [
        ("readonly", "ls -la"),
        ("build", "python3 -m py_compile runtime/llm/router_api.py"),
        ("build", "systemctl restart ialab-router-api"),
        ("execute", "systemctl restart ialab-router-api"),
        ("execute", "rm -rf /opt/ai-lab"),
    ]

    for mode, command in commands:
        result = explain_command(mode, command)
        print(result)

    audit_event(
        "governance_test",
        {
            "modes": list_modes(),
            "status": "ok",
        }
    )

    print("\nGOVERNANCE TEST OK")


if __name__ == "__main__":
    main()
