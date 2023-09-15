# pylint: disable=missing-docstring
# pylint: disable=broad-except
# pylint: disable=invalid-name
import unittest
from typing import Optional

import dpcontracts


class TestDpcontracts(unittest.TestCase):
    def test_recursion_unhandled_in_preconditions(self) -> None:
        @dpcontracts.require("must another_func", lambda args: another_func())  # type: ignore
        @dpcontracts.require("must yet_another_func", lambda args: yet_another_func())  # type: ignore
        def some_func() -> bool:
            return True

        @dpcontracts.require("must some_func", lambda args: some_func())  # type: ignore
        @dpcontracts.require("must yet_yet_another_func", lambda args: yet_yet_another_func())  # type: ignore
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

        self.assertIsNotNone(cause_err)
        self.assertIsInstance(cause_err, RecursionError)

    def test_inheritance_of_postconditions_incorrect(self) -> None:
        class A:
            @dpcontracts.ensure("dummy contract", lambda args, result: result % 2 == 0)  # type: ignore
            def some_func(self) -> int:
                return 2

        class B(A):
            @dpcontracts.ensure("dummy contract", lambda args, result: result % 3 == 0)  # type: ignore
            def some_func(self) -> int:
                # The result 9 satisfies the postcondition of B.some_func, but not A.some_func.
                return 9

        b = B()
        # The correct behavior would be to throw an exception here.
        b.some_func()


if __name__ == "__main__":
    unittest.main()
