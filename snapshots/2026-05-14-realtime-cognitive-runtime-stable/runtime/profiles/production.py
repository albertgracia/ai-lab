PROFILE = {
    "name": "production",

    "description": (
        "Entorno de producción con máxima seguridad."
    ),

    "allow_shell": False,
    "allow_write": False,
    "allow_tools": False,

    "max_command_timeout": 30,

    "blocked_commands": [
        "rm",
        "shutdown",
        "reboot",
        "docker compose down",
        "systemctl restart",
        "mkfs",
    ],

    "audit_level": "paranoid",
}
