"""
Integrate icontract with Hypothesis.

You need to install ``hypothesis`` extras in order to use this module.
"""
# pylint: disable=unused-argument
# pylint: disable=protected-access
# pylint: disable=inconsistent-return-statements

import ast
import datetime
import decimal
import fractions
import inspect
import re
import typing
from typing import TypeVar, Callable, Any, List, Mapping, Optional, Union, Dict, Tuple, Type, AnyStr, Pattern

import hypothesis.errors
import hypothesis.strategies

import icontract._checkers
import icontract._recompute
import icontract._represent
import icontract._types

CallableT = TypeVar('CallableT', bound=Callable[..., Any])

T = TypeVar('T')


def _assume_preconditions_always_satisfied(*args: Tuple[Any, ...], **kwargs: Dict[str, Any]) -> None:
    """Assume that the preconditions are always satisfied (say, when there are no preconditions)."""
    pass


def make_assume_preconditions(func: CallableT) -> Callable[..., None]:
    """
    Create a function that assumes the preconditions are satisfied given the positional and keyword arguments.

    Here is an example test case which tests a function ``some_func``:

    .. code-block:: python

        import unittest
        import hypothesis.strategies
        import icontract.extra.hypothesis

        @icontract.require(lambda x: x > 0)
        @icontract.require(lambda x: x % 3 == 0)
        def some_func(x: int) -> None:
            ...

        class TestSomething(unittest.TestCase):
            def test_that_it_works(self) -> None:
                assume_preconditions = icontract.extra.hypothesis.make_assume_preconditions(some_func)

                @hypothesis.given(x=hypothesis.strategies.integers)
                def run(x: int) -> None:
                    assume_preconditions(x)
                    some_func(x)

                run()
    """
    # The implementation follows tightly icontract._checkers.decorate_with_checker and
    # icontract._checkers._assert_precondition.

    checker = icontract._checkers.find_checker(func)
    if checker is None:
        return _assume_preconditions_always_satisfied

    preconditions = getattr(checker, "__preconditions__", None)
    if preconditions is None:
        return _assume_preconditions_always_satisfied

    sign = inspect.signature(func)
    param_names = list(sign.parameters.keys())
    kwdefaults = icontract._checkers.resolve_kwdefaults(sign=sign)

    def assume_preconditions(*args, **kwargs) -> None:  # type: ignore
        """Accept only positional and keyword arguments that satisfy one of the precondition groups."""
        resolved_kwargs = icontract._checkers.kwargs_from_call(
            param_names=param_names, kwdefaults=kwdefaults, args=args, kwargs=kwargs)

        success = True

        for group in preconditions:  # pylint: disable=not-an-iterable
            success = True
            for contract in group:
                condition_kwargs = icontract._checkers.select_condition_kwargs(
                    contract=contract, resolved_kwargs=resolved_kwargs)

                check = contract.condition(**condition_kwargs)

                if icontract._checkers.not_check(check=check, contract=contract):
                    success = False
                    break

            if success:
                return

        if not success:
            raise hypothesis.errors.UnsatisfiedAssumption()

    return assume_preconditions


class _InferredMinMax:
    """Represent the inference result of boundaries on an argument."""

    def __init__(self,
                 min_value: Optional[Union[int, float]] = None,
                 min_inclusive: bool = False,
                 max_value: Optional[Union[int, float]] = None,
                 max_inclusive: bool = False) -> None:
        """Initialize with the given values."""
        self.min_value = min_value
        self.min_inclusive = min_inclusive
        self.max_value = max_value
        self.max_inclusive = max_inclusive


def _no_name_in_descendants(root: ast.expr, name: str) -> bool:
    """Check whether a ``ast.Name`` node with ``root`` identifier is present in the descendants of the node."""
    found = False

    class Visitor(ast.NodeVisitor):
        """Search for the name node."""

        def visit_Name(self, node: ast.Name) -> None:
            if node.id == name:
                nonlocal found
                found = True

        def generic_visit(self, node: Any) -> None:
            if not found:
                super(Visitor, self).generic_visit(node)

    visitor = Visitor()
    visitor.visit(root)

    return not found


def _recompute(condition: Callable[..., Any], node: ast.expr) -> Tuple[Any, bool]:
    """Recompute the value corresponding to the node."""
    recompute_visitor = icontract._recompute.Visitor(
        variable_lookup=icontract._represent.collect_variable_lookup(condition=condition, condition_kwargs=None))

    recompute_visitor.visit(node=node)

    if node in recompute_visitor.recomputed_values:
        return recompute_visitor.recomputed_values[node], True

    return None, False


def _infer_min_max_from_node(condition: Callable[..., bool], node: ast.Compare,
                             arg_name: str) -> Optional[_InferredMinMax]:
    """Match one of the patterns against the AST compare node."""
    # pylint: disable=too-many-boolean-expressions
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    if len(node.comparators) == 1:
        comparator = node.comparators[0]
        operation = node.ops[0]

        # Match something like "x > 0" and "x < 100"
        if isinstance(node.left, ast.Name) and \
                node.left.id == arg_name and \
                _no_name_in_descendants(root=comparator, name=arg_name):
            value, recomputed = _recompute(condition=condition, node=comparator)

            # If we can not recompute the value, we also can not infer the bounds.
            if not recomputed:
                return None

            # Match something like "x < 100"
            if isinstance(operation, ast.Lt):
                return _InferredMinMax(max_value=value, max_inclusive=False)
            # Match something like "x =< 100"
            elif isinstance(operation, ast.LtE):
                return _InferredMinMax(max_value=value, max_inclusive=True)

            # Match something like "x > 0"
            elif isinstance(operation, ast.Gt):
                return _InferredMinMax(min_value=value, min_inclusive=False)
            # Match something like "x >= 0"
            elif isinstance(operation, ast.GtE):
                return _InferredMinMax(min_value=value, min_inclusive=True)

            # We could not infer any bound from this condition.
            else:
                return None

        # Match something like "0 < x" and "100 > x"
        if _no_name_in_descendants(root=node.left, name=arg_name) and \
                isinstance(comparator, ast.Name) and \
                comparator.id == arg_name:
            value, recomputed = _recompute(condition=condition, node=node.left)

            # If we can not recompute the value, we also can not infer the bounds.
            if not recomputed:
                return None

            # Match something like "0 < x"
            if isinstance(operation, ast.Lt):
                return _InferredMinMax(min_value=value, min_inclusive=False)

            # Match something like "0 =< x"
            if isinstance(operation, ast.LtE):
                return _InferredMinMax(min_value=value, min_inclusive=True)

            # Match something like "100 > x"
            elif isinstance(operation, ast.Gt):
                return _InferredMinMax(max_value=value, max_inclusive=False)

            # Match something like "100 >= x"
            elif isinstance(operation, ast.GtE):
                return _InferredMinMax(max_value=value, max_inclusive=True)

            # We could not infer any bound from this condition.
            else:
                pass

    elif len(node.comparators) == 2:
        # Match something like "0 < x < 100" and "0 > x > -100"
        if _no_name_in_descendants(root=node.left, name=arg_name) and \
                isinstance(node.comparators[0], ast.Name) and \
                node.comparators[0].id == arg_name and \
                _no_name_in_descendants(root=node.comparators[1], name=arg_name):

            left_value, recomputed = _recompute(condition=condition, node=node.left)

            # If we can not recompute the left value, we also can not infer the bounds.
            if not recomputed:
                return None

            right_value, recomputed = _recompute(condition=condition, node=node.comparators[1])

            # If we can not recompute the right value, we also can not infer the bounds.
            if not recomputed:
                return None

            op0, op1 = node.ops

            # Match something like "0 < x < 100"
            if isinstance(op0, (ast.Lt, ast.LtE)) and \
                    isinstance(op1, (ast.Lt, ast.LtE)):
                return _InferredMinMax(
                    min_value=left_value,
                    min_inclusive=isinstance(op0, ast.LtE),
                    max_value=right_value,
                    max_inclusive=isinstance(op1, ast.LtE))

            # Match something like "0 > x > -100"
            elif isinstance(op0, (ast.Gt, ast.GtE)) and \
                    isinstance(op1, (ast.Gt, ast.GtE)):
                return _InferredMinMax(
                    min_value=right_value,
                    min_inclusive=isinstance(op0, ast.GtE),
                    max_value=left_value,
                    max_inclusive=isinstance(op1, ast.GtE))

            # We could not infer any bound from this condition.
            else:
                pass

    return None


def _body_node_from_condition(condition: Callable[..., Any]) -> Optional[ast.expr]:
    """Try to extract the body node of the contract's lambda condition."""
    if not icontract._represent.is_lambda(a_function=condition):
        return None

    lines, condition_lineno = inspect.findsource(condition)
    filename = inspect.getsourcefile(condition)
    assert filename is not None

    decorator_inspection = icontract._represent.inspect_decorator(
        lines=lines, lineno=condition_lineno, filename=filename)
    lambda_inspection = icontract._represent.find_lambda_condition(decorator_inspection=decorator_inspection)

    assert lambda_inspection is not None, \
        "Expected lambda_inspection to be non-None if _is_lambda is True on: {}".format(condition)

    body_node = lambda_inspection.node.body

    return body_node


# yapf: disable
def _infer_min_max_from_preconditions(
        arg_name: str,
        contracts: List[icontract._types.Contract]
) -> Tuple[_InferredMinMax, List[icontract._types.Contract]]:
    """
    Infer the min and max values for the given argument from all related preconditions.

    Return the contracts which could not be interpreted.
    """
    # yapf: enable
    min_value = None  # type: Optional[Union[int, float]]
    max_value = None  # type: Optional[Union[int, float]]

    remaining_contracts = []  # type: List[icontract._types.Contract]

    for contract in contracts:
        body_node = _body_node_from_condition(condition=contract.condition)

        if body_node is None:
            remaining_contracts.append(contract)
            continue

        if isinstance(body_node, ast.Compare):
            inferred = _infer_min_max_from_node(condition=contract.condition, node=body_node, arg_name=arg_name)

            if inferred is not None:
                # We need to constrain min and max values.
                # Hence we use ``max`` for min and ``min`` for max, respectively.
                # This might be a bit counter-intuitive at the first sight.

                if inferred.min_value is not None:
                    min_value = inferred.min_value if min_value is None else max(inferred.min_value, min_value)

                if inferred.max_value is not None:
                    max_value = inferred.max_value if max_value is None else min(inferred.max_value, max_value)
            else:
                remaining_contracts.append(contract)
        else:
            remaining_contracts.append(contract)

    return _InferredMinMax(min_value=min_value, max_value=max_value), remaining_contracts


# yapf: disable
def _make_strategy_with_min_max_for_type(
        a_type: Type[T],
        inferred: _InferredMinMax
) -> hypothesis.strategies.SearchStrategy[T]:
    # yapf: enable
    if a_type == int:
        # hypothesis.strategies.integers is always inclusive so we have to cut off the boundaries a bit
        # if they are exclusive.
        min_value = inferred.min_value
        if min_value is not None and not inferred.min_inclusive:
            min_value += 1

        max_value = inferred.max_value
        if max_value is not None and not inferred.max_inclusive:
            max_value -= 1

        strategy = hypothesis.strategies.integers(
            min_value=min_value,  # type: ignore
            max_value=max_value  # type: ignore
        )  # type: hypothesis.strategies.SearchStrategy[Any]

    elif a_type == float:
        strategy = hypothesis.strategies.floats(
            min_value=inferred.min_value,
            max_value=inferred.max_value,
            exclude_min=inferred.min_value is not None and not inferred.min_inclusive,
            exclude_max=inferred.max_value is not None and not inferred.max_inclusive)

    elif a_type == fractions.Fraction:
        strategy = hypothesis.strategies.fractions(min_value=inferred.min_value, max_value=inferred.max_value)

    elif a_type == decimal.Decimal:
        strategy = hypothesis.strategies.decimals(min_value=inferred.min_value, max_value=inferred.max_value)

    elif a_type == datetime.date:
        strategy = hypothesis.strategies.dates(
            min_value=inferred.min_value if inferred.min_value is not None else datetime.date.min,  # type: ignore
            max_value=inferred.max_value if inferred.max_value is not None else datetime.date.max)  # type: ignore

    elif a_type == datetime.datetime:
        strategy = hypothesis.strategies.datetimes(
            min_value=inferred.min_value if inferred.min_value is not None else datetime.datetime.min,
            max_value=inferred.max_value if inferred.max_value is not None else datetime.datetime.max)

    elif a_type == datetime.time:
        strategy = hypothesis.strategies.times(
            min_value=inferred.min_value if inferred.min_value is not None else datetime.time.min,
            max_value=inferred.max_value if inferred.max_value is not None else datetime.time.max)

    elif a_type == datetime.timedelta:
        strategy = hypothesis.strategies.timedeltas(
            min_value=inferred.min_value if inferred.min_value is not None else datetime.timedelta.min,  # type: ignore
            max_value=inferred.max_value if inferred.max_value is not None else datetime.timedelta.max)  # type: ignore

    else:
        raise AssertionError("Unexpected type hint: {}".format(a_type))

    # The strategies for int and float allow us to trivially handle exclusive bounds.
    # We have to filter for all the other types.
    if not isinstance(a_type, (int, float)):
        if inferred.min_value is not None and not inferred.min_inclusive:
            strategy.filter(lambda x: x > inferred.min_value)

        if inferred.max_value is not None and not inferred.max_inclusive:
            strategy.filter(lambda x: x < inferred.max_value)

    return strategy


# We need to compile a dummy pattern so that we can compare addresses of re.Pattern.match functions.
_DUMMY_RE = re.compile(r'something')


def _infer_regexp_from_condition(arg_name: str, condition: Callable[..., Any]) -> Optional[Pattern[AnyStr]]:
    """Try to infer the regular expression pattern from a precondition."""
    body_node = _body_node_from_condition(condition=condition)
    if body_node is None:
        return None

    if not isinstance(body_node, ast.Call):
        return None

    if not _no_name_in_descendants(root=body_node.func, name=arg_name):
        return None

    if not isinstance(body_node.func, ast.Attribute):
        return None

    if body_node.func.attr != "match":
        return None

    callee, recomputed = _recompute(condition=condition, node=body_node.func.value)
    if not recomputed:
        return None

    if callee == re:
        # Match "re.match(r'Some pattern', s, *args, *kwargs)
        if (len(body_node.args) >= 2 and _no_name_in_descendants(root=body_node.args[0], name=arg_name)
                and isinstance(body_node.args[1], ast.Name) and body_node.args[1].id == arg_name
                and not any(_no_name_in_descendants(root=arg, name=arg_name) for arg in body_node.args[2:])):
            # Recompute the pattern
            args = []  # type: List[Any]
            for arg in [body_node.args[0]] + body_node.args[2:]:
                value, recomputed = _recompute(condition=condition, node=arg)
                if not recomputed:
                    return None

                args.append(value)

            kwargs = dict()  # type: Dict[str, Any]
            for keyword in body_node.keywords:
                value, recomputed = _recompute(condition=condition, node=keyword.value)
                if not recomputed:
                    return None

                assert keyword.arg is not None, 'Unexpected missing arg for a keyword: {}'.format(ast.dump(keyword))
                kwargs[keyword.arg] = value

            pattern = re.compile(*args, **kwargs)
            return pattern

    elif isinstance(callee, re.Pattern):
        return callee

    return None


def _infer_str_strategy_from_preconditions(
        arg_name: str, contracts: List[icontract._types.Contract]
) -> Tuple[Optional[hypothesis.strategies.SearchStrategy[AnyStr]], List[icontract._types.Contract]]:
    """
    Try to match code patterns on AST of the preconditions contracts and infer the string strategy.

    Return (strategy if possible, remaining contracts).
    """
    found_idx = -1  # Index of the contract that defines the pattern, -1 if not found
    re_pattern = None  # type: Optional[re.Pattern[AnyStr]]

    for i, contract in enumerate(contracts):
        re_pattern = _infer_regexp_from_condition(arg_name=arg_name, condition=contract.condition)
        if re_pattern is not None:
            found_idx = i
            break

    if found_idx == -1:
        return None, contracts[:]

    assert re_pattern is not None
    return hypothesis.strategies.from_regex(regex=re_pattern), contracts[:found_idx] + contracts[found_idx + 1:]


# yapf: disable
def _infer_strategies_recursively(
        type_hints: Mapping[str, Any],
        contracts: Optional[List[icontract._types.Contract]]
) -> Mapping[str, hypothesis.strategies.SearchStrategy[Any]]:
    """
    Infer the strategies on the given argument type hints and corresponding contracts.

    Call recursively on all composite types such as classes etc.

    Note that contracts can be None. While the function in question might have no preconditions,
    we need to infer the strategies for arguments of composite types whose ``__init__`` methods
    might still impose the preconditions.
    """
    # yapf: enable
    # pylint: disable=too-many-locals,too-many-branches
    contracts_for_arg = dict()  # type: Dict[str, List[icontract._types.Contract]]
    if contracts is not None:
        for contract in contracts:
            if len(contract.condition_args) == 1:
                arg_name = contract.condition_args[0]
                if arg_name not in contracts_for_arg:
                    contracts_for_arg[arg_name] = [contract]
                else:
                    contracts_for_arg[arg_name].append(contract)

    ##
    # Build up strategies for all the arguments
    ##

    strategies = dict()  # type: Dict[str, hypothesis.strategies.SearchStrategy[Any]]

    for arg_name, type_hint in type_hints.items():
        # Set the basic strategy based on type for arguments for which we can not reduce the search space trivially
        # by filtering
        if arg_name not in contracts_for_arg:
            strategies[arg_name] = hypothesis.strategies.from_type(type_hint)
            continue

        remaining_contracts = contracts_for_arg[arg_name]

        strategy = None  # type: Optional[hypothesis.strategies.SearchStrategy[Any]]

        # yapf: disable
        if type_hint in [
            int, float, fractions.Fraction, decimal.Decimal, datetime.date, datetime.datetime,
            datetime.time, datetime.timedelta
        ]:
            # yapf: enable
            inferred, remaining_contracts = _infer_min_max_from_preconditions(
                arg_name=arg_name, contracts=contracts_for_arg[arg_name])

            if inferred.min_value is not None and \
                    inferred.max_value is not None and \
                    inferred.min_value > inferred.max_value:
                raise ValueError(("The min and max values inferred for the argument {} could not be satisfied: "
                                  "inferred min is {}, inferred max is {}. Are your preconditions correct?").format(
                    arg_name, inferred.min_value, inferred.max_value))

            strategy = _make_strategy_with_min_max_for_type(a_type=type_hint, inferred=inferred)

        if strategy is None and type_hint == str:
            strategy, remaining_contracts = _infer_str_strategy_from_preconditions(
                arg_name=arg_name, contracts=contracts_for_arg[arg_name])

        if strategy is None:
            strategy = hypothesis.strategies.from_type(type_hint)

        for contract in remaining_contracts:
            strategy = strategy.filter(contract.condition)

        strategies[arg_name] = strategy

    return strategies


def _builds_with_preconditions(a_type: Type[T]) -> hypothesis.strategies.SearchStrategy[T]:
    """Creates a strategy to generate instances of type ``a_type`` which satisfy the preconditions on ``__init__``."""
    init = getattr(a_type, "__init__")

    if inspect.isfunction(init):
        strategies = infer_strategies(init)
    elif isinstance(init, icontract._checkers._SLOT_WRAPPER_TYPE):
        # We have to distinguish this special case which is used by named tuples and
        # possibly other optimized data structures.
        # In those cases, we have to infer the strategy based on __new__ instead of __init__.
        new = getattr(a_type, "__new__")
        assert new is not None, "Expected __new__ in {} if __init__ is a slot wrapper.".format(a_type)
        strategies = infer_strategies(new)
    else:
        raise AssertionError("Expected __init__ to be either a function or a slot wrapper, but got: {}".format(
            type(init)))

    return hypothesis.strategies.builds(a_type, **strategies)


# TODO: document in the README that the types will be automatically registered with Hypothesis.


# TODO: document it in the README so that people can debug
# yapf: disable
def infer_strategies(
        func: CallableT
) -> Mapping[str, hypothesis.strategies.SearchStrategy[Any]]:
    r"""
    Infer the search strategies of the arguments for the given function using type hints and heuristics.

    Apart from the internal usage, this function is mainly meant for manual inspection
    of the inferred strategies.

    Here is an example how you can debug what strategies will be used to test ``some_func``:

    .. code-block:: python

        import unittest
        import icontract.extra.hypothesis

        @icontract.require(lambda x: x > 0)
        def some_func(x: int) -> None:
            ...

        class TestSomething(unittest.TestCase):
            def test_that_it_works(self) -> None:
                strategies = icontract.integration.with_hypothesis.\
                    infer_strategies(some_func)

                # This code
                print('strategies: {!r}'.format(strategies))
                # prints: strategies: {'x': integers(min_value=0)}
    """
    # yapf: enable
    type_hints = typing.get_type_hints(func)
    if 'return' in type_hints:
        del type_hints['return']

    checker = icontract._checkers.find_checker(func)

    if checker is None:
        strategies = _infer_strategies_recursively(
            type_hints=type_hints, contracts=None)  # type: Mapping[str, hypothesis.strategies.SearchStrategy[Any]]
    else:
        preconditions = getattr(checker, "__preconditions__", None)  # type: List[List[icontract._types.Contract]]
        if preconditions is None:
            strategies = _infer_strategies_recursively(type_hints=type_hints, contracts=None)
        else:
            if len(preconditions) == 0:
                strategies = _infer_strategies_recursively(type_hints=type_hints, contracts=None)

            # Optimize for the most common case that the preconditions are not weakened
            elif len(preconditions) == 1:
                strategies = _infer_strategies_recursively(type_hints=type_hints, contracts=preconditions[0])
            else:
                # Make unions of strategies for the same variable through one_of's
                # over groups of weakened ("require else") contracts

                unions_of_strategies = dict()  # type: Dict[str, List[hypothesis.strategies.SearchStrategy[Any]]]
                for contracts in preconditions:
                    strategies_for_group = _infer_strategies_recursively(type_hints=type_hints, contracts=contracts)

                    for arg_name, strategy in strategies_for_group.items():
                        if arg_name not in unions_of_strategies:
                            unions_of_strategies[arg_name] = [strategy]
                        else:
                            unions_of_strategies[arg_name].append(strategy)

                # yapf: disable
                strategies = {
                    arg_name: hypothesis.strategies.one_of(*union)
                    for arg_name, union in unions_of_strategies.items()
                }
                # yapf: enable

    return strategies


def test_with_inferred_strategies(func: CallableT) -> None:
    r"""
    Use type hints to infer argument types and heuristics to optimize strategies based on the contracts.

    The heuristics are very basic at the moment. We only match comparisons against numeric constants.

    Here is an example test case which tests a function ``some_func``:

    .. code-block:: python

        import unittest
        import icontract.integration.with_hypothesis

        @icontract.require(lambda x: x > 0)
        @icontract.require(lambda x: x < 100)
        @icontract.require(lambda y: 0 < y < 100)
        def some_func(x: int, y: int) -> None:
            ...

        class TestSomething(unittest.TestCase):
            def test_that_it_works(self) -> None:
                icontract.integration.with_hypothesis.\
                    test_with_inferred_strategies(some_func)
    """
    assume_preconditions = make_assume_preconditions(func=func)

    def execute(*args: Tuple[Any, ...], **kwargs: Dict[str, Any]) -> None:
        # We still need to assume the preconditions for cases
        # where heuristics could not optimize the search space.
        assume_preconditions(*args, **kwargs)
        func(*args, **kwargs)

    strategies = infer_strategies(func=func)

    if len(strategies) == 0:
        raise TypeError(("No strategies could be inferred for the function: {}. "
                         "Have you provided type hints for the arguments?").format(func))

    wrapped = hypothesis.given(**strategies)(execute)
    wrapped()

# TODO: don't forget to mention in readme that behavioral subtyping and inheritance of preconditions is important!
