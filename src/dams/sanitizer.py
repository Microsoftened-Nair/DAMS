"""AST Sanitizer Gate.

Strips test internals (file paths, line numbers, assertion source lines)
from test failure logs before they reach the Coder, so it cannot overfit
to test implementation details.
"""
from __future__ import annotations

import re
from typing import List

# Patterns that leak tester intent or test internals.
_PATTERNS: List[tuple] = [
    # File paths pointing into tests/
    (re.compile(r'^\s*File "(?P<path>[^"]*tests/[^"]*)", line \d+', re.M),
     'File "[TEST_INTERNALS_REDACTED]", line [REDACTED]'),
    # Bare paths into tests/
    (re.compile(r'(?<![\w/.])([\w./-]*tests/[\w./-]+)'), "[TEST_PATH_REDACTED]"),
    # pytest failure location lines:  tests/unit/test_x.py::test_y FAILED
    (re.compile(r'^\s*[\w./-]*tests/[\w./-]+::\S+\s+(PASSED|FAILED|ERROR|SKIPPED).*$', re.M),
     "[TEST_RESULT_LINE_REDACTED]"),
    # "assert <expr>" lines and traceback frames quoting assertion source
    (re.compile(r'^[ \t]*(E\s+)?assert .+$', re.M), "[ASSERTION_SOURCE_REDACTED]"),
    # line numbers like ":42:" inside tracebacks after redaction
    (re.compile(r'line (\d+)'), "line [REDACTED]"),
]


def sanitize(log: str) -> str:
    out = log
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out


# What survives sanitization — useful signal the Coder IS allowed to see:
#   - exception type names (ValueError, TypeError ...)
#   - module/function names in src/
#   - expected vs actual behavior summaries written by the orchestrator
KEEP_HINT = ("Sanitized diagnostics: exception types and src/ stack frames are preserved; "
             "test file paths, line numbers, and assertion sources are redacted.")
