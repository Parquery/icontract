# pylint: disable=missing-docstring
import pathlib
import subprocess
import sys
import tempfile
import unittest

if sys.version_info < (3, 8):
    raise unittest.SkipTest(
        (
            "Mypy since 1.5 dropped support for Python 3.7 and "
            "you are running Python {}, so skipping."
        ).format(sys.version_info)
    )


class TestMypyDecorators(unittest.TestCase):
    def test_functions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mypy_fail_case_") as tmpdir:
            content = '''\
"""Implement a fail case for mypy to test that the types are preserved with the decorators."""

import icontract

@icontract.require(lambda x: x > 0)
def f1(x: int) -> int:
    return x
f1("this is wrong")

@icontract.ensure(lambda result: result > 0)
def f2(x: int) -> int:
    return x
f2("this is wrong")

@icontract.snapshot(lambda x: x)
def f3(x: int) -> int:
    return x
f3("this is wrong")
'''

            pth = pathlib.Path(tmpdir) / "source.py"
            pth.write_text(content, encoding="utf-8")

            with subprocess.Popen(
                ["mypy", "--strict", str(pth)],
                universal_newlines=True,
                stdout=subprocess.PIPE,
            ) as proc:
                out, err = proc.communicate()

                self.assertIsNone(err)
                self.assertEqual(
                    """\
{path}:8: error: Argument 1 to "f1" has incompatible type "str"; expected "int"  [arg-type]
{path}:13: error: Argument 1 to "f2" has incompatible type "str"; expected "int"  [arg-type]
{path}:18: error: Argument 1 to "f3" has incompatible type "str"; expected "int"  [arg-type]
Found 3 errors in 1 file (checked 1 source file)
""".format(
                        path=pth
                    ),
                    out,
                )

    def test_class_type_when_decorated_with_invariant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mypy_fail_case_") as tmpdir:
            content = '''\
"""Implement a passing case for mypy to test that the type of class is preserved."""

import icontract

class SomeClass:
    pass

reveal_type(SomeClass)
    
@icontract.invariant(lambda self: self.x > 0)
class Decorated:
    def __init__(self) -> None:
        self.x = 1

reveal_type(Decorated)
'''

            pth = pathlib.Path(tmpdir) / "source.py"
            pth.write_text(content, encoding="utf-8")

            with subprocess.Popen(
                ["mypy", "--strict", str(pth)],
                universal_newlines=True,
                stdout=subprocess.PIPE,
            ) as proc:
                out, err = proc.communicate()

                self.assertIsNone(err)
                self.assertEqual(
                    """\
{path}:8: note: Revealed type is "def () -> source.SomeClass"
{path}:15: note: Revealed type is "def () -> source.Decorated"
Success: no issues found in 1 source file
""".format(
                        path=pth
                    ),
                    out,
                )

    def test_that_mypy_complains_when_decorating_non_type_with_invariant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mypy_fail_case_") as tmpdir:
            content = '''\
"""Provide a fail case to test that mypy complains when we decorate a non-type with invariant."""

import icontract

@icontract.invariant(lambda: True)
def some_func() -> None:
    pass
'''

            pth = pathlib.Path(tmpdir) / "source.py"
            pth.write_text(content, encoding="utf-8")

            with subprocess.Popen(
                ["mypy", "--strict", str(pth)],
                universal_newlines=True,
                stdout=subprocess.PIPE,
            ) as proc:
                out, err = proc.communicate()

                self.assertIsNone(err)
                self.assertEqual(
                    """\
{path}:5: error: Value of type variable "ClassT" of "__call__" of "invariant" cannot be "Callable[[], None]"  [type-var]
Found 1 error in 1 file (checked 1 source file)
""".format(
                        path=pth
                    ),
                    out,
                )


if __name__ == "__main__":
    unittest.main()
