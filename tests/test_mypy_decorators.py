# pylint: disable=missing-docstring

import subprocess
import tempfile
import textwrap
import unittest


class TestMypyDecorators(unittest.TestCase):
    def test_mypy_me(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="mypy_fail_case_", suffix=".py") as tmp:
            tmp.file.write(  # type: ignore
                textwrap.dedent('''\
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
                ''').encode())

            tmp.file.flush()  # type: ignore

            proc = subprocess.Popen(['mypy', '--strict', tmp.name], universal_newlines=True, stdout=subprocess.PIPE)
            out, err = proc.communicate()

            self.assertIsNone(err)
            self.assertEqual(
                textwrap.dedent('''\
                    {path}:8: error: Argument 1 to "f1" has incompatible type "str"; expected "int"
                    {path}:13: error: Argument 1 to "f2" has incompatible type "str"; expected "int"
                    {path}:18: error: Argument 1 to "f3" has incompatible type "str"; expected "int"
                    Found 3 errors in 1 file (checked 1 source file)
                    '''.format(path=tmp.name)),
                out)


if __name__ == '__main__':
    unittest.main()
