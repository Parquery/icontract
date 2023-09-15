# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import unittest
from typing import Optional

import icontract

import tests.error


class TestAsyncMethod(unittest.IsolatedAsyncioTestCase):
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
        self.assertTrue(
            tests.error.wo_mandatory_location(str(violation_error)).startswith(
                "self.x > 0"
            )
        )
