import subprocess
import shlex

from datetime import datetime, timezone

from runtime.security.capability_guard import validate_shell_command
from runtime.audit.audit_logger import audit_event
from runtime.profiles.loader import load_profile
from runtime.memory.episodic_memory import write_episode
from runtime.execution.execute_v1_policy import is_allowed as v1_is_allowed


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
    validate_shell_command(mode, command)

    allowed, reason = v1_is_allowed(command)
    if not allowed:
        raise PermissionError(f"EXECUTE v1 policy blocked: {reason}")

    profile = load_profile(profile_name)

    try:
        validate_profile_command(profile, command)
    except Exception as exc:
        write_episode(
            event_type="sandbox_execution_blocked",
            summary=(
                f"Blocked command '{command}' in profile '{profile_name}'."
            ),
            payload={
                "mode": mode,
                "profile": profile_name,
                "command": command,
                "reason": str(exc),
            },
        )
        raise

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

    write_episode(
        event_type="sandbox_execution_started",
        summary=(
            f"Started sandbox command '{command}' "
            f"in mode '{mode}' profile '{profile_name}'."
        ),
        payload={
            "mode": mode,
            "profile": profile_name,
            "command": command,
            "timeout": timeout,
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

        write_episode(
            event_type="sandbox_execution_finished",
            summary=(
                f"Finished sandbox command '{command}' "
                f"with return code {result.returncode}."
            ),
            payload=payload,
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

        write_episode(
            event_type="sandbox_execution_timeout",
            summary=f"Sandbox command timed out: {command}",
            payload=payload,
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

        write_episode(
            event_type="sandbox_execution_error",
            summary=f"Sandbox command failed: {command}",
            payload=payload,
        )

        return payload


if __name__ == "__main__":
    tests = [
        ("execute", "pilot", "ls /tmp"),
        ("execute", "pilot", "docker ps"),
        ("execute", "pilot", "cat /etc/shadow"),
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
