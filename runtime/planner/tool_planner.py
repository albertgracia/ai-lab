from runtime.tools.shell_tool import execute


def plan_tools(user_request: str):
    text = user_request.lower()

    commands = []

    if "docker" in text or "container" in text or "contenedor" in text:
        commands.append("docker ps")

    if "traefik" in text:
        commands.append("docker logs traefik --tail 80")
        commands.append("docker inspect traefik")

    if "open-webui" in text or "webui" in text:
        commands.append("docker logs open-webui --tail 80")
        commands.append("docker inspect open-webui")

    if "qdrant" in text:
        commands.append("docker logs qdrant --tail 80")
        commands.append("docker inspect qdrant")

    if "disk" in text or "disco" in text or "storage" in text:
        commands.append("df -h")

    if "memory" in text or "ram" in text or "memoria" in text:
        commands.append("free -h")

    if "git" in text or "repo" in text:
        commands.append("git status")
        commands.append("git log --oneline -5")

    return commands


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
