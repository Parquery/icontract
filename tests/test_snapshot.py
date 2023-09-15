# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unnecessary-lambda
# pylint: disable=unused-argument

import textwrap
import unittest
from typing import List, Optional  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_without_argument(self) -> None:
        z = [1]

        @icontract.snapshot(lambda: z[:], name="z")
        @icontract.ensure(lambda OLD, val: OLD.z + [val] == z)
        def some_func(val: int) -> None:
            z.append(val)

        some_func(2)

    def test_with_name_same_for_single_argument(self) -> None:
        @icontract.snapshot(lambda lst: lst[:])
        @icontract.ensure(lambda OLD, val, lst: OLD.lst + [val] == lst)
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        # Expected to pass
        some_func([1], 2)

    def test_with_custom_name_for_single_argument(self) -> None:
        @icontract.snapshot(lambda lst: len(lst), name="len_lst")
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        # Expected to pass
        some_func([1], 2)

    def test_with_multiple_arguments(self) -> None:
        @icontract.snapshot(lambda lst_a, lst_b: set(lst_a).union(lst_b), name="union")
        @icontract.ensure(
            lambda OLD, lst_a, lst_b: set(lst_a).union(lst_b) == OLD.union
        )
        def some_func(lst_a: List[int], lst_b: List[int]) -> None:
            pass

        # Expected to pass
        some_func(lst_a=[1, 2], lst_b=[3, 4])


class TestViolation(unittest.TestCase):
    def test_with_name_same_as_argument(self) -> None:
        @icontract.snapshot(lambda lst: lst[:])
        @icontract.ensure(lambda OLD, val, lst: OLD.lst + [val] == lst)
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)
            lst.append(1984)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func([1], 2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                OLD.lst + [val] == lst:
                OLD was a bunch of OLD values
                OLD.lst was [1]
                lst was [1, 2, 1984]
                result was None
                val was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_custom_name(self) -> None:
        @icontract.snapshot(lambda lst: len(lst), name="len_lst")
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)
            lst.append(1984)

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func([1], 2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                OLD.len_lst + 1 == len(lst):
                OLD was a bunch of OLD values
                OLD.len_lst was 1
                len(lst) was 3
                lst was [1, 2, 1984]
                result was None
                val was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_with_multiple_arguments(self) -> None:
        @icontract.snapshot(lambda lst_a, lst_b: set(lst_a).union(lst_b), name="union")
        @icontract.ensure(
            lambda OLD, lst_a, lst_b: set(lst_a).union(lst_b) == OLD.union
        )
        def some_func(lst_a: List[int], lst_b: List[int]) -> None:
            lst_a.append(1984)  # bug

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(lst_a=[1, 2], lst_b=[3, 4])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                set(lst_a).union(lst_b) == OLD.union:
                OLD was a bunch of OLD values
                OLD.union was {1, 2, 3, 4}
                lst_a was [1, 2, 1984]
                lst_b was [3, 4]
                result was None
                set(lst_a) was {1, 2, 1984}
                set(lst_a).union(lst_b) was {1, 2, 3, 4, 1984}"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestInvalid(unittest.TestCase):
    def test_missing_snapshot_but_old_in_postcondition(self) -> None:
        @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
        def some_func(lst: List[int], val: int) -> None:
            lst.append(val)

        type_error = None  # type: Optional[TypeError]
        try:
            some_func([1], 2)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual(
            "The argument(s) of the contract condition have not been set: ['OLD']. "
            "Does the original function define them? Did you supply them in the call? "
            "Did you decorate the function with a snapshot to capture OLD values?",
            tests.error.wo_mandatory_location(str(type_error)),
        )

    def test_conflicting_snapshots_with_argument_name(self) -> None:
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
        self.assertEqual(
            "There are conflicting snapshots with the name: 'lst'", str(value_error)
        )

    def test_conflicting_snapshots_with_custom_name(self) -> None:
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst: len(lst), name="len_lst")
            @icontract.snapshot(lambda lst: len(lst), name="len_lst")
            @icontract.ensure(lambda OLD, val, lst: OLD.len_lst + 1 == len(lst))
            def some_func(lst: List[int], val: int) -> None:
                lst.append(val)

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual(
            "There are conflicting snapshots with the name: 'len_lst'", str(value_error)
        )

    def test_with_invalid_argument(self) -> None:
        # lst versus a_list
        type_error = None  # type: Optional[TypeError]
        try:

            @icontract.snapshot(lambda lst: len(lst), name="len_lst")
            @icontract.ensure(lambda OLD, val, a_list: OLD.len_lst + 1 == len(a_list))
            def some_func(a_list: List[int], val: int) -> None:
                a_list.append(val)

            some_func([1], 2)
        except TypeError as err:
            type_error = err

        self.assertIsNotNone(type_error)
        self.assertEqual(
            "The argument(s) of the snapshot have not been set: ['lst']. "
            "Does the original function define them? Did you supply them in the call?",
            tests.error.wo_mandatory_location(str(type_error)),
        )

    def test_with_no_arguments_and_no_name(self) -> None:
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
        self.assertEqual(
            "You must name a snapshot if no argument was given in the capture function.",
            str(value_error),
        )

    def test_with_multiple_arguments_and_no_name(self) -> None:
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst_a, lst_b: set(lst_a).union(lst_b))
            @icontract.ensure(
                lambda OLD, lst_a, lst_b: set(lst_a).union(lst_b) == OLD.union
            )
            def some_func(lst_a: List[int], lst_b: List[int]) -> None:
                pass

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual(
            "You must name a snapshot if multiple arguments were given in the capture function.",
            str(value_error),
        )

    def test_with_no_postcondition(self) -> None:
        value_error = None  # type: Optional[ValueError]
        try:
            # pylint: disable=unused-variable

            @icontract.snapshot(lambda lst: lst[:])
            def some_func(lst: List[int]) -> None:
                return

        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual(
            "You are decorating a function with a snapshot, "
            "but no postcondition was defined on the function before.",
            str(value_error),
        )

    def test_missing_old_attribute(self) -> None:
        @icontract.snapshot(lambda lst: lst[:])
        @icontract.ensure(
            lambda OLD, lst: OLD.len_list == lst
        )  # We miss len_lst in OLD here!
        def some_func(lst: List[int]) -> None:
            return

        attribute_error = None  # type: Optional[AttributeError]

        try:
            some_func(lst=[1, 2, 3])
        except AttributeError as error:
            attribute_error = error

        assert attribute_error is not None

        self.assertEqual(
            "The snapshot with the name 'len_list' is not available in the OLD of a postcondition. "
            "Have you decorated the function with a corresponding snapshot decorator?",
            str(attribute_error),
        )


if __name__ == "__main__":
    unittest.main()
