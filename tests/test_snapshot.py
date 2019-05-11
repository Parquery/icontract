# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unnecessary-lambda
# pylint: disable=unused-argument
# pylint: disable=no-self-use

import unittest
from typing import List, Optional  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_without_argument(self):
        z = [1]

        @icontract.snapshot(lambda: z[:], name="z")
        @icontract.ensure(lambda OLD, val: OLD.z + [val] == z)
        def some_func(val: int) -> None:
            z.append(val)

        some_func(2)

    def test_with_name_same_as_argument(self):
        @icontract.snapshot(lambda lst: lst[:])
        @icontract.ensure(lambda OLD, val, lst: OLD.lst + [val] == lst)
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        # Expected to pass
        some_func([1], 2)

    def test_with_custom_name(self):
        @icontract.snapshot(lambda lst: len(lst), name="len_lst")
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        # Expected to pass
        some_func([1], 2)


class TestViolation(unittest.TestCase):
    def test_with_name_same_as_argument(self):
        @icontract.snapshot(lambda lst: lst[:])
        @icontract.ensure(lambda OLD, val, lst: OLD.lst + [val] == lst)
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)
            lst.append(1984)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func([1], 2)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('OLD.lst + [val] == lst:\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.lst was [1]\n'
                         'lst was [1, 2, 1984]\n'
                         'val was 2', tests.error.wo_mandatory_location(str(icontract_violation_error)))

    def test_with_custom_name(self):
        @icontract.snapshot(lambda lst: len(lst), name="len_lst")
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)
            lst.append(1984)

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func([1], 2)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('OLD.len_lst + 1 == len(lst):\n'
                         'OLD was a bunch of OLD values\n'
                         'OLD.len_lst was 1\n'
                         'len(lst) was 3\n'
                         'lst was [1, 2, 1984]', tests.error.wo_mandatory_location(str(icontract_violation_error)))


class TestInvalid(unittest.TestCase):
    def test_missing_old_snapshot(self):
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        attribute_error = None  # type: Optional[AttributeError]
        try:
            some_func([1], 2)
        except AttributeError as err:
            attribute_error = err

        self.assertIsNotNone(attribute_error)
        self.assertEqual("The snapshot with the name 'len_lst' is not available in the OLD of a postcondition. "
                         "Have you decorated the function with a corresponding snapshot decorator?",
                         str(attribute_error))

    def test_conflicting_snapshots_with_argument_name(self):
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst: lst[:])
            @icontract.snapshot(lambda lst: lst[:])
            @icontract.ensure(lambda OLD, val, lst: len(OLD.lst) + 1 == len(lst))
            def some_func(lst: List[int], val: int) -> None:
                lst.append(val)

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'lst'", str(value_error))

    def test_conflicting_snapshots_with_custom_name(self):
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst: len(lst), name='len_lst')
            @icontract.snapshot(lambda lst: len(lst), name='len_lst')
            @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
            def some_func(lst: List[int], val: int) -> None:
                lst.append(val)

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("There are conflicting snapshots with the name: 'len_lst'", str(value_error))

    def test_with_invalid_argument(self):
        # lst versus a_list
        type_error = None  # type: Optional[TypeError]
        try:

            @icontract.snapshot(lambda lst: len(lst), name='len_lst')
            @icontract.ensure(lambda OLD, val, a_list: OLD.len_lst + 1 == len(a_list))
            def some_func(a_list: List[int], val: int) -> None:
                a_list.append(val)

            some_func([1], 2)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual("The argument of the snapshot has not been set: lst. "
                         "Does the original function define it? Did you supply it in the call?", str(type_error))

    def test_with_invalid_arguments(self):
        # lst versus a_list
        type_error = None  # type: Optional[TypeError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst, val: len(lst) + val, name='dummy_snap')
            @icontract.ensure(lambda OLD: OLD.dummy_snap)
            def some_func(a_list: List[int], val: int) -> None:
                a_list.append(val)

        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual('The capture function of a snapshot expects only a single argument.', str(type_error))

    def test_with_no_arguments_and_no_name(self):
        z = [1]

        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda: z[:])
            @icontract.ensure(lambda OLD, val: OLD.z + [val] == z)
            def some_func(val: int) -> None:
                z.append(val)

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("You must name a snapshot if no argument was given in the capture function.", str(value_error))

    def test_with_no_postcondition(self):
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst: lst[:])
            def some_func(lst: List[int]) -> None:
                return
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("You are decorating a function with a snapshot, "
                         "but no postcondition was defined on the function before.", str(value_error))


if __name__ == '__main__':
    unittest.main()
