# pylint: disable=missing-docstring
import abc
import inspect
import unittest

import icontract


class TestIsabstract(unittest.TestCase):
    """Test that ``icontract.DBC`` plays nicely with ``abc.ABC``."""

    def test_that_DBC_issubclass_of_ABC(self) -> None:
        self.assertTrue(issubclass(icontract.DBC, abc.ABC))

    def test_that_a_concrete_class_is_a_subclass_of_ABC(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                pass

        self.assertTrue(issubclass(A, abc.ABC))

    def test_that_a_concrete_class_is_subclass_of_DBC_and_ABC(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                pass

        self.assertTrue(issubclass(A, icontract.DBC))
        self.assertTrue(issubclass(A, abc.ABC))
