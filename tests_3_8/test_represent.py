#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pylint: disable=unused-argument
import textwrap
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract._recompute
import icontract._represent
import tests.error
import tests.mock


class TestReprValues(unittest.TestCase):
    def test_named_expression(self) -> None:
        @icontract.require(
            lambda x: (t := x + 1) and t > 1
        )  # pylint: disable=undefined-variable
        def func(x: int) -> int:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=0)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                (t := x + 1) and t > 1:
                t was 1
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )


if __name__ == "__main__":
    unittest.main()
