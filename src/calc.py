"""Tiny calculator library (tiny-calc).

Public API over JSON numbers (int or float), standard Python numeric semantics.
"""


def add(a, b):
    """Return a + b. Returns int when both operands are int, else float."""
    return a + b


def subtract(a, b):
    """Return a - b."""
    return a - b


def multiply(a, b):
    """Return a * b."""
    return a * b


def divide(a, b):
    """Return a / b.

    Raises:
        ZeroDivisionError: if b == 0.
    """
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b
