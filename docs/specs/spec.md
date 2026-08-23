# Spec: Tiny Python CLI Calculator Library

Entry point `src/calc.py` exposing four functions: `add`, `subtract`, `multiply`, `divide`.
All arithmetic is over JSON numbers (int or float). No CLI argument parsing is required for
this library; "CLI" refers to the project type (`ui_type: cli`) — the public surface is the
Python API below. Units are ordered and atomic; each unit is independently implementable
and testable.

---

## Unit 1: Addition

Function signature: `add(a, b) -> number`.

Request I/O JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["op", "a", "b"],
  "properties": {
    "op": { "const": "add" },
    "a": { "type": "number" },
    "b": { "type": "number" }
  },
  "additionalProperties": false
}
```

Response JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": { "type": "number" }
  },
  "additionalProperties": false
}
```

Boundary rules:
- Accepts ints and floats; returns int when both operands are int, otherwise float
  (standard Python numeric semantics).
- Must not raise for any finite numeric inputs, including negatives and zero.
- Float overflow propagates naturally (inf per IEEE-754); no special handling.

## Unit 2: Subtraction

Function signature: `subtract(a, b) -> number`.

Request I/O JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["op", "a", "b"],
  "properties": {
    "op": { "const": "subtract" },
    "a": { "type": "number" },
    "b": { "type": "number" }
  },
  "additionalProperties": false
}
```

Response JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": { "type": "number" }
  },
  "additionalProperties": false
}
```

Boundary rules:
- Semantics: `a - b`. Operand order is significant.
- Same int/float return rules as Unit 1. Must not raise for finite numeric inputs.

## Unit 3: Multiplication

Function signature: `multiply(a, b) -> number`.

Request I/O JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["op", "a", "b"],
  "properties": {
    "op": { "const": "multiply" },
    "a": { "type": "number" },
    "b": { "type": "number" }
  },
  "additionalProperties": false
}
```

Response JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": { "type": "number" }
  },
  "additionalProperties": false
}
```

Boundary rules:
- Zero times anything returns 0 (int) when both are ints.
- Same int/float return rules as Unit 1. Must not raise for finite numeric inputs.

## Unit 4: Division

Function signature: `divide(a, b) -> number`.

Request I/O JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["op", "a", "b"],
  "properties": {
    "op": { "const": "divide" },
    "a": { "type": "number" },
    "b": { "type": "number" }
  },
  "additionalProperties": false
}
```

Response JSON schema (success):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": { "type": "number" }
  },
  "additionalProperties": false
}
```

Error response (failure):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["error"],
  "properties": {
    "error": {
      "type": "object",
      "required": ["code", "message"],
      "properties": {
        "code": { "const": "ZERO_DIVISION" },
        "message": { "type": "string" }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

Boundary rules:
- Semantics: true division `a / b`; result is always float (even `4 / 2 == 2.0`).
- When `b == 0` (including `-0.0`), the function MUST raise `ZeroDivisionError`
  with a non-empty message. This is a hard contract; it must never be swallowed,
  converted to inf/nan, or replaced by another exception type.
- Any other input raising is unspecified behavior; only division by zero has a
  defined error contract.

## Unit 5: Module assembly (src/calc.py)

Boundary rules:
- `src/calc.py` defines all four functions at module level with exact names
  `add`, `subtract`, `multiply`, `divide`.
- No side effects on import (no prints, no file I/O); import must succeed with
  exit code 0.
- Optional `if __name__ == "__main__"` block may exist but is not part of the
  contract and must not affect imports or tests.
