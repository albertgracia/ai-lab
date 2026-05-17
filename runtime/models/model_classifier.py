"""Heuristic model classification for dynamic discovery."""

from __future__ import annotations

import re
from typing import Any

_EMBEDDING_MARKERS = ("embed", "embedding", "nomic")
_VISION_MARKERS = ("vision", "moondream", "llava", "vqa", "ocr")
_CODING_MARKERS = ("coder", "code", "deepseek-coder")
_REASONING_MARKERS = (
    "reasoning",
    "reason",
    "r1",
    "qwen3",
    "deepseek-r1",
    "claude-sonnet-distill",
)
_FAST_MARKERS = ("llama", "instruct", "7b", "8b", "9b")
_SIZE_RE = re.compile(r"(?<!\d)(1|3|7|8|9|14|16|20|26|32|35|70)b(?!\w)", re.IGNORECASE)


def _normalize(model_id: str) -> str:
    return (model_id or "").strip()


def _family(model_id: str) -> str:
    model = _normalize(model_id).lower()
    for family in ("qwen", "llama", "deepseek", "gemma", "moondream", "nomic", "flux", "claude"):
        if family in model:
            return family
    if "/" in model:
        return model.split("/")[-1].split("-")[0]
    return model.split("-")[0] if model else "unknown"


def _size_b(model_id: str) -> int:
    model = _normalize(model_id).lower()
    match = _SIZE_RE.search(model)
    if match:
        return int(match.group(1))
    if "1b" in model:
        return 1
    if "2b" in model:
        return 2
    if "4b" in model:
        return 4
    return 0


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def classify_model(model_id: str) -> dict[str, Any]:
    normalized = _normalize(model_id)
    model = normalized.lower()
    family = _family(model)
    size_b = _size_b(model)

    embedding = _contains_any(model, _EMBEDDING_MARKERS)
    vision = _contains_any(model, _VISION_MARKERS)
    coding = _contains_any(model, _CODING_MARKERS)
    reasoning = _contains_any(model, _REASONING_MARKERS)
    fast = _contains_any(model, _FAST_MARKERS)

    if embedding:
        model_type = "embedding"
        skills = ["embeddings", "semantic-search", "rag"]
        chat_eligible = False
    elif vision:
        model_type = "vision"
        skills = ["vision", "captioning", "ocr", "vqa"]
        chat_eligible = False
    elif coding and reasoning:
        model_type = "reasoning"
        skills = ["reasoning", "analysis", "architecture", "coding"]
        chat_eligible = True
    elif coding:
        model_type = "coding"
        skills = ["coding", "debugging", "refactor", "testing"]
        chat_eligible = True
    elif reasoning:
        model_type = "reasoning"
        skills = ["reasoning", "analysis", "architecture"]
        chat_eligible = True
    elif fast:
        model_type = "fast"
        skills = ["fast", "general", "chat"]
        chat_eligible = True
    else:
        model_type = "general"
        skills = ["general", "chat"]
        chat_eligible = True

    confidence = 0.45
    if embedding or vision:
        confidence = 0.92
    elif coding and reasoning:
        confidence = 0.88
    elif coding or reasoning:
        confidence = 0.82
    elif fast:
        confidence = 0.74
    if size_b:
        confidence = min(0.98, confidence + 0.04)

    return {
        "id": normalized,
        "family": family,
        "size_b": size_b,
        "type": model_type,
        "skills": skills,
        "chat_eligible": chat_eligible,
        "embedding": embedding,
        "vision": vision,
        "confidence": round(confidence, 2),
        "source": "heuristic",
    }


def is_chat_model(model_id: str) -> bool:
    meta = classify_model(model_id)
    return bool(meta.get("chat_eligible")) and not bool(meta.get("embedding")) and not bool(meta.get("vision"))


def is_embedding_model(model_id: str) -> bool:
    meta = classify_model(model_id)
    return bool(meta.get("embedding"))


def score_unknown_model(task_type: str, model_id: str) -> float:
    meta = classify_model(model_id)
    model_type = meta.get("type", "general")
    size_b = int(meta.get("size_b") or 0)
    confidence = float(meta.get("confidence") or 0.5)

    if task_type == "embeddings":
        type_score = 1.0 if meta.get("embedding") else 0.05
    elif task_type == "vision":
        type_score = 1.0 if meta.get("vision") else 0.05
    elif task_type == "coding":
        type_score = 1.0 if model_type == "coding" else (0.75 if model_type in ("reasoning", "general", "fast") else 0.2)
    elif task_type == "reasoning":
        type_score = 1.0 if model_type == "reasoning" else (0.8 if model_type == "coding" else 0.35)
    else:
        type_score = 1.0 if model_type in ("fast", "general") else (0.65 if model_type in ("coding", "reasoning") else 0.2)

    if size_b <= 0:
        size_score = 0.35
    elif task_type in ("fast", "general"):
        size_score = max(0.2, 1.0 - (min(size_b, 32) / 48.0))
    elif task_type == "coding":
        size_score = min(1.0, 0.35 + (min(size_b, 32) / 40.0))
    elif task_type == "reasoning":
        size_score = min(1.0, 0.4 + (min(size_b, 32) / 36.0))
    else:
        size_score = min(1.0, 0.45 + (min(size_b, 32) / 50.0))

    score = (type_score * 0.55) + (size_score * 0.3) + (confidence * 0.15)
    return round(min(max(score * 100, 0.0), 100.0), 1)
