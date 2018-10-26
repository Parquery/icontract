#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name,too-many-public-methods,no-self-use
# pylint: disable=unused-argument

import pathlib
import reprlib
import unittest
from typing import Optional, List, Tuple  # pylint: disable=unused-import

import icontract._represent


class TestReprValues(unittest.TestCase):
    def test_num(self):
        @icontract.require(lambda x: x < 5)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=100)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("x < 5: x was 100", str(icontract_violation_error))

    def test_str(self):
        @icontract.require(lambda x: x != "oi")
        def func(x: str) -> str:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x="oi")
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("""x != "oi": x was 'oi'""", str(icontract_violation_error))

    def test_bytes(self):
        @icontract.require(lambda x: x != b"oi")
        def func(x: bytes) -> bytes:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=b"oi")
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("""x != b"oi": x was b'oi'""", str(icontract_violation_error))

    def test_bool(self):
        @icontract.require(lambda x: x is not False)
        def func(x: bool) -> bool:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=False)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x is not False: x was False', str(icontract_violation_error))

    def test_list(self):
        y = 1

        @icontract.require(lambda x: sum([1, y, x]) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum([1, y, x]) == 1:\n'
                         'sum([1, y, x]) was 5\n'
                         'x was 3\n'
                         'y was 1', str(icontract_violation_error))

    def test_tuple(self):
        y = 1

        @icontract.require(lambda x: sum((1, y, x)) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum((1, y, x)) == 1:\n'
                         'sum((1, y, x)) was 5\n'
                         'x was 3\n'
                         'y was 1', str(icontract_violation_error))

    def test_set(self):
        y = 2

        @icontract.require(lambda x: sum({1, y, x}) == 1)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('sum({1, y, x}) == 1:\n'
                         'sum({1, y, x}) was 6\n'
                         'x was 3\n'
                         'y was 2', str(icontract_violation_error))

    def test_dict(self):
        y = "someKey"

        @icontract.require(lambda x: len({y: 3, x: 8}) == 6)
        def func(x: str) -> str:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x="oi")
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("len({y: 3, x: 8}) == 6:\n"
                         "len({y: 3, x: 8}) was 2\n"
                         "x was 'oi'\n"
                         "y was 'someKey'", str(icontract_violation_error))

    def test_unary_op(self):
        @icontract.require(lambda x: not -x + 10 > 3)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('not -x + 10 > 3: x was 1', str(icontract_violation_error))

    def test_binary_op(self):
        @icontract.require(lambda x: -x + x - x * x / x // x**x % x > 3)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('-x + x - x * x / x // x**x % x > 3: x was 1', str(icontract_violation_error))

    def test_binary_op_bit(self):
        @icontract.require(lambda x: ~(x << x | x & x ^ x) >> x > x)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('~(x << x | x & x ^ x) >> x > x: x was 1', str(icontract_violation_error))

    def test_bool_op_single(self):
        # pylint: disable=chained-comparison
        @icontract.require(lambda x: x > 3 and x < 10)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > 3 and x < 10: x was 1', str(icontract_violation_error))

    def test_bool_op_multiple(self):
        # pylint: disable=chained-comparison
        @icontract.require(lambda x: x > 3 and x < 10 and x % 2 == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > 3 and x < 10 and x % 2 == 0: x was 1', str(icontract_violation_error))

    def test_compare(self):
        # pylint: disable=chained-comparison

        # Chain the compare operators in a meaningless order and semantics
        @icontract.require(
            lambda x: 0 < x < 3 and x > 10 and x != 7 and x >= 10 and x <= 11 and x is not None and
                      x in [1, 2, 3] and x not in [1, 2, 3])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('0 < x < 3 and x > 10 and x != 7 and x >= 10 and x <= 11 and x is not None and\n'
                         '              x in [1, 2, 3] and x not in [1, 2, 3]: x was 1', str(icontract_violation_error))

    def test_call(self):
        def y() -> int:
            return 1

        @icontract.require(lambda x: x < y())
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x < y():\n' 'x was 1\n' 'y() was 1', str(icontract_violation_error))

    def test_if_exp_body(self):
        y = 5

        @icontract.require(lambda x: x < (x**2 if y == 5 else x**3))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x < (x**2 if y == 5 else x**3):\n' 'x was 1\n' 'y was 5', str(icontract_violation_error))

    def test_if_exp_orelse(self):
        y = 5

        @icontract.require(lambda x: x < (x**2 if y != 5 else x**3))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
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

        @icontract.require(lambda x: x > a.y)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > a.y:\n' 'a was A()\n' 'a.y was 3\n' 'x was 1', str(icontract_violation_error))

    def test_index(self):
        lst = [1, 2, 3]

        @icontract.require(lambda x: x > lst[1])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > lst[1]:\n' 'lst was [1, 2, 3]\n' 'x was 1', str(icontract_violation_error))

    def test_slice(self):
        lst = [1, 2, 3]

        @icontract.require(lambda x: x > sum(lst[1:2:1]))
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('x > sum(lst[1:2:1]):\n'
                         'lst was [1, 2, 3]\n'
                         'sum(lst[1:2:1]) was 2\n'
                         'x was 1', str(icontract_violation_error))

    def test_lambda(self):
        @icontract.require(lambda x: x > (lambda y: y + 4).__call__(y=7))
        def func(x: int) -> int:
            return x

        not_implemented_err = None  # type: Optional[NotImplementedError]
        try:
            func(x=1)
        except NotImplementedError as err:
            not_implemented_err = err

        self.assertIsNotNone(not_implemented_err)

    def test_generator_expression_with_attr_on_element(self):
        @icontract.ensure(lambda result: all(single_res[1].is_absolute() for single_res in result))
        def some_func() -> List[Tuple[pathlib.Path, pathlib.Path]]:
            return [(pathlib.Path("/home/file1"), pathlib.Path("home/file2"))]

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func()
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual("all(single_res[1].is_absolute() for single_res in result):\n"
                         "all(single_res[1].is_absolute() for single_res in result) was False\n"
                         "result was [(PosixPath('/home/file1'), PosixPath('home/file2'))]",
                         str(icontract_violation_error))

    def test_generator_expression_multiple_for(self):
        lst = [[1, 2], [3]]

        # yapf: disable
        @icontract.require(
            lambda x: all(item == x for sublst in lst for item in sublst)
        )
        # yapf: enable
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)

        self.assertEqual('all(item == x for sublst in lst for item in sublst):\n'
                         'all(item == x for sublst in lst for item in sublst) was False\n'
                         'lst was [[1, 2], [3]]', str(icontract_violation_error))

    def test_list_comprehension(self):
        lst = [1, 2, 3]

        @icontract.require(lambda x: [item < x for item in lst if item % x == 0] == [])
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('[item < x for item in lst if item % x == 0] == []:\n'
                         '[item < x for item in lst if item % x == 0] was [False]\n'
                         'lst was [1, 2, 3]', str(icontract_violation_error))

    def test_set_comprehension(self):
        lst = [1, 2, 3]

        @icontract.require(lambda x: len({item < x for item in lst if item % x == 0}) == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('len({item < x for item in lst if item % x == 0}) == 0:\n'
                         'len({item < x for item in lst if item % x == 0}) was 1\n'
                         'lst was [1, 2, 3]\n'
                         '{item < x for item in lst if item % x == 0} was {False}', str(icontract_violation_error))

    def test_dict_comprehension(self):
        @icontract.require(lambda x: len({i: i**2 for i in range(x)}) == 0)
        def func(x: int) -> int:
            return x

        icontract_violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            icontract_violation_error = err

        self.assertIsNotNone(icontract_violation_error)
        self.assertEqual('len({i: i**2 for i in range(x)}) == 0:\n'
                         'len({i: i**2 for i in range(x)}) was 2\n'
                         'range(x) was range(0, 2)\n'
                         'x was 2\n'
                         '{i: i**2 for i in range(x)} was {0: 0, 1: 1}', str(icontract_violation_error))


class TestConditionAsText(unittest.TestCase):
    """Test decompilation of the condition."""

    def test_single_line(self):
        # yapf: disable
        @icontract.require(lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x > 3: x was 0", str(violation_err))

    def test_condition_on_next_line(self):
        # yapf: disable
        @icontract.require(
            lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual("x > 3: x was 0", str(violation_err))

    def test_condition_on_multiple_lines(self):
        # yapf: disable
        @icontract.require(
            lambda x:
            x
            >
            3)
        def func(x: int) -> int:
            return x

        # yapf: enable

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual('x\n    >\n    3: x was 0', str(violation_err))

    def test_with_multiple_lambdas_on_a_line(self):
        # pylint: disable=unnecessary-lambda
        # yapf: disable
        @icontract.require(
            error=lambda x: ValueError("x > 0, but got: {}".format(x)), condition=lambda x: x > 0)
        @icontract.require(
            error=lambda x: ValueError("x < 100, but got: {}".format(x)), condition=lambda x: x < 100)
        def func(x: int) -> int:
            return x

        # yapf: enable

        value_error = None  # type: Optional[ValueError]
        try:
            func(x=101)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("x < 100, but got: 101", str(value_error))

        value_error = None  # type: Optional[ValueError]
        try:
            func(x=-1)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("x > 0, but got: -1", str(value_error))


SOME_GLOBAL_CONSTANT = 10


class TestRepr(unittest.TestCase):
    def test_repr(self):
        a_repr = reprlib.Repr()
        a_repr.maxlist = 3

        @icontract.require(lambda x: len(x) < 10, a_repr=a_repr)
        def some_func(x: List[int]) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=list(range(10 * 1000)))
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("len(x) < 10:\n" "len(x) was 10000\n" "x was [0, 1, 2, ...]", str(pre_err))


class TestClass(unittest.TestCase):
    def test_nested_attribute(self):
        class B:
            def __init__(self) -> None:
                self.x = 0

            def x_plus_z(self, z: int) -> int:
                return self.x + z

            def __repr__(self) -> str:
                return "B(x={})".format(self.x)

        class A:
            def __init__(self) -> None:
                self.b = B()

            @icontract.require(lambda self: self.b.x > 0)
            def some_func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "A()"

        a = A()

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("self.b.x > 0:\n" "self was A()\n" "self.b was B(x=0)\n" "self.b.x was 0", str(pre_err))

    def test_nested_method(self):
        z = 10

        class C:
            def __init__(self, x: int) -> None:
                self._x = x

            def x(self) -> int:
                return self._x

            def __repr__(self) -> str:
                return "C(x={})".format(self._x)

        class B:
            def c(self, x: int) -> C:
                return C(x=x)

            def __repr__(self) -> str:
                return "B()"

        def gt_zero(value: int) -> bool:
            return value > 0

        class A:
            def __init__(self) -> None:
                self.b = B()

            @icontract.require(lambda self: pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) is None)
            def some_func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "A()"

        a = A()

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) is None:\n"
                         "gt_zero(self.b.c(x=0).x() + 12.2 * z) was True\n"
                         "pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) was PosixPath('True')\n"
                         "self was A()\n"
                         "self.b was B()\n"
                         "self.b.c(x=0) was C(x=0)\n"
                         "self.b.c(x=0).x() was 0\n"
                         "str(gt_zero(self.b.c(x=0).x() + 12.2 * z)) was 'True'\n"
                         "z was 10", str(pre_err))


class TestClosures(unittest.TestCase):
    def test_closure(self):
        y = 4
        z = 5

        @icontract.require(lambda x: x < y + z)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("x < y + z:\n" "x was 100\n" "y was 4\n" "z was 5", str(pre_err))

    def test_global(self):
        @icontract.require(lambda x: x < SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("x < SOME_GLOBAL_CONSTANT:\n" "SOME_GLOBAL_CONSTANT was 10\n" "x was 100", str(pre_err))

    def test_closure_and_global(self):
        y = 4

        @icontract.require(lambda x: x < y + SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        pre_err = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            pre_err = err

        self.assertIsNotNone(pre_err)
        self.assertEqual("x < y + SOME_GLOBAL_CONSTANT:\n"
                         "SOME_GLOBAL_CONSTANT was 10\n"
                         "x was 100\n"
                         "y was 4", str(pre_err))


if __name__ == '__main__':
    unittest.main()
