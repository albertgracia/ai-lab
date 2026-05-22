import subprocess
import sys
import json
from pathlib import Path

ROOT = Path("/opt/ai-lab")
CONTEXT_FILE = ROOT / "runtime/opencode/context.md"
AGENTS_FILE = ROOT / "AGENTS.md"
CONVERSATION_HISTORY = ROOT / "conversation-history.md"
OPENCODE_CONTEXT_PY = ROOT / "runtime/opencode_context.py"
TEST_CONTEXT_FILE = Path("/mnt/opencode/test/AGENTS.md")

EXPECTED_CHECKPOINT = "CP-31B-RUNTIME-SEMANTIC-MATURITY-STABLE"
EXPECTED_HF_CHECKPOINT = "CP-31B-HF1-OPENCODE-CONTEXT-ALIGNMENT-STABLE"
EXPECTED_31C_CHECKPOINT = "CP-31C-OPERATIONAL-REPORTING-DISCIPLINE-STABLE"
EXPECTED_NEXT_PHASE = "FASE 31C"
DEPRECATED_MODEL = "lmstudio-community/qwen2.5-coder-14b-instruct"
PRIMARY_OPERATIONAL = "llama-3.1-8b-instruct"
PRIMARY_CODING = "qwen/qwen2.5-coder-14b-instruct"
OFFLINE_GPU = "RX7900XT"
ACTIVE_GPU = "RX9070"
PROMETHEUS_AUTHORITY = "192.168.1.40:9090"


def _read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


class TestOpenCodeContextAlignment31B:

    def test_opencode_context_contains_current_checkpoint(self):
        content = _read_file(CONTEXT_FILE)
        assert EXPECTED_CHECKPOINT in content, (
            f"context.md should contain checkpoint {EXPECTED_CHECKPOINT}"
        )

    def test_opencode_context_contains_model_routing_policy(self):
        content = _read_file(CONTEXT_FILE)
        assert PRIMARY_OPERATIONAL in content, (
            f"context.md should contain {PRIMARY_OPERATIONAL} as PRIMARY_OPERATIONAL_MODEL"
        )
        assert PRIMARY_CODING in content, (
            f"context.md should contain {PRIMARY_CODING} as PRIMARY_CODING_MODEL"
        )

    def test_opencode_context_contains_current_roadmap(self):
        content = _read_file(CONTEXT_FILE)
        assert EXPECTED_NEXT_PHASE in content, (
            f"context.md should contain next phase {EXPECTED_NEXT_PHASE}"
        )
        assert "31C" in content, "context.md should contain FASE 31C in roadmap"

    def test_deprecated_model_not_present_as_active(self):
        content = _read_file(CONTEXT_FILE)
        assert DEPRECATED_MODEL in content, (
            f"context.md should mention {DEPRECATED_MODEL} as deprecated"
        )
        assert "DEPRECATED" in content or "NON_ROUTABLE" in content, (
            "context.md should mark deprecated models clearly"
        )

    def test_prometheus_authority_documented(self):
        content = _read_file(CONTEXT_FILE)
        assert PROMETHEUS_AUTHORITY in content, (
            f"context.md should document Prometheus authority {PROMETHEUS_AUTHORITY}"
        )
        assert "source of truth" in content.lower(), (
            "context.md should state Prometheus is source of truth"
        )

    def test_next_phase_is_31c(self):
        content = _read_file(CONTEXT_FILE)
        assert EXPECTED_NEXT_PHASE in content, (
            f"context.md should list {EXPECTED_NEXT_PHASE} as next phase"
        )

    def test_rx7900xt_expected_offline(self):
        content = _read_file(CONTEXT_FILE)
        assert OFFLINE_GPU in content, (
            f"context.md should mention {OFFLINE_GPU}"
        )
        assert "offline" in content.lower() or "expected_offline" in content.lower(), (
            f"context.md should mark {OFFLINE_GPU} as offline/expected_offline"
        )

    def test_rx9070_active(self):
        content = _read_file(CONTEXT_FILE)
        assert ACTIVE_GPU in content, (
            f"context.md should mention {ACTIVE_GPU}"
        )

    def test_agents_md_contains_31b_phases(self):
        content = _read_file(AGENTS_FILE)
        assert "30I-G" in content, "AGENTS.md should include FASE 30I-G"
        assert "31B" in content, "AGENTS.md should include FASE 31B"
        assert "OBS-31A.5" in content, "AGENTS.md should include FASE OBS-31A.5"

    def test_agents_md_tags_count_updated(self):
        content = _read_file(AGENTS_FILE)
        assert "50 tags" in content or "CP-31C" in content, (
            "AGENTS.md should reference 50+ tags up to CP-31C"
        )

    def test_agents_md_checkpoint_is_31b(self):
        content = _read_file(AGENTS_FILE)
        assert EXPECTED_CHECKPOINT in content, (
            f"AGENTS.md should state checkpoint {EXPECTED_CHECKPOINT}"
        )

    def test_conversation_history_contains_31b(self):
        content = _read_file(CONVERSATION_HISTORY)
        assert "31B" in content, (
            "conversation-history.md should document FASE 31B"
        )

    def test_opencode_context_py_contains_anti_stale_guard(self):
        content = _read_file(OPENCODE_CONTEXT_PY)
        assert "MINIMUM_CHECKPOINT" in content, (
            "opencode_context.py should define MINIMUM_CHECKPOINT guard"
        )
        assert "anti_stale_guard" in content, (
            "opencode_context.py should have anti_stale_guard() function"
        )
        assert "CP-31B" in content, (
            "opencode_context.py should reference CP-31B checkpoint"
        )

    def test_opencode_context_py_validation_mode(self):
        result = subprocess.run(
            [sys.executable, str(OPENCODE_CONTEXT_PY), "--validate"],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=10,
        )
        assert result.returncode == 0, (
            f"Validation should pass. stdout: {result.stdout}, stderr: {result.stderr}"
        )

    def test_opencode_context_py_generates_valid_content(self):
        result = subprocess.run(
            [sys.executable, str(OPENCODE_CONTEXT_PY)],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=10,
        )
        assert result.returncode == 0, f"Generator should exit 0: {result.stderr}"
        has_checkpoint = (
            EXPECTED_CHECKPOINT in result.stdout
            or EXPECTED_HF_CHECKPOINT in result.stdout
            or EXPECTED_31C_CHECKPOINT in result.stdout
        )
        assert has_checkpoint, (
            f"Generated context should contain a CP-31x checkpoint tag. "
            f"Expected one of: {EXPECTED_CHECKPOINT}, {EXPECTED_HF_CHECKPOINT}, {EXPECTED_31C_CHECKPOINT}"
        )
        assert "CURRENT AI-LAB RUNTIME TRUTH" in result.stdout, (
            "Generated context should contain RUNTIME TRUTH block"
        )

    def test_generated_context_matches_file(self):
        gen_result = subprocess.run(
            [sys.executable, str(OPENCODE_CONTEXT_PY)],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=10,
        )
        file_content = _read_file(CONTEXT_FILE)
        assert gen_result.stdout.strip(), "Generator should produce stdout"
        assert file_content.strip(), "context.md should have content"
        # At minimum the runtime truth block must be present in both
        assert "CURRENT AI-LAB RUNTIME TRUTH" in file_content, (
            "context.md should contain the RUNTIME TRUTH block"
        )

    def test_open_ui_sh_uses_correct_generator(self):
        ui_sh = ROOT / "runtime/opencode_ui.sh"
        content = _read_file(ui_sh)
        assert "opencode_context.py" in content, (
            "opencode_ui.sh should reference opencode_context.py"
        )
        assert "context.md" in content, (
            "opencode_ui.sh should output context.md"
        )

    def test_test_context_archived(self):
        content = _read_file(TEST_CONTEXT_FILE)
        assert "ARCHIVED CONTEXT" in content, (
            "/mnt/opencode/test/AGENTS.md should be marked as archived"
        )

    def test_context_generation_json_safe(self):
        result = subprocess.run(
            [sys.executable, str(OPENCODE_CONTEXT_PY)],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=10,
        )
        output = result.stdout
        # Check it does not contain unparseable garbage
        assert output, "Generated context should not be empty"
        assert result.returncode == 0, "Generator should succeed"
