# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda

import unittest
from typing import Optional, List

import icontract

import tests.error
import tests.mock


class TestAsyncFunctionSyncCondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        @icontract.ensure(lambda result: result > 0)
        async def some_func() -> int:
            return 100

        result = await some_func()
        self.assertEqual(100, result)

    async def test_ok_with_snapshot(self) -> None:
        @icontract.snapshot(lambda lst: len(lst), name="len_lst")
        @icontract.ensure(lambda OLD, result: result > OLD.len_lst)
        async def some_func(lst: List[int]) -> int:
            lst.append(1984)
            return len(lst)

        result = await some_func(lst=[1, 2, 3])
        self.assertEqual(4, result)

    async def test_fail(self) -> None:
        @icontract.ensure(lambda result: result > 0)
        async def some_func() -> int:
            return -100

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = await some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "result > 0: result was -100",
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestAsyncFunctionAsyncCondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        async def result_greater_zero(result: int) -> bool:
            return result > 0

        @icontract.ensure(result_greater_zero)
        async def some_func() -> int:
            return 100

        result = await some_func()
        self.assertEqual(100, result)

    async def test_snapshot(self) -> None:
        async def capture_len_lst(lst: List[int]) -> int:
            return len(lst)

        @icontract.snapshot(capture_len_lst, name="len_lst")
        @icontract.ensure(lambda OLD, lst: OLD.len_lst + 1 == len(lst))
        async def some_func(lst: List[int]) -> None:
            lst.append(1984)

        lst = []  # type: List[int]
        await some_func(lst=lst)
        self.assertListEqual([1984], lst)

    async def test_fail(self) -> None:
        async def result_greater_zero(result: int) -> bool:
            return result > 0

        @icontract.ensure(result_greater_zero)
        async def some_func() -> int:
            return -100

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = await some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "result_greater_zero: result was -100",
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestCoroutine(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        async def some_condition() -> bool:
            return True

        @icontract.ensure(lambda: some_condition())
        async def some_func() -> None:
            pass

        await some_func()

    async def test_fail(self) -> None:
        async def some_condition() -> bool:
            return False

        @icontract.ensure(
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

        @icontract.ensure(lambda: some_condition())
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

    async def test_snapshot(self) -> None:
        async def some_capture() -> int:
            return 1984

        @icontract.snapshot(lambda: some_capture(), name="hoho")
        @icontract.ensure(lambda OLD: OLD.hoho == 1984)
        async def some_func() -> None:
            pass

        await some_func()


class TestInvalid(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_postcondition_arguments(self) -> None:
        @icontract.ensure(lambda b, result: b > result)
        async def some_function(a: int) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            await some_function(a=13)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual(
            "The argument(s) of the contract condition have not been set: ['b']. "
            "Does the original function define them? Did you supply them in the call?",
            tests.error.wo_mandatory_location(str(type_err)),
        )

    async def test_conflicting_result_argument(self) -> None:
        @icontract.ensure(lambda a, result: a > result)
        async def some_function(
            a: int, result: int
        ) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            await some_function(a=13, result=2)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual(
            "Unexpected argument 'result' in a function decorated with postconditions.",
            str(type_err),
        )

    async def test_conflicting_OLD_argument(self) -> None:
        @icontract.snapshot(lambda a: a[:])
        @icontract.ensure(lambda OLD, a: a == OLD.a)
        async def some_function(
            a: List[int], OLD: int
        ) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            await some_function(a=[13], OLD=2)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual(
            "Unexpected argument 'OLD' in a function decorated with postconditions.",
            str(type_err),
        )

    async def test_error_with_invalid_arguments(self) -> None:
        @icontract.ensure(
            lambda result: result > 0,
            error=lambda z, result: ValueError(
                "x is {}, result is {}".format(z, result)
            ),
        )
        async def some_func(x: int) -> int:
            return x

        type_error = None  # type: Optional[TypeError]
        try:
            await some_func(x=0)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual(
            "The argument(s) of the contract error have not been set: ['z']. "
            "Does the original function define them? Did you supply them in the call?",
            tests.error.wo_mandatory_location(str(type_error)),
        )

    async def test_no_boolyness(self) -> None:
        @icontract.ensure(lambda: tests.mock.NumpyArray([True, False]))
        async def some_func() -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            await some_func()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual(
            "Failed to negate the evaluation of the condition.",
            tests.error.wo_mandatory_location(str(value_error)),
        )


if __name__ == "__main__":
    unittest.main()
