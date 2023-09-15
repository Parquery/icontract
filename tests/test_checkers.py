#!/usr/bin/env python3

# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument

import functools
import unittest
from typing import Optional

import icontract._checkers
from icontract._globals import CallableT


def decorator_plus_1(func: CallableT) -> CallableT:
    def wrapper(*args, **kwargs):  # type: ignore
        return func(*args, **kwargs) + 1

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    return wrapper  # type: ignore


def decorator_plus_2(func: CallableT) -> CallableT:
    def wrapper(*args, **kwargs):  # type: ignore
        return func(*args, **kwargs) + 2

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    return wrapper  # type: ignore


class TestUnwindDecoratorStack(unittest.TestCase):
    def test_wo_decorators(self) -> None:
        def func() -> int:
            return 0

        self.assertListEqual(
            [0],
            [a_func() for a_func in icontract._checkers._walk_decorator_stack(func)],
        )

    def test_with_single_decorator(self) -> None:
        @decorator_plus_1
        def func() -> int:
            return 0

        self.assertListEqual(
            [1, 0],
            [a_func() for a_func in icontract._checkers._walk_decorator_stack(func)],
        )

    def test_with_double_decorator(self) -> None:
        @decorator_plus_2
        @decorator_plus_1
        def func() -> int:
            return 0

        self.assertListEqual(
            [3, 1, 0],
            [a_func() for a_func in icontract._checkers._walk_decorator_stack(func)],
        )


class TestResolveKwargs(unittest.TestCase):
    def test_that_extra_args_raise_correct_type_error(self) -> None:
        @icontract.require(lambda: True)
        def some_func(x: int, y: int) -> None:
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(1, 2, 3)  # type: ignore
        except TypeError as error:
            type_error = error

        assert type_error is not None
        self.assertRegex(
            str(type_error),
            r"^([a-zA-Z_0-9<>.]+\.)?some_func\(\) takes 2 positional arguments but 3 were given$",
        )

    def test_that_result_in_kwargs_raises_an_error(self) -> None:
        @icontract.ensure(lambda result: result > 0)
        def some_func(*args, **kwargs) -> int:  # type: ignore
            return -1

        type_error = None  # type: Optional[TypeError]

        try:
            some_func(result=-1)
        except TypeError as error:
            type_error = error

        assert type_error is not None

        self.assertEqual(
            "Unexpected argument 'result' in a function decorated with postconditions.",
            str(type_error),
        )

    def test_that_OLD_in_kwargs_raises_an_error(self) -> None:
        @icontract.ensure(lambda result: result > 0)
        def some_func(*args, **kwargs) -> int:  # type: ignore
            return -1

        type_error = None  # type: Optional[TypeError]

        try:
            some_func(OLD=-1)
        except TypeError as error:
            type_error = error

        assert type_error is not None

        self.assertEqual(
            "Unexpected argument 'OLD' in a function decorated with postconditions.",
            str(type_error),
        )


if __name__ == "__main__":
    unittest.main()
