#!/usr/bin/env python3

# pylint: disable=missing-docstring, invalid-name, unused-argument,no-self-use,unnecessary-lambda
import pathlib
import time
import unittest
import uuid
from typing import Optional  # pylint: disable=unused-import

import icontract


class TestPrecondition(unittest.TestCase):
    def test_ok(self):
        @icontract.pre(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        some_func(x=5)
        some_func(x=5, y=10)

    def test_condition_in_different_code_positions(self):
        # pylint: disable=unused-variable
        @icontract.pre(lambda x: x > 3)
        def func1(x: int, y: int = 5) -> None:
            pass

        @icontract.pre(condition=lambda x: x > 3)
        def func2(x: int, y: int = 5) -> None:
            pass

        @icontract.pre(condition=lambda x: x > 3)
        def func3(x: int, y: int = 5) -> None:
            pass

        @icontract.pre(condition=lambda x: x > 3, description="some description")
        def func4(x: int, y: int = 5) -> None:
            pass

        @icontract.pre(lambda x: x > 3, description="some description")
        def func5(x: int, y: int = 5) -> None:
            pass

        @icontract.pre(lambda x: x > 3, description="some description")
        def func6(x: int, y: int = 5) -> None:
            pass

    def test_fail(self):
        @icontract.pre(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: x > 3: x was 1")

    def test_fail_with_description(self):
        @icontract.pre(lambda x: x > 3, "x must not be small")
        def some_func(x: int, y: int = 5) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: x must not be small: x > 3: x was 1")

    def test_fail_multiline(self):
        @icontract.pre(lambda x: x \
                                     > \
                                     3)
        def some_func(x: int, y: int = 5) -> str:
            return str(x)

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: x > 3: x was 1")

    def test_fail_condition_function(self):
        def some_condition(x: int):
            return x > 3

        @icontract.pre(some_condition)
        def some_func(x: int, y: int = 5) -> str:
            return str(x)

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: some_condition: x was 1")

    def test_pre_with_pathlib(self):
        @icontract.pre(lambda path: path.exists())
        def some_func(path: pathlib.Path) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(path=pathlib.Path("/doesnt/exist/{}".format(uuid.uuid4())))
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertTrue(
            str(pre_err).startswith("Precondition violated: path.exists(): path was PosixPath('/doesnt/exist/"))

    def test_benchmark(self):
        @icontract.pre(lambda x: x > 3)
        def pow_with_pre(x: int, y: int) -> int:
            return x**y

        def pow_wo_pre(x: int, y: int) -> int:
            if x <= 3:
                raise ValueError("precondition")

            return x**y

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_with_pre(x=i, y=2)
        duration_with_pre = time.time() - start

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_wo_pre(x=i, y=2)
        duration_wo_pre = time.time() - start

        self.assertLess(duration_with_pre / duration_wo_pre, 6)

    def test_invalid_precondition_arguments(self):
        type_err = None  # type: Optional[TypeError]
        try:

            @icontract.pre(lambda b: b > 3)
            def some_function(a: int) -> None:  # pylint: disable=unused-variable
                pass
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual(str(type_err), "Unexpected condition argument: b")

    def test_repr_args(self):
        @icontract.pre(lambda x: x > 3, repr_args=lambda x: "x was {:03}".format(x))
        def some_func(x: int, y: int = 5) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: x > 3: x was 001")

    def test_repr_args_unexpected_arguments(self):
        value_err = None  # type: Optional[ValueError]

        try:
            # pylint: disable=unused-variable
            @icontract.pre(lambda x: x > 3, repr_args=lambda z: "z was {:X}".format(z))
            def some_func(x: int, y: int = 5) -> None:
                pass
        except ValueError as err:
            value_err = err

        self.assertIsNotNone(value_err)
        self.assertEqual(str(value_err), "Unexpected argument(s) of repr_args. Expected ['x'], got ['z']")

    def test_class(self):
        class A:
            def __init__(self) -> None:
                self.y = 5

            @icontract.pre(lambda x: x > 3)
            def some_method(self, x: int) -> int:
                return self.y

            @icontract.pre(lambda self: self.y > 10, repr_args=lambda self: "self.y was {}".format(self.y))
            def some_method_with_self(self) -> None:
                pass

        a = A()

        # Test method without self
        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method(x=1)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: x > 3: x was 1")

        # Test method with self
        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method_with_self()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "Precondition violated: self.y > 10: self.y was 5")


class TestPostcondition(unittest.TestCase):
    def test_ok(self):
        @icontract.post(lambda result, x: result > x)
        def some_func(x: int, y: int = 5) -> int:
            return x + y

        some_func(x=5)
        some_func(x=5, y=10)

    def test_fail(self):
        @icontract.post(lambda result, x: result > x)
        def some_func(x: int, y: int = 5) -> int:
            return x - y

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual(str(post_err), "Post-condition violated: result > x: result was -4: x was 1")

    def test_fail_with_description(self):
        @icontract.post(lambda result, x: result > x, "expected summation")
        def some_func(x: int, y: int = 5) -> int:
            return x - y

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual(
            str(post_err), "Post-condition violated: expected summation: result > x: result was -4: x was 1")

    def test_repr(self):
        @icontract.post(
            lambda result, x: result > x, repr_args=lambda result, x: "result was {:05}, x was {:05}".format(result, x))
        def some_func(x: int, y: int = 5) -> int:
            return x - y

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual(str(post_err), "Post-condition violated: result > x: result was -0004, x was 00001")


if __name__ == '__main__':
    unittest.main()
