from runtime.tools.shell_tool import execute


CORE_CONTAINERS = [
    "traefik",
    "open-webui",
    "qdrant",
    "portainer",
    "ollama",
]


def plan_tools(user_request: str):
    text = user_request.lower()

    commands = []

    if any(word in text for word in ["docker", "container", "contenedor", "service", "servicio"]):
        commands.append("docker ps")

    if any(word in text for word in ["traefik", "routing", "router", "proxy", "reverse proxy", "502", "404", "503"]):
        commands.append("docker ps")
        commands.append("docker logs traefik --tail 120")
        commands.append("docker inspect traefik")

        for container in CORE_CONTAINERS:
            if container != "traefik":
                commands.append(f"docker inspect {container}")

    if "open-webui" in text or "webui" in text:
        commands.append("docker logs open-webui --tail 80")
        commands.append("docker inspect open-webui")

    if "qdrant" in text:
        commands.append("docker logs qdrant --tail 80")
        commands.append("docker inspect qdrant")

    if "portainer" in text:
        commands.append("docker logs portainer --tail 80")
        commands.append("docker inspect portainer")

    if "ollama" in text:
        commands.append("docker logs ollama --tail 80")
        commands.append("docker inspect ollama")

    if any(word in text for word in ["disk", "disco", "storage", "almacenamiento"]):
        commands.append("df -h")

    if any(word in text for word in ["memory", "ram", "memoria"]):
        commands.append("free -h")

    if any(word in text for word in ["git", "repo", "repository"]):
        commands.append("git status")
        commands.append("git log --oneline -5")

    # Remove duplicates while preserving order
    seen = set()
    unique_commands = []

    for command in commands:
        if command not in seen:
            unique_commands.append(command)
            seen.add(command)

    return unique_commands


def execute_plan(user_request: str):
    commands = plan_tools(user_request)

    results = []

    for command in commands:
        result = execute(command)
        results.append(
            {
                "command": command,
                "result": result,
            }
        )

    return results


if __name__ == "__main__":
    request = input("Task> ")
    results = execute_plan(request)

    for item in results:
        print("=" * 80)
        print(f"$ {item['command']}")
        print("-" * 80)
        print(item["result"])
