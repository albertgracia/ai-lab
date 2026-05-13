# /opt/ai-lab/runtime/modes/registry.py

MODES = {
    "plan": {
        "capabilities": [
            "analyze",
            "plan",
            "rag",
            "read",
            "search",
        ],
    },

    "build": {
        "capabilities": [
            "analyze",
            "plan",
            "rag",
            "read",
            "search",
            "write",
        ],
    },

    "execute": {
        "capabilities": [
            "analyze",
            "plan",
            "rag",
            "read",
            "search",
            "write",
            "shell",
            "tools",
        ],
    },
}


def get_mode(mode_name: str | None = None):

    if mode_name is None:
        mode_name = "plan"

    if mode_name not in MODES:
        raise ValueError(f"Unknown mode: {mode_name}")

    return MODES[mode_name]


def get_capabilities(mode_name: str | None = None):

    mode = get_mode(mode_name)

    return mode["capabilities"]
