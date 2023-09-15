# The module ``unittest`` supports async only from 3.8 on.
# That is why we had to move this test to 3.8 specific tests.

# pylint: disable=missing-docstring, invalid-name, unnecessary-lambda
import unittest
from typing import Optional, List

import icontract


class TestSyncFunctionAsyncConditionFail(unittest.IsolatedAsyncioTestCase):
    def test_precondition(self) -> None:
        async def x_greater_zero(x: int) -> bool:
            return x > 0

        @icontract.require(x_greater_zero)
        def some_func(x: int) -> int:
            return x * 10

        value_error = None  # type: Optional[ValueError]
        try:
            _ = some_func(100)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine \(async\) condition <.*> for a sync function <.*\.some_func at .*>.",
        )

    def test_postcondition(self) -> None:
        async def result_greater_zero(result: int) -> bool:
            return result > 0

        @icontract.ensure(result_greater_zero)
        def some_func() -> int:
            return 100

        value_error = None  # type: Optional[ValueError]
        try:
            _ = some_func()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine \(async\) condition <.*> for a sync function <.*\.some_func at .*>.",
        )

    def test_snapshot(self) -> None:
        async def capture_len_lst(lst: List[int]) -> int:
            return len(lst)

        @icontract.snapshot(capture_len_lst, name="len_lst")
        @icontract.ensure(lambda OLD, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int]) -> None:
            lst.append(1984)

        value_error = None  # type: Optional[ValueError]
        try:
            some_func([1])
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine \(async\) snapshot capture <function .*\.capture_len_lst at .*> "
            r"for a sync function <function .*\.some_func at .*>\.",
        )


class TestSyncFunctionConditionCoroutineFail(unittest.IsolatedAsyncioTestCase):
    def test_precondition(self) -> None:
        async def x_greater_zero(x: int) -> bool:
            return x > 0

        @icontract.require(lambda x: x_greater_zero(x))
        def some_func(x: int) -> int:
            return x * 10

        value_error = None  # type: Optional[ValueError]
        try:
            _ = some_func(100)
        except ValueError as err:
            value_error = err

        assert value_error is not None

        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine resulting from the condition <function .*> for a sync function <function .*>\.$",
        )

    def test_postcondition(self) -> None:
        async def result_greater_zero(result: int) -> bool:
            return result > 0

        @icontract.ensure(lambda result: result_greater_zero(result))
        def some_func() -> int:
            return 100

        value_error = None  # type: Optional[ValueError]
        try:
            _ = some_func()
        except ValueError as err:
            value_error = err

        assert value_error is not None

        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine resulting from the condition <function .*> for a sync function <function .*>\.$",
        )

    def test_snapshot(self) -> None:
        async def capture_len_lst(lst: List[int]) -> int:
            return len(lst)

        @icontract.snapshot(lambda lst: capture_len_lst(lst), name="len_lst")
        @icontract.ensure(lambda OLD, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int]) -> None:
            lst.append(1984)

        value_error = None  # type: Optional[ValueError]
        try:
            some_func([1])
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine resulting "
            r"from the snapshot capture <function .*> of a sync function <function .*>.$",
        )


class TestAsyncInvariantsFail(unittest.IsolatedAsyncioTestCase):
    def test_that_async_invariants_reported(self) -> None:
        async def some_async_invariant(self: "A") -> bool:
            return self.x > 0

        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable
            @icontract.invariant(some_async_invariant)
            class A:
                def __init__(self) -> None:
                    self.x = 100

        except ValueError as error:
            value_error = error

        assert value_error is not None

        self.assertEqual(
            "Async conditions are not possible in invariants as sync methods such as __init__ have to be wrapped.",
            str(value_error),
        )


if __name__ == "__main__":
    unittest.main()
