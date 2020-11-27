# pylint: disable=missing-docstring
# pylint: disable=no-self-use
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=no-member

import textwrap
import unittest
from typing import Optional

import typeguard

import icontract
import tests.error


class TestPrecondition(unittest.TestCase):
    def test_both_precondition_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.require(lambda x: x > 0)
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

        @typeguard.typechecked
        @icontract.require(lambda x: x.is_ok())
        def some_func(x: A) -> None:
            pass

        b = B()
        type_error = None  # type: Optional[TypeError]
        try:
            some_func(b)
        except TypeError as err:
            type_error = err

        expected = 'type of argument "x" must be '
        self.assertEqual(expected, str(type_error)[:len(expected)])

    def test_precondition_fails_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(-10)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('x > 0: x was -10', tests.error.wo_mandatory_location(str(violation_error)))


class TestInvariant(unittest.TestCase):
    def test_both_invariant_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x > 0)
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

        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x.is_ok())
        class C:
            def __init__(self, a: A) -> None:
                self.a = a

        b = B()

        type_error = None  # type: Optional[TypeError]
        try:
            _ = C(a=b)  # type: ignore
        except TypeError as err:
            type_error = err

        expected = 'type of argument "a" must be '
        self.assertEqual(expected, str(type_error)[:len(expected)])

    def test_invariant_fails_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x > 0)
        class A:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "an instance of A"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = A(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent('''\
                self.x > 0:
                self was an instance of A
                self.x was -1'''), tests.error.wo_mandatory_location(str(violation_error)))


class TestInheritance(unittest.TestCase):
    def test_both_invariant_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x > 0)
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

        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x.is_ok())
        class C(icontract.DBC):
            def __init__(self, a: A) -> None:
                self.a = a

        class D(C):
            pass

        b = B()

        type_error = None  # type: Optional[TypeError]
        try:
            _ = D(a=b)  # type: ignore
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)

        expected = 'type of argument "a" must be '
        self.assertEqual(expected, str(type_error)[:len(expected)])

    def test_invariant_fails_and_typeguard_ok(self) -> None:
        @typeguard.typechecked
        @icontract.invariant(lambda self: self.x > 0)
        class A:
            def __init__(self, x: int) -> None:
                self.x = x

            def __repr__(self) -> str:
                return "an instance of A"

        class B(A):
            def __repr__(self) -> str:
                return "an instance of B"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent('''\
                self.x > 0:
                self was an instance of B
                self.x was -1'''), tests.error.wo_mandatory_location(str(violation_error)))


if __name__ == '__main__':
    unittest.main()
