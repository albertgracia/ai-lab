PROFILE = {
    "name": "sandbox",

    "description": (
        "Entorno experimental para pruebas cognitivas y ejecución flexible."
    ),

    "allow_shell": True,
    "allow_write": True,
    "allow_tools": True,

    "max_command_timeout": 300,

    "blocked_commands": [
        "rm -rf /",
    ],

    "audit_level": "full",
}
