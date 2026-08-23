"""Framework self-test — validates sanitizer, manifest validation, and
guardrails deterministically without any LLM/API calls."""
import json
import tempfile
from pathlib import Path


def run(root=Path(".")):
    results = []

    # 1. Sanitizer strips test internals but keeps exception types
    from dams.sanitizer import sanitize
    raw_log = (
        'Traceback (most recent call last):\n'
        '  File "/proj/tests/unit/test_calc.py", line 42\n'
        'tests/unit/test_calc.py::test_add FAILED\n'
        'E       assert 5 == 4\n'
        'src/calc.py:10: in add\n'
        'ValueError: bad input\n'
    )
    clean = sanitize(raw_log)
    assert "test_calc.py" not in clean, "leaked test path"
    assert "assert 5 == 4" not in clean, "leaked assertion"
    assert "ValueError: bad input" in clean, "lost useful diagnostic"
    assert "line [REDACTED]" in clean or "[TEST_INTERNALS_REDACTED]" in clean
    results.append(("sanitizer", True))

    # 2. Manifest validation
    from dams.manifest import validate, ManifestError
    good = {
        "manifest_version": "1.0", "project_name": "demo",
        "runtime": {"language": "python", "version": "3", "package_manager": "pip",
                     "ui_type": "cli"},
        "commands": {"install": "pip install -e .", "build": "true", "lint": "true",
                      "test_unit": "pytest tests -q", "dev_server": ""},
        "contracts": {"entry_point": "src/main.py", "specs_dir": "docs/specs",
                       "source_dir": "src", "test_dir": "tests", "port_variable": "PORT"},
    }
    validate(good)
    try:
        bad = dict(good); bad.pop("commands")
        validate(bad)
        raise AssertionError("should have raised")
    except ManifestError:
        pass
    results.append(("manifest_validation", True))

    # 3. Monotonicity gate
    from dams.guardrails import check_monotonicity, GuardrailViolation
    check_monotonicity(5, 6)   # growth is fine
    try:
        check_monotonicity(6, 5)
        raise AssertionError("should have raised")
    except GuardrailViolation:
        pass
    results.append(("monotonicity_gate", True))

    # 4. Circuit breaker trips at exactly 3
    from dams.guardrails import CircuitBreaker
    cb = CircuitBreaker()
    for _ in range(3):
        cb.record_failure("x")
    assert cb.tripped() and not CircuitBreaker().tripped()
    results.append(("circuit_breaker", True))

    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("Smoke test complete: all deterministic components verified.")
