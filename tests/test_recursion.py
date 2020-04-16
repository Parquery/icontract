# pylint: disable=missing-docstring
# pylint: disable=no-self-use
import unittest
from typing import List

import icontract


class TestOK(unittest.TestCase):
    def test_recursive_preconditions(self) -> None:
        order = []  # type: List[str]

        @icontract.require(lambda: another_func())  # pylint: disable=unnecessary-lambda
        @icontract.require(lambda: yet_another_func())  # pylint: disable=unnecessary-lambda
        def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.require(lambda: some_func())  # pylint: disable=unnecessary-lambda
        @icontract.require(lambda: yet_yet_another_func())  # pylint: disable=unnecessary-lambda
        def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        some_func()

        self.assertListEqual(['yet_another_func', 'yet_yet_another_func', 'some_func', 'another_func', 'some_func'],
                             order)

    def test_recursive_postconditions(self) -> None:
        order = []  # type: List[str]

        @icontract.ensure(lambda: another_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(lambda: yet_another_func())  # pylint: disable=unnecessary-lambda
        def some_func() -> bool:
            order.append(some_func.__name__)
            return True

        @icontract.ensure(lambda: some_func())  # pylint: disable=unnecessary-lambda
        @icontract.ensure(lambda: yet_yet_another_func())  # pylint: disable=unnecessary-lambda
        def another_func() -> bool:
            order.append(another_func.__name__)
            return True

        def yet_another_func() -> bool:
            order.append(yet_another_func.__name__)
            return True

        def yet_yet_another_func() -> bool:
            order.append(yet_yet_another_func.__name__)
            return True

        some_func()

        self.assertListEqual(['some_func', 'yet_another_func', 'another_func', 'yet_yet_another_func', 'some_func'],
                             order)

    def test_recursive_invariants(self) -> None:
        order = []  # type: List[str]

        @icontract.invariant(lambda self: self.some_func())  # pylint: disable=no-member
        class SomeClass(icontract.DBC):
            def __init__(self) -> None:
                order.append('__init__')

            def some_func(self) -> bool:
                order.append('some_func')
                return True

            def another_func(self) -> bool:
                order.append('another_func')
                return True

        some_instance = SomeClass()
        self.assertListEqual(['__init__', 'some_func'], order)

        # Reset for the next experiment
        order = []

        some_instance.another_func()
        self.assertListEqual(['some_func', 'another_func', 'some_func'], order)


if __name__ == '__main__':
    unittest.main()
