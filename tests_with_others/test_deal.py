# pylint: disable=missing-docstring
# pylint: disable=broad-except
# pylint: disable=invalid-name

import unittest
from typing import Optional

import deal


class TestDeal(unittest.TestCase):
    def test_recursion_handled_in_preconditions(self) -> None:
        @deal.pre(lambda _: another_func())  # type: ignore
        @deal.pre(lambda _: yet_another_func())
        def some_func() -> bool:
            return True

        @deal.pre(lambda _: some_func())
        @deal.pre(lambda _: yet_yet_another_func())
        def another_func() -> bool:
            return True

        def yet_another_func() -> bool:
            return True

        def yet_yet_another_func() -> bool:
            return True

        cause_err = None  # type: Optional[BaseException]
        try:
            some_func()
        except Exception as err:
            cause_err = err.__cause__

        self.assertIsNone(cause_err, "Deal can deal with the recursive contracts.")

    def test_inheritance_of_postconditions_incorrect(self) -> None:
        class A:
            @deal.post(lambda result: result % 2 == 0)
            def some_func(self) -> int:
                return 2

        class B(A):
            @deal.post(lambda result: result % 3 == 0)
            def some_func(self) -> int:
                # The result 9 satisfies the postcondition of B.some_func, but not A.some_func.
                return 9

        b = B()
        # The correct behavior would be to throw an exception here.
        b.some_func()


if __name__ == "__main__":
    unittest.main()
