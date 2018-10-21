# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-self-use
# pylint: disable=unnecessary-lambda

import functools
import pathlib
import reprlib
import time
import unittest
from typing import Optional, List  # pylint: disable=unused-import

import icontract

SOME_GLOBAL_CONSTANT = 10


class TestOK(unittest.TestCase):
    def test_that_it_works(self):
        @icontract.pre(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        some_func(x=5)
        some_func(x=5, y=10)


class TestViolation(unittest.TestCase):
    def test_only_with_condition_arg(self):
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

    def test_with_description(self):
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

    def test_condition_as_function(self):
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


class TestBenchmark(unittest.TestCase):
    @unittest.skip("Skipped the benchmark, execute manually on a prepared benchmark machine.")
    def test_enabled(self):
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
    def test_disabled(self):
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


class TestRepr(unittest.TestCase):
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


class TestError(unittest.TestCase):
    def test_as_type(self):
        @icontract.pre(lambda x: x > 0, error=ValueError)
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x > 0: x was 0', str(value_error))

    def test_as_function(self):
        @icontract.pre(lambda x: x > 0, error=lambda x: ValueError("x non-negative"))
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x non-negative', str(value_error))

    def test_as_function_with_outer_scope(self):
        z = 42

        @icontract.pre(lambda x: x > 0, error=lambda x: ValueError("x non-negative, z: {}".format(z)))
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x non-negative, z: 42', str(value_error))

    def test_with_empty_args(self):
        @icontract.pre(lambda x: x > 0, error=lambda: ValueError("x must be positive"))
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x must be positive', str(value_error))

    def test_with_different_args_from_condition(self):
        @icontract.pre(lambda x: x > 0, error=lambda x, y: ValueError("x is {}, y is {}".format(x, y)))
        def some_func(x: int, y: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0, y=10)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual('x is 0, y is 10', str(value_error))


class TestToggling(unittest.TestCase):
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


class TestInClass(unittest.TestCase):
    def test_instance_method(self):
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

    def test_getter(self):
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

    def test_setter(self):
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

    def test_deleter(self):
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


class TestInvalid(unittest.TestCase):
    def test_unexpected_precondition_arguments(self):
        @icontract.pre(lambda b: b > 3)
        def some_function(a: int) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            some_function(a=13)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual("The argument(s) of the precondition have not been set: ['b']. "
                         "Does the original function define them?", str(type_err))

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

    def test_error_with_invalid_arguments(self):
        @icontract.pre(lambda x: x > 0, error=lambda x, z: ValueError("x is {}, y is {}".format(x, z)))
        def some_func(x: int, y: int) -> int:
            return 0

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(x=0, y=10)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual("The argument(s) of the precondition error have not been set: ['z']. "
                         "Does the original function define them?", str(type_error))


if __name__ == '__main__':
    unittest.main()
