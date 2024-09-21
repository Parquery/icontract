# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=unused-argument

import abc
import textwrap
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_count_checks(self) -> None:
        class Increment:
            count = 0

            def __call__(self) -> bool:
                Increment.count += 1
                return True

        inc = Increment()

        @icontract.invariant(lambda self: inc())
        class A(icontract.DBC):
            def __repr__(self) -> str:
                return "instance of A"

            def some_func(self) -> int:
                return 1

        class B(A):
            def __repr__(self) -> str:
                return "instance of B"

            def some_func(self) -> int:
                return 2

        inst = B()
        self.assertEqual(
            1,
            Increment.count,
            "Invariant is expected to run only once at the initializer.",
        )

        inst.some_func()
        self.assertEqual(
            3,
            Increment.count,
            "Invariant is expected to run before and after the method call.",
        )

    def test_level_1_inheritance_of_invariants_does_not_leak_to_parents(self) -> None:
        # NOTE (mristin):
        # This is a regression test for:
        # https://github.com/Parquery/icontract/issues/295
        #
        # The invariants added to a child class were unexpectedly leaked back to
        # the parent class.

        @icontract.invariant(lambda: True)
        class Base(icontract.DBC):
            def do_something(self) -> None:
                pass

            def __repr__(self) -> str:
                return "instance of {}".format(self.__class__.__name__)

        @icontract.invariant(lambda: False)
        class Derived(Base):
            pass

        Base()

        # NOTE (mristin):
        # This produced an unexpected violation error.
        Base().do_something()

        had_violation_error = False
        try:
            Derived()
        except icontract.ViolationError:
            had_violation_error = True

        assert had_violation_error

    def test_level_2_inheritance_of_invariants_does_not_leak_to_parents(self) -> None:
        # NOTE (mristin):
        # This is a regression test for:
        # https://github.com/Parquery/icontract/issues/295
        #
        # The invariants added to a child class were unexpectedly leaked back to
        # the parent class.

        @icontract.invariant(lambda: True)
        class Base(icontract.DBC):
            def do_something(self) -> None:
                pass

            def __repr__(self) -> str:
                return "instance of {}".format(self.__class__.__name__)

        @icontract.invariant(lambda: True)
        class Derived(Base):
            pass

        @icontract.invariant(lambda: False)
        class DerivedDerived(Base):
            pass

        Base()
        Base().do_something()
        Derived()

        had_violation_error = False
        try:
            DerivedDerived()
        except icontract.ViolationError:
            had_violation_error = True

        assert had_violation_error

    # noinspection PyUnusedLocal
    def test_level_3_inheritance_of_invariants_does_not_leak_to_parents(self) -> None:
        # NOTE (mristin):
        # This is a regression test for:
        # https://github.com/Parquery/icontract/issues/295
        #
        # The invariants added to a child class were unexpectedly leaked back to
        # the parent class.

        class A(icontract.DBC):
            def do_something(self) -> None:
                pass

            def __repr__(self) -> str:
                return "instance of {}".format(self.__class__.__name__)

        @icontract.invariant(lambda: True)
        class B(A):
            pass

        # NOTE (mristin):
        # CFalse should not in any way influence A, B and CTrue, but it did due to
        # a bug.
        @icontract.invariant(lambda: False)
        class CFalse(B):  # pylint: disable=unused-variable
            pass

        @icontract.invariant(lambda: True)
        class CTrue(B):
            pass

        A()

        CTrue()

        A().do_something()

        # NOTE (mristin):
        # This produced an unexpected violation error.
        CTrue().do_something()


class TestViolation(unittest.TestCase):
    def test_inherited(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
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
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 0:
                self was instance of B
                self.x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_violated_in_child(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
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
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 0:
                self was instance of B
                self.x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_additional_invariant_violated_in_childs_init(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "an instance of A"

        @icontract.invariant(lambda self: self.x > 100)
        class B(A):
            def __repr__(self) -> str:
                return "an instance of B"

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 100:
                self was an instance of B
                self.x was 10"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_method_violates_in_child(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 1000

            def some_method(self) -> None:
                self.x = 10

            def __repr__(self) -> str:
                return "an instance of A"

        @icontract.invariant(lambda self: self.x > 100)
        class B(A):
            def __repr__(self) -> str:
                return "an instance of B"

        b = B()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.some_method()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 100:
                self was an instance of B
                self.x was 10"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_triple_inheritance(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
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
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            c.func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.x > 0:
                self was instance of C
                self.x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_abstract_method(self) -> None:
        @icontract.invariant(lambda self: self.x > 0)
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.x = 10

            @abc.abstractmethod
            def func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of A"

        class B(A):
            def func(self) -> None:
                self.x = -1

            def __repr__(self) -> str:
                return "an instance of B"

        b = B()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func()
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


class TestProperty(unittest.TestCase):
    def test_inherited_getter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

        class SomeClass(SomeBase):
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
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_setter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
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
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_deleter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
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
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_invariant_on_getter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = False

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
                self.toggled = True
                return 0

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
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_invariant_on_setter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
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

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        some_inst = SomeClass()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_inst.some_prop = 0
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_invariant_on_deleter(self) -> None:
        @icontract.invariant(lambda self: not self.toggled)
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
                not self.toggled:
                self was an instance of SomeClass
                self.toggled was True"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


if __name__ == "__main__":
    unittest.main()
