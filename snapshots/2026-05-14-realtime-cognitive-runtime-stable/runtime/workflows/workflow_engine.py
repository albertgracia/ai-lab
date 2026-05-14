from runtime.distributed.execution_coordinator import (
    execute_with_failover,
)

from runtime.memory.episodic_memory import (
    write_episode,
)


# ============================================================
# WORKFLOW BLUEPRINTS
# ============================================================

WORKFLOW_STEPS = [

    {
        "order": 1,
        "title": "Understand user goal and classify intent",
        "mode": "plan",
        "profile": "sandbox",
        "capability_required": "analyze",
        "distributed_task": "reasoning",
    },

    {
        "order": 2,
        "title": "Load semantic context and relevant operational memory",
        "mode": "plan",
        "profile": "sandbox",
        "capability_required": "rag",
        "distributed_task": "memory",
    },

    {
        "order": 3,
        "title": "Generate implementation or operational plan",
        "mode": "plan",
        "profile": "sandbox",
        "capability_required": "plan",
        "distributed_task": "reasoning",
    },

    {
        "order": 4,
        "title": "Prepare code changes in build mode",
        "mode": "build",
        "profile": "sandbox",
        "capability_required": "write",
        "distributed_task": "coding",
    },

    {
        "order": 5,
        "title": "Validate changes with safe tests",
        "mode": "execute",
        "profile": "pilot",
        "capability_required": "shell",
        "distributed_task": "orchestration",
    },
]


# ============================================================
# WORKFLOW
# ============================================================

def build_workflow(goal):

    workflow = {
        "user_goal": goal,
        "intent": "coding",
        "mode": "build",
        "profile": "sandbox",
        "status": "initialized",
        "steps": [],
    }

    for item in WORKFLOW_STEPS:

        workflow["steps"].append({
            **item,
            "status": "pending",
            "result": None,
        })

    return workflow


# ============================================================
# EXECUTION
# ============================================================

def execute_workflow(goal):

    workflow = build_workflow(goal)

    degraded = False

    for step in workflow["steps"]:

        execution = execute_with_failover(
            step["distributed_task"]
        )

        step["execution"] = execution

        if execution["success"]:

            step["status"] = "executed"

            step["result"] = (
                f"Executed on "
                f"{execution['final_node']}"
            )

        else:

            step["status"] = "failed"

            step["result"] = (
                "Execution failed "
                "after retries."
            )

            degraded = True

    if degraded:

        workflow["status"] = (
            "execution_degraded"
        )

    else:

        workflow["status"] = (
            "execution_completed"
        )

    write_episode(
        event_type="workflow_executed",
        summary=(
            f"Workflow executed "
            f"with status "
            f"'{workflow['status']}'."
        ),
        payload=workflow,
    )

    return workflow


# ============================================================
# OUTPUT
# ============================================================

def print_workflow(workflow):

    print()
    print("AI-LAB LIVE DISTRIBUTED WORKFLOW")
    print("================================")

    print(
        "GOAL:",
        workflow["user_goal"]
    )

    print(
        "INTENT:",
        workflow["intent"]
    )

    print(
        "MODE:",
        workflow["mode"]
    )

    print(
        "PROFILE:",
        workflow["profile"]
    )

    print(
        "STATUS:",
        workflow["status"]
    )

    print()

    for step in workflow["steps"]:

        print(
            f"{step['order']}. "
            f"{step['title']}"
        )

        print(
            f"   mode="
            f"{step['mode']}"
        )

        print(
            f"   profile="
            f"{step['profile']}"
        )

        print(
            f"   capability="
            f"{step['capability_required']}"
        )

        print(
            f"   distributed_task="
            f"{step['distributed_task']}"
        )

        print(
            f"   status="
            f"{step['status']}"
        )

        if "execution" in step:

            print(
                f"   execution_success="
                f"{step['execution']['success']}"
            )

            print(
                f"   execution_node="
                f"{step['execution']['final_node']}"
            )

        print(
            f"   result="
            f"{step['result']}"
        )

        print()


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    workflow = execute_workflow(
        "Implementa un workflow seguro "
        "para revisar estado Docker "
        "y documentar resultados"
    )

    print_workflow(workflow)

