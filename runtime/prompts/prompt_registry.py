"""FASE 27.5: Prompt governance — versionado, checksums y validacion.

Centraliza la gestion de prompts para detectar drift y cambios accidentales.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _PROMPTS_DIR / "manifest.json"

FORBIDDEN_PROMPT_MARKERS = [
    "HARD_FACTS",
    "question tool",
    "auto tool",
    "tool_use automatic",
]


def prompt_checksum(name: str) -> str:
    """Devuelve el hash MD5 del contenido de un prompt."""
    path = _PROMPTS_DIR / name
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def prompt_version(name: str) -> str:
    """Alias para checksum — version = hash del contenido."""
    return prompt_checksum(name)[:8]


def validate_prompt(name: str) -> tuple[bool, list[str]]:
    """Valida que un prompt no contenga marcadores prohibidos.

    Returns (is_valid, [markers_found]).
    """
    path = _PROMPTS_DIR / name
    if not path.exists():
        return False, ["file_not_found"]
    text = path.read_text(encoding="utf-8").lower()
    hits = [m for m in FORBIDDEN_PROMPT_MARKERS if m.lower() in text]
    return len(hits) == 0, hits


def get_prompt_versions() -> dict[str, str]:
    """Devuelve versiones de todos los prompts en el directorio."""
    versions = {}
    for f in sorted(_PROMPTS_DIR.glob("*.md")):
        versions[f.name] = prompt_version(f.name)
    return versions
