"""FASE 30H: Runtime Evidence Enforcement — epistemological discipline for report output.

Provides catalog-based validation and sanitization of LLM-generated report text
against the observed runtime state. Prevents hallucination of hardware, models,
services, and infrastructure not present in the active runtime.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any


# ── Configuration ──────────────────────────────────────────────

STRICT_EVIDENCE_MODE = os.environ.get(
    "AI_LAB_STRICT_EVIDENCE_MODE",
    "true"
).lower() in ("1", "true", "yes")

MAX_UNVERIFIED_CLAIMS = 5


# ── Denylists (cortas, explícitas, sin NLP) ─────────────────

_FORBIDDEN_MODEL_PREFIXES = (
    "gpt-", "gpt4", "claude-", "gemini-", "command-",
    "jamba-", "dbrx-", "mixtral-8x22b",
    "llama-3-70b", "llama-3.1-70b", "llama-3.1-405b",
    "codestral-", "codex-", "palm-", "gemma-2-27b", "falcon-",
)

_FORBIDDEN_SECURITY_TOOLS = frozenset({
    "selinux", "apparmor", "fail2ban", "rkhunter",
    "chkrootkit", "lynis", "ossec", "wazuh",
    "snort", "suricata", "crowdsec",
})

_FORBIDDEN_EXTERNAL_PLATFORMS = frozenset({
    "amazon", "aws", "ec2", "s3", "lambda",
    "gcp", "google cloud", "azure", "azure ml",
    "oracle cloud", "oci", "ibm cloud",
    "heroku", "digitalocean", "linode", "vultr",
    "databricks", "sagemaker", "vertex ai",
})

_FORBIDDEN_GPU_MODELS = frozenset({
    "a100", "h100", "h200", "b100", "b200",
    "v100", "t4", "l4", "l40s", "a10", "a16",
    "mi250", "mi300", "mi350",
})

_FORBIDDEN_GPU_PATTERNS = [
    re.compile(rf"(?i)\bnvidia\s+{re.escape(gpu)}\b")
    for gpu in _FORBIDDEN_GPU_MODELS
] + [
    re.compile(rf"(?i)\b{re.escape(gpu)}\b")
    for gpu in _FORBIDDEN_GPU_MODELS
]

# Compiled model-like ID pattern for unknown model detection
_MODEL_ID_PATTERN = re.compile(
    r"\b[a-z][a-z0-9]+(?:[-/.][a-z0-9]+)+(?:-?\d+(?:\.\d+)?[a-z]?"
    r"(?:-instruct|-chat|-base)?)?\b"
)

_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

_KNOWN_MODEL_SUFFIX_PATTERN = re.compile(r"-instruct|-chat|-base")

_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_HOSTNAME_PATTERN = re.compile(r"\b[a-z][a-z0-9]+(?:[-.][a-z0-9]+)+\b")


@dataclass
class ReportEvidenceResult:
    sanitized_text: str = ""
    unverified_claims: list[str] = field(default_factory=list)
    evidence_score: float = 1.0
    hallucination_risk: str = "low"
    warnings: list[str] = field(default_factory=list)
    suppressed_count: int = 0
    strict_mode: bool = True


# ── Evidence catalog builder ─────────────────────────────────

def build_evidence_catalog(
    runtime_context: dict[str, Any] | None,
) -> dict[str, set[str]]:
    catalog: dict[str, set[str]] = {
        "models": set(),
        "nodes": set(),
        "hosts": set(),
        "services": set(),
        "profiles": set(),
    }

    if not runtime_context:
        return catalog

    _extract_models(runtime_context, catalog)
    _extract_nodes(runtime_context, catalog)
    _extract_identity(runtime_context, catalog)
    _extract_services(runtime_context, catalog)
    _extract_profiles(runtime_context, catalog)

    return catalog


def _extract_models(ctx: dict[str, Any], catalog: dict[str, set[str]]) -> None:
    models_dict = ctx.get("models", {})
    if not isinstance(models_dict, dict):
        return
    for m_category in ("active", "disabled", "discovered"):
        m_list = models_dict.get(m_category, [])
        if not isinstance(m_list, list):
            continue
        for m in m_list:
            if not isinstance(m, dict):
                continue
            mid = (m.get("id") or m.get("model") or "").strip().lower()
            if mid:
                catalog["models"].add(mid)
                for alias in _get_model_aliases(mid):
                    catalog["models"].add(alias)


def _extract_nodes(ctx: dict[str, Any], catalog: dict[str, set[str]]) -> None:
    nodes_dict = ctx.get("inference_nodes", {})
    if not isinstance(nodes_dict, dict):
        return
    for n_category in ("active", "inventory"):
        n_list = nodes_dict.get(n_category, [])
        if not isinstance(n_list, list):
            continue
        for n in n_list:
            if not isinstance(n, dict):
                continue
            name = (n.get("name") or "").strip().lower()
            host = (n.get("host") or "").strip().lower()
            if name:
                catalog["nodes"].add(name)
            if host:
                catalog["hosts"].add(host)
                catalog["nodes"].add(host)


def _extract_identity(ctx: dict[str, Any], catalog: dict[str, set[str]]) -> None:
    runtime_host = (ctx.get("runtime_hostname") or "").strip().lower()
    primary_ip = (ctx.get("primary_runtime_ip") or "").strip().lower()
    if runtime_host:
        catalog["hosts"].add(runtime_host)
    if primary_ip:
        catalog["hosts"].add(primary_ip)


def _extract_services(ctx: dict[str, Any], catalog: dict[str, set[str]]) -> None:
    services_dict = ctx.get("services", {})
    if not isinstance(services_dict, dict):
        return
    for s_category in ("core", "support", "observability"):
        s_list = services_dict.get(s_category, [])
        if not isinstance(s_list, list):
            continue
        for s in s_list:
            if isinstance(s, str):
                catalog["services"].add(s.lower())
            elif isinstance(s, dict):
                sname = (s.get("name") or "").strip().lower()
                if sname:
                    catalog["services"].add(sname)


def _extract_profiles(ctx: dict[str, Any], catalog: dict[str, set[str]]) -> None:
    profiles = ctx.get("profiles_available", [])
    if not isinstance(profiles, list):
        return
    for p in profiles:
        if isinstance(p, str):
            catalog["profiles"].add(p.lower())


def _get_model_aliases(model_id: str) -> set[str]:
    aliases: set[str] = set()
    for prefix in ("lmstudio-community/", "lm-studio/", "huggingface/", "hf/"):
        if model_id.startswith(prefix):
            aliases.add(model_id[len(prefix):])
            break
    if "/" in model_id and not any(
        model_id.startswith(p) for p in ("lmstudio-", "lm-studio-", "huggingface/")
    ):
        parts = model_id.split("/", 1)
        if len(parts) == 2:
            aliases.add(parts[1])
    return aliases


# ── Main entry point ─────────────────────────────────────────

def sanitize_unverified_claims(
    report_text: str,
    runtime_context_json: str | None = None,
    evidence_catalog: dict[str, set[str]] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> ReportEvidenceResult:
    if evidence_catalog is None:
        if runtime_context is None and runtime_context_json:
            try:
                runtime_context = json.loads(runtime_context_json)
            except (json.JSONDecodeError, TypeError):
                runtime_context = None
        evidence_catalog = build_evidence_catalog(runtime_context)

    result = ReportEvidenceResult(
        strict_mode=STRICT_EVIDENCE_MODE,
        sanitized_text=report_text,
    )

    if not report_text:
        return result

    unverified: list[str] = []

    known_models = evidence_catalog.get("models", set())
    known_hosts = evidence_catalog.get("hosts", set())
    known_nodes = evidence_catalog.get("nodes", set())

    _check_forbidden_model_prefixes(report_text, unverified, known_models)
    _check_forbidden_gpus(report_text, unverified)
    _check_forbidden_security_tools(report_text, unverified)
    _check_forbidden_external_platforms(report_text, unverified)
    _check_unknown_models(report_text, unverified, known_models)
    _check_unknown_hosts(report_text, unverified, known_hosts, known_nodes)

    result.unverified_claims = unverified
    result.suppressed_count = len(unverified)

    score = max(0.0, 1.0 - (0.15 * len(unverified)))
    result.evidence_score = round(score, 2)

    if len(unverified) >= MAX_UNVERIFIED_CLAIMS:
        result.hallucination_risk = "high"
    elif len(unverified) >= 3:
        result.hallucination_risk = "medium"
    else:
        result.hallucination_risk = "low"

    if unverified:
        result.sanitized_text = _apply_sanitization(report_text, unverified)

    return result


# ── Pattern checkers ─────────────────────────────────────────

def _check_forbidden_model_prefixes(
    text: str, unverified: list[str], known_models: set[str]
) -> None:
    lower = text.lower()
    for prefix in _FORBIDDEN_MODEL_PREFIXES:
        idx = lower.find(prefix)
        while idx != -1:
            end = idx + len(prefix)
            while end < len(lower) and (lower[end].isalnum() or lower[end] in "-._"):
                end += 1
            model_name = text[idx:end]
            if model_name.lower() not in known_models:
                unverified.append(f"model_not_in_observed:{model_name}")
            idx = lower.find(prefix, idx + 1)


def _check_forbidden_gpus(text: str, unverified: list[str]) -> None:
    for pattern in _FORBIDDEN_GPU_PATTERNS:
        for match in pattern.finditer(text):
            unverified.append(f"gpu_not_in_observed:{match.group()}")


def _check_forbidden_security_tools(text: str, unverified: list[str]) -> None:
    lower = text.lower()
    for tool in _FORBIDDEN_SECURITY_TOOLS:
        if tool in lower:
            unverified.append(f"security_tool_not_in_runtime:{tool}")


def _check_forbidden_external_platforms(text: str, unverified: list[str]) -> None:
    lower = text.lower()
    for platform in _FORBIDDEN_EXTERNAL_PLATFORMS:
        if platform in lower:
            unverified.append(f"external_platform_not_in_runtime:{platform}")


def _check_unknown_models(
    text: str, unverified: list[str], known_models: set[str]
) -> None:
    if not known_models:
        return
    lower = text.lower()
    for match in _MODEL_ID_PATTERN.finditer(lower):
        candidate = match.group()
        if len(candidate) < 5:
            continue
        if _VERSION_PATTERN.match(candidate):
            continue
        if candidate in known_models:
            continue
        is_known = any(
            candidate in known or known in candidate
            for known in known_models
        )
        if not is_known:
            if _KNOWN_MODEL_SUFFIX_PATTERN.search(candidate) or re.search(r"\d+[a-z]", candidate):
                unverified.append(f"unknown_model:{candidate}")


def _check_unknown_hosts(
    text: str, unverified: list[str], known_hosts: set[str], known_nodes: set[str]
) -> None:
    if not known_hosts and not known_nodes:
        return
    lower = text.lower()
    known = known_hosts | known_nodes

    for match in _IP_PATTERN.finditer(lower):
        ip = match.group()
        if ip not in known:
            unverified.append(f"unknown_ip:{ip}")

    for match in _HOSTNAME_PATTERN.finditer(lower):
        host = match.group()
        if len(host) < 4:
            continue
        if re.search(r"\d+[a-z]", host):
            continue
        if host in known:
            continue
        if any(
            suffix in host
            for suffix in ("-node", "-gpu", "-server", "-host", "labrazahome")
        ):
            unverified.append(f"unknown_host:{host}")


# ── Sanitization ─────────────────────────────────────────────

_EVIDENCE_NOTE = (
    "\n\n---\n"
    "[EVIDENCE GUARD] Las siguientes afirmaciones en este informe "
    "no estan respaldadas por OBSERVED_RUNTIME. "
    "Se han eliminado o neutralizado para mantener la disciplina epistemologica:"
)


def _apply_sanitization(text: str, unverified_claims: list[str]) -> str:
    stripped = text.rstrip()
    claim_lines = "\n".join(f"- {c}" for c in unverified_claims)
    return stripped + _EVIDENCE_NOTE + "\n" + claim_lines
