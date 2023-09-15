# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument

import textwrap
import unittest
from typing import NamedTuple, Optional  # pylint: disable=unused-import

import icontract
import tests.error


class TestOK(unittest.TestCase):
    def test_on_named_tuple(self) -> None:
        # This test is related to the issue #171.
        #
        # The test could not be executed under Python 3.6 as the ``inspect`` module
        # could not figure out the type of getters.
        @icontract.invariant(lambda self: self.first > 0)
        class RightHalfPlanePoint(NamedTuple):
            first: int
            second: int

        _ = RightHalfPlanePoint(1, 0)

        self.assertEqual(
            "Create new instance of RightHalfPlanePoint(first, second)",
            RightHalfPlanePoint.__new__.__doc__,
        )


class TestViolation(unittest.TestCase):
    def test_on_named_tuple(self) -> None:
        # This test is related to the issue #171.
        #
        # The test could not be executed under Python 3.6 as the ``inspect`` module
        # could not figure out the type of getters.
        @icontract.invariant(lambda self: self.second > 0)
        @icontract.invariant(lambda self: self.first > 0)
        class RightHalfPlanePoint(NamedTuple):
            first: int
            second: int

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            _ = RightHalfPlanePoint(1, -1)
        except icontract.ViolationError as err:
            violation_error = err

        self.assertIsNotNone(violation_error)
        self.assertEqual(
            textwrap.dedent(
                """\
                self.second > 0:
                self was RightHalfPlanePoint(first=1, second=-1)
                self.second was -1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


if __name__ == "__main__":
    unittest.main()
