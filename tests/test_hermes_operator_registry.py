import pytest

from runtime.hermes.loader import load_all, load_operators
from runtime.hermes.validation import validate_all
from runtime.hermes.models import HermesRegistry


class TestOperatorIdsUnique:
    def test_all_ids_unique(self):
        ops = load_operators()
        ids = [o.id for o in ops]
        assert len(ids) == len(set(ids))


class TestOperatorRequiredFields:
    def test_all_have_description(self):
        ops = load_operators()
        for op in ops:
            assert op.description, f"Operator {op.id} has no description"

    def test_all_have_capabilities(self):
        ops = load_operators()
        for op in ops:
            assert op.capabilities, f"Operator {op.id} has no capabilities"

    def test_all_have_domains(self):
        ops = load_operators()
        for op in ops:
            assert op.domains, f"Operator {op.id} has no domains"

    def test_all_have_forbidden_actions(self):
        ops = load_operators()
        for op in ops:
            assert op.forbidden_actions, f"Operator {op.id} has no forbidden actions"

    def test_all_have_reports(self):
        ops = load_operators()
        for op in ops:
            assert op.reports, f"Operator {op.id} has no reports"

    def test_all_have_success_criteria(self):
        ops = load_operators()
        for op in ops:
            assert op.success_criteria, f"Operator {op.id} has no success_criteria"

    def test_all_have_failure_conditions(self):
        ops = load_operators()
        for op in ops:
            assert op.failure_conditions, f"Operator {op.id} has no failure_conditions"


class TestOperatorExecutionMode:
    def test_all_modes_valid(self):
        ops = load_operators()
        valid = {"readonly", "advisory", "execute"}
        for op in ops:
            assert op.execution_mode in valid, f"Operator {op.id} invalid mode '{op.execution_mode}'"

    def test_no_execute_without_authorization(self):
        registry = load_all()
        result = validate_all(registry)
        auth_warnings = [w for w in result.warnings
                        if "authorization_required" in w.field]
        assert len(auth_warnings) == 0


class TestOperatorProtocols:
    def test_all_protocols_known(self):
        registry = load_all()
        result = validate_all(registry)
        proto_warnings = [w for w in result.warnings
                         if "required_protocols" in w.field]
        assert len(proto_warnings) == 0


class TestOperatorMCP:
    def test_required_mcp_exist(self):
        registry = load_all()
        result = validate_all(registry)
        mcp_warnings = [w for w in result.warnings
                       if w.field == "required_mcp" and w.source.startswith("operators/")]
        assert len(mcp_warnings) == 0


class TestOperatorTruthModel:
    def test_all_have_truth_model(self):
        ops = load_operators()
        for op in ops:
            assert isinstance(op.truth_model, dict), f"Operator {op.id} missing truth_model"

    def test_all_have_min_confidence(self):
        ops = load_operators()
        for op in ops:
            assert "min_confidence" in op.truth_model, f"Operator {op.id} missing min_confidence"

    def test_all_have_require_citations(self):
        ops = load_operators()
        for op in ops:
            assert "require_citations" in op.truth_model, f"Operator {op.id} missing require_citations"


class TestOperatorValidationIntegration:
    def test_validation_zero_operator_errors(self):
        registry = load_all()
        result = validate_all(registry)
        op_errors = [e for e in result.errors if e.source.startswith("operators/")]
        assert len(op_errors) == 0

    def test_validation_zero_operator_warnings(self):
        registry = load_all()
        result = validate_all(registry)
        op_warnings = [w for w in result.warnings if w.source.startswith("operators/")]
        assert len(op_warnings) == 0
