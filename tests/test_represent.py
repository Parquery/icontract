#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda

import pathlib
import re
import reprlib
import textwrap
import unittest
from typing import Optional, List, Tuple, Any  # pylint: disable=unused-import

import numpy

import icontract._represent
import tests.error
import tests.mock


class TestReprValues(unittest.TestCase):
    def test_num(self) -> None:
        @icontract.require(lambda x: x < 5)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=100)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x < 5: x was 100", tests.error.wo_mandatory_location(str(violation_error))
        )

    def test_str(self) -> None:
        @icontract.require(lambda x: x != "oi")
        def func(x: str) -> str:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x="oi")
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            """x != "oi": x was 'oi'""",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_bytes(self) -> None:
        @icontract.require(lambda x: x != b"oi")
        def func(x: bytes) -> bytes:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=b"oi")
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            """x != b"oi": x was b'oi'""",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_bool(self) -> None:
        @icontract.require(lambda x: x is not False)
        def func(x: bool) -> bool:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=False)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x is not False: x was False",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_list(self) -> None:
        y = 1

        @icontract.require(lambda x: sum([1, y, x]) == 1)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                sum([1, y, x]) == 1:
                sum([1, y, x]) was 5
                x was 3
                y was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_tuple(self) -> None:
        y = 1

        @icontract.require(lambda x: sum((1, y, x)) == 1)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                sum((1, y, x)) == 1:
                sum((1, y, x)) was 5
                x was 3
                y was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_set(self) -> None:
        y = 2

        @icontract.require(lambda x: sum({1, y, x}) == 1)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=3)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                sum({1, y, x}) == 1:
                sum({1, y, x}) was 6
                x was 3
                y was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_dict(self) -> None:
        y = "someKey"

        @icontract.require(lambda x: len({y: 3, x: 8}) == 6)
        def func(x: str) -> str:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x="oi")
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len({y: 3, x: 8}) == 6:
                len({y: 3, x: 8}) was 2
                x was 'oi'
                y was 'someKey'"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_unary_op(self) -> None:
        @icontract.require(lambda x: not -x + 10 > 3)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "not -x + 10 > 3: x was 1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_binary_op(self) -> None:
        @icontract.require(lambda x: -x + x - x * x / x // x**x % x > 3)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "-x + x - x * x / x // x**x % x > 3: x was 1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_binary_op_bit(self) -> None:
        @icontract.require(lambda x: ~(x << x | x & x ^ x) >> x > x)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "~(x << x | x & x ^ x) >> x > x: x was 1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_bool_op_single(self) -> None:
        # pylint: disable=chained-comparison
        @icontract.require(lambda x: x > 3 and x < 10)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x > 3 and x < 10: x was 1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_bool_op_multiple(self) -> None:
        # pylint: disable=chained-comparison
        @icontract.require(lambda x: x > 3 and x < 10 and x % 2 == 0)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            "x > 3 and x < 10 and x % 2 == 0: x was 1",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_compare(self) -> None:
        # pylint: disable=chained-comparison

        # Chain the compare operators in a meaningless order and semantics
        @icontract.require(
            lambda x: 0 < x < 3
            and x > 10
            and x != 7
            and x >= 10
            and x <= 11
            and x is not None
            and x in [1, 2, 3]
            and x not in [1, 2, 3]
        )
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            """\
0 < x < 3
    and x > 10
    and x != 7
    and x >= 10
    and x <= 11
    and x is not None
    and x in [1, 2, 3]
    and x not in [1, 2, 3]: x was 1""",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_call(self) -> None:
        def y() -> int:
            return 1

        @icontract.require(lambda x: x < y())
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < y():
                x was 1
                y() was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_if_exp_body(self) -> None:
        y = 5

        @icontract.require(lambda x: x < (x**2 if y == 5 else x**3))
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < (x**2 if y == 5 else x**3):
                x was 1
                y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_if_exp_orelse(self) -> None:
        y = 5

        @icontract.require(lambda x: x < (x**2 if y != 5 else x**3))
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < (x**2 if y != 5 else x**3):
                x was 1
                y was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_attr(self) -> None:
        class A:
            def __init__(self) -> None:
                self.y = 3

            def __repr__(self) -> str:
                return "an instance of {}".format(self.__class__.__name__)

        a = A()

        @icontract.require(lambda x: x > a.y)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > a.y:
                a was an instance of A
                a.y was 3
                x was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_index(self) -> None:
        lst = [1, 2, 3]

        @icontract.require(lambda x: x > lst[1])
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > lst[1]:
                lst was [1, 2, 3]
                lst[1] was 2
                x was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_slice(self) -> None:
        lst = [1, 2, 3]

        @icontract.require(lambda x: x > sum(lst[1:2:1]))
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x > sum(lst[1:2:1]):
                lst was [1, 2, 3]
                lst[1:2:1] was [2]
                sum(lst[1:2:1]) was 2
                x was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_ext_slice(self) -> None:
        class SomeClass:
            def __getitem__(self, item: Any) -> Any:
                return item

            def __repr__(self) -> str:
                return "<instance of SomeClass>"

        @icontract.require(lambda something: something[1, 2:3] is None)
        def func(something: SomeClass) -> None:
            pass

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            an_instance = SomeClass()
            func(something=an_instance)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                something[1, 2:3] is None:
                something was <instance of SomeClass>
                something[1, 2:3] was (1, slice(2, 3, None))"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_lambda(self) -> None:
        @icontract.require(lambda x: x > (lambda y: y + 4).__call__(y=7))  # type: ignore
        def func(x: int) -> int:
            return x

        runtime_error = None  # type: Optional[RuntimeError]
        try:
            func(x=1)
        except RuntimeError as err:
            runtime_error = err

        assert runtime_error is not None
        assert runtime_error.__cause__ is not None
        assert isinstance(runtime_error.__cause__, NotImplementedError)

        not_implemented_error = runtime_error.__cause__

        self.assertEqual(
            "Re-computation of in-line lambda functions is not supported since it is quite tricky to implement and "
            "we decided to implement it only once there is a real need for it. "
            "Please make a feature request on https://github.com/Parquery/icontract",
            str(not_implemented_error),
        )


class TestGeneratorExpr(unittest.TestCase):
    def test_attr_on_element(self) -> None:
        @icontract.ensure(
            lambda result: all(single_res[1].is_absolute() for single_res in result)
        )
        def some_func() -> List[Tuple[pathlib.Path, pathlib.Path]]:
            return [(pathlib.Path("/home/file1"), pathlib.Path("home/file2"))]

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func()
        except icontract.ViolationError as err:
            violation_error = err

        # This dummy path is necessary to obtain the class name.
        dummy_path = pathlib.Path("/also/doesnt/exist")

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                all(single_res[1].is_absolute() for single_res in result):
                all(single_res[1].is_absolute() for single_res in result) was False, e.g., with
                  single_res = ({0}('/home/file1'), {0}('home/file2'))
                result was [({0}('/home/file1'), {0}('home/file2'))]"""
            ).format(dummy_path.__class__.__name__),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_multiple_for(self) -> None:
        lst = [[1, 2], [3]]

        # fmt: off
        @icontract.require(
            lambda x: all(item == x for sublst in lst for item in sublst)
        )
        # fmt: on
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        self.assertEqual(
            textwrap.dedent(
                """\
                all(item == x for sublst in lst for item in sublst):
                all(item == x for sublst in lst for item in sublst) was False, e.g., with
                  sublst = [1, 2]
                  item = 1
                lst was [[1, 2], [3]]
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_zip_and_multiple_for(self) -> None:
        # Taken from a solution for Advent of Code 2020 day 11.
        @icontract.ensure(
            lambda layout, result: all(
                cell == result_cell
                for row, result_row in zip(layout, result[0])
                for cell, result_cell in zip(row, result_row)
                if cell == "."
            ),
            "Floor remains floor",
        )
        def apply(layout: List[List[str]]) -> Tuple[List[List[str]], int]:
            height = len(layout)
            width = len(layout[0])

            result = [[""] * width] * height
            return result, 0

        layout = [["L", ".", "#"], [".", "#", "#"]]

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _, _ = apply(layout=layout)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        text = re.sub(
            r"<zip object at 0x[0-9a-fA-F]+>",
            "<zip object at some address>",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

        self.assertEqual(
            textwrap.dedent(
                """\
                Floor remains floor: all(
                        cell == result_cell
                        for row, result_row in zip(layout, result[0])
                        for cell, result_cell in zip(row, result_row)
                        if cell == "."
                    ):
                all(
                        cell == result_cell
                        for row, result_row in zip(layout, result[0])
                        for cell, result_cell in zip(row, result_row)
                        if cell == "."
                    ) was False, e.g., with
                  row = ['L', '.', '#']
                  result_row = ['', '', '']
                  cell = '.'
                  result_cell = ''
                layout was [['L', '.', '#'], ['.', '#', '#']]
                result was ([['', '', ''], ['', '', '']], 0)
                result[0] was [['', '', ''], ['', '', '']]
                zip(layout, result[0]) was <zip object at some address>"""
            ),
            text,
        )


class TestListComprehension(unittest.TestCase):
    def test_single(self) -> None:
        lst = [1, 2, 3]

        @icontract.require(lambda x: [item < x for item in lst if item % x == 0] == [])
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                [item < x for item in lst if item % x == 0] == []:
                [item < x for item in lst if item % x == 0] was [False]
                lst was [1, 2, 3]
                x was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_nested(self) -> None:
        lst_of_lsts = [[1, 2, 3]]

        # fmt: off
        @icontract.require(
            lambda:
            [
                [item for item in sublst if item > 0]
                for sublst in lst_of_lsts
            ] == [[]]
        )
        # fmt: on
        def func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                [
                        [item for item in sublst if item > 0]
                        for sublst in lst_of_lsts
                    ] == [[]]:
                [
                        [item for item in sublst if item > 0]
                        for sublst in lst_of_lsts
                    ] was [[1, 2, 3]]
                lst_of_lsts was [[1, 2, 3]]"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestSetComprehension(unittest.TestCase):
    def test_single(self) -> None:
        lst = [1, 2, 3]

        @icontract.require(
            lambda x: len({item < x for item in lst if item % x == 0}) == 0
        )
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len({item < x for item in lst if item % x == 0}) == 0:
                len({item < x for item in lst if item % x == 0}) was 1
                lst was [1, 2, 3]
                x was 2
                {item < x for item in lst if item % x == 0} was {False}"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_nested(self) -> None:
        lst_of_lsts = [[1, 2, 3]]

        # fmt: off
        @icontract.require(
            lambda:
            {
                len({item for item in lst if item > 0})
                for lst in lst_of_lsts
            } == set()
        )
        # fmt: on
        def func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                {
                        len({item for item in lst if item > 0})
                        for lst in lst_of_lsts
                    } == set():
                lst_of_lsts was [[1, 2, 3]]
                set() was set()
                {
                        len({item for item in lst if item > 0})
                        for lst in lst_of_lsts
                    } was {3}"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestDictComprehension(unittest.TestCase):
    def test_single(self) -> None:
        @icontract.require(lambda x: len({i: i**2 for i in range(x)}) == 0)
        def func(x: int) -> int:
            return x

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=2)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len({i: i**2 for i in range(x)}) == 0:
                len({i: i**2 for i in range(x)}) was 2
                range(x) was range(0, 2)
                x was 2
                {i: i**2 for i in range(x)} was {0: 0, 1: 1}"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_nested(self) -> None:
        lst_of_lsts = [[1, 2, 3]]

        # fmt: off
        @icontract.require(
            lambda:
            len({
                len(lst): {item: item for item in lst}
                for lst in lst_of_lsts
            }) == 0
        )
        # fmt: on
        def func() -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len({
                        len(lst): {item: item for item in lst}
                        for lst in lst_of_lsts
                    }) == 0:
                len({
                        len(lst): {item: item for item in lst}
                        for lst in lst_of_lsts
                    }) was 1
                lst_of_lsts was [[1, 2, 3]]
                {
                        len(lst): {item: item for item in lst}
                        for lst in lst_of_lsts
                    } was {3: {1: 1, 2: 2, 3: 3}}"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestConditionAsText(unittest.TestCase):
    """Test decompilation of the condition."""

    def test_single_line(self) -> None:
        # fmt: off
        @icontract.require(lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # fmt: on

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            "x > 3: x was 0", tests.error.wo_mandatory_location(str(violation_err))
        )

    def test_condition_on_next_line(self) -> None:
        # fmt: off
        @icontract.require(
            lambda x: x > 3)
        def func(x: int) -> int:
            return x

        # fmt: on

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            "x > 3: x was 0", tests.error.wo_mandatory_location(str(violation_err))
        )

    def test_condition_on_multiple_lines(self) -> None:
        # fmt: off
        @icontract.require(
            lambda x:
            x
            >
            3)
        def func(x: int) -> int:
            return x

        # fmt: on

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                x
                    >
                    3: x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_with_multiple_lambdas_on_a_line(self) -> None:
        # pylint: disable=unnecessary-lambda
        # fmt: off
        @icontract.require(
            error=lambda x: ValueError("x > 0, but got: {}".format(x)), condition=lambda x: x > 0)
        @icontract.require(
            error=lambda x: ValueError("x < 100, but got: {}".format(x)), condition=lambda x: x < 100)
        def func(x: int) -> int:
            return x

        # fmt: on

        value_error = None  # type: Optional[ValueError]
        try:
            func(x=101)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("x < 100, but got: 101", str(value_error))

        value_error = None
        try:
            func(x=-1)
        except ValueError as err:
            value_error = err

        self.assertIsNotNone(value_error)
        self.assertEqual("x > 0, but got: -1", str(value_error))


SOME_GLOBAL_CONSTANT = 10


class TestRepr(unittest.TestCase):
    def test_repr(self) -> None:
        a_repr = reprlib.Repr()
        a_repr.maxlist = 3

        @icontract.require(lambda x: len(x) < 10, a_repr=a_repr)
        def some_func(x: List[int]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=list(range(10 * 1000)))
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len(x) < 10:
                len(x) was 10000
                x was [0, 1, 2, ...]"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestClass(unittest.TestCase):
    def test_nested_attribute(self) -> None:
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

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.b.x > 0:
                self was A()
                self.b was B(x=0)
                self.b.x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_nested_method(self) -> None:
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

            @icontract.require(
                lambda self: pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z)))
                is None
            )
            def some_func(self) -> None:
                pass

            def __repr__(self) -> str:
                return "A()"

        a = A()

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            a.some_func()
        except icontract.ViolationError as err:
            violation_error = err

        # This dummy path is necessary to obtain the class name.
        dummy_path = pathlib.Path("/just/a/dummy/path")

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z)))
                    is None:
                gt_zero(self.b.c(x=0).x() + 12.2 * z) was True
                pathlib.Path(str(gt_zero(self.b.c(x=0).x() + 12.2 * z))) was {}('True')
                self was A()
                self.b was B()
                self.b.c(x=0) was C(x=0)
                self.b.c(x=0).x() was 0
                str(gt_zero(self.b.c(x=0).x() + 12.2 * z)) was 'True'
                z was 10"""
            ).format(dummy_path.__class__.__name__),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestClosures(unittest.TestCase):
    def test_closure(self) -> None:
        y = 4
        z = 5

        @icontract.require(lambda x: x < y + z)
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < y + z:
                x was 100
                y was 4
                z was 5"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_global(self) -> None:
        @icontract.require(lambda x: x < SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < SOME_GLOBAL_CONSTANT:
                SOME_GLOBAL_CONSTANT was 10
                x was 100"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_closure_and_global(self) -> None:
        y = 4

        @icontract.require(lambda x: x < y + SOME_GLOBAL_CONSTANT)
        def some_func(x: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=100)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                x < y + SOME_GLOBAL_CONSTANT:
                SOME_GLOBAL_CONSTANT was 10
                x was 100
                y was 4"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestWithNumpyMock(unittest.TestCase):
    def test_that_mock_works(self) -> None:
        arr = tests.mock.NumpyArray(values=[-3, 3])

        value_err = None  # type: Optional[ValueError]
        try:
            not (arr > 0)  # pylint: disable=superfluous-parens,unneeded-not
        except ValueError as err:
            value_err = err

        self.assertIsNotNone(value_err)
        self.assertEqual(
            "The truth value of an array with more than one element is ambiguous.",
            str(value_err),
        )

    def test_that_single_comparator_works(self) -> None:
        @icontract.require(lambda arr: (arr > 0).all())
        def some_func(arr: tests.mock.NumpyArray) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(arr=tests.mock.NumpyArray(values=[-3, 3]))
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                (arr > 0).all():
                (arr > 0).all() was False
                arr was NumpyArray([-3, 3])"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_that_multiple_comparators_fail(self) -> None:
        """
        Test that multiple comparators in an expression will fail.

        Multiple comparisons are not implemented in numpy as of version <= 1.16.
        The following snippet exemplifies the problem:

        .. code-block:: python

            import numpy as np

            x = np.array([-3, 3])
            -100 < x < 100
            Traceback (most recent call last):
            ...
            ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()

        :return:
        """

        @icontract.require(lambda arr: (-3 < arr < 0).all())
        def some_func(arr: tests.mock.NumpyArray) -> None:
            pass

        value_err = None  # type: Optional[ValueError]
        try:
            some_func(arr=tests.mock.NumpyArray(values=[-10, -1]))
        except ValueError as err:
            value_err = err

        self.assertIsNotNone(value_err)
        self.assertEqual(
            "The truth value of an array with more than one element is ambiguous.",
            str(value_err),
        )


class TestNumpyArrays(unittest.TestCase):
    def test_arange_in_args(self) -> None:
        # This test case addresses ``visit_Call` in the Visitor.
        # See: https://github.com/Parquery/icontract/issues/229

        @icontract.require(lambda arr: len(arr) > 2)
        def some_func(arr: Any) -> None:
            return

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(arr=numpy.arange(2))
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                len(arr) > 2:
                arr was array([0, 1])
                len(arr) was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_arange_in_kwargs_values(self) -> None:
        # This test case addresses ``visit_Call` in the Visitor.
        # See: https://github.com/Parquery/icontract/issues/229

        def custom_len(arr: Any) -> int:
            return len(arr)

        @icontract.require(lambda arr: custom_len(arr=arr) > 2)
        def some_func(arr: Any) -> None:
            return

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(arr=numpy.arange(2))
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                custom_len(arr=arr) > 2:
                arr was array([0, 1])
                custom_len(arr=arr) was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestRecomputationFailure(unittest.TestCase):
    def test_that_the_error_is_informative(self) -> None:
        counter = 0

        def some_condition() -> bool:
            nonlocal counter
            if counter == 0:
                # The first time we return False, so that the pre-condition fails.
                counter += 1
                return False

            # Every next time we raise the exception, so that the re-computation fails.
            raise RuntimeError("Recomputation shall fail.")

        @icontract.require(lambda: some_condition())
        def some_func() -> None:
            pass

        runtime_error = None  # type: Optional[RuntimeError]
        try:
            some_func()
        except RuntimeError as err:
            runtime_error = err

        assert runtime_error is not None

        lines = [
            re.sub(
                r"^File (.*), line ([0-9]+) in (.*):$",
                "File <erased path>, line <erased line> in <erased function>:",
                line,
            )
            for line in str(runtime_error).splitlines()
        ]
        text = "\n".join(lines)

        self.assertEqual(
            textwrap.dedent(
                """\
            Failed to recompute the values of the contract condition:
            File <erased path>, line <erased line> in <erased function>:
            lambda: some_condition()"""
            ),
            text,
        )


class TestTracingAll(unittest.TestCase):
    def test_global_variable(self) -> None:
        # fmt: off
        @icontract.require(
            lambda lst:
            all(
                value > SOME_GLOBAL_CONSTANT
                for value in lst
            )
        )
        # fmt: on
        def func(lst: List[int]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(lst=[-1, -2])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        got = tests.error.wo_mandatory_location(str(violation_error))

        self.assertEqual(
            textwrap.dedent(
                """\
                all(
                        value > SOME_GLOBAL_CONSTANT
                        for value in lst
                    ):
                SOME_GLOBAL_CONSTANT was 10
                all(
                        value > SOME_GLOBAL_CONSTANT
                        for value in lst
                    ) was False, e.g., with
                  value = -1
                lst was [-1, -2]"""
            ),
            got,
        )

    def test_formatted_string(self) -> None:
        # fmt: off
        @icontract.require(
            lambda lst:
            all(
                f'{value}' == 'x'
                for value in lst
            )
        )
        # fmt: on
        def func(lst: List[str]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(lst=["y"])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        got = tests.error.wo_mandatory_location(str(violation_error))

        self.assertEqual(
            textwrap.dedent(
                """\
                all(
                        f'{value}' == 'x'
                        for value in lst
                    ):
                all(
                        f'{value}' == 'x'
                        for value in lst
                    ) was False, e.g., with
                  value = 'y'
                lst was ['y']"""
            ),
            got,
        )

    def test_two_fors_and_two_ifs(self) -> None:
        # fmt: off
        @icontract.require(
            lambda matrix:
            all(
                cell > SOME_GLOBAL_CONSTANT
                for i, row in enumerate(matrix)
                if i > 0
                for j, cell in enumerate(row)
                if i == j
            )
        )
        # fmt: on
        def func(matrix: List[List[int]]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(matrix=[[-1, -1], [-1, -1]])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        got = re.sub(
            r"<enumerate object at 0x[0-9A-Za-z]+>",
            "<enumerate object at 0x...>",
            tests.error.wo_mandatory_location(str(violation_error)),
        )

        self.assertEqual(
            textwrap.dedent(
                """\
            all(
                    cell > SOME_GLOBAL_CONSTANT
                    for i, row in enumerate(matrix)
                    if i > 0
                    for j, cell in enumerate(row)
                    if i == j
                ):
            SOME_GLOBAL_CONSTANT was 10
            all(
                    cell > SOME_GLOBAL_CONSTANT
                    for i, row in enumerate(matrix)
                    if i > 0
                    for j, cell in enumerate(row)
                    if i == j
                ) was False, e.g., with
              i = 1
              row = [-1, -1]
              j = 1
              cell = -1
            enumerate(matrix) was <enumerate object at 0x...>
            matrix was [[-1, -1], [-1, -1]]"""
            ),
            got,
        )

    def test_nested_all(self) -> None:
        # Nesting is not recursively followed by design. Only the outer-most all expression should be traced.

        # fmt: off
        @icontract.require(
            lambda lst_of_lsts:
            all(
                all(item > 0 for item in sublst)
                for sublst in lst_of_lsts
            )
        )
        # fmt: on
        def func(lst_of_lsts: List[List[int]]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(lst_of_lsts=[[-1, -1]])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                all(
                        all(item > 0 for item in sublst)
                        for sublst in lst_of_lsts
                    ):
                all(
                        all(item > 0 for item in sublst)
                        for sublst in lst_of_lsts
                    ) was False, e.g., with
                  sublst = [-1, -1]
                lst_of_lsts was [[-1, -1]]"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_property_of_an_object_represented(self) -> None:
        class Something:
            def __init__(self) -> None:
                self.some_property = 0

            def __repr__(self) -> str:
                return "Something()"

        # fmt: off
        @icontract.require(
            lambda something, lst:
            all(
                item > something.some_property
                for item in lst
            )
        )
        # fmt: on
        def func(something: Something, lst: List[int]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(something=Something(), lst=[-1])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)

        self.assertEqual(
            textwrap.dedent(
                """\
                all(
                        item > something.some_property
                        for item in lst
                    ):
                all(
                        item > something.some_property
                        for item in lst
                    ) was False, e.g., with
                  item = -1
                lst was [-1]
                something was Something()
                something.some_property was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )

    def test_shadows_in_targets(self) -> None:
        # fmt: off
        @icontract.require(
            lambda lst_of_lsts:
            all(
                all(item > 0 for item in item)
                for item in lst_of_lsts
            )
        )
        # fmt: on
        def func(lst_of_lsts: List[List[int]]) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            func(lst_of_lsts=[[-1, -1]])
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                all(
                        all(item > 0 for item in item)
                        for item in lst_of_lsts
                    ):
                all(
                        all(item > 0 for item in item)
                        for item in lst_of_lsts
                    ) was False, e.g., with
                  item = [-1, -1]
                lst_of_lsts was [[-1, -1]]"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


if __name__ == "__main__":
    unittest.main()
