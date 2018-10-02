#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name,too-many-public-methods,no-self-use
import pathlib
import unittest
from typing import Optional, List, Tuple  # pylint: disable=unused-import

import icontract2.represent


class TestReprValues(unittest.TestCase):
    def test_num(self):
        @icontract2.requires(lambda x: x < 5)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=100)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("x < 5: x was 100", str(icontract_violation_error))

    def test_str(self):
        @icontract2.requires(lambda x: x != "oi")
        def func(x: str) -> str:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x="oi")
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("""x != "oi": x was 'oi'""", str(icontract_violation_error))

    def test_bytes(self):
        @icontract2.requires(lambda x: x != b"oi")
        def func(x: bytes) -> bytes:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=b"oi")
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("""x != b"oi": x was b'oi'""", str(icontract_violation_error))

    def test_bool(self):
        @icontract2.requires(lambda x: x != False)
        def func(x: bool) -> bool:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=False)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x != False: x was False', str(icontract_violation_error))

    def test_list(self):
        y = 1

        @icontract2.requires(lambda x: sum([1, y, x]) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=3)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum([1, y, x]) == 1:\n'
                         'sum([1, y, x]) was 5\n'
                         'x was 3\n'
                         'y was 1', str(icontract_violation_error))

    def test_tuple(self):
        y = 1

        @icontract2.requires(lambda x: sum((1, y, x)) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=3)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum((1, y, x)) == 1:\n'
                         'sum((1, y, x)) was 5\n'
                         'x was 3\n'
                         'y was 1', str(icontract_violation_error))

    def test_set(self):
        y = 2

        @icontract2.requires(lambda x: sum({1, y, x}) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=3)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum({1, y, x}) == 1:\n'
                         'sum({1, y, x}) was 6\n'
                         'x was 3\n'
                         'y was 2', str(icontract_violation_error))

    def test_dict(self):
        y = "someKey"

        @icontract2.requires(lambda x: len({y: 3, x: 8}) == 6)
        def func(x: str) -> str:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x="oi")
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("len({y: 3, x: 8}) == 6:\n"
                         "len({y: 3, x: 8}) was 2\n"
                         "x was 'oi'\n"
                         "y was 'someKey'", str(icontract_violation_error))

    def test_unary_op(self):
        @icontract2.requires(lambda x: not -x + 10 > 3)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not -x + 10 > 3: x was 1', str(icontract_violation_error))

    def test_binary_op(self):
        @icontract2.requires(lambda x: -x + x - x * x / x // x**x % x > 3)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('-x + x - x * x / x // x**x % x > 3: x was 1', str(icontract_violation_error))

    def test_binary_op_bit(self):
        @icontract2.requires(lambda x: ~(x << x | x & x ^ x) >> x > x)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('~(x << x | x & x ^ x) >> x > x: x was 1', str(icontract_violation_error))

    def test_bool_op_single(self):
        @icontract2.requires(lambda x: x > 3 and x < 10)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > 3 and x < 10: x was 1', str(icontract_violation_error))

    def test_bool_op_multiple(self):
        @icontract2.requires(lambda x: x > 3 and x < 10 and x % 2 == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > 3 and x < 10 and x % 2 == 0: x was 1', str(icontract_violation_error))

    def test_compare(self):
        # Chain the compare operators in a meaningless order and semantics

        @icontract2.requires(
            lambda x: 0 < x < 3 and x > 10 and x != 7 and x >= 10 and x <= 11 and x is not None and
                      x in [1, 2, 3] and x not in [1, 2, 3])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('0 < x < 3 and x > 10 and x != 7 and x >= 10 and x <= 11 and x is not None and\n'
                         '                      x in [1, 2, 3] and x not in [1, 2, 3]: x was 1',
                         str(icontract_violation_error))

    def test_call(self):
        def y() -> int:
            return 1

        @icontract2.requires(lambda x: x < y())
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x < y():\n' 'x was 1\n' 'y() was 1', str(icontract_violation_error))

    def test_if_exp_body(self):
        y = 5

        @icontract2.requires(lambda x: x < (x**2 if y == 5 else x**3))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x < (x**2 if y == 5 else x**3):\n' 'x was 1\n' 'y was 5', str(icontract_violation_error))

    def test_if_exp_orelse(self):
        y = 5

        @icontract2.requires(lambda x: x < (x**2 if y != 5 else x**3))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x < (x**2 if y != 5 else x**3):\nx was 1\ny was 5', str(icontract_violation_error))

    def test_attr(self):
        class A:
            def __init__(self) -> None:
                self.y = 3

            def __repr__(self) -> str:
                return "A()"

        a = A()

        @icontract2.requires(lambda x: x > a.y)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > a.y:\n' 'a was A()\n' 'a.y was 3\n' 'x was 1', str(icontract_violation_error))

    def test_index(self):
        lst = [1, 2, 3]

        @icontract2.requires(lambda x: x > lst[1])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > lst[1]:\n' 'lst was [1, 2, 3]\n' 'x was 1', str(icontract_violation_error))

    def test_slice(self):
        lst = [1, 2, 3]

        @icontract2.requires(lambda x: x > sum(lst[1:2:1]))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=1)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > sum(lst[1:2:1]):\n'
                         'lst was [1, 2, 3]\n'
                         'sum(lst[1:2:1]) was 2\n'
                         'x was 1', str(icontract_violation_error))

    def test_lambda(self):
        @icontract2.requires(lambda x: x > (lambda y: y + 4).__call__(y=7))
        def func(x: int) -> int:
            return x

        not_implemented_err = None  # type: Optional[NotImplementedError]
        try:
            func(x=1)
        except NotImplementedError as err:
            not_implemented_err = err

        self.assertIsNotNone(not_implemented_err)

    def test_generator_expression_with_attr_on_element(self):
        @icontract2.ensures(lambda result: all(single_res[1].is_absolute() for single_res in result))
        def some_func() -> List[Tuple[pathlib.Path, pathlib.Path]]:
            return [(pathlib.Path("/home/file1"), pathlib.Path("home/file2"))]

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            some_func()
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('all(single_res[1].is_absolute() for single_res in result): all(single_res[1].is_absolute() '
                         'for single_res in result) was False', str(icontract_violation_error))

    def test_generator_expression_multiple_for(self):
        lst = [1, 2, 3]
        another_lst = [4, 5, 6]

        # yapf: disable
        @icontract2.requires(
            lambda x: all(item == x or another_item == x
                          for item in lst if item % 2 == 0
                          for another_item in another_lst if another_item % 3 == 0)
        )
        # yapf: enable
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=0)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual(
            'all(item == x or another_item == x\n'
            '                          for item in lst if item % 2 == 0\n'
            '                          for another_item in another_lst if another_item % 3 == 0): '
            'all(item == x or another_item == x\n'
            '                          for item in lst if item % 2 == 0\n'
            '                          for another_item in another_lst if another_item % 3 == 0) was False',
            str(icontract_violation_error))

    def test_list_comprehension(self):
        lst = [1, 2, 3]

        @icontract2.requires(lambda x: [item < x for item in lst if item % x == 0] == [])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=2)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('[item < x for item in lst if item % x == 0] == []: '
                         '[item < x for item in lst if item % x == 0] was [False]', str(icontract_violation_error))

    def test_set_comprehension(self):
        lst = [1, 2, 3]

        @icontract2.requires(lambda x: len({item < x for item in lst if item % x == 0}) == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=2)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('len({item < x for item in lst if item % x == 0}) == 0:\n'
                         'len({item < x for item in lst if item % x == 0}) was 1\n'
                         '{item < x for item in lst if item % x == 0} was {False}', str(icontract_violation_error))

    def test_dict_comprehension(self):
        @icontract2.requires(lambda x: len({i: i**2 for i in range(x)}) == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=2)
        except icontract2.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('len({i: i**2 for i in range(x)}) == 0:\n'
                         'len({i: i**2 for i in range(x)}) was 2\n'
                         '{i: i**2 for i in range(x)} was {0: 0, 1: 1}', str(icontract_violation_error))


class TestConditionAsText(unittest.TestCase):
    """Test decompilation of the condition."""

    def test_single_line(self):
        # yapf: disable
        @icontract2.requires(lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=0)
        except icontract2.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x > 3: x was 0", str(violation_err))

    def test_condition_on_next_line(self):
        # yapf: disable
        @icontract2.requires(
            lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=0)
        except icontract2.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x > 3: x was 0", str(violation_err))

    def test_condition_on_multiple_lines(self):
        # yapf: disable
        @icontract2.requires(
            lambda x:
            x
            >
            3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=0)
        except icontract2.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual('x\n            >\n            3: x was 0', str(violation_err))

    def test_with_repr_args_and_multiple_conditions(self):
        # pylint: disable=unnecessary-lambda
        # yapf: disable
        @icontract2.requires(
            repr_args=lambda x: "x was {}".format(x), condition=lambda x: x > 0)
        @icontract2.requires(
            repr_args=lambda x: "x was {}".format(x), condition=lambda x: x < 100)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract2.ViolationError]
        try:
            func(x=101)
        except icontract2.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x < 100: x was 101", str(violation_err))


if __name__ == '__main__':
    unittest.main()
