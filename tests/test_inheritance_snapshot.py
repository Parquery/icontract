# pylint: disable=missing-docstring
# pylint: disable=invalid-name

import unittest
from typing import Optional, List  # pylint: disable=unused-import

import icontract

import tests.error


class TestOK(unittest.TestCase):
    def test_with_no_override(self) -> None:
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.lst = []  # type: List[int]

            @icontract.snapshot(lambda self: self.lst[:], name="lst")
            @icontract.ensure(lambda OLD, self, val: OLD.lst + [val] == self.lst)
            def some_func(self, val: int) -> None:
                self.lst.append(val)

        class B(A):
            pass

        b = B()
        b.some_func(2)


class TestViolation(unittest.TestCase):
    def test_with_no_override(self) -> None:
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.lst = []  # type: List[int]

            @icontract.snapshot(lambda self: self.lst[:], name="lst")
            @icontract.ensure(lambda OLD, self, val: OLD.lst + [val] == self.lst)
            def some_func(self, val: int) -> None:
                self.lst.append(val)
                self.lst.append(1984)

        class B(A):
            def __repr__(self) -> str:
                return self.__class__.__name__

        b = B()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.some_func(2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('OLD.lst + [val] == self.lst:\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.lst was []\n'
                         'self was B\n'
                         'self.lst was [2, 1984]\n'
                         'val was 2', tests.error.wo_mandatory_location(str(violation_error)))

    def test_with_inherited_snapshot(self) -> None:
        class A(icontract.DBC):
            def __init__(self) -> None:
                self.lst = []  # type: List[int]

            @icontract.snapshot(lambda self: len(self.lst), name="len_lst")
            @icontract.ensure(lambda self: self.lst)
            def some_func(self, val: int) -> None:
                pass

        class B(A):
            @icontract.ensure(lambda OLD, self: OLD.len_lst + 1 == len(self.lst))
            def some_func(self, val: int) -> None:
                self.lst.append(val)
                self.lst.append(1984)

            def __repr__(self) -> str:
                return self.__class__.__name__

        b = B()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            b.some_func(2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('OLD.len_lst + 1 == len(self.lst):\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.len_lst was 0\n'
                         'len(self.lst) was 2\n'
                         'self was B\n'
                         'self.lst was [2, 1984]', tests.error.wo_mandatory_location(str(violation_error)))


class TestPropertyOK(unittest.TestCase):
    def test_getter_setter_deleter(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.gets = 0
                self.sets = 0
                self.dels = 0

            @property  # type: ignore
            @icontract.snapshot(lambda self: self.gets, name="gets")
            @icontract.ensure(lambda OLD, self: self.gets == OLD.gets + 1)
            def some_prop(self) -> int:
                self.gets += 1
                return 0

            @some_prop.setter  # type: ignore
            @icontract.snapshot(lambda self: self.sets, name="sets")
            @icontract.ensure(lambda OLD, self: self.sets == OLD.sets + 1)
            def some_prop(self, value: int) -> None:
                # pylint: disable=unused-argument
                self.sets += 1

            @some_prop.deleter  # type: ignore
            @icontract.snapshot(lambda self: self.dels, name="dels")
            @icontract.ensure(lambda OLD, self: self.dels == OLD.dels + 1)
            def some_prop(self) -> None:
                self.dels += 1

        class SomeClass(SomeBase):
            pass

        some_inst = SomeClass()
        _ = some_inst.some_prop
        some_inst.some_prop = 3  # type: ignore
        del some_inst.some_prop

        self.assertEqual(1, some_inst.gets)
        self.assertEqual(1, some_inst.sets)
        self.assertEqual(1, some_inst.dels)


class TestPropertyViolation(unittest.TestCase):
    def test_getter_setter_deleter_fail(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.gets = 0
                self.sets = 0
                self.dels = 0

            @property  # type: ignore
            @icontract.snapshot(lambda self: self.gets, name="gets")
            @icontract.ensure(lambda OLD, self: self.gets == OLD.gets + 1)
            def some_prop(self) -> int:
                # no self.gets increment
                return 0

            @some_prop.setter  # type: ignore
            @icontract.snapshot(lambda self: self.sets, name="sets")
            @icontract.ensure(lambda OLD, self: self.sets == OLD.sets + 1)
            def some_prop(self, value: int) -> None:
                # pylint: disable=unused-argument
                # no self.sets increment
                return

            @some_prop.deleter  # type: ignore
            @icontract.snapshot(lambda self: self.dels, name="dels")
            @icontract.ensure(lambda OLD, self: self.dels == OLD.dels + 1)
            def some_prop(self) -> None:
                # no self.dels increment
                return

        class SomeClass(SomeBase):
            def __repr__(self) -> str:
                return self.__class__.__name__

        some_inst = SomeClass()

        # getter fails
        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('self.gets == OLD.gets + 1:\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.gets was 0\n'
                         'self was SomeClass\n'
                         'self.gets was 0', tests.error.wo_mandatory_location(str(violation_error)))

        # setter fails
        violation_error = None
        try:
            some_inst.some_prop = 1  # type: ignore
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('self.sets == OLD.sets + 1:\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.sets was 0\n'
                         'self was SomeClass\n'
                         'self.sets was 0', tests.error.wo_mandatory_location(str(violation_error)))

        # deleter fails
        violation_error = None
        try:
            del some_inst.some_prop
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual('self.dels == OLD.dels + 1:\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.dels was 0\n'
                         'self was SomeClass\n'
                         'self.dels was 0', tests.error.wo_mandatory_location(str(violation_error)))


class TestInvalid(unittest.TestCase):
    def test_conflicting_snapshot_names(self) -> None:
        value_error = None  # type: Optional[ValueError]
        try:

            class A(icontract.DBC):
                def __init__(self) -> None:
                    self.lst = []  # type: List[int]

                @icontract.snapshot(lambda self: len(self.lst), name="len_lst")
                @icontract.ensure(lambda self: self.lst)
                def some_func(self, val: int) -> None:
                    pass

            # pylint: disable=unused-variable

            class B(A):
                @icontract.snapshot(lambda self: len(self.lst), name="len_lst")
                @icontract.ensure(lambda OLD, self: OLD.len_lst + 1 == len(self.lst))
                def some_func(self, val: int) -> None:
                    self.lst.append(val)
                    self.lst.append(1984)

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'len_lst'.\n\n"
                         "Please mind that the snapshots are inherited from the base classes. "
                         "Does one of the base classes defines a snapshot with the same name?", str(value_error))


class TestPropertyInvalid(unittest.TestCase):
    def test_getter_with_conflicting_snapshot_names(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.gets = 0

            @property  # type: ignore
            @icontract.snapshot(lambda self: self.gets, name="gets")
            @icontract.ensure(lambda OLD, self: self.gets == OLD.gets + 1)
            def some_prop(self) -> int:
                self.gets += 1
                return 0

        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            class SomeClass(SomeBase):
                @property  # type: ignore
                @icontract.snapshot(lambda self: self.gets, name="gets")
                @icontract.ensure(lambda OLD, self: self.gets == OLD.gets + 1)
                def some_prop(self) -> int:
                    return 0

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'gets'.\n\n"
                         "Please mind that the snapshots are inherited from the base classes. "
                         "Does one of the base classes defines a snapshot with the same name?", str(value_error))

    def test_setter_with_conflicting_snapshot_names(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.sets = 0

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.setter  # type: ignore
            @icontract.snapshot(lambda self: self.sets, name="sets")
            @icontract.ensure(lambda OLD, self: self.sets == OLD.sets + 1)
            def some_prop(self, value: int) -> None:
                # pylint: disable=unused-argument
                self.sets += 1

        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            class SomeClass(SomeBase):
                @property
                def some_prop(self) -> int:
                    return 0

                @some_prop.setter  # type: ignore
                @icontract.snapshot(lambda self: self.sets, name="sets")
                @icontract.ensure(lambda OLD, self: self.sets == OLD.sets + 1)
                def some_prop(self, value: int) -> None:
                    # pylint: disable=unused-argument
                    return

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'sets'.\n\n"
                         "Please mind that the snapshots are inherited from the base classes. "
                         "Does one of the base classes defines a snapshot with the same name?", str(value_error))

    def test_deleter_with_conflicting_snapshot_names(self) -> None:
        class SomeBase(icontract.DBC):
            def __init__(self) -> None:
                self.dels = 0

            @property
            def some_prop(self) -> int:
                return 0

            @some_prop.deleter  # type: ignore
            @icontract.snapshot(lambda self: self.dels, name="dels")
            @icontract.ensure(lambda OLD, self: self.dels == OLD.dels + 1)
            def some_prop(self) -> None:
                self.dels += 1

        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            class SomeClass(SomeBase):
                @property
                def some_prop(self) -> int:
                    return 0

                @some_prop.deleter  # type: ignore
                @icontract.snapshot(lambda self: self.dels, name="dels")
                @icontract.ensure(lambda OLD, self: self.dels == OLD.dels + 1)
                def some_prop(self) -> None:
                    return

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'dels'.\n\n"
                         "Please mind that the snapshots are inherited from the base classes. "
                         "Does one of the base classes defines a snapshot with the same name?", str(value_error))


if __name__ == '__main__':
    unittest.main()
