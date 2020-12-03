"""Test tests.integration.with_hypothesis.sample_module with inferred Hypothesis strategies."""

import unittest

import hypothesis.strategies as st
from hypothesis import assume, given
import icontract.integration.with_hypothesis

import tests.integration.with_hypothesis.sample_module


class TestWithInferredStrategies(unittest.TestCase):
    """Test all functions from tests.integration.with_hypothesis.sample_module with inferred Hypothesis strategies."""

    def test_square_greater_than_zero(self) -> None:
        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(
            func=tests.integration.with_hypothesis.sample_module.square_greater_than_zero)

        @given(x=st.integers())
        def execute(x) -> None:
            assume_preconditions(x)
            tests.integration.with_hypothesis.sample_module.square_greater_than_zero(x)

    def test_some_func(self) -> None:
        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(
            func=tests.integration.with_hypothesis.sample_module.some_func)

        @given(x=st.integers(min_value=1))
        def execute(x) -> None:
            assume_preconditions(x)
            tests.integration.with_hypothesis.sample_module.some_func(x)

    def test_another_func(self) -> None:
        assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(
            func=tests.integration.with_hypothesis.sample_module.another_func)

        @given(x=st.integers(min_value=1).filter(lambda x: square_greater_than_zero(x)))
        def execute(x) -> None:
            assume_preconditions(x)
            tests.integration.with_hypothesis.sample_module.another_func(x)


if __name__ == '__main__':
    unittest.main()
