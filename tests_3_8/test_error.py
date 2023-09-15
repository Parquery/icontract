# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unused-variable

import textwrap
import unittest
from typing import Optional

import icontract

import tests.error


class TestNoneSpecified(unittest.TestCase):
    def test_that_original_call_arguments_do_not_shadow_condition_variables_in_the_generated_message(
        self,
    ) -> None:
        # ``y`` in the condition shadows the ``y`` in the arguments, but the condition lambda does not refer to
        # the original ``y``.
        @icontract.require(lambda x: (y := x + 3, x > 0)[1])
        def some_func(x: int, y: int) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(x=-1, y=-1000)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None
        self.assertEqual(
            textwrap.dedent(
                """\
                (y := x + 3, x > 0)[1]:
                (y := x + 3, x > 0)[1] was False
                x was -1
                y was 2"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


if __name__ == "__main__":
    unittest.main()
