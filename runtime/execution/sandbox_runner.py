import subprocess
import shlex
from datetime import datetime, timezone

from runtime.security.capability_guard import validate_shell_command
from runtime.audit.audit_logger import audit_event


DEFAULT_TIMEOUT = 30


def run_safe_command(
    mode: str,
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
):
    """
    Ejecuta comandos shell bajo governance.
    """

    validate_shell_command(mode, command)

    started = datetime.now(timezone.utc).isoformat()

    audit_event(
        "sandbox_execution_started",
        {
            "mode": mode,
            "command": command,
            "timeout": timeout,
            "started": started,
        },
    )

    try:

        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        payload = {
            "mode": mode,
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:4000],
        }

        audit_event(
            "sandbox_execution_finished",
            payload,
        )

        return payload

    except subprocess.TimeoutExpired:

        payload = {
            "mode": mode,
            "command": command,
            "timeout": timeout,
            "error": "timeout",
        }

        audit_event(
            "sandbox_execution_timeout",
            payload,
        )

        return payload

    except Exception as exc:

        payload = {
            "mode": mode,
            "command": command,
            "error": str(exc),
        }

        audit_event(
            "sandbox_execution_error",
            payload,
        )

        return payload


if __name__ == "__main__":

    result = run_safe_command(
        mode="execute",
        command="docker ps",
    )

    print(result)
