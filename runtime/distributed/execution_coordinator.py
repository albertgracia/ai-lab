from datetime import datetime

ACTIVE_EXECUTIONS = []


def register_execution(task, model):
    execution = {
        "task": task,
        "model": model,
        "timestamp": datetime.utcnow().isoformat()
    }

    ACTIVE_EXECUTIONS.append(execution)

    return execution


def list_executions():
    return ACTIVE_EXECUTIONS[-50:]
