MODEL_CAPABILITIES = {
    "deepseek-r1-distill-qwen-14b": {
        "reasoning": 8,
        "coding": 9,
        "speed": 5,
        "memory": 6,
        "node": "rx9070",
    },
    "qwen2.5-coder-32b-instruct": {
        "reasoning": 9,
        "coding": 10,
        "speed": 4,
        "memory": 5,
        "node": "rx7900xt",
    },
}


def choose_model(task_type="general"):
    if task_type == "coding":
        return "deepseek-r1-distill-qwen-14b"
    if task_type == "reasoning":
        return "qwen2.5-coder-32b-instruct"
    if task_type == "fast":
        return "deepseek-r1-distill-qwen-14b"
    return "deepseek-r1-distill-qwen-14b"
