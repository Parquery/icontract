# The module ``unittest`` supports async only from 3.8 on.
# That is why we had to move this test to 3.8 specific tests.

# pylint: disable=missing-docstring, invalid-name, no-member, unnecessary-lambda
import dataclasses
import unittest
from typing import Optional, List, Iterable, TypeVar, Awaitable

import icontract
import tests.error


class TestAsyncFunctionSyncPrecondition(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual("x > 0: x was -1", tests.error.wo_mandatory_location(str(violation_error)))


class TestAsyncFunctionSyncPostcondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        @icontract.ensure(lambda result: result > 0)
        async def some_func() -> int:
            return 100

        result = await some_func()
        self.assertEqual(100, result)

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
        self.assertEqual("result > 0: result was -100", tests.error.wo_mandatory_location(str(violation_error)))


class TestAsyncMethodAndInvariant(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class A:
            def __init__(self) -> None:
                self.x = 100

            async def some_func(self) -> int:
                self.x = 200
                return self.x

            def another_func(self) -> int:
                self.x = 300
                return self.x

        a = A()
        result = await a.some_func()
        self.assertEqual(200, result)

        result = a.another_func()
        self.assertEqual(300, result)

    async def test_fail(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class A:
            def __init__(self) -> None:
                self.x = 100

            async def some_func(self) -> None:
                self.x = -1

        a = A()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            await a.some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertTrue(tests.error.wo_mandatory_location(str(violation_error)).startswith('self.x > 0'))


class TestAsyncFunctionAsyncPrecondition(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual("x_greater_zero: x was -1", tests.error.wo_mandatory_location(str(violation_error)))


class TestAsyncFunctionAsyncPostcondition(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual("result_greater_zero: result was -100", tests.error.wo_mandatory_location(
            str(violation_error)))


class TestSyncFunction(unittest.IsolatedAsyncioTestCase):
    def test_that_async_precondition_fails(self) -> None:
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
            r'^Unexpected coroutine \(async\) condition <.*> for a sync function <.*\.some_func at .*>.')

    def test_that_async_postcondition_fails(self) -> None:
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
            r'^Unexpected coroutine \(async\) condition <.*> for a sync function <.*\.some_func at .*>.')

    def test_that_async_snapshot_fails(self) -> None:
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
            str(value_error), r'^Unexpected coroutine \(async\) snapshot capture <function .*\.capture_len_lst at .*> '
            r'for a sync function <function .*\.some_func at .*>\.')


class TestAsyncInvariantsFail(unittest.IsolatedAsyncioTestCase):
    def test_that_async_invariants_reported(self) -> None:
        async def some_async_invariant(self: 'A') -> bool:
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

        self.assertEqual(
            "Async conditions are not possible in invariants as sync methods such as __init__ have to be wrapped.",
            str(value_error))


class TestCoroutines(unittest.IsolatedAsyncioTestCase):
    async def test_mock_backend_example(self) -> None:
        # This is an example of a backend system.
        # This test demonstrates how contracts can be used with coroutines.

        T = TypeVar('T')

        async def awaited_all(aws: Iterable[Awaitable[T]]) -> bool:
            for awaitable in aws:
                if not await awaitable:
                    return False

            return True

        async def has_author(identifier: str) -> bool:
            return identifier in ["Margaret Cavendish", "Jane Austen"]

        async def has_category(category: str) -> bool:
            return category in await get_categories()

        async def get_categories() -> List[str]:
            return ["sci-fi", "romance"]

        @dataclasses.dataclass
        class Book:
            identifier: str
            author: str

        @icontract.require(lambda categories: awaited_all(map(has_category, categories)))
        @icontract.ensure(lambda result: awaited_all(has_author(book.author) for book in result))
        async def list_books(categories: List[str]) -> List[Book]:
            result = []  # type: List[Book]
            for category in categories:
                if category == "sci-fi":
                    result.extend([Book(identifier="The Blazing World", author="Margaret Cavendish")])
                elif category == "romance":
                    result.extend([Book(identifier="Pride and Prejudice", author="Jane Austen")])
                else:
                    raise AssertionError(category)

            return result

        sci_fi_books = await list_books(categories=['sci-fi'])
        self.assertListEqual(['The Blazing World'], [book.identifier for book in sci_fi_books])


class TestCoroutinePrecondition(unittest.IsolatedAsyncioTestCase):
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

        @icontract.require(lambda: some_condition(), error=lambda: icontract.ViolationError("hihi"))
        async def some_func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            await some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("hihi", str(violation_error))

    async def test_reported_if_without_error(self) -> None:
        async def some_condition() -> bool:
            return False

        @icontract.require(lambda: some_condition())
        async def some_func() -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            await some_func()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertRegex(
            str(value_error), r"^Unexpected coroutine function <function .*> as a condition of a contract\. "
            r"You must specify your own error if the condition of your contract is a coroutine function\.")


class TestCoroutinePostcondition(unittest.IsolatedAsyncioTestCase):
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

        @icontract.ensure(lambda: some_condition(), error=lambda: icontract.ViolationError("hihi"))
        async def some_func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            await some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual("hihi", str(violation_error))

    async def test_reported_if_without_error(self) -> None:
        async def some_condition() -> bool:
            return False

        @icontract.ensure(lambda: some_condition())
        async def some_func() -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            await some_func()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertRegex(
            str(value_error), r"^Unexpected coroutine function <function .*> as a condition of a contract\. "
            r"You must specify your own error if the condition of your contract is a coroutine function\.")

    async def test_snapshot(self) -> None:
        async def some_capture() -> int:
            return 1984

        @icontract.snapshot(lambda: some_capture(), name="hoho")
        @icontract.ensure(lambda OLD: OLD.hoho == 1984)
        async def some_func() -> None:
            pass

        await some_func()


if __name__ == '__main__':
    unittest.main()
