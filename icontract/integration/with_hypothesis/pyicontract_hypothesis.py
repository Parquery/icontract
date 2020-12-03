#!/usr/bin/env python3
"""Run Hypothesis tests on a module with inferred strategies."""
import argparse
import collections
import contextlib
import enum
import importlib.machinery
import importlib
import inspect
import io
import json
import pathlib
import re
import sys
import textwrap
import tokenize
import types
from typing import List, Optional, Tuple, TextIO, Mapping, Any, MutableMapping, Union, Callable, Set, Dict, TypeVar, \
    NoReturn, overload, AnyStr, Iterator

import hypothesis
import hypothesis.strategies
import hypothesis.strategies._internal

import icontract
import icontract._checkers
import icontract._represent

import icontract.integration.with_hypothesis


class LineRange:
    """Represent a line range (indexed from 1, both first and last inclusive)."""

    def __init__(self, first: int, last: int) -> None:
        """Initialize with the given values."""
        self.first = first
        self.last = last


class ParamsGeneral:
    """Represent general program parameters specified regardless of the command."""

    # yapf: disable
    def __init__(
            self,
            include: List[Union[re.Pattern[str], LineRange]],
            exclude: List[Union[re.Pattern[str], LineRange]]
    ) -> None:
        # yapf: enable
        self.include = include  # type: List[Union[re.Pattern[str], LineRange]]
        self.exclude = exclude  # type: List[Union[re.Pattern[str], LineRange]]


_LINE_RANGE_RE = re.compile(r'^\s*(?P<first>[0-9]|[1-9][0-9]+)(\s*-\s*(?P<last>[1-9]|[1-9][0-9]+))?\s*$')


def _parse_point_spec(text: str) -> Tuple[Optional[Union[LineRange, re.Pattern[str]]], List[str]]:
    """
    Try to parse the given specification of function point(s).
    
    Return (parsed point spec, errors if any)
    """
    errors = []  # type: List[str]

    mtch = _LINE_RANGE_RE.match(text)
    if mtch:
        if mtch.group('last') is None:
            first = int(mtch.group('first'))
            if first <= 0:
                errors.append("Unexpected line index (expected to start from 1): {}".format(text))
                return None, errors

            return LineRange(first=int(mtch.group('first')), last=first), errors
        else:
            first = int(mtch.group('first'))
            last = int(mtch.group('last'))

            if first <= 0:
                errors.append("Unexpected line index (expected to start from 1): {}".format(text))
                return None, errors

            if last < first:
                errors.append("Unexpected line range (last < first): {}".format(text))
                return None, errors

            else:
                return LineRange(first=int(mtch.group('first')), last=int(mtch.group('last'))), errors

    try:
        pattern = re.compile(text)
        return pattern, errors
    except re.error as err:
        errors.append("Failed to parse the pattern {}: {}".format(text, err))
        return None, errors


def _parse_general_params(args: argparse.Namespace) -> Tuple[Optional[ParamsGeneral], List[str]]:
    """
    Try to parse general parameters of the program (regardless of the command).

    Return (parsed parameters, errors if any).
    """
    errors = []  # type: List[str]

    include = []  # type: List[Union[re.Pattern[str], LineRange]]
    if args.include is not None:
        for include_str in args.include:
            point_spec, point_spec_errors = _parse_point_spec(text=include_str)
            errors.extend(point_spec_errors)

            if not point_spec_errors:
                assert point_spec is not None
                include.append(point_spec)

    exclude = []  # type: List[Union[re.Pattern[str], LineRange]]
    if args.exclude is not None:
        for exclude_str in args.exclude:
            point_spec, point_spec_errors = _parse_point_spec(text=exclude_str)
            errors.extend(point_spec_errors)

            if not point_spec_errors:
                assert point_spec is not None
                exclude.append(point_spec)

    if errors:
        return None, errors

    return ParamsGeneral(include=include, exclude=exclude), errors


class ParamsTest:
    """Represent parameters of the command "test"."""

    def __init__(self, path: pathlib.Path, settings: Mapping[str, Any]) -> None:
        self.path = path
        self.settings = settings


_SETTING_STATEMENT_RE = re.compile(r'^(?P<identifier>[a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*(?P<value>.*)\s*$')


def _parse_test_params(args: argparse.Namespace) -> Tuple[Optional[ParamsTest], List[str]]:
    """
    Try to parse the parameters of the command "test".

    Return (parsed parameters, errors if any).
    """
    errors = []  # type: List[str]

    path = pathlib.Path(args.path)

    settings = collections.OrderedDict()  # type: MutableMapping[str, Any]

    if args.settings is not None:
        for i, statement in enumerate(args.settings):
            mtch = _SETTING_STATEMENT_RE.match(statement)
            if not mtch:
                errors.append("Invalid setting statement {}. Expected statement to match {}, but got: {}".format(
                    i + 1, _SETTING_STATEMENT_RE.pattern, statement))

                return None, errors

            identifier = mtch.group("identifier")
            value_str = mtch.group("value")

            try:
                value = json.loads(value_str)
            except json.decoder.JSONDecodeError as error:
                errors.append("Failed to parse the value of the setting {}: {}".format(identifier, error))
                return None, errors

            settings[identifier] = value

    if errors:
        return None, errors

    return ParamsTest(path=path, settings=settings), errors


class Explicit(enum.Enum):
    """Specify how explicit the ghostwriter should be."""
    STRATEGIES = "strategies"
    STRATEGIES_AND_ASSUMES = "strategies-and-assumes"


class ParamsGhostwrite:
    """Represent parameters of the command "ghostwrite"."""

    def __init__(self, module_name: str, output: Optional[pathlib.Path], explicit: Optional[Explicit],
                 bare: bool) -> None:
        self.module_name = module_name
        self.output = output
        self.explicit = explicit
        self.bare = bare


def _parse_ghostwrite_params(args: argparse.Namespace) -> Tuple[Optional[ParamsGhostwrite], List[str]]:
    """
    Try to parse the parameters of the command "ghostwrite".

    Return (parsed parameters, errors if any).
    """
    output = pathlib.Path(args.output) if args.output != '-' else None

    return ParamsGhostwrite(
        module_name=args.module,
        output=output,
        explicit=Explicit(args.explicit) if args.explicit is not None else None,
        bare=args.bare), []


class Params:
    """Represent the parameters of the program."""

    def __init__(self, general: ParamsGeneral, command: Union[ParamsTest, ParamsGhostwrite]) -> None:
        self.general = general
        self.command = command


def _parse_args_to_params(args: argparse.Namespace) -> Tuple[Optional[Params], List[str]]:
    """
    Parse the parameters from the command-line arguments.

    Return parsed parameters, errors if any
    """
    errors = []  # type: List[str]

    general, general_errors = _parse_general_params(args=args)
    errors.extend(general_errors)

    command = None  # type: Optional[Union[ParamsTest, ParamsGhostwrite]]
    if args.command == 'test':
        test, command_errors = _parse_test_params(args=args)
        errors.extend(command_errors)

        command = test

    elif args.command == 'ghostwrite':
        ghostwrite, command_errors = _parse_ghostwrite_params(args=args)
        errors.extend(command_errors)
        command = ghostwrite

    if errors:
        return None, errors

    assert general is not None
    assert command is not None

    return Params(general=general, command=command), []


def _make_argument_parser() -> argparse.ArgumentParser:
    """Create an instance of the argument parser to parse command-line arguments."""
    parser = argparse.ArgumentParser(prog="pyicontract-hypothesis", description=__doc__)
    subparsers = parser.add_subparsers(help="Commands", dest='command')
    subparsers.required = True

    test_parser = subparsers.add_parser(
        "test", help="Test the functions automatically by inferring search strategies and preconditions")

    test_parser.add_argument("-p", "--path", help="Path to the Python file to test", required=True)

    test_parser.add_argument(
        "--settings",
        help=("Specify settings for Hypothesis\n\n"
              "The settings are assigned by '='."
              "The value of the setting needs to be encoded as JSON.\n\n"
              "Example: max_examples=500"),
        nargs="*")

    ghostwriter_parser = subparsers.add_parser(
        "ghostwrite", help="Ghostwrite the unit test module based on inferred search strategies")

    ghostwriter_parser.add_argument("-m", "--module", help="Module to process", required=True)

    ghostwriter_parser.add_argument(
        "-o",
        "--output",
        help="Path to the file where the output should be written. If '-', writes to STDOUT.",
        default="-")

    ghostwriter_parser.add_argument(
        "--explicit",
        help=("Write the strategies explicitly in the unit test module instead of inferring them at run-time\n\n"
              "This is practical if you want to tune and refine the strategies and "
              "just want to use ghostwriting as a starting point."
              "\n\n"
              "Mind that pyicontract-hypothesis does not automatically fix imports as this is usually project-specific."
              "You have to fix imports manually after the ghostwriting."
              "\n\n"
              "Possible levels of explicitness:"
              "* {0}: Explicitly write out the inferred strategies, but keep inferred assumptions general\n"
              "* {1}: Write out both the inferred strategies and the preconditions").format(
                  Explicit.STRATEGIES.value, Explicit.STRATEGIES_AND_ASSUMES.value),
        choices=[item.value for item in Explicit])

    ghostwriter_parser.add_argument(
        "--bare",
        help=("Print only the body of the tests and omit header/footer "
              "(such as TestCase class or import statements).\n\n"
              "This is useful when you only want to inspect a single test or "
              "include a single test function in a custom test suite."),
        action='store_true')

    for subparser in [test_parser, ghostwriter_parser]:
        subparser.add_argument(
            "-i",
            "--include",
            help=("Regular expressions, lines or line ranges of the functions to process\n\n"
                  "If a line or line range overlaps the body of a function, the function is considered included."
                  "Example 1: ^do_something.*$\n"
                  "Example 2: 3\n"
                  "Example 3: 34-65"),
            required=False,
            nargs="*")

        subparser.add_argument(
            "-e",
            "--exclude",
            help=("Regular expressions of the functions to exclude from processing"
                  "If a line or line range overlaps the body of a function, the function is considered excluded."
                  "Example 1: ^do_something.*$\n"
                  "Example 2: 3\n"
                  "Example 3: 34-65"),
            default=['^_.*$'],
            nargs="*")

    return parser


def _parse_args(parser: argparse.ArgumentParser, argv: List[str]) -> Tuple[Optional[argparse.Namespace], str, str]:
    """
    Parse the command-line arguments.

    Return (parsed args or None if failure, captured stdout, captured stderr).
    """
    pass  # for pydocstyle

    # From https://stackoverflow.com/questions/18160078
    @contextlib.contextmanager
    def captured_output():  # type: ignore
        new_out, new_err = io.StringIO(), io.StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = new_out, new_err
            yield sys.stdout, sys.stderr
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    with captured_output() as (out, err):
        try:
            parsed_args = parser.parse_args(argv)

            err.seek(0)
            out.seek(0)
            return parsed_args, out.read(), err.read()

        except SystemExit:
            err.seek(0)
            out.seek(0)
            return None, out.read(), err.read()


_DIRECTIVE_RE = re.compile(r'^#\s*pyicontract-hypothesis\s*:\s*(?P<value>[^ \t]*)\s*$')


class FunctionPoint:
    """Represent a testable function."""

    @icontract.require(lambda first_row: first_row > 0)
    @icontract.require(lambda last_row: last_row > 0)
    @icontract.require(lambda first_row, last_row: first_row <= last_row)
    def __init__(self, first_row: int, last_row: int, func: Callable[..., Any]) -> None:
        """
        Initialize with the given values.

        First and last row are both inclusive.
        """
        self.first_row = first_row
        self.last_row = last_row
        self.func = func


def _overlap(first: int, last: int, another_first: int, another_last: int) -> bool:
    """
    Return True if the two intervals overlap.

    >>> not any([
    ...     _overlap(1, 1, 2, 2),
    ...     _overlap(2, 2, 1, 1)
    ... ])
    True

    >>> all([
    ...     _overlap(1, 1, 1, 1),
    ...     _overlap(1, 5, 1, 1),
    ...     _overlap(1, 1, 1, 5),
    ...     _overlap(1, 3, 2, 5),
    ...     _overlap(2, 5, 1, 3),
    ...     _overlap(1, 5, 2, 3),
    ...     _overlap(2, 3, 1, 5),
    ...  ])
    True
    """
    return min(last, another_last) - max(first, another_first) >= 0


def _select_function_points(source_code: str, mod: types.ModuleType, include: List[Union[LineRange, re.Pattern[str]]],
                            exclude: List[Union[LineRange, re.Pattern[str]]]) -> Tuple[List[FunctionPoint], List[str]]:
    included = []  # type: List[FunctionPoint]
    errors = []  # type: List[str]

    for key in dir(mod):
        value = getattr(mod, key)
        if inspect.isfunction(value):
            func = value  # type: Callable[..., Any]
            source_lines, srow = inspect.getsourcelines(func)
            point = FunctionPoint(first_row=srow, last_row=srow + len(source_lines) - 1, func=func)
            included.append(point)

    # The built-in dir() gives us an unsorted directory.
    included = sorted(included, key=lambda point: point.first_row)

    ##
    # Add ranges of lines given by comment directives to the ``exclude``
    ##

    extended_exclude = exclude[:]

    range_start = None  # type: Optional[int]
    reader = io.BytesIO(source_code.encode('utf-8'))
    for toktype, _, (first_row, _), _, line in tokenize.tokenize(reader.readline):
        if toktype == tokenize.COMMENT:
            mtch = _DIRECTIVE_RE.match(line.strip())
            if mtch:
                value = mtch.group('value')

                if value not in ['enable', 'disable']:
                    errors.append(("Unexpected directive on line {}. "
                                   "Expected '# pyicontract-hypothesis: (disable|enable)', "
                                   "but got: {}").format(first_row, line.strip()))
                    continue

                if value == 'disable':
                    if range_start is not None:
                        continue

                    range_start = first_row

                elif value == 'enable':
                    if range_start is not None:
                        extended_exclude.append(LineRange(first=range_start, last=first_row))

                else:
                    raise AssertionError("Unexpected value: {}".format(json.dumps(value)))

    exclude = extended_exclude

    if errors:
        return [], errors

    ##
    # Remove ``included`` which do not match ``include``
    ##

    if len(include) > 0:
        incl_line_ranges = [incl for incl in include if isinstance(incl, LineRange)]
        if len(incl_line_ranges) > 100:
            # yapf: disable
            print(
                ("There are much more --include items then expected: {0}. "
                 "Please consider filing an issue by visiting this link: "
                 "https://github.com/Parquery/icontract/issues/new"
                 "?title=Use+interval+tree"
                 "&body=We+had+{0}+include+line+ranges+in+pyicontract-hypothesis."
                 ).format(len(incl_line_ranges)))
            # yapf: enable

        if len(incl_line_ranges) > 0:
            filtered_included = []  # type: List[FunctionPoint]
            for point in included:
                # yapf: disable
                overlaps_include = any(
                    _overlap(first=line_range.first, last=line_range.last,
                             another_first=point.first_row, another_last=point.last_row)
                    for line_range in incl_line_ranges)
                # yapf: enable

                if overlaps_include:
                    filtered_included.append(point)

            included = filtered_included

        # Match regular expressions
        patterns = [incl for incl in include if isinstance(incl, re.Pattern)]
        if len(patterns) > 0:
            filtered_included = []
            for pattern in patterns:
                for point in included:
                    if pattern.match(point.func.__name__):
                        filtered_included.append(point)

            included = filtered_included

    if len(included) == 0:
        return [], []

    ##
    # Exclude all points in ``included`` if matched in ``exclude``
    ##

    if len(exclude) > 0:
        excl_line_ranges = [excl for excl in exclude if isinstance(excl, LineRange)]
        if len(excl_line_ranges) > 100:
            # yapf: disable
            print(
                ("There are much more --exclude items then expected: {0}. "
                 "Please consider filing an issue by visiting this link: "
                 "https://github.com/Parquery/icontract/issues/new"
                 "?title=Use+interval+tree"
                 "&body=We+had+{0}+exclude+line+ranges+in+pyicontract-hypothesis."
                 ).format(len(excl_line_ranges)))
            # yapf: enable

        if len(excl_line_ranges) > 0:
            filtered_included = []
            for point in included:
                # yapf: disable
                overlaps_exclude = any(
                    _overlap(first=line_range.first, last=line_range.last,
                             another_first=point.first_row, another_last=point.last_row)
                    for line_range in excl_line_ranges)
                # yapf: enable

                if not overlaps_exclude:
                    filtered_included.append(point)

            included = filtered_included

        patterns = [excl for excl in exclude if isinstance(excl, re.Pattern)]
        if len(patterns) > 0:
            filtered_included = []
            for pattern in patterns:
                for point in included:
                    if not pattern.match(point.func.__name__):
                        filtered_included.append(point)

            included = filtered_included

    return included, []


def _load_module_from_source_file(path: pathlib.Path) -> Tuple[Optional[types.ModuleType], List[str]]:
    """
    Try to load a module from the source file.

    Return (loaded module, errors if any).
    """
    fullname = re.sub(r'[^A-Za-z0-9_]', '_', path.stem)

    mod = None  # type: Optional[types.ModuleType]
    try:
        loader = importlib.machinery.SourceFileLoader(fullname=fullname, path=str(path))
        mod = types.ModuleType(loader.name)
        loader.exec_module(mod)
    except Exception as error:
        return None, ['Failed to import the file {}: {}'.format(path, error)]

    assert mod is not None, "Expected mod to be set before"

    return mod, []


def _test_function_point(point: FunctionPoint, settings: Optional[Mapping[str, Any]]) -> List[str]:
    """
    Test a single function point.

    Return errors if any.
    """
    errors = []  # type: List[str]

    func = point.func  # Optimize the look-up
    assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(func=func)

    def execute(*args: Tuple[Any, ...], **kwargs: Dict[str, Any]) -> None:
        assume_preconditions(*args, **kwargs)
        func(*args, **kwargs)

    strategies = icontract.integration.with_hypothesis.infer_strategies(func=func)

    if len(strategies) == 0:
        errors.append(("No strategies could be inferred for the function: {}. "
                       "Have you provided type hints for the arguments?").format(func))
        return errors

    wrapped = hypothesis.given(**strategies)(execute)
    if settings:
        wrapped = hypothesis.settings(**settings)(wrapped)

    wrapped()

    return []


def test(general: ParamsGeneral, command: ParamsTest) -> List[str]:
    """
    Test the specified functions.

    Return errors if any.
    """
    if not command.path.exists():
        return ['The file to be tested does not exist: {}'.format(command.path)]

    try:
        source_code = command.path.read_text(encoding='utf-8')
    except Exception as error:
        return ['Failed to read the file {}: {}'.format(command.path, error)]

    mod, errors = _load_module_from_source_file(path=command.path)
    if errors:
        return errors

    assert mod is not None

    points, errors = _select_function_points(
        source_code=source_code, mod=mod, include=general.include, exclude=general.exclude)
    if errors:
        return errors

    for point in points:
        test_errors = _test_function_point(point=point, settings=command.settings)
        errors.extend(test_errors)

        if errors:
            return errors

    return []


def _load_module_with_name(name: str) -> Tuple[Optional[types.ModuleType], List[str]]:
    """
    Load the module given its name.

    Example identifier: some.module
    """
    try:
        mod = importlib.import_module(name=name)
        assert isinstance(mod, types.ModuleType)
        return mod, []
    except Exception as error:
        return None, ["Failed to import the module {}: {}".format(name, error)]


@overload
def _indent_but_first(lines: List[str], level: int = 1) -> List[str]:
    ...


@overload
def _indent_but_first(lines: str, level: int = 1) -> str:
    ...


def _indent_but_first(lines: Union[List[str], str], level: int = 1) -> Union[str, List[str]]:
    r"""
    Indents the text by 4 spaces.

    >>> _indent_but_first([''], 0)
    ['']

    >>> _indent_but_first(['test'], 1)
    ['test']

    >>> _indent_but_first(['test', '', 'me'], 1)
    ['test', '', '    me']

    >>> _indent_but_first('test\n\nme', 1)
    'test\n\n    me'
    """
    if isinstance(lines, str):
        result = lines.splitlines()
        for i in range(1, len(result)):
            if len(result[i]) > 0:
                result[i] = '    ' * level + result[i]

        return '\n'.join(result)

    elif isinstance(lines, list):
        result = lines[:]
        for i in range(1, len(result)):
            if len(result[i]) > 0:
                result[i] = '    ' * level + result[i]

        return result

    else:
        raise AssertionError("Unhandled input: {}".format(lines))


def _assert_never(x: NoReturn) -> NoReturn:
    """Enforce exhaustive matching at mypy time."""
    assert False, "Unhandled type: {}".format(type(x).__name__)


def _ghostwrite_condition_code(condition: Callable[..., Any]) -> str:
    """Ghostwrite the code representing the condition in an assumption."""
    if not icontract._represent.is_lambda(a_function=condition):
        sign = inspect.signature(condition)
        args = ', '.join(param for param in sign.parameters.keys())

        return '{}({})'.format(condition.__name__, args)

    # We need to extract the source code corresponding to the decorator since inspect.getsource() is broken with
    # lambdas.

    # Find the line corresponding to the condition lambda
    lines, condition_lineno = inspect.findsource(condition)
    filename = inspect.getsourcefile(condition)
    assert filename is not None

    decorator_inspection = icontract._represent.inspect_decorator(
        lines=lines, lineno=condition_lineno, filename=filename)

    lambda_inspection = icontract._represent.find_lambda_condition(decorator_inspection=decorator_inspection)

    assert lambda_inspection is not None, \
        "Expected lambda_inspection to be non-None if is_lambda is True on: {}".format(condition)

    return lambda_inspection.text


@icontract.ensure(
    lambda result: not result.endswith('\n') and not result.startswith(' ') and not result.startswith('\t'),
    'Not indented and no newline at the end')
def _ghostwrite_assumes(func: Callable[..., Any]) -> str:
    """Ghostwrite the assume statements for the given function."""
    checker = icontract._checkers.find_checker(func)
    if checker is None:
        return ''

    preconditions = getattr(checker, "__preconditions__", None)
    if preconditions is None:
        return ''

    # We need to pack all the preconditions in a large boolean expression so that the weakening can be
    # handled easily.

    dnf = []  # type: List[List[str]]
    for group in preconditions:
        conjunctions = []  # type: List[str]
        for contract in group:
            code = _ghostwrite_condition_code(condition=contract.condition)
            conjunctions.append(code)

        dnf.append(conjunctions)

    if len(dnf) == 0:
        return ''

    if len(dnf) == 1:
        if len(dnf[0]) == 1:
            return 'assume({})'.format(dnf[0][0])
        else:
            formatted_conjunctions = textwrap.dedent('''\
                assume(
                    {}
                )''').format(_indent_but_first(' and\n'.join('({})'.format(code) for code in dnf[0]), level=1))

            return formatted_conjunctions

    dnf_formatted = []  # type: List[str]
    for conjunctions in dnf:
        if len(conjunctions) == 1:
            dnf_formatted.append('({})'.format(conjunctions[0]))
        else:
            dnf_formatted.append(
                textwrap.dedent('''\
                (
                    {}
                )''').format(_indent_but_first(' and\n'.join('({})'.format(code) for code in conjunctions), level=1)))

    return textwrap.dedent('''\
        assume(
            {}
        )''').format(_indent_but_first(' or \n'.join(dnf_formatted)))


def _ghostwrite_test_function(module_name: str, point: FunctionPoint,
                              explicit: Optional[Explicit]) -> Tuple[str, List[str]]:
    """
    Ghostwrite a test function for the given function point.

    The result needs to be properly indented afterwards.

    Return (code, errors if any)
    """
    test_func = ''

    if explicit is None:
        test_func = textwrap.dedent('''\
            def test_{1}(self) -> None:
                icontract.integration.with_hypothesis.test_with_inferred_strategies(
                        func={0}.{1})
            '''.format(module_name, point.func.__name__)).strip()

    elif explicit is Explicit.STRATEGIES or explicit is Explicit.STRATEGIES_AND_ASSUMES:
        strategies = icontract.integration.with_hypothesis.infer_strategies(func=point.func)

        if len(strategies) == 0:
            return '', [
                "No strategy could be inferred for the function on line {}: {}".format(
                    point.first_row, point.func.__name__)
            ]

        args = ', '.join(strategies.keys())

        given_args_lines = []  # type: List[str]
        for i, (arg_name, strategy) in enumerate(strategies.items()):
            strategy_code = str(strategy)
            for name in hypothesis.strategies.__all__:
                prefix = '{}('.format(name)
                if strategy_code.startswith(prefix):
                    strategy_code = 'st.' + strategy_code
                    break

            if i < len(strategies) - 1:
                given_args_lines.append('{}={},'.format(arg_name, strategy_code))
            else:
                given_args_lines.append('{}={}'.format(arg_name, strategy_code))

        if explicit is Explicit.STRATEGIES:
            test_func = textwrap.dedent('''\
                def test_{func}(self) -> None:
                    assume_preconditions = icontract.integration.with_hypothesis.make_assume_preconditions(
                        func={module}.{func})
                    
                    @given(
                        {given_args})  
                    def execute({args}) -> None:
                        assume_preconditions({args})
                        {module}.{func}({args})
                ''').format(
                module=module_name,
                func=point.func.__name__,
                args=args,
                given_args='\n'.join(_indent_but_first(given_args_lines, 2))).strip()

        elif explicit is Explicit.STRATEGIES_AND_ASSUMES:
            assume_statements = _ghostwrite_assumes(func=point.func)

            if assume_statements == '':
                test_func = textwrap.dedent('''\
                    def test_{func}(self) -> None:
                        @given(
                            {given_args})
                        def execute({args}) -> None:
                            {module}.{func}({args})
                    ''').format(
                    module=module_name,
                    func=point.func.__name__,
                    args=args,
                    given_args='\n'.join(_indent_but_first(given_args_lines, 2))).strip()
            else:
                test_func = textwrap.dedent('''\
                    def test_{func}(self) -> None:
                        @given(
                            {given_args})  
                        def execute({args}) -> None:
                            {assumes}
                            {module}.{func}({args})
                    ''').format(
                    module=module_name,
                    func=point.func.__name__,
                    args=args,
                    assumes=_indent_but_first(assume_statements, level=2),
                    given_args='\n'.join(_indent_but_first(given_args_lines, 2))).strip()

        else:
            _assert_never(explicit)
    else:
        _assert_never(explicit)

    return test_func, []


def _ghostwrite_for_function_points(points: List[FunctionPoint], module_name: str, explicit: Optional[Explicit],
                                    bare: bool) -> Tuple[str, List[str]]:
    """
    Ghostwrite a test case for the given function points.

    Return (generated code, errors if any).
    """
    errors = []  # type: List[str]
    test_funcs = []  # type: List[str]
    for point in points:
        test_func, test_func_errors = _ghostwrite_test_function(module_name=module_name, point=point, explicit=explicit)
        if test_func_errors:
            errors.extend(test_func_errors)
        else:
            test_funcs.append(test_func)

    if errors:
        return '', errors

    if bare:
        return '\n\n'.join(test_funcs), []

    blocks = []  # type: List[str]

    # yapf: disable
    header = '\n\n'.join([
        '"""Test {} with inferred Hypothesis strategies."""'.format(module_name),
        "import unittest",
        (("import hypothesis.strategies as st\n"
          "from hypothesis import assume, given\n") if explicit else '') +
        "import icontract.integration.with_hypothesis",
        "import {}".format(module_name),
    ])
    blocks.append(header)
    # yapf: enable

    if len(points) == 0:
        blocks.append(
            textwrap.dedent('''\
                class TestWithInferredStrategies(unittest.TestCase):
                    """Test all functions from {0} with inferred Hypothesis strategies."""
                    # Either there are no functions in {0} or all the functions were excluded.
                '''.format(module_name)).strip())
    else:
        body = '\n\n'.join(test_funcs)

        # yapf: disable
        test_case = [
            textwrap.dedent('''\
                    class TestWithInferredStrategies(unittest.TestCase):
                        """Test all functions from {module} with inferred Hypothesis strategies."""
                        
                        {body}
                    ''').format(
                module=module_name,
                body='\n'.join(_indent_but_first(lines=body.splitlines(), level=1))).strip()
        ]
        # yapf: enable
        blocks.append(''.join(test_case))

    blocks.append(textwrap.dedent('''\
        if __name__ == '__main__':
            unittest.main()
        '''))

    return '\n\n\n'.join(blocks), []


def ghostwrite(general: ParamsGeneral, command: ParamsGhostwrite) -> Tuple[str, List[str]]:
    """
    Write a unit test module for the specified functions.

    Return (generated code, errors if any).
    """
    mod, errors = _load_module_with_name(command.module_name)
    if errors:
        return '', errors

    assert mod is not None

    points, errors = _select_function_points(
        source_code=inspect.getsource(mod), mod=mod, include=general.include, exclude=general.exclude)
    if errors:
        return '', errors

    return _ghostwrite_for_function_points(
        points=points, module_name=command.module_name, explicit=command.explicit, bare=command.bare)


def run(argv: List[str], stdout: TextIO, stderr: TextIO) -> int:
    """Execute the run routine."""
    parser = _make_argument_parser()
    args, out, err = _parse_args(parser=parser, argv=argv)
    if len(out) > 0:
        stdout.write(out)

    if len(err) > 0:
        stderr.write(err)

    if args is None:
        return 1

    params, errors = _parse_args_to_params(args=args)
    if errors:
        for error in errors:
            print(error, file=stderr)
            return 1

    assert params is not None

    if isinstance(params.command, ParamsTest):
        errors = test(general=params.general, command=params.command)
    elif isinstance(params.command, ParamsGhostwrite):
        code, errors = ghostwrite(general=params.general, command=params.command)
        if not errors:
            if params.command.output is None:
                stdout.write(code)
            else:
                params.command.output.write_text(code)
    else:
        _assert_never(params.command)

    if errors:
        for error in errors:
            print(error, file=stderr)
            return 1

    return 0


def entry_point() -> int:
    """Wrap the entry_point routine wit default arguments."""
    return run(argv=sys.argv[1:], stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    sys.exit(entry_point())
