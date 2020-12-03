"""Provide a valid module for testing pyicontract-hypothesis."""

from tests.integration.with_hypothesis.sample_library import square_greater_than_zero

import icontract

SOME_FUNC_CALLS = 0


@icontract.require(lambda x: x > 0)
def some_func(x: int) -> None:
    global SOME_FUNC_CALLS
    SOME_FUNC_CALLS += 1


ANOTHER_FUNC_CALLS = 0


@icontract.require(lambda x: x > 0)
@icontract.require(lambda x: square_greater_than_zero(x), "dummy precondition to test filtering")
def another_func(x: int) -> None:
    global ANOTHER_FUNC_CALLS
    ANOTHER_FUNC_CALLS += 1


# pyicontract-hypothesis: disable
def expected_to_be_ignored(x: int) -> None:
    pass


# pyicontract-hypothesis: enable


# Class is ignored as well.
class A:
    @icontract.require(lambda x: x > 0)
    def __init__(self, x: int) -> None:
        self.x = x

    @icontract.require(lambda y: y > 0)
    @icontract.ensure(lambda result: result > 0)
    def some_method(self, y: int) -> int:
        return self.x + y
