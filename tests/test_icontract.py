#!/usr/bin/env python3
# pylint: disable=too-many-lines
# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-self-use
# pylint: disable=unnecessary-lambda
# pylint: disable=too-many-public-methods
# pylint: disable=protected-access
import abc
import functools
import pathlib
import reprlib
import time
import unittest
from typing import Optional, List, Callable, Any, Type  # pylint: disable=unused-import

import icontract

SOME_GLOBAL_CONSTANT = 10


def decorator_plus_1(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args, **kwargs) -> Any:
        return func(*args, **kwargs) + 1

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    return wrapper


def decorator_plus_2(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args, **kwargs) -> Any:
        return func(*args, **kwargs) + 2

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    return wrapper


class TestUnwindDecoratorStack(unittest.TestCase):
    def test_wo_decorators(self):
        def func() -> int:
            return 0

        self.assertListEqual([0], [a_func() for a_func in icontract._unwind_decorator_stack(func)])

    def test_with_single_decorator(self):
        @decorator_plus_1
        def func() -> int:
            return 0

        self.assertListEqual([1, 0], [a_func() for a_func in icontract._unwind_decorator_stack(func)])

    def test_with_double_decorator(self):
        @decorator_plus_2
        @decorator_plus_1
        def func() -> int:
            return 0

        self.assertListEqual([3, 1, 0], [a_func() for a_func in icontract._unwind_decorator_stack(func)])


class TestPrecondition(unittest.TestCase):
    def test_ok(self):
        @icontract.pre(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        some_func(x=5)
        some_func(x=5, y=10)

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
        self.assertEqual(str(pre_err), "x > 3: x was 1")

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
        self.assertEqual(str(pre_err), "x must not be small: x > 3: x was 1")

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
        self.assertEqual(str(pre_err), "some_condition: x was 1")

    def test_with_pathlib(self):
        @icontract.pre(lambda path: path.exists())
        def some_func(path: pathlib.Path) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(path=pathlib.Path("/doesnt/exist/test_contract"))
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("path.exists():\n"
                         "path was PosixPath('/doesnt/exist/test_contract')\n"
                         "path.exists() was False", str(pre_err))

    def test_with_multiple_comparators(self):
        @icontract.pre(lambda x: 0 < x < 3)
        def some_func(x: int) -> str:
            return str(x)

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=10)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual(str(pre_err), "0 < x < 3: x was 10")

    def test_with_stacked_decorators(self):
        def mydecorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                result = f(*args, **kwargs)
                return result

            return wrapped

        some_var = 100
        another_var = 0

        @mydecorator
        @icontract.pre(lambda x: x < some_var)
        @icontract.pre(lambda x: x > another_var)
        @mydecorator
        def some_func(x: int) -> str:
            return str(x)

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=0)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("x > another_var:\n" "another_var was 0\n" "x was 0", str(pre_err))

    def test_with_default_values(self):
        @icontract.pre(lambda a: a < 10)
        @icontract.pre(lambda b: b < 10)
        @icontract.pre(lambda c: c < 10)
        def some_func(a: int, b: int = 21, c: int = 22) -> int:
            return a + b

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(a=2)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("c < 10: c was 22", str(pre_err))

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(a=2, c=8)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("b < 10: b was 21", str(pre_err))

    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
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

    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
    def test_benchmark_when_disabled(self):
        @icontract.pre(lambda x: x > 3, enabled=False)
        def pow_with_pre(x: int, y: int) -> int:
            return x**y

        def pow_wo_pre(x: int, y: int) -> int:
            return x**y

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_with_pre(x=i, y=2)
        duration_with_pre = time.time() - start

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_wo_pre(x=i, y=2)
        duration_wo_pre = time.time() - start

        self.assertLess(duration_with_pre / duration_wo_pre, 1.2)

    def test_invalid_precondition_arguments(self):
        @icontract.pre(lambda b: b > 3)
        def some_function(a: int) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            some_function(a=13)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("The argument of the contract condition has not been set: b. Does the function define it?",
                         str(type_err))

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
        self.assertEqual(str(pre_err), "x > 3: x was 001")

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
        self.assertEqual("len(x) < 10:\n" "len(x) was 10000\n" "x was [0, 1, 2, ...]", str(pre_err))

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
        self.assertEqual("x > 3: x was 1", str(pre_err))

        # Test method with self
        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method_with_self()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("self.y > 10: self.y was 5", str(pre_err))

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
        self.assertEqual("self.b.x > 0:\n" "self was A()\n" "self.b was B(x=0)\n" "self.b.x was 0", str(pre_err))

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
        self.assertEqual("pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) is None:\n"
                         "gt_zero(self.b.c(x=0).x() + 12.2 * z) was True\n"
                         "pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) was PosixPath('True')\n"
                         "self was A()\n"
                         "self.b was B()\n"
                         "self.b.c(x=0) was C(x=0)\n"
                         "self.b.c(x=0).x() was 0\n"
                         "str(gt_zero(self.b.c(x=0).x() + 12.2 * z)) was 'True'\n"
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
        self.assertEqual("x < y + z:\n" "x was 100\n" "y was 4\n" "z was 5", str(pre_err))

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
        self.assertEqual("x < SOME_GLOBAL_CONSTANT:\n" "SOME_GLOBAL_CONSTANT was 10\n" "x was 100", str(pre_err))

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
        self.assertEqual("x < y + SOME_GLOBAL_CONSTANT:\n"
                         "SOME_GLOBAL_CONSTANT was 10\n"
                         "x was 100\n"
                         "y was 4", str(pre_err))

    def test_enabled(self):
        @icontract.pre(lambda x: x > 10, enabled=False)
        def some_func(x: int) -> int:
            return 123

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            result = some_func(x=0)
            self.assertEqual(123, result)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNone(pre_err)

    def test_property_getter(self):
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            @icontract.pre(lambda self: self._some_prop > 0)
            def some_prop(self) -> int:
                return self._some_prop

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self._some_prop > 0:\n'
                         'self was SomeClass\n'
                         'self._some_prop was -1', str(icontract_violation_error))

    def test_property_setter(self):
        class SomeClass:
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            @icontract.pre(lambda value: value > 0)
            def some_prop(self, value: int) -> None:
                pass

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = -1
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('value > 0: value was -1', str(icontract_violation_error))

    def test_property_deleter(self):
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            def some_prop(self) -> int:
                return self._some_prop

            @some_prop.deleter
            @icontract.pre(lambda self: self.some_prop > 0)
            def some_prop(self) -> None:
                pass

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.some_prop > 0:\nself was SomeClass\nself.some_prop was -1',
                         str(icontract_violation_error))


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
        self.assertEqual("result > x:\n" "result was -4\n" "x was 1", str(post_err))

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
        self.assertEqual("expected summation: result > x:\n" "result was -4\n" "x was 1", str(post_err))

    def test_with_stacked_decorators(self):
        def mydecorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                result = f(*args, **kwargs)
                return result

            return wrapped

        some_var = 1
        another_var = 2

        @mydecorator
        @icontract.post(lambda result, x: x < result + some_var)
        @icontract.post(lambda result, y: y > result + another_var)
        @mydecorator
        def some_func(x: int, y: int) -> int:
            return 100

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=0, y=10)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual("y > result + another_var:\n"
                         "another_var was 2\n"
                         "result was 100\n"
                         "y was 10", str(post_err))

    def test_with_default_values_outer(self):
        @icontract.post(lambda result, c: result % c == 0)
        @icontract.post(lambda result, b: result < b)
        def some_func(a: int, b: int = 21, c: int = 2) -> int:
            return a

        # Check first the outer post condition
        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(a=13)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual("result % c == 0:\n" "c was 2\n" "result was 13", str(post_err))

        # Check the inner post condition
        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(a=36)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual("result < b:\n" "b was 21\n" "result was 36", str(post_err))

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
        self.assertEqual("result > x: result was -0004, x was 00001", str(post_err))

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
        self.assertEqual("len(result) > x:\n"
                         "len(result) was 10000\n"
                         "result was [0, 1, 2, ...]\n"
                         "x was 10000", str(post_err))

    def test_only_result(self):
        @icontract.post(lambda result: result > 3)
        def some_func(x: int) -> int:
            return 0

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=10 * 1000)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNotNone(post_err)
        self.assertEqual("result > 3: result was 0", str(post_err))

    def test_enabled(self):
        @icontract.post(lambda x, result: x > result, enabled=False)
        def some_func(x: int) -> int:
            return 123

        post_err = None  # type: Optional[icontract.ViolationError]
        try:
            result = some_func(x=1234)
            self.assertEqual(123, result)
        except icontract.ViolationError as err:
            post_err = err

        self.assertIsNone(post_err)

    def test_invalid_postcondition_arguments(self):
        @icontract.post(lambda b, result: b > result)
        def some_function(a: int) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            some_function(a=13)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("The argument of the contract condition has not been set: b. Does the function define it?",
                         str(type_err))

    def test_postcondition_in_static_method(self):
        class SomeClass:
            @staticmethod
            @icontract.post(lambda result: result != 0)
            def some_func(x: int) -> int:
                return x

        result = SomeClass.some_func(x=1)
        self.assertEqual(1, result)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass.some_func(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('result != 0: result was 0', str(icontract_violation_error))

    def test_postcondition_in_class_method(self):
        class SomeClass:
            @classmethod
            @icontract.post(lambda result: result != 0)
            def some_func(cls: Type, x: int) -> int:
                return x

        result = SomeClass.some_func(x=1)
        self.assertEqual(1, result)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass.some_func(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('result != 0: result was 0', str(icontract_violation_error))

    def test_postcondition_in_abstract_static_method(self):
        class SomeAbstract(icontract.DBC):
            @staticmethod
            @icontract.post(lambda result: result != 0)
            def some_func(x: int) -> int:
                pass

        class SomeClass(SomeAbstract):
            @staticmethod
            def some_func(x: int) -> int:
                return x

        result = SomeClass.some_func(x=1)
        self.assertEqual(1, result)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass.some_func(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('result != 0: result was 0', str(icontract_violation_error))

    def test_postcondition_in_abstract_class_method(self):
        class Abstract(icontract.DBC):
            @classmethod
            @abc.abstractmethod
            @icontract.post(lambda result: result != 0)
            def some_func(cls: Type, x: int) -> int:
                pass

        class SomeClass(Abstract):
            @classmethod
            def some_func(cls: Type, x: int) -> int:
                return x

        result = SomeClass.some_func(x=1)
        self.assertEqual(1, result)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass.some_func(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('result != 0: result was 0', str(icontract_violation_error))

    def test_property_getter(self):
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            @icontract.post(lambda result: result > 0)
            def some_prop(self) -> int:
                return self._some_prop

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('result > 0: result was -1', str(icontract_violation_error))

    def test_property_setter(self):
        class SomeClass:
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            @icontract.post(lambda self: self.some_prop > 0)
            def some_prop(self, value: int) -> None:
                pass

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = -1
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.some_prop > 0:\nself was SomeClass\nself.some_prop was 0',
                         str(icontract_violation_error))

    def test_property_deleter(self):
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            def some_prop(self) -> int:
                return self._some_prop

            @some_prop.deleter
            @icontract.post(lambda self: self.some_prop > 0)
            def some_prop(self) -> None:
                pass

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('self.some_prop > 0:\nself was SomeClass\nself.some_prop was -1',
                         str(icontract_violation_error))


class TestSlow(unittest.TestCase):
    def test_slow_set(self):
        self.assertTrue(icontract.SLOW,
                        "icontract.SLOW was not set. Please check if you set the environment variable ICONTRACT_SLOW "
                        "before running this test.")


class TestInvariant(unittest.TestCase):
    def test_init_ok(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_method_ok(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(1000, inst.x)

    def test_magic_method_ok(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = 1000

        inst = SomeClass()
        inst()

        self.assertEqual(1000, inst.x)

    def test_class_method_ok(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @classmethod
            def some_class_method(cls) -> None:
                pass

        inst = SomeClass()
        self.assertEqual(100, inst.x)

    def test_protected_method_may_violate_inv(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A protected method is allowed to break the invariant.
            def _some_protected_method(self) -> None:
                self.x = -1

            def some_method(self) -> None:
                self._some_protected_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()

        self.assertEqual(10, inst.x)

    def test_inv_broken_before_protected_method(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A protected method can not expect the invariant to hold.
            def _some_protected_method(self) -> None:
                pass

            def some_method(self) -> None:
                self.x = -1
                self._some_protected_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_private_method_may_violate_inv(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A private method is allowed to break the invariant.
            def __some_private_method(self) -> None:
                self.x = -1

            def some_method(self) -> None:
                self.__some_private_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_inv_broken_before_private_method(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            # A private method can not expect the invariant to hold.
            def __some_private_method(self) -> None:
                pass

            def some_method(self) -> None:
                self.x = -1
                self.__some_private_method()
                self.x = 10

        inst = SomeClass()
        inst.some_method()
        self.assertEqual(10, inst.x)

    def test_init_checked(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "some instance"

        _ = SomeClass(x=1)

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual('self.x > 0:\n' 'self was some instance\n' 'self.x was 0', str(violation_err))

    def test_inv_as_precondition(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.x = -1
            inst.some_method()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_method_checked(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def some_method(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_magic_method_checked(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __call__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_multiple_invs_first_checked(self):
        @icontract.inv(lambda self: self.x > 0)
        @icontract.inv(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_multiple_invs_last_checked(self):
        @icontract.inv(lambda self: self.x > 0)
        @icontract.inv(lambda self: self.x < 10)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            _ = SomeClass()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x < 10:\n" "self was some instance\n" "self.x was 100", str(violation_err))

    def test_inv_checked_after_pre(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.pre(lambda y: y > 0)
            def some_method(self, y: int) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method(y=-1)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("y > 0: y was -1", str(violation_err))

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method(y=100)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_inv_ok_but_post_violated(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.post(lambda result: result > 0)
            def some_method(self) -> int:
                self.x = 10
                return -1

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result > 0: result was -1", str(violation_err))

    def test_inv_violated_but_post_ok(self):
        @icontract.inv(lambda self: self.x > 0)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

            @icontract.post(lambda result: result > 0)
            def some_method(self) -> int:
                self.x = -1
                return 10

            def __repr__(self) -> str:
                return "some instance"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            inst = SomeClass()
            inst.some_method()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was some instance\n" "self.x was -1", str(violation_err))

    def test_inv_with_invalid_arguments(self):
        val_err = None  # type: Optional[ValueError]
        try:

            @icontract.inv(lambda self, z: self.x > z)
            class _:
                def __init__(self) -> None:
                    self.x = 100

        except ValueError as err:
            val_err = err

        self.assertIsNotNone(val_err)
        self.assertEqual("Expected a condition function with a single argument 'self', but got: ['self', 'z']",
                         str(val_err))

    def test_inv_disabled(self):
        @icontract.inv(lambda self: self.x > 0, enabled=False)
        class SomeClass:
            def __init__(self) -> None:
                self.x = -1

        inst = SomeClass()
        self.assertEqual(-1, inst.x)

    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
    def test_benchmark_when_disabled(self):
        @icontract.inv(lambda self: bool(time.sleep(5)), enabled=False)
        class SomeClass:
            def __init__(self) -> None:
                self.x = 100

        class AnotherClass:
            def __init__(self) -> None:
                self.x = 100

        start = time.time()
        _ = SomeClass()
        duration_with_inv = time.time() - start

        start = time.time()
        _ = AnotherClass()
        duration_wo_inv = time.time() - start

        self.assertLess(duration_with_inv / duration_wo_inv, 1.2)

    def test_property_getter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_property_setter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            def some_prop(self, value: int) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_property_deleter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeClass:
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            def some_prop(self) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))


class TestPreconditionInheritance(unittest.TestCase):
    def test_inherited_without_implementation(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            pass

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=1000)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x < 100: x was 1000", str(violation_err))

    def test_inherited_with_implementation(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            def func(self, x: int) -> None:
                pass

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=1000)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x < 100: x was 1000", str(violation_err))

    def test_require_else(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.pre(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        b = B()
        b.func(x=4)
        b.func(x=9)

    def test_require_else_fails(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.pre(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        b = B()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=5)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x % 3 == 0: x was 5", str(violation_err))

    def test_triple_inheritance_wo_implementation(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            pass

        class C(B):
            pass

        c = C()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=1000)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x < 100: x was 1000", str(violation_err))

    def test_triple_inheritance_with_implementation(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            pass

        class C(B):
            def func(self, x: int) -> None:
                pass

        c = C()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=1000)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x < 100: x was 1000", str(violation_err))

    def test_triple_inheritance_with_require_else(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.pre(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        class C(B):
            @icontract.pre(lambda x: x % 5 == 0)
            def func(self, x: int) -> None:
                pass

        c = C()
        c.func(x=5)

    def test_triple_inheritance_with_require_else_fails(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.pre(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        class C(B):
            @icontract.pre(lambda x: x % 5 == 0)
            def func(self, x: int) -> None:
                pass

        c = C()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=7)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x % 5 == 0: x was 7", str(violation_err))

    def test_abstract_method_not_implemented(self):
        # pylint: disable=abstract-method
        class A(icontract.DBC):
            @icontract.pre(lambda x: x > 0)
            @abc.abstractmethod
            def func(self, x: int) -> int:
                pass

        class B(A):
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            _ = B()
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("Can't instantiate abstract class B with abstract methods func", str(type_err))

    def test_abstract_method(self):
        class A(icontract.DBC):
            @icontract.pre(lambda x: x > 0)
            @abc.abstractmethod
            def func(self, x: int) -> int:
                pass

        class B(A):
            def func(self, x: int) -> int:
                return 1000

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=-1)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x > 0: x was -1", str(violation_err))


class TestPostconditionInheritance(unittest.TestCase):
    def test_inherited_without_implementation(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            def func(self) -> int:
                return 1000

        class B(A):
            pass

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 1000", str(violation_err))

    def test_inherited_with_modified_implementation(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            def func(self) -> int:
                return 1000

        class B(A):
            def func(self) -> int:
                return 10000

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 10000", str(violation_err))

    def test_ensure_then(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 6

        b = B()
        b.func()

    def test_ensure_then_fails_in_base(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 3

        b = B()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result % 2 == 0: result was 3", str(violation_err))

    def test_ensure_then_fails_in_child(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result % 2 == 0)
            def func(self) -> int:
                return 10

        class B(A):
            @icontract.post(lambda result: result % 3 == 0)
            def func(self) -> int:
                return 2

        b = B()

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result % 3 == 0: result was 2", str(violation_err))

    def test_abstract_method_not_implemented(self):
        # pylint: disable=abstract-method
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            @abc.abstractmethod
            def func(self) -> int:
                pass

        class B(A):
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            _ = B()
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("Can't instantiate abstract class B with abstract methods func", str(type_err))

    def test_abstract_method(self):
        class A(icontract.DBC):
            @icontract.post(lambda result: result < 100)
            @abc.abstractmethod
            def func(self) -> int:
                pass

        class B(A):
            def func(self) -> int:
                return 1000

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("result < 100: result was 1000", str(violation_err))

    def test_count_checks(self):
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.inv(lambda self: inc())
        class SomeClass:
            def __init__(self) -> None:
                pass

            def some_func(self) -> None:
                return

        inst = SomeClass()
        self.assertEqual(1, Increment.count)  # Invariant needs to be checked once after the initialization.

        inst.some_func()
        self.assertEqual(3, Increment.count)  # Invariant needs to be checked before and after some_func.

    def test_count_checks_in_slot_wrappers(self):
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.inv(lambda self: inc())
        class SomeClass:
            pass

        inst = SomeClass()
        self.assertEqual(1, Increment.count)  # Invariant needs to be checked once after the initialization.

        _ = str(inst)
        self.assertEqual(3, Increment.count)  # Invariant needs to be checked before and after __str__.


class TestInvariantInheritance(unittest.TestCase):
    def test_inherited(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            def func(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "instance of A"

        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was instance of B\n" "self.x was -1", str(violation_err))

    def test_inherited_fails_in_child(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            def func(self) -> None:
                self.x = 100

            def __repr__(self) -> str:
                return "instance of A"

        class B(A):
            def func(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "instance of B"

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was instance of B\n" "self.x was -1", str(violation_err))

    def test_additional_invariant_that_fails_in_childs_init(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "instance of A"

        @icontract.inv(lambda self: self.x > 100)
        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 100:\n" "self was instance of B\n" "self.x was 10", str(violation_err))

    def test_func_fails_in_child(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 1000

            def func(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "instance of A"

        @icontract.inv(lambda self: self.x > 100)
        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 100:\n" "self was instance of B\n" "self.x was 10", str(violation_err))

    def test_triple_inheritance(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            def func(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "instance of A"

        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

        class C(B):
            def __repr__(self) -> str:
                return "instance of C"

        c = C()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            c.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was instance of C\n" "self.x was -1", str(violation_err))

    def test_with_abstract_method(self):
        @icontract.inv(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            @abc.abstractmethod
            def func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "instance of A"

        class B(A):
            def func(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "instance of B"

        b = B()
        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("self.x > 0:\n" "self was instance of B\n" "self.x was -1", str(violation_err))

    def test_count_checks(self):
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.inv(lambda self: inc())
        class A(icontract.DBC):
            def __repr__(self) -> str:
                return "instance of A"

            def some_func(self):
                return 1

        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

            def some_func(self):
                return 2

        inst = B()
        self.assertEqual(1, Increment.count, "Invariant is expected to run only once at the initializer.")

        inst.some_func()
        self.assertEqual(3, Increment.count, "Invariant is expected to run before and after the method call.")


class TestInvariantInheritanceWithProperties(unittest.TestCase):
    def test_inherited_getter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

        class SomeClass(SomeBase):
            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_inherited_setter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            def some_prop(self, value: int) -> None:
                self.toggled = True

        class SomeClass(SomeBase):
            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_inherited_deleter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            def some_prop(self) -> None:
                self.toggled = True

        class SomeClass(SomeBase):
            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_inherited_invariant_on_getter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_inherited_invariant_on_setter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            def some_prop(self, value: int) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))

    def test_inherited_invariant_on_deleter(self):
        @icontract.inv(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            def some_prop(self) -> None:
                self.toggled = True

            def __repr__(self):
                return self.__class__.__name__

        some_inst = SomeClass()

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not self.toggled:\n'
                         'self was SomeClass\n'
                         'self.toggled was True', str(icontract_violation_error))


if __name__ == '__main__':
    unittest.main()
