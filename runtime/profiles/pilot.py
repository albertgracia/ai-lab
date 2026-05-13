PROFILE = {
    "name": "pilot",

    "description": (
        "Entorno piloto con governance reforzada."
    ),

    "allow_shell": True,
    "allow_write": True,
    "allow_tools": True,

    "max_command_timeout": 120,

    "blocked_commands": [
        "rm -rf",
        "docker compose down",
        "shutdown",
        "reboot",
    ],

    "audit_level": "strict",
}
