# pylint: disable=missing-docstring
import pathlib
import subprocess
import tempfile
import textwrap
import unittest


class TestMypyDecorators(unittest.TestCase):
    def test_that_approach_with_paramspec_works_with_mypy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mypy_ok_case_") as tmpdir:
            content = '''\
"""Document that mypy works with ParamSpec"""

from typing import Callable, ParamSpec, TypeVar

ParametersT = ParamSpec("ParametersT")
ResultT = TypeVar("ResultT")


class some_decorator:
    def __init__(self, x: int) -> None:
        self.x = x
        
    def __call__(
        self, 
        func: Callable[ParametersT, ResultT]
    ) -> Callable[ParametersT, ResultT]:
        return func;


@some_decorator(x=3)
def custom_add(a: int, b: int) -> int:
    return a + b
'''

            pth = pathlib.Path(tmpdir) / "source.py"
            pth.write_text(content)

            with subprocess.Popen(
                    ['mypy', '--strict', str(pth)], universal_newlines=True, stdout=subprocess.PIPE) as proc:
                out, err = proc.communicate()

                self.assertEqual(0, proc.returncode, f"{out=}, {err=}")


if __name__ == '__main__':
    unittest.main()
