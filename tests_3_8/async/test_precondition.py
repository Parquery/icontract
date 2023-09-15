# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda

import unittest
from typing import Optional

import icontract
import tests.error


class TestAsyncFunctionSyncCondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        @icontract.require(lambda x: x > 0)
        async def some_func(x: int) -> int:
            return x * 10

        result = await some_func(1)
        self.assertEqual(10, result)

    async def test_fail(self) -> None:
        @icontract.require(lambda x: x > 0)
        async def some_func(x: int) -> int:
            return x * 10

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = await some_func(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x > 0: x was -1", tests.error.wo_mandatory_location(str(violation_error))
        )


class TestAsyncFunctionAsyncCondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        async def x_greater_zero(x: int) -> bool:
            return x > 0

        @icontract.require(x_greater_zero)
        async def some_func(x: int) -> int:
            return x * 10

        result = await some_func(1)
        self.assertEqual(10, result)

    async def test_fail(self) -> None:
        async def x_greater_zero(x: int) -> bool:
            return x > 0

        @icontract.require(x_greater_zero)
        async def some_func(x: int) -> int:
            return x * 10

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = await some_func(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x_greater_zero: x was -1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestCoroutine(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        async def some_condition() -> bool:
            return True

        @icontract.require(lambda: some_condition())
        async def some_func() -> None:
            pass

        await some_func()

    async def test_fail(self) -> None:
        async def some_condition() -> bool:
            return False

        @icontract.require(
            lambda: some_condition(), error=lambda: icontract.ViolationError("hihi")
        )
        async def some_func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            await some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("hihi", str(violation_error))

    async def test_reported_if_no_error_is_specified_as_we_can_not_recompute_coroutine_functions(
        self,
    ) -> None:
        async def some_condition() -> bool:
            return False

        @icontract.require(lambda: some_condition())
        async def some_func() -> None:
            pass

        runtime_error = None  # type: Optional[RuntimeError]
        try:
            await some_func()
        except RuntimeError as err:
            runtime_error = err

        assert runtime_error is not None
        assert runtime_error.__cause__ is not None
        assert isinstance(runtime_error.__cause__, ValueError)

        value_error = runtime_error.__cause__

        self.assertRegex(
            str(value_error),
            r"^Unexpected coroutine function <function .*> as a condition of a contract\. "
            r"You must specify your own error if the condition of your contract is a coroutine function\.",
        )


if __name__ == "__main__":
    unittest.main()
