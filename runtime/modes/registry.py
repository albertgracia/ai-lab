from runtime.modes import plan, readonly, build, execute

MODES = {
    "plan": plan,
    "readonly": readonly,
    "build": build,
    "execute": execute,
}

DEFAULT_MODE = "readonly"


def get_mode(mode_name: str | None = None):
    name = mode_name or DEFAULT_MODE

    if name not in MODES:
        raise ValueError(f"Unknown mode: {name}")

    return MODES[name]


def list_modes():
    return list(MODES.keys())


def describe_mode(mode_name: str):
    mode = get_mode(mode_name)

    return {
        "name": mode.MODE_NAME,
        "description": mode.DESCRIPTION,
        "capabilities": sorted(mode.ALLOWED_CAPABILITIES),
    }


if __name__ == "__main__":
    for name in list_modes():
        print(describe_mode(name))
