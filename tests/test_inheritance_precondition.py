# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import abc
import sys
import textwrap
import unittest
from typing import Optional, Sequence, cast  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_require_else(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        b = B()
        b.func(x=4)
        b.func(x=9)

    def test_triple_inheritance_with_require_else(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        class C(B):
            @icontract.require(lambda x: x % 5 == 0)
            def func(self, x: int) -> None:
                pass

        c = C()
        c.func(x=5)


class TestViolation(unittest.TestCase):
    def test_inherited_without_implementation(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        b = B()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=1000)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < 100:
                self was an instance of B
                x was 1000"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_inherited_with_implementation(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            def func(self, x: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        b = B()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=1000)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < 100:
                self was an instance of B
                x was 1000"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_require_else(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        b = B()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=5)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x % 3 == 0:
                self was an instance of B
                x was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_triple_inheritance_wo_implementation(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        class C(B):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        c = C()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=1000)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < 100:
                self was an instance of C
                x was 1000"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_triple_inheritance_with_implementation(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x < 100)
            def func(self, x: int) -> None:
                pass

        class B(A):
            pass

        class C(B):
            def func(self, x: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        c = C()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=1000)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < 100:
                self was an instance of C
                x was 1000"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_triple_inheritance_with_require_else(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 2 == 0)
            def func(self, x: int) -> None:
                pass

        class B(A):
            @icontract.require(lambda x: x % 3 == 0)
            def func(self, x: int) -> None:
                pass

        class C(B):
            @icontract.require(lambda x: x % 5 == 0)
            def func(self, x: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        c = C()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            c.func(x=7)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x % 5 == 0:
                self was an instance of C
                x was 7"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_abstract_method(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            @abc.abstractmethod
            def func(self, x: int) -> int:
                pass

        class B(A):
            def func(self, x: int) -> int:
                return 1000

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        b = B()
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.func(x=-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > 0:
                self was an instance of B
                x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_that_base_preconditions_apply_to_init_if_not_defined(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x >= 0)
            def __init__(self, x: int) -> None:
                pass

        class B(A):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        violation_error = None  # Optional[icontract.ViolationError]
        try:
            _ = B(x=-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x >= 0:
                self was an instance of B
                x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_that_base_preconditions_dont_apply_to_init_if_overridden(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x >= 0)
            def __init__(self, x: int) -> None:
                pass

        class B(A):
            # pylint: disable=super-init-not-called
            @icontract.require(lambda x: x < 0)
            def __init__(self, x: int) -> None:
                pass

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        # Preconditions of B need to be satisfied, but not from A
        _ = B(x=-100)

        violation_error = None  # Optional[icontract.ViolationError]
        try:
            _ = B(x=0)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < 0:
                self was an instance of B
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestPropertyOK(unittest.TestCase):
    def test_getter_setter_deleter(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.deleted = False
                self._some_prop = 1

            @property
            @icontract.require(lambda self: self._some_prop > 0)
            def some_prop(self) -> int:
                return self._some_prop

            @some_prop.setter
            @icontract.require(lambda value: value > 0)
            def some_prop(self, value: int) -> None:
                self._some_prop = value

            @some_prop.deleter
            @icontract.require(lambda self: not self.deleted)
            def some_prop(self) -> None:
                self.deleted = True

        class SomeClass(SomeBase):
            pass

        some_inst = SomeClass()
        some_inst.some_prop = 3
        self.assertEqual(3, some_inst.some_prop)

        del some_inst.some_prop
        self.assertTrue(some_inst.deleted)


class TestPropertyViolation(unittest.TestCase):
    def test_getter(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = True

            @property
            @icontract.require(lambda self: not self.toggled)
            def some_prop(self) -> int:
                return 0

        class SomeClass(SomeBase):
            @property
            def some_prop(self) -> int:
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

    def test_setter(self) -> None:
        class SomeBase(icontract.DBC):
            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter
            @icontract.require(lambda value: value > 0)
            def some_prop(self, value: int) -> None:
                pass

        class SomeClass(SomeBase):
            @SomeBase.some_prop.setter  # type: ignore
            def some_prop(self, value: int) -> None:
                pass

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
                value > 0:
                self was an instance of SomeClass
                value was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_deleter(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.toggled = True

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter
            @icontract.require(lambda self: not self.toggled)
            def some_prop(self) -> None:
                pass

        class SomeClass(SomeBase):
            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

            @SomeBase.some_prop.deleter  # type: ignore
            def some_prop(self) -> None:
                pass

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


class TestConstructor(unittest.TestCase):
    def test_init_tightens_preconditions(self) -> None:
        class A(icontract.DBC):
            def __init__(self, x: int) -> None:
                pass

        class B(A):
            # B can require tighter pre-conditions than A.
            # __init__ is a special case: while other functions need to satisfy Liskov substitution principle,
            # __init__ is an exception.
            @icontract.require(lambda x: x > 0)
            def __init__(self, x: int) -> None:
                super().__init__(x=x)

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        _ = B(3)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B(-1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > 0:
                self was an instance of B
                x was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_new_tightens_preconditions(self) -> None:
        class A(icontract.DBC):
            def __new__(cls, xs: Sequence[int]) -> "A":
                return cast(A, xs)

        class B(A):
            # B can require tighter pre-conditions than A.
            # __new__ is a special case: while other functions need to satisfy Liskov substitution principle,
            # __new__ is an exception.
            @icontract.require(lambda xs: all(x > 0 for x in xs))
            def __new__(cls, xs: Sequence[int]) -> "B":
                return cast(B, xs)

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        _ = B([1, 2, 3])

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = B([-1, -2, -3])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                all(x > 0 for x in xs):
                all(x > 0 for x in xs) was False, e.g., with
                  x = -1
                xs was [-1, -2, -3]"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestInvalid(unittest.TestCase):
    def test_abstract_method_not_implemented(self) -> None:
        # pylint: disable=abstract-method
        class A(icontract.DBC):
            @icontract.require(lambda x: x > 0)
            @abc.abstractmethod
            def func(self, x: int) -> int:
                pass

        class B(A):
            pass

        type_err = None  # type: Optional[TypeError]
        try:
            _ = B()  # type: ignore
        except TypeError as err:
            type_err = err

        self.assertIsNotNone(type_err)
        if sys.version_info < (3, 9):
            self.assertEqual(
                "Can't instantiate abstract class B with abstract methods func",
                str(type_err),
            )
        else:
            self.assertEqual(
                "Can't instantiate abstract class B with abstract method func",
                str(type_err),
            )

    def test_cant_weaken_base_function_without_preconditions(self) -> None:
        class A(icontract.DBC):
            @abc.abstractmethod
            def func(self, x: int) -> int:
                raise NotImplementedError()

        type_error = None  # type: Optional[TypeError]
        try:

            class B(A):  # pylint: disable=unused-variable
                @icontract.require(lambda x: x < 0)
                def func(self, x: int) -> int:
                    return 1000

        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual(
            "The function "
            "TestInvalid.test_cant_weaken_base_function_without_preconditions.<locals>.B.func can not "
            "weaken the preconditions because the bases specify no preconditions at all. Hence this function must "
            "accept all possible input since the preconditions are OR'ed and no precondition implies a dummy "
            "precondition which is always fulfilled.",
            str(type_error),
        )


if __name__ == "__main__":
    unittest.main()
