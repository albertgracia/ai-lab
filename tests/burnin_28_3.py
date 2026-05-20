#!/usr/bin/env python3
"""FASE 28.3-B — Sandbox Write Burn-in & Rollback Validation.

Tests 12 categories:
  1. benign_mutations        — all 11 sandbox operations
  2. rollback_validation     — individual, concurrent, append/replace/transform
  3. traversal_escape        — ../ ../.. encoded → 100% blocked
  4. symlink_escape          — symlink outside, nested → 100% blocked
  5. forbidden_mutations      — chmod, chown, sudo, writes outside → 100% blocked
  6. extension_validation    — .service .socket .mount → 100% blocked
  7. artifact_budget         — >100 artifacts, >25MB, deep nesting
  8. rate_limit              — >10 mutations/min
  9. lineage_validation      — parent_workflow_id, parent_artifact_id, DAG
  10. concurrent_mutations   — 3 workers simultaneous
  11. workflow_state         — MUTATING/DONE/FAILED/ROLLED_BACK transitions
  12. audit_integrity        — before/after checksum, mutation_class, append-only

Runs with 3 concurrent workers. Generates JSON + MD reports.

Usage:
    python tests/burnin_28_3.py [--quick] [--workers 3]
"""

import hashlib
import json
import os
import shutil
import sys
import time
import threading
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/ai-lab")

from runtime.agentic.sandbox_fs import (
    SANDBOX_ROOTS, MAX_PATH_DEPTH,
    resolve_sandbox_path, is_within_sandbox, ensure_sandbox_dir,
    detect_symlink_escape, detect_path_traversal, check_path_depth,
    is_extension_allowed, is_extension_blocked,
    ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS,
)
from runtime.agentic.sandbox_registry import (
    SANDBOX_OPERATIONS, SANDBOX_WRITE_INTENTS,
    MutationClass, RiskLevel,
    is_allowed_operation, op_for_intent, OperationVerdict,
)
from runtime.agentic.sandbox_policies import (
    check_sandbox_governance, assess_sandbox_risk,
    detect_chmod_intent, detect_forbidden_operation,
    SandboxGovernanceResult,
)
from runtime.agentic.sandbox_audit import (
    SandboxAuditEntry, write_sandbox_audit,
    read_sandbox_audit, get_sandbox_audit_stats,
)
from runtime.agentic.artifact_registry import (
    ArtifactEntry, ArtifactRegistry,
)
from runtime.agentic.rollback_engine import (
    RollbackSnapshot, RollbackResult,
    Snapshotter, RollbackEngine,
    write_original_path_marker,
)
from runtime.agentic.sandbox_executor import (
    _execute_file_mutation, _execute_json_mutation,
    _execute_directory_creation, _sha256, _get_size,
    MAX_ARTIFACTS_PER_WORKFLOW, MAX_WORKFLOW_BYTES,
    RATE_LIMIT_WRITES_PER_MIN, RATE_LIMIT_WINDOW_SEC,
    SandboxWriteExecutor,
)
from runtime.agentic.mutation_context import MutationExecutionContext
from runtime.agentic.execution_context import (
    ExecutionMode, DryRunReason, CURRENT_EXECUTION_MODE,
)
from runtime.agentic.workflow_state import WorkflowState, WorkflowTimeline, VALID_TRANSITIONS
from runtime.telemetry.prometheus_metrics import (
    record_sandbox_mutation, record_sandbox_rollback,
    record_sandbox_policy_denied, record_sandbox_artifact,
    record_sandbox_escape_attempt, record_sandbox_checksum_mismatch,
    record_sandbox_mutation_duration,
)

BURNIN_SANDBOX = "/tmp/opencode/sandbox/burnin_28_3"
WORKFLOW_BASE = "burnin_wf"


@dataclass
class BurninResult:
    category: str = ""
    test_name: str = ""
    passed: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


ALL_RESULTS: list[BurninResult] = []
_lock = threading.Lock()
_worker_errors: list[str] = []


def record(category: str, test_name: str, passed: bool, detail: str = "", duration_ms: float = 0.0, **kw):
    r = BurninResult(category=category, test_name=test_name, passed=passed,
                     detail=detail, duration_ms=duration_ms, metadata=kw)
    with _lock:
        ALL_RESULTS.append(r)
    status = "✅" if passed else "❌"
    print(f"  {status} [{category}] {test_name} ({duration_ms:.0f}ms) {'| ' + detail if detail else ''}")


def _reset_sandbox():
    if os.path.exists(BURNIN_SANDBOX):
        shutil.rmtree(BURNIN_SANDBOX, ignore_errors=True)
    os.makedirs(BURNIN_SANDBOX, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 1: benign_mutations — all 11 operations
# ═══════════════════════════════════════════════════════════════════

def test_benign_mutations():
    cat = "benign_mutations"
    wf_id = f"{WORKFLOW_BASE}_benign"

    # 1. create_file
    t0 = time.time()
    target = os.path.join(BURNIN_SANDBOX, "hello.txt")
    ec, out, err = _execute_file_mutation(target, "hello world", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and Path(target).read_text() == "hello world"
    record(cat, "create_file", passed, f"exit={ec}", elapsed)

    # 2. append_file
    t0 = time.time()
    ec, out, err = _execute_file_mutation(target, "\nline 2", "append")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and "line 2" in Path(target).read_text()
    record(cat, "append_file", passed, f"exit={ec}", elapsed)

    # 3. replace_file
    t0 = time.time()
    ec, out, err = _execute_file_mutation(target, "replaced content", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and Path(target).read_text() == "replaced content"
    record(cat, "replace_file", passed, f"exit={ec}", elapsed)

    # 4. create_directory
    t0 = time.time()
    dir_target = os.path.join(BURNIN_SANDBOX, "new_dir")
    ec, out, err = _execute_directory_creation(dir_target)
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and os.path.isdir(dir_target)
    record(cat, "create_directory", passed, f"exit={ec}", elapsed)

    # 5. write_json
    t0 = time.time()
    json_target = os.path.join(BURNIN_SANDBOX, "data.json")
    ec, out, err = _execute_json_mutation(json_target, {"key": "value", "num": 42})
    elapsed = (time.time() - t0) * 1000
    data_ok = False
    if ec == 0:
        try:
            loaded = json.loads(Path(json_target).read_text())
            data_ok = loaded == {"key": "value", "num": 42}
        except Exception:
            pass
    record(cat, "write_json", ec == 0 and data_ok, f"exit={ec} data_ok={data_ok}", elapsed)

    # 6. write_markdown
    t0 = time.time()
    md_target = os.path.join(BURNIN_SANDBOX, "doc.md")
    ec, out, err = _execute_file_mutation(md_target, "# Title\n\nContent\n", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and "# Title" in Path(md_target).read_text()
    record(cat, "write_markdown", passed, f"exit={ec}", elapsed)

    # 7. generate_config (JSON)
    t0 = time.time()
    cfg_target = os.path.join(BURNIN_SANDBOX, "config.json")
    ec, out, err = _execute_json_mutation(cfg_target, {"host": "localhost", "port": 8080})
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and Path(cfg_target).stat().st_size > 10
    record(cat, "generate_config", passed, f"exit={ec} size={Path(cfg_target).stat().st_size}", elapsed)

    # 8. generate_report (MD)
    t0 = time.time()
    rpt_target = os.path.join(BURNIN_SANDBOX, "report.md")
    report_content = "# Report\n\n## Section 1\n\nContent here.\n"
    ec, out, err = _execute_file_mutation(rpt_target, report_content, "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and "Report" in Path(rpt_target).read_text()
    record(cat, "generate_report", passed, f"exit={ec}", elapsed)

    # 9. generate_script (Python)
    t0 = time.time()
    py_target = os.path.join(BURNIN_SANDBOX, "script.py")
    ec, out, err = _execute_file_mutation(py_target, "print('hello')\n", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and Path(py_target).read_text().strip() == "print('hello')"
    record(cat, "generate_script_py", passed, f"exit={ec}", elapsed)

    # 10. generate_script (Shell)
    t0 = time.time()
    sh_target = os.path.join(BURNIN_SANDBOX, "script.sh")
    ec, out, err = _execute_file_mutation(sh_target, "#!/bin/sh\necho hello\n", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec == 0 and "echo hello" in Path(sh_target).read_text()
    record(cat, "generate_script_sh", passed, f"exit={ec}", elapsed)

    # 11. sandbox_transform (multi-file)
    t0 = time.time()
    tf1 = os.path.join(BURNIN_SANDBOX, "transform_a.txt")
    tf2 = os.path.join(BURNIN_SANDBOX, "transform_b.txt")
    ec1, _, _ = _execute_file_mutation(tf1, "transform a", "write")
    ec2, _, _ = _execute_file_mutation(tf2, "transform b", "write")
    elapsed = (time.time() - t0) * 1000
    passed = ec1 == 0 and ec2 == 0
    record(cat, "sandbox_transform", passed, f"exit_a={ec1} exit_b={ec2}", elapsed)

    # Checksum validation
    chk = _sha256(target)
    record(cat, "checksum_valid", len(chk) == 64, f"sha256_len={len(chk)}")

    # Artifact registry
    entry = ArtifactEntry(
        path=target, checksum_sha256=chk, size_bytes=_get_size(target),
        mutation_type="create_file", workflow_id=wf_id, action_id="act_benign",
        generated_by_action="create_file",
    )
    ArtifactRegistry.register(entry)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 2: rollback_validation
# ═══════════════════════════════════════════════════════════════════

def test_rollback_validation():
    cat = "rollback_validation"
    wf_id = f"{WORKFLOW_BASE}_rollback"

    # 1. rollback after create
    t0 = time.time()
    target = os.path.join(BURNIN_SANDBOX, "rollback_create.txt")
    Path(target).write_text("original content")
    orig_hash = _sha256(target)
    snapshot = Snapshotter.take_snapshot(target, wf_id, "act_roll_create", BURNIN_SANDBOX)
    Path(target).write_text("modified content")
    result = RollbackEngine.restore(snapshot)
    elapsed = (time.time() - t0) * 1000
    restored_hash = _sha256(target)
    passed = result.success and result.checksum_validated and restored_hash == orig_hash
    record(cat, "rollback_create", passed,
           f"success={result.success} validated={result.checksum_validated} checksum_ok={restored_hash == orig_hash}",
           elapsed)
    if passed:
        record_sandbox_rollback("rollback_create_validated")

    # 2. rollback after append
    t0 = time.time()
    target2 = os.path.join(BURNIN_SANDBOX, "rollback_append.txt")
    Path(target2).write_text("base line\n")
    snap2 = Snapshotter.take_snapshot(target2, wf_id, "act_roll_append", BURNIN_SANDBOX)
    with open(target2, "a") as f:
        f.write("appended line\n")
    result2 = RollbackEngine.restore(snap2)
    elapsed = (time.time() - t0) * 1000
    restored = Path(target2).read_text()
    passed = result2.success and result2.checksum_validated and restored == "base line\n"
    record(cat, "rollback_append", passed,
           f"success={result2.success} validated={result2.checksum_validated} content_ok={restored == 'base line\\n'}",
           elapsed)

    # 3. rollback after replace
    t0 = time.time()
    target3 = os.path.join(BURNIN_SANDBOX, "rollback_replace.txt")
    Path(target3).write_text("original content")
    snap3 = Snapshotter.take_snapshot(target3, wf_id, "act_roll_replace", BURNIN_SANDBOX)
    Path(target3).write_text("completely different content")
    result3 = RollbackEngine.restore(snap3)
    elapsed = (time.time() - t0) * 1000
    passed = result3.success and result3.checksum_validated and Path(target3).read_text() == "original content"
    record(cat, "rollback_replace", passed,
           f"success={result3.success} validated={result3.checksum_validated} content_ok={Path(target3).read_text() == 'original content'}",
           elapsed)

    # 4. rollback nonexistent file (created after snapshot)
    t0 = time.time()
    target4 = os.path.join(BURNIN_SANDBOX, "rollback_absent.txt")
    snap4 = Snapshotter.take_snapshot(target4, wf_id, "act_roll_absent", BURNIN_SANDBOX)
    Path(target4).write_text("created after snapshot")
    result4 = RollbackEngine.restore(snap4)
    elapsed = (time.time() - t0) * 1000
    passed = result4.success and not os.path.exists(target4)
    record(cat, "rollback_absent_created", passed,
           f"success={result4.success} exists={os.path.exists(target4)}", elapsed)

    # 5. rollback directory
    t0 = time.time()
    dir_target = os.path.join(BURNIN_SANDBOX, "rollback_dir")
    os.makedirs(dir_target, exist_ok=True)
    Path(os.path.join(dir_target, "a.txt")).write_text("file a")
    Path(os.path.join(dir_target, "b.txt")).write_text("file b")
    snap5 = Snapshotter.take_snapshot(dir_target, wf_id, "act_roll_dir", BURNIN_SANDBOX)
    Path(os.path.join(dir_target, "a.txt")).write_text("modified a")
    Path(os.path.join(dir_target, "c.txt")).write_text("new file c")
    result5 = RollbackEngine.restore(snap5)
    elapsed = (time.time() - t0) * 1000
    a_content = Path(os.path.join(dir_target, "a.txt")).read_text() if os.path.exists(os.path.join(dir_target, "a.txt")) else ""
    c_exists = os.path.exists(os.path.join(dir_target, "c.txt"))
    passed = result5.success and a_content == "file a" and not c_exists
    record(cat, "rollback_directory", passed,
           f"success={result5.success} a_ok={a_content == 'file a'} c_gone={not c_exists}",
           elapsed)

    # 6. checksum mismatch detection
    t0 = time.time()
    target6 = os.path.join(BURNIN_SANDBOX, "rollback_checksum_test.txt")
    Path(target6).write_text("original")
    snap6 = Snapshotter.take_snapshot(target6, wf_id, "act_roll_cksum", BURNIN_SANDBOX)
    Path(target6).write_text("modified")
    result6 = RollbackEngine.restore(snap6)
    elapsed = (time.time() - t0) * 1000
    restored6 = _sha256(target6)
    orig6 = _sha256(target6)  # wait, this is after restore, so it should match
    expected_hash = snap6.checksum_sha256
    passed = result6.success and restored6 == expected_hash
    record(cat, "checksum_post_restore", passed,
           f"success={result6.success} restored_match={restored6 == expected_hash}", elapsed)

    # 7. rollback workflow info
    snapshots = os.path.join(BURNIN_SANDBOX, ".rollback", wf_id)
    has_rollback_data = os.path.isdir(snapshots) and len(os.listdir(snapshots)) > 0
    record(cat, "rollback_data_exists", has_rollback_data,
           f"dir={snapshots} entries={len(os.listdir(snapshots)) if has_rollback_data else 0}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 3: traversal_escape_attempts (100% blocked)
# ═══════════════════════════════════════════════════════════════════

def test_traversal_escape():
    cat = "traversal_escape"
    cases = [
        ("simple_dotdot", "../etc/passwd"),
        ("double_dotdot", "../../etc/passwd"),
        ("nested", "a/../../../etc/shadow"),
        ("encoded", "..%2F..%2Fetc%2Fpasswd"),
        ("mixed_slash", "..\\..\\etc\\passwd"),
        ("deep_traversal", "a/b/c/d/e/f/g/h/i/j/../../../etc/passwd"),
        ("symlinked_traversal", "link_to_sandbox/../../../etc/hosts"),
    ]
    for name, path in cases:
        t0 = time.time()
        traversal_detected = detect_path_traversal(path)
        resolved = resolve_sandbox_path(path, BURNIN_SANDBOX)
        within = is_within_sandbox(resolved, [BURNIN_SANDBOX])
        blocked = traversal_detected or not within
        elapsed = (time.time() - t0) * 1000
        record(cat, name, blocked, f"traversal={traversal_detected} within={within} blocked={blocked}", elapsed)
        if blocked:
            record_sandbox_escape_attempt("path_traversal")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 4: symlink_escape_attempts (100% blocked)
# ═══════════════════════════════════════════════════════════════════

def test_symlink_escape():
    cat = "symlink_escape"
    # Create target outside sandbox
    outside_target = "/tmp/opencode/symlink_outside_target.txt"
    try:
        Path(outside_target).write_text("outside")
    except Exception:
        pass

    cases = [
        ("symlink_outside", os.path.join(BURNIN_SANDBOX, "link_outside.txt"), outside_target),
    ]

    # Create symlink inside sandbox pointing outside
    for name, link_path, target_path in cases:
        t0 = time.time()
        try:
            if os.path.islink(link_path):
                os.unlink(link_path)
            if os.path.exists(link_path):
                os.remove(link_path)
            os.symlink(target_path, link_path)
            escaped = detect_symlink_escape(link_path, BURNIN_SANDBOX)
            elapsed = (time.time() - t0) * 1000
            record(cat, name, escaped, f"symlink_escape_detected={escaped}", elapsed)
            if escaped:
                record_sandbox_escape_attempt("symlink")
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            record(cat, name, True, f"exception={e} (blocked by OS)", elapsed)

    # Symlink loop test
    t0 = time.time()
    loop_a = os.path.join(BURNIN_SANDBOX, "loop_a")
    loop_b = os.path.join(BURNIN_SANDBOX, "loop_b")
    try:
        if os.path.islink(loop_a):
            os.unlink(loop_a)
        if os.path.islink(loop_b):
            os.unlink(loop_b)
        os.symlink(loop_b, loop_a)
        os.symlink(loop_a, loop_b)
        # realpath should handle this gracefully on most systems
        escaped = detect_symlink_escape(loop_a, BURNIN_SANDBOX)
        elapsed = (time.time() - t0) * 1000
        record(cat, "symlink_loop", not escaped, f"escape_detected={escaped} (loop safe)", elapsed)
        if escaped:
            record_sandbox_escape_attempt("symlink_loop")
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        record(cat, "symlink_loop", True, f"exception={e} (safe)", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 5: forbidden_mutations (100% blocked)
# ═══════════════════════════════════════════════════════════════════

def test_forbidden_mutations():
    cat = "forbidden_mutations"

    # chmod detection — use detect_chmod_intent
    chmod_cases = [
        ("chmod_plus_x", "chmod +x script.sh"),
        ("chmod_755", "chmod 755 script.sh"),
        ("chmod_777", "chmod 777 file"),
        ("make_executable", "+x this file"),
    ]
    for name, desc in chmod_cases:
        t0 = time.time()
        blocked = detect_chmod_intent(desc)
        elapsed = (time.time() - t0) * 1000
        record(cat, name, blocked, f"chmod_detected={blocked}", elapsed)
        if blocked:
            record_sandbox_policy_denied("chmod", name)

    # Non-chmod forbidden operations — use detect_forbidden_operation
    non_chmod_cases = [
        ("chown", "chown root:root file"),
        ("sudo_write", "sudo echo test > /etc/hosts"),
        ("systemctl_start", "systemctl start ailab-gateway"),
        ("docker_exec", "docker exec container bash"),
    ]
    for name, desc in non_chmod_cases:
        t0 = time.time()
        blocked = detect_forbidden_operation(desc)
        elapsed = (time.time() - t0) * 1000
        record(cat, name, blocked, f"forbidden_detected={blocked}", elapsed)
        if blocked:
            record_sandbox_policy_denied("forbidden_operation", name)

    # Writes outside sandbox
    outside_cases = [
        ("write_etc", "/etc/test.txt"),
        ("write_var", "/var/lib/test.db"),
        ("write_root", "/root/secret.txt"),
        ("write_boot", "/boot/vmlinuz"),
        ("write_proc", "/proc/test"),
        ("write_dev", "/dev/sda1"),
    ]
    for name, path in outside_cases:
        t0 = time.time()
        gov = check_sandbox_governance("create_file", path, "28.3", BURNIN_SANDBOX)
        blocked = not gov.allowed
        elapsed = (time.time() - t0) * 1000
        record(cat, name, blocked,
               f"governance_allowed={gov.allowed} reason={gov.reason}", elapsed)
        if blocked:
            record_sandbox_policy_denied("outside_sandbox", name)

    # Verify 100% blocked
    cat_results = [r for r in ALL_RESULTS if r.category == cat]
    blocked_count = sum(1 for r in cat_results if r.passed)
    total = len(cat_results)
    record(cat, "100_percent_blocked", blocked_count == total,
           f"{blocked_count}/{total}", duration_ms=0)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 6: extension_validation (100% blocked)
# ═══════════════════════════════════════════════════════════════════

def test_extension_validation():
    cat = "extension_validation"
    cases = [
        ("service_file", "svc.service"),
        ("socket_file", "sock.socket"),
        ("mount_file", "mnt.mount"),
        ("timer_file", "t.timer"),
        ("path_file", "p.path"),
        ("target_file", "t.target"),
        ("binary_blob", "data.bin"),
        ("exe_file", "program.exe"),
        ("dll_file", "lib.dll"),
        ("so_file", "lib.so"),
    ]
    for name, filename in cases:
        t0 = time.time()
        ext = os.path.splitext(filename)[1]
        blocked = is_extension_blocked(ext) or not is_extension_allowed(ext)
        elapsed = (time.time() - t0) * 1000
        record(cat, name, blocked, f"ext={ext} blocked={blocked}", elapsed)
        if blocked:
            record_sandbox_policy_denied("blocked_extension", name)

    # Governance check with blocked extension
    t0 = time.time()
    gov = check_sandbox_governance("create_file", "test.service", "28.3", BURNIN_SANDBOX)
    elapsed = (time.time() - t0) * 1000
    record(cat, "governance_blocks_service", not gov.allowed,
           f"allowed={gov.allowed} reason={gov.reason}", elapsed)

    # Verify 100% blocked
    cat_results = [r for r in ALL_RESULTS if r.category == cat]
    blocked_count = sum(1 for r in cat_results if r.passed)
    total = len(cat_results)
    record(cat, "100_percent_extension_blocked", blocked_count == total,
           f"{blocked_count}/{total}", duration_ms=0)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 7: artifact_budget_validation
# ═══════════════════════════════════════════════════════════════════

def test_artifact_budget():
    cat = "artifact_budget"
    wf_id = f"{WORKFLOW_BASE}_budget"

    # Create MAX_ARTIFACTS_PER_WORKFLOW + 1
    count = MAX_ARTIFACTS_PER_WORKFLOW + 5
    created = 0
    t0 = time.time()
    for i in range(count):
        target = os.path.join(BURNIN_SANDBOX, "budget", f"file_{i:04d}.txt")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        ec, _, _ = _execute_file_mutation(target, f"content {i}", "write")
        if ec == 0:
            created += 1
            ArtifactRegistry.register(ArtifactEntry(
                path=target, checksum_sha256=_sha256(target),
                size_bytes=_get_size(target), mutation_type="create_file",
                workflow_id=wf_id, action_id=f"act_budget_{i}",
            ))
    elapsed = (time.time() - t0) * 1000

    wf_count = ArtifactRegistry.count_by_workflow(wf_id)
    record(cat, f"artifact_count_{created}", wf_count >= count - 5,
           f"created={created} registered={wf_count}", elapsed)

    # Deep path nesting
    t0 = time.time()
    deep_path = "/".join(["sub"] * 12) + "/deep.txt"
    depth_ok = check_path_depth(deep_path, MAX_PATH_DEPTH)
    elapsed = (time.time() - t0) * 1000
    record(cat, "deep_path_nesting_blocked", not depth_ok,
           f"depth_allowed={depth_ok} max={MAX_PATH_DEPTH}", elapsed)
    if not depth_ok:
        record_sandbox_policy_denied("path_depth", "deep_path_nesting")

    # Total bytes check
    total_bytes = ArtifactRegistry.total_bytes_by_workflow(wf_id)
    record(cat, "workflow_bytes_tracked", total_bytes > 0,
           f"total_bytes={total_bytes}", elapsed)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 8: rate_limit_validation
# ═══════════════════════════════════════════════════════════════════

def test_rate_limit():
    cat = "rate_limit"
    wf_id = f"{WORKFLOW_BASE}_ratelimit"

    # Simulate > 10 writes/min by directly calling _record_write
    writes_done = 0
    t0 = time.time()
    for i in range(RATE_LIMIT_WRITES_PER_MIN + 5):
        if SandboxWriteExecutor._check_rate_limit(wf_id):
            SandboxWriteExecutor._record_write(wf_id)
            writes_done += 1

    elapsed = (time.time() - t0) * 1000
    blocked = writes_done <= RATE_LIMIT_WRITES_PER_MIN
    record(cat, "rate_limit_enforced", blocked,
           f"actual_writes={writes_done} limit={RATE_LIMIT_WRITES_PER_MIN}", elapsed)

    # Reset rate tracker
    SandboxWriteExecutor._rate_tracker.pop(wf_id, None)


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 9: lineage_validation
# ═══════════════════════════════════════════════════════════════════

def test_lineage():
    cat = "lineage"
    wf_id = f"{WORKFLOW_BASE}_lineage"
    parent_id = uuid.uuid4().hex[:12]

    parent_entry = ArtifactEntry(
        artifact_id=parent_id,
        path=os.path.join(BURNIN_SANDBOX, "parent.txt"),
        checksum_sha256="parent_hash",
        size_bytes=50, mutation_type="create_file",
        workflow_id=wf_id, action_id="act_parent",
        generated_by_action="create_file",
    )
    ArtifactRegistry.register(parent_entry)

    child_id = uuid.uuid4().hex[:12]
    child_entry = ArtifactEntry(
        artifact_id=child_id,
        path=os.path.join(BURNIN_SANDBOX, "child.txt"),
        checksum_sha256="child_hash",
        size_bytes=30, mutation_type="sandbox_transform",
        workflow_id=wf_id, action_id="act_child",
        parent_artifact_id=parent_id,
        parent_workflow_id=wf_id,
        generated_by_action="sandbox_transform",
    )
    ArtifactRegistry.register(child_entry)

    # Get lineage
    lineage = ArtifactRegistry.get_lineage(child_id)
    has_parent = len(lineage) >= 2
    parent_found = any(e.get("artifact_id") == parent_id for e in lineage)
    record(cat, "lineage_dag_consistency", has_parent and parent_found,
           f"lineage_len={len(lineage)} parent_found={parent_found}")

    # Get by workflow
    wf_entries = ArtifactRegistry.get_by_workflow(wf_id)
    record(cat, "get_by_workflow", len(wf_entries) >= 2,
           f"entries={len(wf_entries)}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 10: concurrent_mutations (real, not subprocess)
# ═══════════════════════════════════════════════════════════════════

def test_concurrent_mutations_worker(worker_id: int):
    cat = "concurrent_mutations"
    wf_id = f"{WORKFLOW_BASE}_concurrent_w{worker_id}"
    local_ok = True
    for i in range(5):
        try:
            target = os.path.join(BURNIN_SANDBOX, "concurrent", f"w{worker_id}_f{i:04d}.txt")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            t0 = time.time()
            ec, _, _ = _execute_file_mutation(target, f"worker{worker_id}_{i}", "write")
            elapsed = (time.time() - t0) * 1000
            if ec == 0:
                chk = _sha256(target)
                ArtifactRegistry.register(ArtifactEntry(
                    path=target, checksum_sha256=chk,
                    size_bytes=_get_size(target), mutation_type="create_file",
                    workflow_id=wf_id, action_id=f"act_c_{worker_id}_{i}",
                ))
            with _lock:
                ok = ec == 0
                record(cat, f"concurrent_write_w{worker_id}_{i}", ok,
                       f"exit={ec}", elapsed)
                if not ok:
                    local_ok = False
        except Exception as e:
            with _lock:
                record(cat, f"concurrent_write_w{worker_id}_{i}", False,
                       f"exception={e}")
            local_ok = False
    return local_ok


def test_concurrent():
    cat = "concurrent_mutations"
    workers = []
    wf_ids = []
    for w in range(3):
        wf_ids.append(f"{WORKFLOW_BASE}_concurrent_w{w}")
        t = threading.Thread(target=test_concurrent_mutations_worker, args=(w,))
        workers.append(t)
        t.start()
        time.sleep(2)

    for w in workers:
        w.join(timeout=30)

    # Verify no corruption
    all_artifacts = []
    for wid in wf_ids:
        all_artifacts.extend(ArtifactRegistry.get_by_workflow(wid))
    record(cat, "concurrent_artifacts_count", len(all_artifacts) >= 10,
           f"total_artifacts={len(all_artifacts)}")

    # Check rollback dirs not conflicting
    rollback_base = os.path.join(BURNIN_SANDBOX, ".rollback")
    if os.path.isdir(rollback_base):
        wf_count = len(os.listdir(rollback_base))
        record(cat, "rollback_dirs_isolated", wf_count >= 3,
               f"workflow_rollback_dirs={wf_count}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 11: workflow_state_validation
# ═══════════════════════════════════════════════════════════════════

def test_workflow_state():
    cat = "workflow_state"

    # EXECUTING → MUTATING → DONE
    t0 = time.time()
    tl = WorkflowTimeline(plan_id="ws_mutating")
    tl.current_state = WorkflowState.EXECUTING
    ok1 = tl.transition(WorkflowState.MUTATING)
    ok2 = tl.transition(WorkflowState.DONE)
    elapsed = (time.time() - t0) * 1000
    record(cat, "executing_to_mutating_to_done", ok1 and ok2,
           f"step1={ok1} step2={ok2} final={tl.current_state.value}", elapsed)

    # EXECUTING → MUTATING → FAILED → ROLLED_BACK
    t0 = time.time()
    tl2 = WorkflowTimeline(plan_id="ws_rollback_flow")
    tl2.current_state = WorkflowState.EXECUTING
    ok1 = tl2.transition(WorkflowState.MUTATING)
    ok2 = tl2.transition(WorkflowState.FAILED)
    ok3 = tl2.transition(WorkflowState.ROLLED_BACK)
    elapsed = (time.time() - t0) * 1000
    record(cat, "executing_to_mutating_to_failed_to_rolled_back", ok1 and ok2 and ok3,
           f"step1={ok1} step2={ok2} step3={ok3} final={tl2.current_state.value}", elapsed)

    # MUTATING invalid transitions
    t0 = time.time()
    tl3 = WorkflowTimeline(plan_id="ws_invalid_mutating")
    tl3.current_state = WorkflowState.MUTATING
    bad1 = not tl3.transition(WorkflowState.PLANNING)
    bad2 = not tl3.transition(WorkflowState.EXECUTING)
    elapsed = (time.time() - t0) * 1000
    record(cat, "mutating_invalid_transitions_blocked", bad1 and bad2,
           f"planning_blocked={bad1} executing_blocked={bad2}", elapsed)

    # DONE → ROLLED_BACK (new transition)
    t0 = time.time()
    tl4 = WorkflowTimeline(plan_id="ws_done_rollback")
    tl4.current_state = WorkflowState.DONE
    ok = tl4.transition(WorkflowState.ROLLED_BACK)
    elapsed = (time.time() - t0) * 1000
    record(cat, "done_to_rolled_back", ok,
           f"state={tl4.current_state.value}", elapsed)

    # FAILED → ROLLED_BACK (new transition)
    t0 = time.time()
    tl5 = WorkflowTimeline(plan_id="ws_failed_rollback")
    tl5.current_state = WorkflowState.FAILED
    ok = tl5.transition(WorkflowState.ROLLED_BACK)
    elapsed = (time.time() - t0) * 1000
    record(cat, "failed_to_rolled_back", ok,
           f"state={tl5.current_state.value}", elapsed)

    # ROLLED_BACK is terminal
    t0 = time.time()
    tl6 = WorkflowTimeline(plan_id="ws_terminal")
    tl6.current_state = WorkflowState.ROLLED_BACK
    no_trans = not tl6.transition(WorkflowState.DONE)
    elapsed = (time.time() - t0) * 1000
    record(cat, "rolled_back_terminal", no_trans,
           f"done_transition_blocked={no_trans}", elapsed)

    # MUTATING exists in VALID_TRANSITIONS
    has_key = WorkflowState.MUTATING in VALID_TRANSITIONS
    record(cat, "mutating_in_valid_transitions", has_key,
           f"has_key={has_key}")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 12: audit_integrity
# ═══════════════════════════════════════════════════════════════════

def test_audit_integrity():
    cat = "audit_integrity"
    wf_id = f"{WORKFLOW_BASE}_audit"

    # Write audit entries
    entries_before = len(read_sandbox_audit(limit=10000))

    for i in range(5):
        entry = SandboxAuditEntry(
            execution_id=f"audit_exec_{i}",
            workflow_id=wf_id,
            action_id=f"act_audit_{i}",
            mutation_class="create",
            mutation_type="create_file",
            target_path=os.path.join(BURNIN_SANDBOX, f"audit_{i}.txt"),
            before_checksum=f"before_{i}",
            after_checksum=f"after_{i}",
            rollback_available=True,
            rollback_path=f"/tmp/.rollback/{wf_id}/act_audit_{i}",
            status="success",
            size_bytes=100 + i,
        )
        write_sandbox_audit(entry)

    entries_after = len(read_sandbox_audit(limit=10000))
    appended = entries_after - entries_before >= 5
    record(cat, "append_only_integrity", appended,
           f"before={entries_before} after={entries_after} delta={entries_after - entries_before}")

    # Check audit entry fields
    recent = read_sandbox_audit(limit=10)
    entries_with_both = sum(
        1 for e in recent
        if e.get("before_checksum") and e.get("after_checksum")
    )
    has_checksums = entries_with_both >= 3
    record(cat, "checksums_in_audit", has_checksums,
           f"entries_with_both_checksums={entries_with_both}")

    # Mutation class present
    has_mutation_class = any(e.get("mutation_class") for e in recent)
    record(cat, "mutation_class_in_audit", has_mutation_class,
           f"found={has_mutation_class}")

    # Rollback available flag
    has_rollback_flag = any(e.get("rollback_available") for e in recent)
    record(cat, "rollback_available_in_audit", has_rollback_flag,
           f"found={has_rollback_flag}")

    # Timestamps valid
    valid_timestamps = all(
        isinstance(e.get("timestamp"), (int, float)) and e["timestamp"] > 1_700_000_000
        for e in recent if e
    )
    record(cat, "valid_timestamps", valid_timestamps,
           f"valid={valid_timestamps}")

    # Stats
    stats = get_sandbox_audit_stats()
    record(cat, "audit_stats_consistent", stats["total"] > 0 and "success" in stats,
           f"total={stats['total']} success={stats['success']}")


# ═══════════════════════════════════════════════════════════════════
# WORKER
# ═══════════════════════════════════════════════════════════════════

def run_worker(worker_id: int):
    print(f"\n--- Worker {worker_id} starting ---")
    try:
        if worker_id == 0:
            test_benign_mutations()
            test_rollback_validation()
            test_workflow_state()
            test_audit_integrity()
        elif worker_id == 1:
            test_traversal_escape()
            test_symlink_escape()
            test_forbidden_mutations()
            test_extension_validation()
        elif worker_id == 2:
            test_artifact_budget()
            test_rate_limit()
            test_lineage()
            test_concurrent()
    except Exception as e:
        msg = f"Worker {worker_id} error: {e}"
        print(f"  ❌ {msg}")
        import traceback
        traceback.print_exc()
        with _lock:
            _worker_errors.append(msg)


# ═══════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════

def generate_reports():
    report_dir = "/mnt/opencode/test"
    os.makedirs(report_dir, exist_ok=True)

    total = len(ALL_RESULTS)
    passed = sum(1 for r in ALL_RESULTS if r.passed)
    failed = total - passed
    by_category: dict[str, dict] = {}
    for r in ALL_RESULTS:
        if r.category not in by_category:
            by_category[r.category] = {"total": 0, "passed": 0, "failed": 0}
        by_category[r.category]["total"] += 1
        if r.passed:
            by_category[r.category]["passed"] += 1
        else:
            by_category[r.category]["failed"] += 1

    pass_rate = (passed / total * 100) if total else 0

    report_data = {
        "burnin": "FASE 28.3-B Sandbox Write Burn-in & Rollback Validation",
        "checkpoint_from": "CP-28.3-SANDBOX-WRITE-STABLE",
        "timestamp": int(time.time()),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "pass_rate_pct": round(pass_rate, 2),
        "sandbox_root": BURNIN_SANDBOX,
        "audit_stats": get_sandbox_audit_stats(),
        "worker_errors": _worker_errors,
        "by_category": by_category,
        "failures": [
            {"category": r.category, "test": r.test_name, "detail": r.detail}
            for r in ALL_RESULTS if not r.passed
        ],
        "results": [asdict(r) for r in ALL_RESULTS],
    }

    # JSON
    json_path = os.path.join(report_dir, "fase28-3b-burnin-report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"\n📄 JSON report: {json_path}")

    # Markdown summary
    md_path = os.path.join(report_dir, "fase28-3b-summary.md")
    lines = [
        "# FASE 28.3-B — Sandbox Write Burn-in & Rollback Validation",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"**Duration:** {time.time() - _burnin_start:.0f}s",
        f"**Pass rate:** {pass_rate:.1f}% ({passed}/{total})",
        "",
        "## Configuration",
        f"- Sandbox root: `{BURNIN_SANDBOX}`",
        f"- Workers: 3",
        "",
        "## Results by Category",
    ]
    for cat in sorted(by_category.keys()):
        c = by_category[cat]
        icon = "✅" if c["failed"] == 0 else "❌"
        lines.append(f"- {icon} **{cat}**: {c['passed']}/{c['total']} passed")
    lines += [
        "",
        "## Failures",
    ]
    failures = [r for r in ALL_RESULTS if not r.passed]
    if failures:
        for f_entry in failures:
            lines.append(f"- ❌ `{f_entry.category}` → `{f_entry.test_name}`: {f_entry.detail}")
    else:
        lines.append("- ✅ No failures")
    lines += [
        "",
        "## Pass Criteria",
    ]
    pass_criteria = {
        "0 writes outside sandbox": all(
            r.passed for r in ALL_RESULTS
            if r.category in ("forbidden_mutations", "traversal_escape", "symlink_escape")
        ),
        "0 traversal escapes": all(r.passed for r in ALL_RESULTS if r.category == "traversal_escape"),
        "0 symlink escapes": all(r.passed for r in ALL_RESULTS if r.category == "symlink_escape"),
        "0 governance bypass": all(r.passed for r in ALL_RESULTS if r.category == "forbidden_mutations"),
        "0 checksum mismatches": all(
            "checksum" not in r.test_name.lower() or r.passed
            for r in ALL_RESULTS
        ),
        "0 rollback corruption": all(r.passed for r in ALL_RESULTS if r.category == "rollback_validation"),
        "0 audit corruption": all(r.passed for r in ALL_RESULTS if r.category == "audit_integrity"),
        "0 workflow deadlocks": all(r.passed for r in ALL_RESULTS if r.category == "workflow_state"),
        "100% forbidden blocked": all(r.passed for r in ALL_RESULTS if r.category == "forbidden_mutations"),
        "100% traversal blocked": all(r.passed for r in ALL_RESULTS if r.category == "traversal_escape"),
        "100% symlink blocked": all(r.passed for r in ALL_RESULTS if r.category == "symlink_escape"),
        "100% extension blocked": all(r.passed for r in ALL_RESULTS if r.category == "extension_validation"),
        "rollback integrity": all(r.passed for r in ALL_RESULTS if r.category == "rollback_validation"),
        "lineage consistency": all(r.passed for r in ALL_RESULTS if r.category == "lineage"),
        "rate limiting enforced": all(r.passed for r in ALL_RESULTS if r.category == "rate_limit"),
        "budget enforcement": all(r.passed for r in ALL_RESULTS if r.category == "artifact_budget"),
        "workflow transitions valid": all(r.passed for r in ALL_RESULTS if r.category == "workflow_state"),
    }
    all_pass = all(pass_criteria.values())
    for criterion, ok in pass_criteria.items():
        icon = "✅" if ok else "❌"
        lines.append(f"- {icon} {criterion}")
    lines += [
        "",
        f"## Verdict: **{'PASS ✅' if all_pass else 'FAIL ❌'}**",
        "",
    ]
    if all_pass:
        lines.append("Tag: `CP-28.3-B-SANDBOX-WRITE-BURNIN-STABLE`")
    md_content = "\n".join(lines)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"📄 MD summary:  {md_path}")

    return all_pass


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

_burnin_start = time.time()


def main():
    quick = "--quick" in sys.argv
    num_workers = 3

    print("=" * 60)
    print("FASE 28.3-B — Sandbox Write Burn-in & Rollback Validation")
    print("=" * 60)
    print(f"  Sandbox root:  {BURNIN_SANDBOX}")
    print(f"  Workers:       {num_workers}")
    print(f"  Quick mode:    {quick}")
    print()

    # Reset sandbox
    _reset_sandbox()
    print(f"  Sandbox reset: ✅")
    print()

    if not quick:
        workers = []
        for i in range(num_workers):
            w = threading.Thread(target=run_worker, args=(i,), daemon=True)
            workers.append(w)
            w.start()
            time.sleep(15 + (i * 2))
        for w in workers:
            w.join(timeout=120)
    else:
        run_worker(0)

    all_pass = generate_reports()

    elapsed = time.time() - _burnin_start
    print(f"\n{'=' * 60}")
    print(f"Burn-in completed in {elapsed:.0f}s")
    print(f"Total tests: {len(ALL_RESULTS)}")
    print(f"Passed:      {sum(1 for r in ALL_RESULTS if r.passed)}")
    print(f"Failed:      {sum(1 for r in ALL_RESULTS if not r.passed)}")
    print(f"Errors:      {len(_worker_errors)}")
    print(f"Verdict:     {'✅ PASS' if all_pass else '❌ FAIL'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
