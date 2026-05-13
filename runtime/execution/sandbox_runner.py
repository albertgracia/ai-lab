import subprocess
import shlex

from datetime import datetime, timezone

from runtime.security.capability_guard import validate_shell_command
from runtime.audit.audit_logger import audit_event
from runtime.profiles.loader import load_profile


DEFAULT_TIMEOUT = 30


def validate_profile_command(profile: dict, command: str):

    if not profile["allow_shell"]:
        raise PermissionError(
            f"Profile '{profile['name']}' blocks shell execution"
        )

    for blocked in profile["blocked_commands"]:

        if blocked in command:
            raise PermissionError(
                f"Blocked command in profile '{profile['name']}': {blocked}"
            )


def run_safe_command(
    mode: str,
    command: str,
    profile_name: str = "pilot",
    timeout: int = DEFAULT_TIMEOUT,
):
    """
    Governed shell execution with mode + profile validation.
    """

    validate_shell_command(mode, command)

    profile = load_profile(profile_name)

    validate_profile_command(
        profile,
        command,
    )

    timeout = min(
        timeout,
        profile["max_command_timeout"],
    )

    started = datetime.now(timezone.utc).isoformat()

    audit_event(
        "sandbox_execution_started",
        {
            "mode": mode,
            "profile": profile_name,
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
            "profile": profile_name,
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
            "profile": profile_name,
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
            "profile": profile_name,
            "command": command,
            "error": str(exc),
        }

        audit_event(
            "sandbox_execution_error",
            payload,
        )

        return payload


if __name__ == "__main__":

    tests = [
        ("execute", "sandbox", "docker ps"),
        ("execute", "pilot", "docker ps"),
        ("execute", "production", "docker ps"),
    ]

    for mode, profile, cmd in tests:

        print()
        print("====================")
        print("PROFILE:", profile)

        try:
            result = run_safe_command(
                mode=mode,
                profile_name=profile,
                command=cmd,
            )

            print(result)

        except Exception as exc:
            print({
                "mode": mode,
                "profile": profile,
                "command": cmd,
                "blocked": True,
                "reason": str(exc),
            })
