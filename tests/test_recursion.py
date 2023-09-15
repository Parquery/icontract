# pylint: disable=missing-docstring
# pylint: disable=unnecessary-lambda
import unittest
from typing import List

import icontract


class TestPrecondition(unittest.TestCase):
    def test_ok(self) -> None:
        order = []  # type: List[str]

        @icontract.require(lambda: another_func())
        @icontract.require(lambda: yet_another_func())
        def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.require(lambda: some_func())
        @icontract.require(
            lambda: yet_yet_another_func()
        )  # pylint: disable=unnecessary-lambda
        def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        some_func()

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

    def test_recover_after_exception(self) -> None:
        order = []  # type: List[str]
        some_func_should_raise = True

        class CustomError(Exception):
            pass

        @icontract.require(lambda: another_func())
        @icontract.require(lambda: yet_another_func())
        def some_func() -> bool:
            order.append(some_func.__name__)
            if some_func_should_raise:
                raise CustomError("some_func_should_raise")
            return True

        @icontract.require(lambda: some_func())
        @icontract.require(lambda: yet_yet_another_func())
        def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        try:
            some_func()
        except CustomError:
            pass

        self.assertListEqual(
            ["yet_another_func", "yet_yet_another_func", "some_func"], order
        )

        # Reset for the next experiment
        order = []
        some_func_should_raise = False

        some_func()

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


class TestPostcondition(unittest.TestCase):
    def test_ok(self) -> None:
        order = []  # type: List[str]
        another_func_should_raise = True

        class CustomError(Exception):
            pass

        @icontract.ensure(lambda: another_func())
        @icontract.ensure(lambda: yet_another_func())
        def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.ensure(lambda: some_func())
        @icontract.ensure(lambda: yet_yet_another_func())
        def another_func() -> bool:
            order.append(another_func.__name__)
            if another_func_should_raise:
                raise CustomError("some_func_should_raise")

            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        try:
            some_func()
        except CustomError:
            pass

        self.assertListEqual(["some_func", "yet_another_func", "another_func"], order)

        # Reset for the next experiments
        order = []
        another_func_should_raise = False

        some_func()

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

    def test_recover_after_exception(self) -> None:
        order = []  # type: List[str]

        @icontract.ensure(lambda: another_func())
        @icontract.ensure(lambda: yet_another_func())
        def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.ensure(lambda: some_func())
        @icontract.ensure(lambda: yet_yet_another_func())
        def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        some_func()

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


class TestInvariant(unittest.TestCase):
    def test_ok(self) -> None:
        order = []  # type: List[str]

        @icontract.invariant(lambda self: self.some_func())
        class SomeClass(icontract.DBC):
            def __init__(self) -> None:
                order.append("__init__")

            def some_func(self) -> bool:
                order.append("some_func")
                return True

            def another_func(self) -> bool:
                order.append("another_func")
                return True

        some_instance = SomeClass()
        self.assertListEqual(["__init__", "some_func"], order)

        # Reset for the next experiment
        order = []

        some_instance.another_func()
        self.assertListEqual(["some_func", "another_func", "some_func"], order)

    def test_recover_after_exception(self) -> None:
        order = []  # type: List[str]
        some_func_should_raise = False

        class CustomError(Exception):
            pass

        @icontract.invariant(lambda self: self.some_func())
        class SomeClass(icontract.DBC):
            def __init__(self) -> None:
                order.append("__init__")

            def some_func(self) -> bool:
                order.append("some_func")
                if some_func_should_raise:
                    raise CustomError("some_func_should_raise")

                return True

            def another_func(self) -> bool:
                order.append("another_func")
                return True

        some_instance = SomeClass()
        self.assertListEqual(["__init__", "some_func"], order)

        # Reset for the next experiment
        order = []
        some_func_should_raise = True

        try:
            some_instance.another_func()
        except CustomError:
            pass

        self.assertListEqual(["some_func"], order)

        # Reset for the next experiment
        order = []
        some_func_should_raise = False

        some_instance.another_func()
        self.assertListEqual(["some_func", "another_func", "some_func"], order)

    def test_member_function_call_in_constructor(self) -> None:
        order = []  # type: List[str]

        @icontract.invariant(lambda self: self.some_attribute > 0)
        class SomeClass(icontract.DBC):
            def __init__(self) -> None:
                order.append("__init__ enters")
                self.some_attribute = self.some_func()
                order.append("__init__ exits")

            def some_func(self) -> int:
                order.append("some_func")
                return 3

        _ = SomeClass()
        self.assertListEqual(["__init__ enters", "some_func", "__init__ exits"], order)


if __name__ == "__main__":
    unittest.main()
