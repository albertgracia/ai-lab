from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any


def new_error_id() -> str:
    return uuid.uuid4().hex[:16]


def stack_hash(tb: str | None) -> str:
    if not tb:
        return ""
    normalized = "".join(
        line.strip() for line in tb.splitlines()
        if not line.strip().startswith("File")
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


DEDUP_KEYS: frozenset[str] = frozenset({
    "category",
    "exception_class",
    "stack_hash",
    "component",
    "origin_stage",
    "model",
})


def dedup_key(event_dict: dict[str, Any]) -> str:
    parts = [str(event_dict.get(k, "")) for k in sorted(DEDUP_KEYS)]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class CorrelationTags:
    session_id: str | None = None
    user_id: str | None = None
    conversation_id: str | None = None
    deployment_id: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        d: dict[str, str] = {}
        if self.session_id:
            d["session_id"] = self.session_id
        if self.user_id:
            d["user_id"] = self.user_id
        if self.conversation_id:
            d["conversation_id"] = self.conversation_id
        if self.deployment_id:
            d["deployment_id"] = self.deployment_id
        d.update(self.extra)
        return d
