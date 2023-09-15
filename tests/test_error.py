# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable

import unittest
from typing import Optional

import icontract

import tests.error


class TestNoneSpecified(unittest.TestCase):
    def test_that_it_works(self) -> None:
        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=-1)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None
        self.assertEqual(
            "x > 0: x was -1", tests.error.wo_mandatory_location(str(violation_error))
        )


class TestSpecifiedAsFunction(unittest.TestCase):
    def test_lambda(self) -> None:
        @icontract.require(
            lambda x: x > 0,
            error=lambda x: ValueError("x must be positive: {}".format(x)),
        )
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("x must be positive: -1", str(value_error))

    def test_separate_function(self) -> None:
        def error_func(x: int) -> ValueError:
            return ValueError("x must be positive: {}".format(x))

        @icontract.require(lambda x: x > 0, error=error_func)
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("x must be positive: -1", str(value_error))

    def test_separate_method(self) -> None:
        class Errorer:
            def error_func(self, x: int) -> ValueError:
                return ValueError("x must be positive: {}".format(x))

        errorer = Errorer()

        @icontract.require(lambda x: x > 0, error=errorer.error_func)
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("x must be positive: -1", str(value_error))

    def test_report_if_result_is_not_base_exception(self) -> None:
        @icontract.require(lambda x: x > 0, error=lambda x: "x must be positive")  # type: ignore
        def some_func(x: int) -> None:
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(x=-1)
        except TypeError as err:
            type_error = err

        assert type_error is not None
        self.assertRegex(
            str(type_error),
            r"^The exception returned by the contract's error <function .*> does not inherit from BaseException\.$",
        )


class TestSpecifiedAsType(unittest.TestCase):
    def test_valid_exception(self) -> None:
        @icontract.require(lambda x: x > 0, error=ValueError)
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual(
            "x > 0: x was -1", tests.error.wo_mandatory_location(str(value_error))
        )


class TestSpecifiedAsInstance(unittest.TestCase):
    def test_valid_exception(self) -> None:
        @icontract.require(lambda x: x > 0, error=ValueError("negative x"))
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("negative x", str(value_error))

    def test_repeated_raising(self) -> None:
        @icontract.require(lambda x: x > 0, error=ValueError("negative x"))
        def some_func(x: int) -> None:
            pass

        value_error = None  # type: Optional[ValueError]
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("negative x", str(value_error))

        # Repeat
        value_error = None
        try:
            some_func(x=-1)
        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertEqual("negative x", str(value_error))


class TestSpecifiedAsInvalidType(unittest.TestCase):
    def test_in_precondition(self) -> None:
        class A:
            pass

        value_error = None  # type: Optional[ValueError]
        try:

            @icontract.require(lambda x: x > 0, error=A)  # type: ignore
            def some_func(x: int) -> None:
                pass

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"The error of the contract is given as a type, "
            r"but the type does not inherit from BaseException: <class .*\.A'>",
        )

    def test_in_postcondition(self) -> None:
        class A:
            pass

        value_error = None  # type: Optional[ValueError]
        try:

            @icontract.ensure(lambda result: result > 0, error=A)  # type: ignore
            def some_func() -> int:
                return -1

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"The error of the contract is given as a type, "
            r"but the type does not inherit from BaseException: <class .*\.A'>",
        )

    def test_in_invariant(self) -> None:
        value_error = None  # type: Optional[ValueError]
        try:

            class A:
                pass

            @icontract.invariant(lambda self: self.x > 0, error=A)  # type: ignore
            class B:
                def __init__(self) -> None:
                    self.x = -1

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"The error of the contract is given as a type, "
            r"but the type does not inherit from BaseException: <class .*\.A'>",
        )


class TestSpecifiedAsInstanceOfInvalidType(unittest.TestCase):
    def test_in_precondition(self) -> None:
        class A:
            def __init__(self, msg: str) -> None:
                self.msg = msg

        value_error = None  # type: Optional[ValueError]
        try:

            @icontract.require(lambda x: x > 0, error=A("something went wrong"))  # type: ignore
            def some_func(x: int) -> None:
                pass

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"^The error of the contract must be either a callable \(a function or a method\), "
            r"a class \(subclass of BaseException\) or an instance of BaseException, "
            r"but got: <.*\.A object at 0x.*>$",
        )

    def test_in_postcondition(self) -> None:
        class A:
            def __init__(self, msg: str) -> None:
                self.msg = msg

        value_error = None  # type: Optional[ValueError]
        try:

            @icontract.ensure(lambda result: result > 0, error=A("something went wrong"))  # type: ignore
            def some_func() -> int:
                return -1

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"^The error of the contract must be either a callable \(a function or a method\), "
            r"a class \(subclass of BaseException\) or an instance of BaseException, "
            r"but got: <.*\.A object at 0x.*>$",
        )

    def test_in_invariant(self) -> None:
        class A:
            def __init__(self, msg: str) -> None:
                self.msg = msg

        value_error = None  # type: Optional[ValueError]
        try:

            @icontract.invariant(lambda self: self.x > 0, error=A("something went wrong"))  # type: ignore
            class B:
                def __init__(self) -> None:
                    self.x = -1

        except ValueError as err:
            value_error = err

        assert value_error is not None
        self.assertRegex(
            str(value_error),
            r"^The error of the contract must be either a callable \(a function or a method\), "
            r"a class \(subclass of BaseException\) or an instance of BaseException, "
            r"but got: <.*\.A object at 0x.*>$",
        )


if __name__ == "__main__":
    unittest.main()
