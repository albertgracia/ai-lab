MODEL_CAPABILITIES = {
    "llama-3.1-8b-instruct": {
        "reasoning": 5, "coding": 6, "speed": 10, "memory": 8, "node": "rx9070",
    },
    "qwen2.5-coder-14b-instruct": {
        "reasoning": 7, "coding": 9, "speed": 7, "memory": 6, "node": "rx9070",
    },
    "qwen2.5-coder-32b-instruct": {
        "reasoning": 9, "coding": 10, "speed": 4, "memory": 5, "node": "rx7900xt",
    },
}


def choose_model(task_type="general"):
    if task_type == "coding":
        return "qwen2.5-coder-14b-instruct"
    if task_type == "reasoning":
        return "qwen2.5-coder-32b-instruct"
    if task_type == "fast":
        return "llama-3.1-8b-instruct"
    return "qwen2.5-coder-14b-instruct"
