# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument

import textwrap
import unittest
from typing import Optional

import typeguard

import icontract
import tests.error


class TestPrecondition(unittest.TestCase):
    def test_both_precondition_and_typeguard_ok(self) -> None:
        @icontract.require(lambda x: x > 0)
        @typeguard.typechecked
        def some_func(x: int) -> None:
            pass

        some_func(1)

    def test_precondition_ok_and_typeguard_fails(self) -> None:
        class A:
            def is_ok(self) -> bool:
                return True

        class B:
            def is_ok(self) -> bool:
                return True

        @icontract.require(lambda x: x.is_ok())
        @typeguard.typechecked
        def some_func(x: A) -> None:
            pass

        b = B()
        type_check_error = None  # type: Optional[typeguard.TypeCheckError]
        try:
            some_func(b)  # type: ignore
        except typeguard.TypeCheckError as err:
            type_check_error = err

        self.assertIsNotNone(type_check_error)

    def test_precondition_fails_and_typeguard_ok(self) -> None:
        @icontract.require(lambda x: x > 0)
        @typeguard.typechecked
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(-10)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x > 0: x was -10", tests.error.wo_mandatory_location(str(violation_error))
        )


class TestInvariant(unittest.TestCase):
    def test_both_invariant_and_typeguard_ok(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @typeguard.typechecked
        class A:
            def __init__(self, x: int) -> None:
                self.x = x

            def do_something(self, y: int) -> None:
                self.x += y

        a = A(x=1)
        a.do_something(y=2)

    def test_invariant_ok_and_typeguard_fails(self) -> None:
        class A:
            def is_ok(self) -> bool:
                return True

        class B:
            def is_ok(self) -> bool:
                return True

        @icontract.invariant(lambda self: self.x.is_ok())
        @typeguard.typechecked
        class C:
            def __init__(self, a: A) -> None:
                self.a = a

        b = B()

        type_check_error = None  # type: Optional[typeguard.TypeCheckError]
        try:
            _ = C(a=b)  # type: ignore
        except typeguard.TypeCheckError as err:
            type_check_error = err

        self.assertIsNotNone(type_check_error)

    def test_invariant_fails_and_typeguard_ok(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @typeguard.typechecked
        class A:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = A(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 0:
                self was an instance of A
                self.x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestInheritance(unittest.TestCase):
    def test_both_invariant_and_typeguard_ok(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @typeguard.typechecked
        class A(icontract.DBC):
            def __init__(self, x: int) -> None:
                self.x = x

            def do_something(self, y: int) -> None:
                self.x += y

        class B(A):
            pass

        b = B(x=1)
        b.do_something(y=2)

    def test_invariant_ok_and_typeguard_fails(self) -> None:
        class A:
            def is_ok(self) -> bool:
                return True

        class B:
            def is_ok(self) -> bool:
                return True

        @icontract.invariant(lambda self: self.x.is_ok())
        @typeguard.typechecked
        class C(icontract.DBC):
            def __init__(self, a: A) -> None:
                self.a = a

        class D(C):
            pass

        b = B()

        type_check_error = None  # type: Optional[typeguard.TypeCheckError]
        try:
            _ = D(a=b)  # type: ignore
        except typeguard.TypeCheckError as err:
            type_check_error = err

        self.assertIsNotNone(type_check_error)

    def test_invariant_fails_and_typeguard_ok(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @typeguard.typechecked
        class A:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        class B(A):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 0:
                self was an instance of B
                self.x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


if __name__ == "__main__":
    unittest.main()
