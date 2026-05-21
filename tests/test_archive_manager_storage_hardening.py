import json
from pathlib import Path

from runtime.storage.archive_manager import (
    build_archive_manifest,
    classify_snapshot_tier,
    compute_archive_integrity,
    create_archive_layout,
    detect_recursive_backup,
    estimate_backup_size,
    generate_storage_inventory,
    load_backup_excludes,
    validate_backup_targets,
    validate_nas_archive_root,
    write_archive_manifest,
)


def test_load_backup_excludes(tmp_path: Path):
    excludes = tmp_path / ".backup-excludes"
    excludes.write_text("backups/\n# comment\nnode_modules/\n", encoding="utf-8")
    assert load_backup_excludes(str(excludes)) == ["backups/", "node_modules/"]


def test_detect_recursive_backup_in_snapshot(tmp_path: Path):
    root = tmp_path / "snapshot-a"
    nested = root / "docs" / "backups" / "stable-topology"
    nested.mkdir(parents=True)
    assert detect_recursive_backup(str(root), []) is True


def test_detect_recursive_backup_clean_tree(tmp_path: Path):
    root = tmp_path / "snapshot-b"
    (root / "runtime" / "state").mkdir(parents=True)
    assert detect_recursive_backup(str(root), []) is False


def test_estimate_backup_size_respects_excludes(tmp_path: Path):
    root = tmp_path / "candidate"
    (root / "runtime").mkdir(parents=True)
    (root / "node_modules").mkdir(parents=True)
    (root / "runtime" / "a.json").write_text("x" * 100, encoding="utf-8")
    (root / "node_modules" / "skip.js").write_text("y" * 200, encoding="utf-8")
    report = estimate_backup_size([str(root)], ["node_modules/"])
    assert report["size_before_bytes"] >= 300
    assert report["excluded_bytes"] >= 200
    assert any("node_modules" in item for item in report["excluded_matches"])


def test_classify_snapshot_tier():
    assert classify_snapshot_tier("release-stable", 100, 1) == "release"
    assert classify_snapshot_tier("burnin-foo", 100, 1) == "burn-in"
    assert classify_snapshot_tier("recent-small", 100, 1) == "hot"
    assert classify_snapshot_tier("two-weeks", 100, 10) == "warm"
    assert classify_snapshot_tier("old-large", 3 * 1024 * 1024 * 1024, 40) == "cold"


def test_validate_nas_archive_root(tmp_path: Path):
    create_archive_layout(str(tmp_path / "archives"))
    result = validate_nas_archive_root(str(tmp_path / "archives"))
    assert result.valid is True
    assert result.nas_available is True


def test_validate_backup_targets_rejects_local_deprecated(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    excludes = tmp_path / ".backup-excludes"
    excludes.write_text("backups/\n", encoding="utf-8")
    result = validate_backup_targets([str(source)], "/opt/ai-lab/backups/auto-1", str(excludes))
    assert result.valid is False
    assert any("deprecated" in error for error in result.errors)


def test_compute_archive_integrity_partial():
    integrity, confidence = compute_archive_integrity(copy_errors=1, symlink_failures=1)
    assert integrity in ("partial", "low")
    assert 0.0 <= confidence <= 1.0


def test_manifest_roundtrip(tmp_path: Path):
    manifest = build_archive_manifest(
        source_paths=["/tmp/source"],
        excluded_paths=["node_modules/"],
        size_before_bytes=100,
        size_after_bytes=80,
        recursive_detected=False,
        moved_to="/mnt/opencode/ai-lab-archives/backups",
    )
    path = write_archive_manifest(manifest, str(tmp_path / "manifests"))
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert payload["source_paths"] == ["/tmp/source"]
    assert payload["archive_integrity"] in ("high", "partial", "low")


def test_generate_storage_inventory(tmp_path: Path):
    excludes = tmp_path / ".backup-excludes"
    excludes.write_text("backups/\n", encoding="utf-8")
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    (snapshots / "phase-a").mkdir()
    (snapshots / "phase-a" / "data.txt").write_text("hello", encoding="utf-8")
    (snapshots / "phase-b").mkdir()
    (snapshots / "phase-b" / "backups").mkdir()
    inventory = generate_storage_inventory([str(snapshots)], str(excludes))
    assert len(inventory) == 2
    assert any(item.recursive_detected for item in inventory)
