# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
import io
import os
import pathlib
import re
import textwrap
import unittest
import uuid

import icontract
import icontract.integration.with_hypothesis.pyicontract_hypothesis as pyicontract_hypothesis

# TODO: split these tests in separate modules, test_common.py, test_test.py and test_ghostwrite.py


class TestLineRangeRe(unittest.TestCase):
    def test_only_first(self) -> None:
        mtch = pyicontract_hypothesis._LINE_RANGE_RE.match(' 123 ')
        assert mtch is not None

        self.assertEqual('123', mtch.group('first'))
        self.assertIsNone(mtch.group('last'), "Unexpected last group: {}".format(mtch.group('last')))

    def test_first_and_last(self) -> None:
        mtch = pyicontract_hypothesis._LINE_RANGE_RE.match(' 123 - 435 ')
        assert mtch is not None

        self.assertEqual('123', mtch.group('first'))
        self.assertEqual('435', mtch.group('last'))

    def test_no_match(self) -> None:
        mtch = pyicontract_hypothesis._LINE_RANGE_RE.match('123aa')
        assert mtch is None, "Expected no match, but got: {}".format(mtch)


class TestParsingOfPointSpecs(unittest.TestCase):
    def test_single_line(self) -> None:
        text = '123'
        point_spec, errors = pyicontract_hypothesis._parse_point_spec(text=text)

        self.assertListEqual([], errors)
        assert isinstance(point_spec, pyicontract_hypothesis.LineRange)
        self.assertEqual(123, point_spec.first)
        self.assertEqual(123, point_spec.last)

    def test_line_range(self) -> None:
        text = '123-345'
        point_spec, errors = pyicontract_hypothesis._parse_point_spec(text=text)

        self.assertListEqual([], errors)
        assert isinstance(point_spec, pyicontract_hypothesis.LineRange)
        self.assertEqual(123, point_spec.first)
        self.assertEqual(345, point_spec.last)

    def test_invalid_line_range(self) -> None:
        text = '345-123'
        point_spec, errors = pyicontract_hypothesis._parse_point_spec(text=text)

        assert point_spec is None
        self.assertListEqual(['Unexpected line range (last < first): 345-123'], errors)

    def test_pattern(self) -> None:
        text = r'^do_.*$'
        point_spec, errors = pyicontract_hypothesis._parse_point_spec(text=text)

        self.assertListEqual([], errors)
        assert isinstance(point_spec, re.Pattern)
        self.assertEqual(text, point_spec.pattern)


class TestParsingOfParameters(unittest.TestCase):
    def test_no_command(self) -> None:
        argv = ['-m', 'some_module']

        stdout, stderr = io.StringIO(), io.StringIO()

        pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stdout.getvalue())
        self.assertEqual('''\
usage: pyicontract-hypothesis [-h] {test,ghostwrite} ...
pyicontract-hypothesis: error: argument command: invalid choice: 'some_module' (choose from 'test', 'ghostwrite')
''', stderr.getvalue())

    def test_subcommand_test(self) -> None:
        # yapf: disable
        argv = ['test',
                '--path', 'some_module.py', '--include', 'include-something',
                '--exclude', 'exclude-something',
                '--setting', 'suppress_health_check=[2, 3]']
        # yapf: enable

        parser = pyicontract_hypothesis._make_argument_parser()
        args, out, err = pyicontract_hypothesis._parse_args(parser=parser, argv=argv)
        assert args is not None, "Failed to parse argv {!r}: {}".format(argv, err)

        general, errs = pyicontract_hypothesis._parse_general_params(args=args)

        self.assertListEqual([], errs)
        assert general is not None
        self.assertListEqual([re.compile(pattern) for pattern in ["include-something"]], general.include)
        self.assertListEqual([re.compile(pattern) for pattern in ["exclude-something"]], general.exclude)

        test, errs = pyicontract_hypothesis._parse_test_params(args=args)

        self.assertListEqual([], errs)
        assert test is not None
        self.assertEqual(pathlib.Path('some_module.py'), test.path)
        self.assertDictEqual({"suppress_health_check": [2, 3]}, dict(test.settings))

    def test_subcommand_ghostwrite(self) -> None:
        # yapf: disable
        argv = ['ghostwrite',
                '--module', 'some_module',
                '--include', 'include-something',
                '--exclude', 'exclude-something',
                '--explicit', 'strategies',
                '--bare']
        # yapf: enable
        parser = pyicontract_hypothesis._make_argument_parser()
        args, out, err = pyicontract_hypothesis._parse_args(parser=parser, argv=argv)
        assert args is not None, "Failed to parse argv {!r}: {}".format(argv, err)

        general, errs = pyicontract_hypothesis._parse_general_params(args=args)

        self.assertListEqual([], errs)
        assert general is not None
        self.assertListEqual([re.compile(pattern) for pattern in ["include-something"]], general.include)
        self.assertListEqual([re.compile(pattern) for pattern in ["exclude-something"]], general.exclude)

        ghostwrite, errs = pyicontract_hypothesis._parse_ghostwrite_params(args=args)

        self.assertListEqual([], errs)
        assert ghostwrite is not None
        self.assertEqual('some_module', ghostwrite.module_name)
        self.assertTrue(ghostwrite.explicit, 'strategies')
        self.assertTrue(ghostwrite.bare)


class TestSelectFunctionPoints(unittest.TestCase):
    def test_invalid_module(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_invalid_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(), mod=mod, include=[], exclude=[])

        # yapf: disable
        self.assertListEqual(
            ["Unexpected directive on line 7. "
             "Expected '# pyicontract-hypothesis: (disable|enable)', "
             "but got: # pyicontract-hypothesis: disable-once"], errors)
        # yapf: enable

    def test_no_include_and_no_exclude(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(), mod=mod, include=[], exclude=[])
        self.assertListEqual([], errors)

        self.assertListEqual(['some_func', 'square_greater_than_zero', 'another_func'],
                             [point.func.__name__ for point in points])

    def test_include_line_range(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod,
            # A single line that overlaps the function should be enough to include it.
            include=[pyicontract_hypothesis.LineRange(first=9, last=9)],
            exclude=[])
        self.assertListEqual([], errors)
        # yapf: enable

        self.assertListEqual(['some_func'], [point.func.__name__ for point in points])

    def test_include_pattern(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod,
            include=[re.compile(r'^some_.*$')],
            exclude=[])
        self.assertListEqual([], errors)
        # yapf: enable

        self.assertListEqual(['some_func'], [point.func.__name__ for point in points])

    def test_exclude_line_range(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod,
            include=[],
            # A single line that overlaps the function should be enough to exclude it.
            exclude=[pyicontract_hypothesis.LineRange(first=9, last=9)])
        self.assertListEqual([], errors)
        # yapf: enable

        self.assertListEqual(['square_greater_than_zero', 'another_func'], [point.func.__name__ for point in points])

    def test_exclude_pattern(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod,
            include=[],
            exclude=[re.compile(r'^some_.*$')])
        self.assertListEqual([], errors)
        # yapf: enable

        self.assertListEqual(['square_greater_than_zero', 'another_func'], [point.func.__name__ for point in points])


class TestTest(unittest.TestCase):
    def test_default_behavior(self) -> None:
        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod, include=[], exclude=[])
        self.assertListEqual([], errors)
        # yapf: enable

        for point in points:
            test_errors = pyicontract_hypothesis._test_function_point(point=point, settings=None)
            self.assertListEqual([], test_errors)

        some_func_calls = getattr(mod, 'SOME_FUNC_CALLS')
        self.assertEqual(100, some_func_calls)

        another_func_calls = getattr(mod, 'ANOTHER_FUNC_CALLS')
        self.assertEqual(100, another_func_calls)

    def test_settings(self) -> None:
        settings = {"max_examples": 10}

        path = pathlib.Path(os.path.realpath(__file__)).parent / "sample_module.py"

        mod, errors = pyicontract_hypothesis._load_module_from_source_file(path=path)
        self.assertListEqual([], errors)
        assert mod is not None

        # yapf: disable
        points, errors = pyicontract_hypothesis._select_function_points(
            source_code=path.read_text(),
            mod=mod, include=[], exclude=[])
        self.assertListEqual([], errors)
        # yapf: enable

        for point in points:
            test_errors = pyicontract_hypothesis._test_function_point(point=point, settings=settings)
            self.assertListEqual([], test_errors)

        some_func_calls = getattr(mod, 'SOME_FUNC_CALLS')
        self.assertEqual(10, some_func_calls)

        another_func_calls = getattr(mod, 'ANOTHER_FUNC_CALLS')
        self.assertEqual(10, another_func_calls)


class TestTestViaSmoke(unittest.TestCase):
    """Perform smoke testing of the "test" command."""

    def test_nonexisting_file(self) -> None:
        path = "doesnt-exist.{}".format(uuid.uuid4())
        argv = ['test', '--path', path]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual("The file to be tested does not exist: {}".format(path), stderr.getvalue().strip())
        self.assertEqual(exit_code, 1)

    def test_common_case(self) -> None:
        this_dir = pathlib.Path(os.path.realpath(__file__)).parent

        argv = ['test', '--path', str(this_dir / "sample_module.py")]

        stdout = io.StringIO()
        stderr = io.StringIO()

        # This is merely a smoke test.
        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

    def test_with_settings(self) -> None:
        this_dir = pathlib.Path(os.path.realpath(__file__)).parent

        argv = ['test', '--path', str(this_dir / "sample_module.py"), '--settings', 'max_examples=5']

        stdout = io.StringIO()
        stderr = io.StringIO()

        # This is merely a smoke test.
        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

    def test_with_include_exclude(self) -> None:
        this_dir = pathlib.Path(os.path.realpath(__file__)).parent

        argv = ['test', '--path', str(this_dir / "sample_module.py"), '--include', '.*_func', '--exclude', 'some.*']

        stdout = io.StringIO()
        stderr = io.StringIO()

        # This is merely a smoke test.
        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)


# TODO: split the command in different modules: ghostwrite and test
# TODO: split the unit tests as well!


class TestGhostwriteAssumes(unittest.TestCase):
    def test_no_preconditions(self) -> None:
        def some_func(x: int) -> None:
            ...

        text = pyicontract_hypothesis._ghostwrite_assumes(func=some_func)

        self.assertEqual('', text)

    def test_lambda_precondition(self) -> None:
        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            ...

        text = pyicontract_hypothesis._ghostwrite_assumes(func=some_func)

        self.assertEqual('assume(x > 0)', text)

    def test_function_precondition(self) -> None:
        def some_precondition(x: int) -> bool:
            return True

        @icontract.require(some_precondition)
        def some_func(x: int) -> None:
            ...

        text = pyicontract_hypothesis._ghostwrite_assumes(func=some_func)

        self.assertEqual('assume(some_precondition(x))', text)

    def test_multiple_preconditions(self) -> None:
        @icontract.require(lambda x: x > 0)
        @icontract.require(lambda x: x < 100)
        def some_func(x: int) -> None:
            ...

        text = pyicontract_hypothesis._ghostwrite_assumes(func=some_func)

        self.assertEqual(
            textwrap.dedent('''\
            assume(
                (x < 100) and
                (x > 0)
            )'''), text)

    def test_weakened_single_precondition(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            def some_func(self, x: int) -> None:
                ...

        class B(A):
            @icontract.require(lambda x: x % 7 == 0)
            def some_func(self, x: int) -> None:
                ...

        b = B()
        text = pyicontract_hypothesis._ghostwrite_assumes(func=b.some_func)

        self.assertEqual(
            textwrap.dedent('''\
            assume(
                (x % 3 == 0) or 
                (x % 7 == 0)
            )'''), text)

    def test_weakened_preconditions(self) -> None:
        class A(icontract.DBC):
            @icontract.require(lambda x: x % 3 == 0)
            @icontract.require(lambda x: x > 100)
            def some_func(self, x: int) -> None:
                ...

        class B(A):
            @icontract.require(lambda x: x % 7 == 0)
            @icontract.require(lambda x: x < 200)
            def some_func(self, x: int) -> None:
                ...

        b = B()
        text = pyicontract_hypothesis._ghostwrite_assumes(func=b.some_func)

        self.assertEqual(
            textwrap.dedent('''\
            assume(
                (
                    (x > 100 == 0) and
                    (x % 3 == 0)
                ) or 
                (
                    (x < 200 == 0) and
                    (x % 7 == 0)
                )
            )'''), text)


class TestGhostwrite(unittest.TestCase):
    def test_bare_and_explicit_strategies(self) -> None:
        argv = [
            'ghostwrite', '--module', "tests.integration.with_hypothesis.sample_module", "--bare", "--explicit",
            "strategies"
        ]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        expected_pth = (this_dir / 'expected_ghostwrites' /
                        ('for_{}.txt'.format(TestGhostwrite.test_bare_and_explicit_strategies.__name__)))

        expected = expected_pth.read_text()
        self.assertEqual(expected, stdout.getvalue())

    def test_bare_and_explicit_strategies_and_assumes(self) -> None:
        argv = [
            'ghostwrite', '--module', "tests.integration.with_hypothesis.sample_module", "--bare", "--explicit",
            "strategies-and-assumes"
        ]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        expected_pth = (this_dir / 'expected_ghostwrites' /
                        ('for_{}.txt'.format(TestGhostwrite.test_bare_and_explicit_strategies_and_assumes.__name__)))

        expected = expected_pth.read_text()
        self.assertEqual(expected, stdout.getvalue())

    def test_bare_and_non_explicit(self) -> None:
        argv = ['ghostwrite', '--module', "tests.integration.with_hypothesis.sample_module", "--bare"]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        expected_pth = (this_dir / 'expected_ghostwrites' /
                        ('for_{}.txt'.format(TestGhostwrite.test_bare_and_non_explicit.__name__)))

        expected = expected_pth.read_text()
        self.assertEqual(expected, stdout.getvalue())

    def test_non_bare_and_explicit_strategies(self) -> None:
        argv = ['ghostwrite', '--module', "tests.integration.with_hypothesis.sample_module", "--explicit", "strategies"]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        expected_pth = (this_dir / 'expected_ghostwrites' /
                        ('for_{}.py'.format(TestGhostwrite.test_non_bare_and_explicit_strategies.__name__)))

        expected = expected_pth.read_text()
        self.assertEqual(expected, stdout.getvalue())

    def test_non_bare_and_non_explicit(self) -> None:
        argv = ['ghostwrite', '--module', "tests.integration.with_hypothesis.sample_module"]

        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = pyicontract_hypothesis.run(argv=argv, stdout=stdout, stderr=stderr)

        self.assertEqual('', stderr.getvalue())
        self.assertEqual(exit_code, 0)

        this_dir = pathlib.Path(os.path.realpath(__file__)).parent
        expected_pth = (this_dir / 'expected_ghostwrites' /
                        ('for_{}.py'.format(TestGhostwrite.test_non_bare_and_non_explicit.__name__)))

        expected = expected_pth.read_text()
        self.assertEqual(expected, stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
