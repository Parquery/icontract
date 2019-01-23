# pylint: disable=missing-docstring

import subprocess
import tempfile
import textwrap
import unittest


class TestMypyDecorators(unittest.TestCase):
    def test_mypy_me(self):
        with tempfile.NamedTemporaryFile(prefix="mypy_fail_case_", suffix=".py") as tmp:
            tmp.file.write(
                textwrap.dedent('''\
                """Implement a fail case for mypy to test that the types are preserved with the decorators."""

                import icontract

                def some_precond(x: int) -> bool: return x > 0

                @icontract.require(some_precond)
                def f1(x: int) -> int:
                    return x
                f1("this is wrong")

                def some_postcond(result: int) -> bool: return result > 0

                @icontract.ensure(some_postcond)
                def f2(x: int) -> int:
                    return x
                f2("this is wrong")

                def some_snapshot(x: int) -> int: return x

                @icontract.snapshot(some_snapshot)
                def f3(x: int) -> int:
                    return x
                f3("this is wrong")
                ''').encode())

            tmp.file.flush()

            proc = subprocess.Popen(['mypy', '--strict', tmp.name], universal_newlines=True, stdout=subprocess.PIPE)
            out, err = proc.communicate()

            self.assertIsNone(err)
            self.assertEqual(
                textwrap.dedent('''\
                    {path}:10: error: Argument 1 to "f1" has incompatible type "str"; expected "int"
                    {path}:17: error: Argument 1 to "f2" has incompatible type "str"; expected "int"
                    {path}:24: error: Argument 1 to "f3" has incompatible type "str"; expected "int"
                    '''.format(path=tmp.name)),
                out)


if __name__ == '__main__':
    unittest.main()
