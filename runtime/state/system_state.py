import json
from pathlib import Path

from runtime.state.docker_state import get_docker_state
from runtime.state.lmstudio_state import get_lmstudio_state


STATE_PATH = Path("/opt/ai-lab/runtime/state/system_snapshot.json")


def build_system_state():
    state = {
        "docker": get_docker_state(),
        "llm": get_lmstudio_state()
    }

    STATE_PATH.write_text(
        json.dumps(state, indent=2)
    )

    return state


if __name__ == "__main__":
    state = build_system_state()

    print(json.dumps(state, indent=2))