from runtime.modes.registry import get_mode


DANGEROUS_COMMANDS = [
    "rm -rf",
    "mkfs",
    "shutdown",
    "reboot",
    "poweroff",
    "sudo",
    "chmod 777",
    "dd if=",
    ":(){:|:&};:",
]


def can_execute_shell(mode: str) -> bool:
    cfg = get_mode(mode)
    return "shell" in cfg["capabilities"]


def validate_shell_command(mode: str, command: str):

    if not can_execute_shell(mode):
        raise PermissionError(
            f"Mode '{mode}' does not allow shell execution"
        )

    lower = command.lower()

    for banned in DANGEROUS_COMMANDS:
        if banned in lower:
            raise PermissionError(
                f"Dangerous command blocked: {banned}"
            )

    return True
