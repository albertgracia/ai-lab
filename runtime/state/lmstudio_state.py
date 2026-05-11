import requests


LMSTUDIO_NODES = [
    {
        "name": "Main LM Studio",
        "host": "192.168.1.200",
        "port": 1234
    },
    {
        "name": "Gaming PC RX7900XT",
        "host": "192.168.1.60",
        "port": 1234
    },
    {
        "name": "Gaming PC RX9070XT",
        "host": "192.168.1.50",
        "port": 1234
    }
]


def get_models(node):
    url = f"http://{node['host']}:{node['port']}/v1/models"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()

        return {
            "node": node["name"],
            "host": node["host"],
            "port": node["port"],
            "online": True,
            "models": [
                model["id"]
                for model in data.get("data", [])
            ]
        }

    except Exception as e:
        return {
            "node": node["name"],
            "host": node["host"],
            "port": node["port"],
            "online": False,
            "error": str(e)
        }


def get_lmstudio_state():
    return {
        "lmstudio_nodes": [
            get_models(node)
            for node in LMSTUDIO_NODES
        ]
    }
