#!/usr/bin/env python3

# pylint: disable=missing-docstring, invalid-name, unused-argument,no-self-use,unnecessary-lambda
import pathlib
import reprlib
import time
import unittest
from typing import Optional, List  # pylint: disable=unused-import

import icontract

SOME_GLOBAL_CONSTANT = 10


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
            some_func(path=pathlib.Path("/doesnt/exist/test_contract"))
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: path.exists():\n"
                         "path was PosixPath('/doesnt/exist/test_contract')\n"
                         "path.exists() was False", str(pre_err))

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

    def test_repr(self):
        a_repr = reprlib.Repr()
        a_repr.maxlist = 3

        @icontract.pre(lambda x: len(x) < 10, a_repr=a_repr)
        def some_func(x: List[int]) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=list(range(10 * 1000)))
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: len(x) < 10:\n"
                         "len(x) was 10000\n"
                         "x was [0, 1, 2, ...]", str(pre_err))

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
        self.assertEqual("Precondition violated: x > 3: x was 1", str(pre_err))

        # Test method with self
        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method_with_self()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: self.y > 10: self.y was 5", str(pre_err))

    def test_repr_nested_property(self):
        class B:
            def __init__(self) -> None:
                self.x = 0

            def x_plus_z(self, z: int) -> int:
                return self.x + z

            def __repr__(self) -> str:
                return "B(x={})".format(self.x)

        class A:
            def __init__(self) -> None:
                self.b = B()

            @icontract.pre(lambda self: self.b.x > 0)
            def some_func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "A()"

        a = A()

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: self.b.x > 0:\n"
                         "self was A()\n"
                         "self.b was B(x=0)\n"
                         "self.b.x was 0", str(pre_err))

    def test_repr_nested_method(self):
        z = 10

        class C:
            def __init__(self, x: int) -> None:
                self._x = x

            def x(self) -> int:
                return self._x

            def __repr__(self) -> str:
                return "C(x={})".format(self._x)

        class B:
            def c(self, x: int) -> C:
                return C(x=x)

            def __repr__(self) -> str:
                return "B()"

        def gt_zero(value: int) -> bool:
            return value > 0

        class A:
            def __init__(self) -> None:
                self.b = B()

            @icontract.pre(lambda self: pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) is None)
            def some_func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "A()"

        a = A()

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(
            "Precondition violated: pathlib.Path(str(gt_zero((self.b.c(x=0).x() + (12.2 * z))))) is None:\n"
            "gt_zero((self.b.c(x=0).x() + (12.2 * z))) was True\n"
            "pathlib.Path(str(gt_zero((self.b.c(x=0).x() + (12.2 * z))))) was PosixPath('True')\n"
            "self was A()\n"
            "self.b was B()\n"
            "self.b.c(x=0) was C(x=0)\n"
            "self.b.c(x=0).x() was 0\n"
            "str(gt_zero((self.b.c(x=0).x() + (12.2 * z)))) was 'True'\n"
            "z was 10", str(pre_err))

    def test_repr_value_closure(self):
        y = 4
        z = 5

        @icontract.pre(lambda x: x < y + z)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: x < (y + z):\n" "x was 100\n" "y was 4\n" "z was 5", str(pre_err))

    def test_repr_value_global(self):
        @icontract.pre(lambda x: x < SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: x < SOME_GLOBAL_CONSTANT:\n"
                         "SOME_GLOBAL_CONSTANT was 10\n"
                         "x was 100", str(pre_err))

    def test_repr_value_closure_and_global(self):
        y = 4

        @icontract.pre(lambda x: x < y + SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("Precondition violated: x < (y + SOME_GLOBAL_CONSTANT):\n"
                         "SOME_GLOBAL_CONSTANT was 10\n"
                         "x was 100\n"
                         "y was 4", str(pre_err))


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
        self.assertEqual("Post-condition violated: result > x:\n" "result was -4\n" "x was 1", str(post_err))

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
        self.assertEqual("Post-condition violated: expected summation: result > x:\n"
                         "result was -4\n"
                         "x was 1", str(post_err))

    def test_repr_args(self):
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
        self.assertEqual("Post-condition violated: result > x: result was -0004, x was 00001", str(post_err))

    def test_repr(self):
        a_repr = reprlib.Repr()
        a_repr.maxlist = 3

        @icontract.post(lambda result, x: len(result) > x, a_repr=a_repr)
        def some_func(x: int) -> List[int]:
            return list(range(x))

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=10 * 1000)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual("Post-condition violated: len(result) > x:\n"
                         "len(result) was 10000\n"
                         "result was [0, 1, 2, ...]\n"
                         "x was 10000", str(post_err))


if __name__ == '__main__':
    unittest.main()
