# pylint: disable=missing-docstring
# pylint: disable=unnecessary-lambda
import unittest
from typing import List

import icontract


class TestPrecondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        order = []  # type: List[str]

        @icontract.require(lambda: another_func())
        @icontract.require(lambda: yet_another_func())
        async def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.require(lambda: some_func())
        @icontract.require(lambda: yet_yet_another_func())
        async def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        async def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        async def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        await some_func()

        self.assertListEqual(
            [
                "yet_another_func",
                "yet_yet_another_func",
                "some_func",
                "another_func",
                "some_func",
            ],
            order,
        )

    async def test_recover_after_exception(self) -> None:
        order = []  # type: List[str]
        some_func_should_raise = True

        class CustomError(Exception):
            pass

        @icontract.require(lambda: another_func())  # pylint: disable=unnecessary-lambda
        @icontract.require(
            lambda: yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def some_func() -> bool:
            order.append(some_func.__name__)
            if some_func_should_raise:
                raise CustomError("some_func_should_raise")
            return True

        @icontract.require(lambda: some_func())  # pylint: disable=unnecessary-lambda
        @icontract.require(
            lambda: yet_yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        async def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        async def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        try:
            await some_func()
        except CustomError:
            pass

        self.assertListEqual(
            ["yet_another_func", "yet_yet_another_func", "some_func"], order
        )

        # Reset for the next experiment
        order = []
        some_func_should_raise = False

        await some_func()

        self.assertListEqual(
            [
                "yet_another_func",
                "yet_yet_another_func",
                "some_func",
                "another_func",
                "some_func",
            ],
            order,
        )


class TestPostcondition(unittest.IsolatedAsyncioTestCase):
    async def test_ok(self) -> None:
        order = []  # type: List[str]
        another_func_should_raise = True

        class CustomError(Exception):
            pass

        @icontract.ensure(lambda: another_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(
            lambda: yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.ensure(lambda: some_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(
            lambda: yet_yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def another_func() -> bool:
            order.append(another_func.__name__)
            if another_func_should_raise:
                raise CustomError("some_func_should_raise")

            return True

        async def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        async def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        try:
            await some_func()
        except CustomError:
            pass

        self.assertListEqual(["some_func", "yet_another_func", "another_func"], order)

        # Reset for the next experiments
        order = []
        another_func_should_raise = False

        await some_func()

        self.assertListEqual(
            [
                "some_func",
                "yet_another_func",
                "another_func",
                "yet_yet_another_func",
                "some_func",
            ],
            order,
        )

    async def test_recover_after_exception(self) -> None:
        order = []  # type: List[str]

        @icontract.ensure(lambda: another_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(
            lambda: yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.ensure(lambda: some_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(
            lambda: yet_yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        async def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        async def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        async def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        await some_func()

        self.assertListEqual(
            [
                "some_func",
                "yet_another_func",
                "another_func",
                "yet_yet_another_func",
                "some_func",
            ],
            order,
        )


if __name__ == "__main__":
    unittest.main()
