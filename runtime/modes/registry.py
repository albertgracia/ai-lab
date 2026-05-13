# /opt/ai-lab/runtime/modes/registry.py

MODES = {
    "plan": {
        "name": "plan",
        "description": (
            "Modo planificación: solo análisis, lectura, RAG y generación de plan."
        ),
        "capabilities": [
            "analyze",
            "plan",
            "rag",
            "read",
            "search",
        ],
    },

    "build": {
        "name": "build",
        "description": (
            "Modo construcción: permite preparar cambios y escritura controlada sin shell."
        ),
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
        "name": "execute",
        "description": (
            "Modo ejecución: permite shell y tools bajo governance y perfiles."
        ),
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


def describe_mode(mode_name: str | None = None):

    mode = get_mode(mode_name)

    return {
        "name": mode["name"],
        "description": mode["description"],
        "capabilities": mode["capabilities"],
    }


def list_modes():

    return {
        name: describe_mode(name)
        for name in MODES
    }
