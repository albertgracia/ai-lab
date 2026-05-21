from __future__ import annotations

import fnmatch
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Any


ARCHIVE_ROOT = "/mnt/opencode/ai-lab-archives"
EXCLUDES_FILE = "/opt/ai-lab/.backup-excludes"
MANIFESTS_DIRNAME = "manifests"
RUNTIME_GENERATION = "STORAGE-HARDENING"
ARCHIVE_DIRS = (
    "backups",
    "snapshots",
    "burnins",
    "experiments",
    "runtime-history",
    MANIFESTS_DIRNAME,
)
RECURSIVE_COMPONENTS = {"backups", "snapshots"}
TEMPORARY_COMPONENTS = {
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    "coverage",
    "tmp",
    "dist",
    "actions-runner",
}

ArchiveTier = Literal["hot", "warm", "cold", "burn-in", "release"]
ArchiveIntegrity = Literal["high", "partial", "low"]
ArchiveConfidence = Literal["high", "medium", "low"]


@dataclass
class ArchiveCandidate:
    path: str
    kind: str
    size_bytes: int
    modified_at: float | None = None
    tier: ArchiveTier | None = None
    recursive_detected: bool = False
    contains_symlinks: bool = False
    excluded_hits: list[str] = field(default_factory=list)


@dataclass
class ArchiveValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    nas_available: bool = False
    confidence: ArchiveConfidence = "low"


@dataclass
class ArchiveManifest:
    archive_id: str
    created_at: str
    source_paths: list[str]
    excluded_paths: list[str]
    size_before_bytes: int
    size_after_bytes: int
    recursive_detected: bool
    moved_to: str
    runtime_generation: str
    archive_integrity: ArchiveIntegrity
    copy_errors: int
    symlink_failures: int
    confidence: float


def load_backup_excludes(excludes_file: str = EXCLUDES_FILE) -> list[str]:
    path = Path(excludes_file)
    if not path.exists():
        raise FileNotFoundError(f"backup excludes file missing: {excludes_file}")
    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def create_archive_layout(archive_root: str = ARCHIVE_ROOT) -> list[str]:
    root = Path(archive_root)
    root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for dirname in ARCHIVE_DIRS:
        target = root / dirname
        target.mkdir(parents=True, exist_ok=True)
        created.append(str(target))
    return created


def is_archive_path(path: str, archive_root: str = ARCHIVE_ROOT) -> bool:
    try:
        resolved = Path(path).resolve()
        root = Path(archive_root).resolve()
        return resolved == root or root in resolved.parents
    except Exception:
        return False


def _relative_parts(root: Path, candidate: Path) -> tuple[str, ...]:
    try:
        rel = candidate.relative_to(root)
    except ValueError:
        return tuple()
    return tuple(part for part in rel.parts if part not in (".", ""))


def _is_excluded(rel_path: str, name: str, patterns: list[str]) -> bool:
    norm_rel = rel_path.replace("\\", "/")
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if pattern.endswith("/"):
            if norm_rel == normalized or norm_rel.startswith(normalized + "/"):
                return True
            if name == normalized:
                return True
        elif fnmatch.fnmatch(name, normalized) or fnmatch.fnmatch(norm_rel, normalized):
            return True
    return False


def detect_symlink_issues(path: str) -> dict[str, Any]:
    root = Path(path)
    issues = {
        "contains_symlinks": False,
        "symlink_failures": 0,
        "broken_symlinks": [],
        "escaping_symlinks": [],
    }
    if not root.exists():
        return issues
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in list(dirnames) + list(filenames):
            candidate = current / name
            if not candidate.is_symlink():
                continue
            issues["contains_symlinks"] = True
            try:
                resolved = candidate.resolve(strict=True)
                if root.resolve() not in resolved.parents and resolved != root.resolve():
                    issues["escaping_symlinks"].append(str(candidate))
            except FileNotFoundError:
                issues["symlink_failures"] += 1
                issues["broken_symlinks"].append(str(candidate))
    return issues


def scan_snapshot_recursion(path: str, excludes: list[str] | None = None) -> dict[str, Any]:
    root = Path(path)
    patterns = excludes or []
    nested_backup_paths: list[str] = []
    nested_snapshot_paths: list[str] = []
    excluded_hits: list[str] = []
    max_depth = 0
    if not root.exists():
        return {
            "recursive_detected": False,
            "paths": [],
            "nested_backup_paths": [],
            "nested_snapshot_paths": [],
            "excluded_hits": [],
            "symlink_failures": 0,
            "contains_symlinks": False,
            "max_depth": 0,
        }
    symlink_report = detect_symlink_issues(str(root))
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        rel_parts = _relative_parts(root, current)
        for dirname in dirnames:
            rel_dir = _relative_parts(root, current / dirname)
            if rel_dir and dirname == "backups":
                nested_backup_paths.append(str(current / dirname))
            if len(rel_dir) > 1 and dirname == "snapshots":
                nested_snapshot_paths.append(str(current / dirname))
        if rel_parts:
            rel_path = "/".join(rel_parts)
            max_depth = max(max_depth, len(rel_parts))
            if "backups" in rel_parts:
                nested_backup_paths.append(str(current))
            if len(rel_parts) > 1 and "snapshots" in rel_parts:
                nested_snapshot_paths.append(str(current))
            if _is_excluded(rel_path, current.name, patterns):
                excluded_hits.append(rel_path)
        dirnames[:] = [
            d for d in dirnames
            if not _is_excluded(
                "/".join(_relative_parts(root, current / d)),
                d,
                patterns,
            )
        ]
        for filename in filenames:
            rel_file = "/".join(_relative_parts(root, current / filename))
            if rel_file and _is_excluded(rel_file, filename, patterns):
                excluded_hits.append(rel_file)
    recursive_detected = bool(nested_backup_paths or nested_snapshot_paths)
    return {
        "recursive_detected": recursive_detected,
        "paths": nested_backup_paths + nested_snapshot_paths,
        "nested_backup_paths": nested_backup_paths,
        "nested_snapshot_paths": nested_snapshot_paths,
        "excluded_hits": sorted(set(excluded_hits)),
        "symlink_failures": symlink_report["symlink_failures"],
        "contains_symlinks": symlink_report["contains_symlinks"],
        "max_depth": max_depth,
    }


def detect_recursive_backup(path: str, excludes: list[str] | None = None) -> bool:
    return bool(scan_snapshot_recursion(path, excludes).get("recursive_detected"))


def estimate_backup_size(paths: list[str], excludes: list[str]) -> dict[str, Any]:
    size_before = 0
    excluded_bytes = 0
    files_count = 0
    excluded_matches: list[str] = []
    for raw_path in paths:
        root = Path(raw_path)
        if not root.exists():
            continue
        if root.is_file():
            size_before += root.stat().st_size
            files_count += 1
            continue
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
            current = Path(dirpath)
            kept_dirnames: list[str] = []
            for dirname in dirnames:
                rel_dir = "/".join(_relative_parts(root, current / dirname))
                if _is_excluded(rel_dir, dirname, excludes):
                    dir_size = _dir_size(current / dirname)
                    size_before += dir_size
                    excluded_bytes += dir_size
                    excluded_matches.append(rel_dir)
                else:
                    kept_dirnames.append(dirname)
            dirnames[:] = kept_dirnames
            for filename in filenames:
                candidate = current / filename
                rel = "/".join(_relative_parts(root, candidate))
                try:
                    file_size = candidate.stat().st_size
                except OSError:
                    continue
                size_before += file_size
                files_count += 1
                if rel and _is_excluded(rel, filename, excludes):
                    excluded_bytes += file_size
                    excluded_matches.append(rel)
    return {
        "size_before_bytes": size_before,
        "excluded_bytes": excluded_bytes,
        "estimated_archive_bytes": max(0, size_before - excluded_bytes),
        "files_count": files_count,
        "excluded_matches": sorted(set(excluded_matches)),
    }


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for dirpath, _, filenames in os.walk(path, followlinks=False):
        current = Path(dirpath)
        for filename in filenames:
            try:
                total += (current / filename).stat().st_size
            except OSError:
                continue
    return total


def classify_snapshot_tier(path: str, size_bytes: int, age_days: int, tags: list[str] | None = None) -> ArchiveTier:
    joined = f"{path} {' '.join(tags or [])}".lower()
    if "release" in joined or "stable" in joined:
        return "release"
    if "burnin" in joined or "burn-in" in joined:
        return "burn-in"
    if age_days <= 3 and size_bytes < 250 * 1024 * 1024:
        return "hot"
    if age_days <= 14 and size_bytes < 2 * 1024 * 1024 * 1024:
        return "warm"
    return "cold"


def validate_nas_archive_root(archive_root: str = ARCHIVE_ROOT) -> ArchiveValidationResult:
    root = Path(archive_root)
    errors: list[str] = []
    warnings: list[str] = []
    nas_available = False
    if not root.exists():
        errors.append(f"archive root missing: {archive_root}")
    elif not root.is_dir():
        errors.append(f"archive root is not a directory: {archive_root}")
    else:
        nas_available = True
        if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            errors.append(f"archive root not writable: {archive_root}")
            nas_available = False
        try:
            os.statvfs(root)
        except OSError as exc:
            errors.append(f"archive root stat failed: {exc}")
            nas_available = False
    confidence: ArchiveConfidence = "high" if nas_available and not errors else "low"
    if nas_available and not (root / MANIFESTS_DIRNAME).exists():
        warnings.append("archive manifests directory missing")
        confidence = "medium"
    return ArchiveValidationResult(
        valid=nas_available and not errors,
        errors=errors,
        warnings=warnings,
        nas_available=nas_available,
        confidence=confidence,
    )


def validate_backup_targets(source_paths: list[str], dest_path: str, excludes_file: str = EXCLUDES_FILE) -> ArchiveValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        excludes = load_backup_excludes(excludes_file)
    except FileNotFoundError as exc:
        return ArchiveValidationResult(valid=False, errors=[str(exc)], nas_available=False, confidence="low")
    nas_result = validate_nas_archive_root()
    errors.extend(nas_result.errors)
    warnings.extend(nas_result.warnings)
    if dest_path.startswith("/opt/ai-lab/backups"):
        errors.append("/opt/ai-lab/backups is deprecated as archive destination")
    if not is_archive_path(dest_path):
        errors.append(f"destination is outside archive root: {dest_path}")
    try:
        dest_resolved = Path(dest_path).resolve()
    except FileNotFoundError:
        dest_resolved = Path(dest_path).parent.resolve() / Path(dest_path).name
    for source in source_paths:
        src = Path(source)
        if not src.exists():
            errors.append(f"source path missing: {source}")
            continue
        src_resolved = src.resolve()
        if is_archive_path(str(src_resolved)):
            errors.append(f"source already inside archive root: {source}")
        if dest_resolved == src_resolved or src_resolved in dest_resolved.parents:
            errors.append(f"destination nests source path: {source} -> {dest_path}")
        if detect_recursive_backup(str(src), excludes):
            errors.append(f"recursive backup detected in source: {source}")
        symlink_report = detect_symlink_issues(str(src))
        if symlink_report["symlink_failures"]:
            warnings.append(f"broken symlinks detected in source: {source}")
    confidence: ArchiveConfidence = "high"
    if warnings and not errors:
        confidence = "medium"
    if errors:
        confidence = "low"
    return ArchiveValidationResult(
        valid=not errors and nas_result.nas_available,
        errors=errors,
        warnings=warnings,
        nas_available=nas_result.nas_available,
        confidence=confidence,
    )


def compute_archive_integrity(
    *,
    copy_errors: int = 0,
    symlink_failures: int = 0,
    recursive_detected: bool = False,
    missing_files: int = 0,
) -> tuple[ArchiveIntegrity, float]:
    score = 1.0
    score -= min(copy_errors * 0.2, 0.6)
    score -= min(symlink_failures * 0.05, 0.2)
    score -= min(missing_files * 0.1, 0.3)
    if recursive_detected:
        score -= 0.5
    score = max(0.0, round(score, 2))
    if score >= 0.95:
        integrity: ArchiveIntegrity = "high"
    elif score >= 0.7:
        integrity = "partial"
    else:
        integrity = "low"
    return integrity, score


def build_archive_manifest(
    *,
    source_paths: list[str],
    excluded_paths: list[str],
    size_before_bytes: int,
    size_after_bytes: int,
    recursive_detected: bool,
    moved_to: str,
    runtime_generation: str = RUNTIME_GENERATION,
    copy_errors: int = 0,
    symlink_failures: int = 0,
    archive_id: str | None = None,
) -> ArchiveManifest:
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if archive_id is None:
        archive_id = f"archive-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}"
    integrity, confidence = compute_archive_integrity(
        copy_errors=copy_errors,
        symlink_failures=symlink_failures,
        recursive_detected=recursive_detected,
    )
    return ArchiveManifest(
        archive_id=archive_id,
        created_at=created_at,
        source_paths=source_paths,
        excluded_paths=excluded_paths,
        size_before_bytes=size_before_bytes,
        size_after_bytes=size_after_bytes,
        recursive_detected=recursive_detected,
        moved_to=moved_to,
        runtime_generation=runtime_generation,
        archive_integrity=integrity,
        copy_errors=copy_errors,
        symlink_failures=symlink_failures,
        confidence=confidence,
    )


def write_archive_manifest(manifest: ArchiveManifest, manifests_root: str | None = None) -> str:
    root = Path(manifests_root or (Path(ARCHIVE_ROOT) / MANIFESTS_DIRNAME))
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{manifest.archive_id}.json"
    target.write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def generate_storage_inventory(roots: list[str], excludes_file: str = EXCLUDES_FILE) -> list[ArchiveCandidate]:
    excludes = load_backup_excludes(excludes_file)
    now = time.time()
    inventory: list[ArchiveCandidate] = []
    for raw_root in roots:
        path = Path(raw_root)
        if not path.exists():
            continue
        for child in sorted(path.iterdir()):
            try:
                size_report = estimate_backup_size([str(child)], excludes)
                recursive_report = scan_snapshot_recursion(str(child), excludes)
                stat = child.stat()
                age_days = int((now - stat.st_mtime) / 86400)
                candidate = ArchiveCandidate(
                    path=str(child),
                    kind="directory" if child.is_dir() else "file",
                    size_bytes=size_report["estimated_archive_bytes"],
                    modified_at=stat.st_mtime,
                    tier=classify_snapshot_tier(str(child), size_report["estimated_archive_bytes"], age_days),
                    recursive_detected=recursive_report["recursive_detected"],
                    contains_symlinks=recursive_report["contains_symlinks"],
                    excluded_hits=recursive_report["excluded_hits"],
                )
                inventory.append(candidate)
            except OSError:
                continue
    return inventory


def move_to_archive(
    source_paths: list[str],
    archive_root: str = ARCHIVE_ROOT,
    category: str = "backups",
    dry_run: bool = True,
) -> dict[str, Any]:
    excludes = load_backup_excludes()
    destination_root = Path(archive_root) / category
    validation = validate_backup_targets(source_paths, str(destination_root))
    if not validation.valid:
        return {
            "ok": False,
            "validation": asdict(validation),
        }
    destination_root.mkdir(parents=True, exist_ok=True)
    size_report = estimate_backup_size(source_paths, excludes)
    moved: list[str] = []
    copy_errors = 0
    symlink_failures = 0
    for source in source_paths:
        symlink_failures += detect_symlink_issues(source)["symlink_failures"]
    if not dry_run:
        for source in source_paths:
            src = Path(source)
            target = destination_root / src.name
            try:
                shutil.move(str(src), str(target))
                moved.append(str(target))
            except shutil.Error:
                copy_errors += 1
    manifest = build_archive_manifest(
        source_paths=source_paths,
        excluded_paths=size_report["excluded_matches"],
        size_before_bytes=size_report["size_before_bytes"],
        size_after_bytes=size_report["estimated_archive_bytes"],
        recursive_detected=any(detect_recursive_backup(p, excludes) for p in source_paths),
        moved_to=str(destination_root),
        copy_errors=copy_errors,
        symlink_failures=symlink_failures,
    )
    manifest_path = write_archive_manifest(manifest)
    return {
        "ok": copy_errors == 0,
        "dry_run": dry_run,
        "moved": moved,
        "destination": str(destination_root),
        "manifest": manifest_path,
        "validation": asdict(validation),
        "size_report": size_report,
    }


def archive_old_burnins(paths: list[str], dry_run: bool = True) -> dict[str, Any]:
    return move_to_archive(paths, category="burnins", dry_run=dry_run)


def rotate_old_snapshots(paths: list[str], dry_run: bool = True) -> dict[str, Any]:
    return move_to_archive(paths, category="snapshots", dry_run=dry_run)
