# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda

import functools
import pathlib
import textwrap
import time
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract
from icontract._globals import CallableT
import tests.error
import tests.mock


class TestOK(unittest.TestCase):
    def test_that_it_works(self) -> None:
        @icontract.require(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        some_func(x=5)
        some_func(x=5, y=10)


class TestViolation(unittest.TestCase):
    def test_only_with_condition_arg(self) -> None:
        @icontract.require(lambda x: x > 3)
        def some_func(x: int, y: int = 5) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > 3:
                x was 1
                y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_description(self) -> None:
        @icontract.require(lambda x: x > 3, "x must not be small")
        def some_func(x: int, y: int = 5) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x must not be small: x > 3:
                x was 1
                y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_condition_as_function(self) -> None:
        def some_condition(x: int) -> bool:
            return x > 3

        @icontract.require(some_condition)
        def some_func(x: int, y: int = 5) -> str:
            return str(x)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                some_condition:
                x was 1
                y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_condition_as_function_with_default_argument_value(self) -> None:
        def some_condition(x: int, y: int = 0) -> bool:
            return x > y

        @icontract.require(some_condition)
        def some_func(x: int) -> None:
            pass

        # Valid call
        some_func(x=1)

        # Invalid call
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "some_condition: x was -1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_condition_as_function_with_default_argument_value_set(self) -> None:
        def some_condition(x: int, y: int = 0) -> bool:
            return x > y

        @icontract.require(some_condition)
        def some_func(x: int, y: int) -> None:
            pass

        # Valid call
        some_func(x=3, y=1)

        # Invalid call
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=-1, y=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                some_condition:
                x was -1
                y was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_pathlib(self) -> None:
        @icontract.require(lambda path: path.exists())
        def some_func(path: pathlib.Path) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(path=pathlib.Path("/doesnt/exist/test_contract"))
        except icontract.ViolationError as err:
            violation_error = err

        # This dummy path is necessary to obtain the class name.
        dummy_path = pathlib.Path("/also/doesnt/exist")

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                path.exists():
                path was {}('/doesnt/exist/test_contract')
                path.exists() was False"""
            ).format(dummy_path.__class__.__name__),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_multiple_comparators(self) -> None:
        @icontract.require(lambda x: 0 < x < 3)
        def some_func(x: int) -> str:
            return str(x)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=10)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "0 < x < 3: x was 10",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_stacked_decorators(self) -> None:
        def mydecorator(f: CallableT) -> CallableT:
            @functools.wraps(f)
            def wrapped(*args, **kwargs):  # type: ignore
                result = f(*args, **kwargs)
                return result

            return wrapped  # type: ignore

        some_var = 100
        another_var = 0

        @mydecorator
        @icontract.require(lambda x: x < some_var)
        @icontract.require(lambda x: x > another_var)
        @mydecorator
        def some_func(x: int) -> str:
            return str(x)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=0)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > another_var:
                another_var was 0
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_default_values(self) -> None:
        @icontract.require(lambda a: a < 10)
        @icontract.require(lambda b: b < 10)
        @icontract.require(lambda c: c < 10)
        def some_func(a: int, b: int = 21, c: int = 22) -> int:
            return a + b

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(a=2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                c < 10:
                a was 2
                b was 21
                c was 22"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

        violation_error = None
        try:
            some_func(a=2, c=8)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                b < 10:
                a was 2
                b was 21
                c was 8"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestBenchmark(unittest.TestCase):
    @unittest.skip(
        "Skipped the benchmark, execute manually on a prepared benchmark machine."
    )
    def test_enabled(self) -> None:
        @icontract.require(lambda x: x > 3)
        def pow_with_pre(x: int, y: int) -> int:
            result = x**y
            assert isinstance(result, int)
            return result

        def pow_wo_pre(x: int, y: int) -> int:
            if x <= 3:
                raise ValueError("precondition")

            result = x**y
            assert isinstance(result, int)
            return result

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_with_pre(x=i, y=2)
        duration_with_pre = time.time() - start

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_wo_pre(x=i, y=2)
        duration_wo_pre = time.time() - start

        self.assertLess(duration_with_pre / duration_wo_pre, 6)

    @unittest.skip(
        "Skipped the benchmark, execute manually on a prepared benchmark machine."
    )
    def test_disabled(self) -> None:
        @icontract.require(lambda x: x > 3, enabled=False)
        def pow_with_pre(x: int, y: int) -> int:
            result = x**y
            assert isinstance(result, int)
            return result

        def pow_wo_pre(x: int, y: int) -> int:
            result = x**y
            assert isinstance(result, int)
            return result

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_with_pre(x=i, y=2)
        duration_with_pre = time.time() - start

        start = time.time()
        for i in range(5, 10 * 1000):
            pow_wo_pre(x=i, y=2)
        duration_wo_pre = time.time() - start

        self.assertLess(duration_with_pre / duration_wo_pre, 1.2)


class TestError(unittest.TestCase):
    def test_as_type(self) -> None:
        @icontract.require(lambda x: x > 0, error=ValueError)
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual(
            "x > 0: x was 0", tests.error.wo_mandatory_location(str(value_error))
        )

    def test_as_function(self) -> None:
        @icontract.require(
            lambda x: x > 0, error=lambda x: ValueError("x non-negative")
        )
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual("x non-negative", str(value_error))

    def test_as_function_with_outer_scope(self) -> None:
        z = 42

        @icontract.require(
            lambda x: x > 0,
            error=lambda x: ValueError("x non-negative, z: {}".format(z)),
        )
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual("x non-negative, z: 42", str(value_error))

    def test_with_empty_args(self) -> None:
        @icontract.require(
            lambda x: x > 0, error=lambda: ValueError("x must be positive")
        )
        def some_func(x: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual("x must be positive", str(value_error))

    def test_with_different_args_from_condition(self) -> None:
        @icontract.require(
            lambda x: x > 0,
            error=lambda x, y: ValueError("x is {}, y is {}".format(x, y)),
        )
        def some_func(x: int, y: int) -> int:
            return 0

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=0, y=10)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertIsInstance(value_error, ValueError)
        self.assertEqual("x is 0, y is 10", str(value_error))


class TestToggling(unittest.TestCase):
    def test_enabled(self) -> None:
        @icontract.require(lambda x: x > 10, enabled=False)
        def some_func(x: int) -> int:
            return 123

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            result = some_func(x=0)
            self.assertEqual(123, result)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNone(violation_error)


class TestInClass(unittest.TestCase):
    def test_instance_method(self) -> None:
        class A:
            def __init__(self) -> None:
                self.y = 5

            @icontract.require(lambda x: x > 3)
            def some_method(self, x: int) -> int:
                return self.y

            @icontract.require(lambda self: self.y > 10)
            def some_method_with_self(self) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        a = A()

        # Test method without self
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_method(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > 3:
                self was an instance of A
                x was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

        # Test method with self
        violation_error = None
        try:
            a.some_method_with_self()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.y > 10:
                self was an instance of A
                self.y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_unbound_instance_method_with_self_as_kwarg(self) -> None:
        class A:
            def __init__(self) -> None:
                self.y = 5

            @icontract.require(lambda self: self.y > 10)
            def some_method_with_self(self) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        a = A()

        func = a.some_method_with_self.__func__  # type: ignore

        violation_error = None
        try:
            func(self=a)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.y > 10:
                self was an instance of A
                self.y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_getter(self) -> None:
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            @icontract.require(lambda self: self._some_prop > 0)
            def some_prop(self) -> int:
                return self._some_prop

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self._some_prop > 0:
                self was an instance of SomeClass
                self._some_prop was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_setter(self) -> None:
        class SomeClass:
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            @icontract.require(lambda value: value > 0)
            def some_prop(self, value: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = -1
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                value > 0:
                self was an instance of SomeClass
                value was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_deleter(self) -> None:
        class SomeClass:
            def __init__(self) -> None:
                self._some_prop = -1

            @property
            def some_prop(self) -> int:
                return self._some_prop

            @some_prop.deleter
            @icontract.require(lambda self: self.some_prop > 0)
            def some_prop(self) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.some_prop > 0:
                self was an instance of SomeClass
                self.some_prop was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestInvalid(unittest.TestCase):
    def test_unexpected_precondition_arguments(self) -> None:
        @icontract.require(lambda b: b > 3)
        def some_function(a: int) -> None:  # pylint: disable=unused-variable
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            some_function(a=13)
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        self.assertEqual(
            "The argument(s) of the contract condition have not been set: ['b']. "
            "Does the original function define them? Did you supply them in the call?",
            tests.error.wo_mandatory_location(str(type_err)),
        )

    def test_error_with_invalid_arguments(self) -> None:
        @icontract.require(
            lambda x: x > 0,
            error=lambda x, z: ValueError("x is {}, y is {}".format(x, z)),
        )
        def some_func(x: int, y: int) -> int:
            return 0

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(x=0, y=10)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual(
            "The argument(s) of the contract error have not been set: ['z']. "
            "Does the original function define them? Did you supply them in the call?",
            tests.error.wo_mandatory_location(str(type_error)),
        )

    def test_no_boolyness(self) -> None:
        @icontract.require(lambda: tests.mock.NumpyArray([True, False]))
        def some_func() -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func()
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual(
            "Failed to negate the evaluation of the condition.",
            tests.error.wo_mandatory_location(str(value_error)),
        )

    def test_unexpected_positional_argument(self) -> None:
        @icontract.require(lambda: True)
        def some_func() -> None:
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(0)  # type: ignore
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertRegex(
            str(type_error),
            r"^([a-zA-Z_0-9<>.]+\.)?some_func\(\) takes 0 positional arguments but 1 was given$",
        )

    def test_unexpected_keyword_argument(self) -> None:
        @icontract.require(lambda: True)
        def some_func() -> None:
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            # pylint: disable=unexpected-keyword-arg
            some_func(x=0)  # type: ignore
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertRegex(
            str(type_error),
            r"^([a-zA-Z_0-9<>.]+\.)?some_func\(\) got an unexpected keyword argument 'x'$",
        )


if __name__ == "__main__":
    unittest.main()
