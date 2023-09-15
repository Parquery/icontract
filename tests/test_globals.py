# pylint: disable=missing-docstring

import unittest

import icontract


class TestSlow(unittest.TestCase):
    def test_slow_set(self) -> None:
        self.assertTrue(
            icontract.SLOW,
            "icontract.SLOW was not set. Please check if you set the environment variable ICONTRACT_SLOW "
            "before running this test.",
        )


if __name__ == "__main__":
    unittest.main()
