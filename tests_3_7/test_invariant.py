# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument

import dataclasses
import textwrap
import unittest
from typing import NamedTuple, Optional  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_on_dataclass(self) -> None:
        @icontract.invariant(lambda self: self.first > 0)
        @dataclasses.dataclass
        class RightHalfPlanePoint:
            first: int
            second: int

        _ = RightHalfPlanePoint(1, 0)

        self.assertEqual(
            "Create and return a new object.  See help(type) for accurate signature.",
            RightHalfPlanePoint.__new__.__doc__,
        )

    def test_on_dataclass_with_field(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        @dataclasses.dataclass
        class Foo:
            x: int = dataclasses.field(default=42)

        _ = Foo()


class TestViolation(unittest.TestCase):
    def test_on_dataclass(self) -> None:
        @icontract.invariant(lambda self: self.second > 0)
        @icontract.invariant(lambda self: self.first > 0)
        @dataclasses.dataclass
        class RightHalfPlanePoint:
            first: int
            second: int

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = RightHalfPlanePoint(1, -1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
            self.second > 0:
            self was TestViolation.test_on_dataclass.<locals>.RightHalfPlanePoint(first=1, second=-1)
            self.second was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_on_dataclass_with_field(self) -> None:
        @icontract.invariant(lambda self: self.x < 0)
        @dataclasses.dataclass
        class Foo:
            x: int = dataclasses.field(default=-1)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = Foo(3)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
            self.x < 0:
            self was TestViolation.test_on_dataclass_with_field.<locals>.Foo(x=3)
            self.x was 3"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_on_dataclass_with_field_default_violating(self) -> None:
        @icontract.invariant(lambda self: self.x < 0)
        @dataclasses.dataclass
        class Foo:
            x: int = dataclasses.field(default=42)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = Foo()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
            self.x < 0:
            self was TestViolation.test_on_dataclass_with_field_default_violating.<locals>.Foo(x=42)
            self.x was 42"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestCheckOn(unittest.TestCase):
    def test_setattr_with_dataclass(self) -> None:
        @icontract.invariant(
            lambda self: self.x > 0, check_on=icontract.InvariantCheckEvent.SETATTR
        )
        @dataclasses.dataclass
        class A:
            x: int = 10

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        a = A()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.x = -1
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


if __name__ == "__main__":
    unittest.main()
