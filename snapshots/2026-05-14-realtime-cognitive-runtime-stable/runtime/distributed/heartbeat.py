import time
from datetime import datetime, timezone

from runtime.distributed.health_monitor import (
    NODES,
    check_node,
    load_cluster_state,
    save_cluster_state,
)

from runtime.distributed.node_discovery import (
    run_discovery,
)

from runtime.memory.episodic_memory import write_episode


HEARTBEAT_INTERVAL_SECONDS = 30


def run_heartbeat_once():
    cluster_state = load_cluster_state()

    updated_nodes = []

    for node in NODES:
        result = check_node(node)
        updated_nodes.append(result)

    discovered_nodes = run_discovery()

    cluster_state["nodes"] = updated_nodes
    cluster_state["discovered_nodes"] = discovered_nodes
    cluster_state["updated_at"] = int(time.time())
    cluster_state["updated_at_iso"] = datetime.now(timezone.utc).isoformat()

    online_nodes = [
        node for node in updated_nodes
        if node.get("online")
    ]

    offline_nodes = [
        node for node in updated_nodes
        if not node.get("online")
    ]

    discovered_online = [
        node for node in discovered_nodes
        if node.get("online")
    ]

    if not online_nodes:
        cluster_health = "offline"
    elif offline_nodes:
        cluster_health = "degraded"
    else:
        cluster_health = "healthy"

    cluster_state["cluster_health"] = cluster_health
    cluster_state["online_nodes"] = len(online_nodes)
    cluster_state["offline_nodes"] = len(offline_nodes)
    cluster_state["discovered_online_nodes"] = len(discovered_online)
    cluster_state["discovered_total_nodes"] = len(discovered_nodes)

    save_cluster_state(cluster_state)

    write_episode(
        event_type="cluster_heartbeat",
        summary=(
            f"Cluster heartbeat completed with status "
            f"'{cluster_health}'."
        ),
        payload={
            "cluster_health": cluster_health,
            "online_nodes": len(online_nodes),
            "offline_nodes": len(offline_nodes),
            "discovered_online_nodes": len(discovered_online),
            "discovered_total_nodes": len(discovered_nodes),
            "nodes": updated_nodes,
            "discovered_nodes": discovered_nodes,
        },
    )

    return cluster_state


def run_forever():
    print("AI-LAB HEARTBEAT")
    print("================")
    print(f"Interval: {HEARTBEAT_INTERVAL_SECONDS}s")
    print("Press CTRL+C to stop.")
    print()

    while True:
        state = run_heartbeat_once()

        print(
            f"[{state['updated_at_iso']}] "
            f"health={state['cluster_health']} "
            f"online={state['online_nodes']} "
            f"offline={state['offline_nodes']} "
            f"discovered_online={state['discovered_online_nodes']}/"
            f"{state['discovered_total_nodes']}"
        )

        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
