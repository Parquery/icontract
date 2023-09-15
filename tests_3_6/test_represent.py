#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pylint: disable=unused-argument

import textwrap
import unittest
from typing import Optional  # pylint: disable=unused-import

import icontract._represent
import tests.error
import tests.mock


class TestLiteralStringInterpolation(unittest.TestCase):
    def test_plain_string(self) -> None:
        # pylint: disable=f-string-without-interpolation
        @icontract.require(lambda x: f"something" == "")  # type: ignore
        def func(x: float) -> float:
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
                f"something" == "":
                f"something" was 'something'
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_simple_interpolation(self) -> None:
        @icontract.require(lambda x: f"{x}" == "")
        def func(x: float) -> float:
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
                f"{x}" == "":
                f"{x}" was '0'
                x was 0"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_string_formatting(self) -> None:
        @icontract.require(lambda x: f"{x!s}" == "")
        def func(x: float) -> float:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1.984)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                f"{x!s}" == "":
                f"{x!s}" was '1.984'
                x was 1.984"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_repr_formatting(self) -> None:
        @icontract.require(lambda x: f"{x!r}" == "")
        def func(x: float) -> float:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1.984)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                f"{x!r}" == "":
                f"{x!r}" was '1.984'
                x was 1.984"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_ascii_formatting(self) -> None:
        @icontract.require(lambda x: f"{x!a}" == "")
        def func(x: float) -> float:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1.984)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                f"{x!a}" == "":
                f"{x!a}" was '1.984'
                x was 1.984"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_format_spec(self) -> None:
        @icontract.require(lambda x: f"{x:.3}" == "")
        def func(x: float) -> float:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1.984)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                f"{x:.3}" == "":
                f"{x:.3}" was '1.98'
                x was 1.984"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )

    def test_conversion_and_format_spec(self) -> None:
        @icontract.require(lambda x: f"{x!r:.3}" == "")
        def func(x: float) -> float:
            return x

        violation_err = None  # type: Optional[icontract.ViolationError]
        try:
            func(x=1.984)
        except icontract.ViolationError as err:
            violation_err = err

        self.assertIsNotNone(violation_err)
        self.assertEqual(
            textwrap.dedent(
                """\
                f"{x!r:.3}" == "":
                f"{x!r:.3}" was '1.9'
                x was 1.984"""
            ),
            tests.error.wo_mandatory_location(str(violation_err)),
        )


if __name__ == "__main__":
    unittest.main()
