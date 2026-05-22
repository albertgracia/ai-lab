from __future__ import annotations

import json
from typing import Any


def format_verbose_report(contract: Any) -> str:
    d = contract.to_dict() if hasattr(contract, "to_dict") else contract
    return json.dumps(d, indent=2, ensure_ascii=False)
