"""Black-box pytest suite for the calculator library (Units 1-4).

Written strictly against docs/specs/spec.md. No knowledge of the
implementation in src/ is used beyond the public module path
(src/calc.py) and function signatures named in the spec.
"""

import importlib.util
import math
import os
import sys

import pytest

# Import src/calc.py as a top-level module without requiring packaging.
_CALC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "calc.py")
_spec = importlib.util.spec_from_file_location("calc_under_test", _CALC_PATH)
calc = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("calc_under_test", calc)
_spec.loader.exec_module(calc)


class TestAdd:
    def test_basic_ints(self):
        assert calc.add(2, 3) == 5

    def test_negative_ints(self):
        assert calc.add(-2, -3) == -5

    def test_with_zero(self):
        assert calc.add(0, 0) == 0
        assert calc.add(7, 0) == 7
        assert calc.add(0, -7) == -7

    def test_floats(self):
        assert calc.add(1.5, 2.25) == 3.75

    def test_mixed_int_float_returns_float(self):
        result = calc.add(1, 0.5)
        assert isinstance(result, float)
        assert result == 1.5

    def test_int_int_returns_int_type(self):
        assert isinstance(calc.add(2, 3), int)

    def test_large_values(self):
        assert calc.add(10**18, 10**18) == 2 * 10**18

    def test_float_overflow_propagates_to_inf(self):
        # Spec: overflow propagates naturally (inf per IEEE-754).
        assert calc.add(1e308, 1e308) == math.inf


class TestSubtract:
    def test_basic_ints(self):
        assert calc.subtract(5, 3) == 2

    def test_operand_order_significant(self):
        assert calc.subtract(3, 5) == -2
        assert calc.subtract(5, 3) != calc.subtract(3, 5)

    def test_negatives_and_zero(self):
        assert calc.subtract(-4, -6) == 2
        assert calc.subtract(0, 9) == -9
        assert calc.subtract(9, 0) == 9

    def test_floats(self):
        assert calc.subtract(2.5, 1.25) == 1.25
        assert isinstance(calc.subtract(1, 0.5), float)


class TestMultiply:
    def test_basic_ints(self):
        assert calc.multiply(4, 6) == 24

    def test_zero_times_anything_ints(self):
        # Spec: zero times anything returns int 0 when both are ints.
        result = calc.multiply(0, 12345)
        assert result == 0
        assert isinstance(result, int)
        result = calc.multiply(-7, 0)
        assert result == 0
        assert isinstance(result, int)

    def test_negatives(self):
        assert calc.multiply(-3, 4) == -12
        assert calc.multiply(-3, -4) == 12

    def test_floats(self):
        assert calc.multiply(1.5, 2.0) == 3.0
        assert isinstance(calc.multiply(2, 0.5), float)

    def test_must_not_raise_for_finite_inputs(self):
        calc.multiply(1e308, -1e308)  # -inf allowed; must not raise


class TestDivide:
    def test_true_division_always_float(self):
        result = calc.divide(4, 2)
        assert result == 2.0
        assert isinstance(result, float)

    def test_exact_division(self):
        assert calc.divide(10, 4) == 2.5

    def test_non_terminating_division(self):
        result = calc.divide(1, 3)
        assert isinstance(result, float)
        assert result == pytest.approx(0.3333333333333333)

    def test_division_by_zero_raises_zerodivisionerror(self):
        with pytest.raises(ZeroDivisionError):
            calc.divide(1, 0)

    def test_division_of_zero_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            calc.divide(0, 0)

    def test_division_by_negative_zero_raises(self):
        # Spec: b == 0 including -0.0 must raise ZeroDivisionError.
        with pytest.raises(ZeroDivisionError):
            calc.divide(1, -0.0)

    def test_error_message_non_empty(self):
        try:
            calc.divide(5, 0)
        except ZeroDivisionError as exc:
            assert len(str(exc)) > 0
        else:
            pytest.fail("ZeroDivisionError not raised")

    def test_divide_by_one_identity(self):
        assert calc.divide(42, 1) == 42.0
