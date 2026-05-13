from runtime.modes.registry import get_mode


def has_capability(mode_name: str, capability: str) -> bool:
    mode = get_mode(mode_name)
    return capability in mode.ALLOWED_CAPABILITIES


def require_capability(mode_name: str, capability: str):
    if not has_capability(mode_name, capability):
        raise PermissionError(
            f"Capability '{capability}' is not allowed in mode '{mode_name}'"
        )

    return True


def explain_capability(mode_name: str, capability: str):
    allowed = has_capability(mode_name, capability)

    return {
        "mode": mode_name,
        "capability": capability,
        "allowed": allowed,
    }


if __name__ == "__main__":
    tests = [
        ("plan", "write"),
        ("readonly", "logs"),
        ("build", "write"),
        ("build", "deploy"),
        ("execute", "deploy"),
    ]

    for mode, capability in tests:
        print(explain_capability(mode, capability))
