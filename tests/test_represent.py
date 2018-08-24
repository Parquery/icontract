#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name,too-many-public-methods,no-self-use

import reprlib
import unittest

import icontract.represent


class TestReprValues(unittest.TestCase):
    def test_num(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x < 5, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)
        self.assertListEqual(['x was 3'], result)

    def test_str(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x != 'noi', condition_kwargs={"x": 'oi'}, a_repr=reprlib.aRepr)
        self.assertListEqual(["x was 'oi'"], result)

    @unittest.skip("Skipped due to an upstream bug in meta module.")
    def test_bytes(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x != b'noi', condition_kwargs={"x": b'oi'}, a_repr=reprlib.aRepr)
        self.assertListEqual(["x was b'oi'"], result)

    def test_bool(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x, condition_kwargs={"x": False}, a_repr=reprlib.aRepr)
        self.assertListEqual(["x was False"], result)

    def test_list(self):
        y = 1
        result = icontract.represent.repr_values(
            condition=lambda x: sum([1, y, x]) == 6, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)
        self.assertListEqual(['sum([1, y, x]) was 5', 'x was 3', 'y was 1'], result)

    def test_tuple(self):
        y = 1
        result = icontract.represent.repr_values(
            condition=lambda x: sum((1, y, x)) == 6, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)
        self.assertListEqual(['sum((1, y, x)) was 5', 'x was 3', 'y was 1'], result)

    def test_set(self):
        # Mind that 1 is also contained in the set.
        y = 1
        result = icontract.represent.repr_values(
            condition=lambda x: sum({1, y, x}) == 6, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)
        self.assertListEqual(['sum({1, y, x}) was 4', 'x was 3', 'y was 1'], result)

    @unittest.skip("Skipped due to an upstream bug in meta module.")
    def test_dict(self):
        y = "someKey"
        _ = icontract.represent.repr_values(
            condition=lambda x: len({y: 3, x: 8}) == 6, condition_kwargs={"x": "anotherKey"}, a_repr=reprlib.aRepr)

        raise NotImplementedError("Test not implemented due to an upstream bug in meta module.")

    def test_name_constant(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x is None, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_name(self):
        result = icontract.represent.repr_values(
            condition=lambda x: x > 3, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_unary_op(self):
        result = icontract.represent.repr_values(
            condition=lambda x: not (-x + 10 > 3), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_binary_op(self):
        result = icontract.represent.repr_values(
            condition=lambda x: -x + x - x * x / x // x**x % x > 3, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_binary_op_bit(self):
        result = icontract.represent.repr_values(
            condition=lambda x: ~(x << x | x & x ^ x) >> x > x, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_bool_op(self):
        # single "and" and "or"
        result = icontract.represent.repr_values(
            condition=lambda x: x > 3 and x < 10, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

        result = icontract.represent.repr_values(
            condition=lambda x: x > 3 or x < 10, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

        # multiple "and"
        result = icontract.represent.repr_values(
            condition=lambda x: x > 3 and x < 10 and x % 2 == 0, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_compare(self):
        # Chain the compare operators in a meaningless order and semantics
        result = icontract.represent.repr_values(
            condition=lambda x: 0 < x < 3 and x > 10 and x != 7 and x >= 10 and x <= 11 and x is not None and
                                x in [1, 2, 3] and x not in [1, 2, 3], condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3'], result)

    def test_call(self):
        def y() -> int:
            return 1

        result = icontract.represent.repr_values(
            condition=lambda x: x < y(), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3', 'y() was 1'], result)

    def test_if_exp_body(self):
        y = 5
        result = icontract.represent.repr_values(
            condition=lambda x: x < (x**2 if y == 5 else x**3), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3', 'y was 5'], result)

    def test_if_exp_orelse(self):
        y = 5
        result = icontract.represent.repr_values(
            condition=lambda x: x < (x**2 if y != 5 else x**3), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['x was 3', 'y was 5'], result)

    def test_attr(self):
        class A:
            def __init__(self) -> None:
                self.y = 3

            def __repr__(self) -> str:
                return "A()"

        a = A()
        result = icontract.represent.repr_values(
            condition=lambda x: x < a.y, condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['a was A()', 'a.y was 3', 'x was 3'], result)

    def test_index(self):
        lst = [1, 2, 3]
        result = icontract.represent.repr_values(
            condition=lambda x: x < lst[1], condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['lst was [1, 2, 3]', 'x was 3'], result)

    def test_slice(self):
        lst = [1, 2, 3]
        result = icontract.represent.repr_values(
            condition=lambda x: x < sum(lst[1:2:1]), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        self.assertListEqual(['lst was [1, 2, 3]', 'sum(lst[1:2:1]) was 2', 'x was 3'], result)

    @unittest.skip("Skipped due to an upstream bug in meta module.")
    def test_lambda(self):
        _ = icontract.represent.repr_values(
            condition=lambda x: x < (lambda: 4).__call__(), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        raise NotImplementedError("Test not implemented due to an upstream bug in meta module.")

    @unittest.skip("Skipped due to an upstream bug in meta module.")
    def test_list_comprehension(self):
        lst = [1, 2, 3]
        _ = icontract.represent.repr_values(
            condition=lambda x: x < sum([i**2 for i in lst]), condition_kwargs={"x": 3}, a_repr=reprlib.aRepr)

        raise NotImplementedError("Test not implemented due to an upstream bug in meta module.")


if __name__ == '__main__':
    unittest.main()
