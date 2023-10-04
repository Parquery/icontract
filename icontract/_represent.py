"""Handle representations necessary for informative error messages."""
import ast
import inspect
import re
import reprlib
import sys
import textwrap
import uuid
from typing import (
    Any,
    Mapping,
    MutableMapping,
    Callable,
    List,
    Dict,
    cast,
    Optional,
)  # pylint: disable=unused-import

import asttokens.asttokens

import icontract._recompute
from icontract._types import Contract
from icontract._globals import CallableT

# pylint does not play with typing.Mapping.
# pylint: disable=unsubscriptable-object


def _representable(value: Any) -> bool:
    """
    Check whether we want to represent the value in the error message on contract breach.

    We do not want to represent classes, methods, modules and functions.

    :param value: value related to an AST node
    :return: True if we want to represent it in the violation error
    """
    return (
        not inspect.isclass(value)
        and not inspect.isfunction(value)
        and not inspect.ismethod(value)
        and not inspect.ismodule(value)
        and not inspect.isbuiltin(value)
    )


class Visitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and collect the representations of the selected nodes."""

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring

    def __init__(
        self,
        recomputed_values: Mapping[ast.AST, Any],
        variable_lookup: List[Mapping[str, Any]],
        atok: asttokens.asttokens.ASTTokens,
    ) -> None:
        """
        Initialize.

        :param recomputed_values: AST node of a condition function -> value associated with the node
        :param variable_lookup:
            list of lookup tables to look-up the values of the variables, sorted by precedence.
            The visitor needs it here to check whether we overrode a built-in variable (like ``id``).
        :param atok: parsed AST tree and tokens with additional positions in source code

        """
        self._recomputed_values = recomputed_values
        self._variable_lookup = variable_lookup
        self.reprs = dict()  # type: MutableMapping[str, str]
        self._atok = atok

    if sys.version_info >= (3, 6):

        def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
            """Show the whole joined strings without descending into the values."""
            if node in self._recomputed_values:
                value = self._recomputed_values[node]

                if _representable(value=value):
                    text = self._atok.get_text(node)
                    self.reprs[text] = value

    def visit_Name(self, node: ast.Name) -> None:
        """
        Resolve the name from the variable look-up and the built-ins.

        Due to possible branching (e.g., If-expressions), some nodes might lack the recomputed values. These nodes
        are ignored.
        """
        if node in self._recomputed_values:
            value = self._recomputed_values[node]

            # Check if it is a non-built-in
            is_builtin = True
            for lookup in self._variable_lookup:
                if node.id in lookup:
                    is_builtin = False
                    break

            if not is_builtin and _representable(value=value):
                text = self._atok.get_text(node)
                self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Represent the attribute by dumping its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]

            if _representable(value=value):
                text = self._atok.get_text(node)
                self.reprs[text] = value

        self.generic_visit(node=node)

    if sys.version_info >= (3, 8):

        def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
            """Represent the target with the value of the node."""
            if node in self._recomputed_values:
                value = self._recomputed_values[node]

                target = node.target

                if _representable(value=value):
                    self.reprs[target.id] = value

            self.generic_visit(node=node)

    def visit_Call(self, node: ast.Call) -> None:
        """Represent the call by dumping its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]
            text = self._atok.get_text(node)

            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Represent the list comprehension by dumping its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]
            text = self._atok.get_text(node)

            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Represent the set comprehension by dumping its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]
            text = self._atok.get_text(node)

            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Represent the dictionary comprehension by dumping its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]
            text = self._atok.get_text(node)

            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Represent the subscript with its source code."""
        if node in self._recomputed_values:
            value = self._recomputed_values[node]
            text = self._atok.get_text(node)

            self.reprs[text] = value

        self.generic_visit(node=node)


def is_lambda(a_function: CallableT) -> bool:
    """
    Check whether the function is a lambda function.

    >>> def some_func()->bool: return True
    >>> is_lambda(some_func)
    False

    >>> lmbd = lambda x: x > 0
    >>> is_lambda(lmbd)
    True

    :return: True if condition is defined as lambda function
    """
    return a_function.__name__ == "<lambda>"


class ConditionLambdaInspection:
    """Represent the inspection of the condition function given as a lambda."""

    def __init__(self, atok: asttokens.asttokens.ASTTokens, node: ast.Lambda) -> None:
        """
        Initialize.

        :param atok: parsed AST tree and tokens with added positional properties
        :param node: lambda AST node corresponding to the condition
        """
        self.atok = atok
        self.node = node

        text = atok.get_text(node.body)
        assert isinstance(text, str)
        self.text = text


_DECORATOR_RE = re.compile(r"^\s*@[a-zA-Z_]")
_DEF_CLASS_RE = re.compile(r"^\s*(async\s+def|def |class )")


class DecoratorInspection:
    """Represent the inspection of a decorator extracted from a source file and embedded in a dummy dynamic module."""

    def __init__(self, atok: asttokens.asttokens.ASTTokens, node: ast.Call) -> None:
        """
        Initialize.

        :param atok: parsed AST tree and tokens with added positional properties
        :param node: lambda AST node corresponding to the condition
        """
        self.atok = atok
        self.node = node


def inspect_decorator(
    lines: List[str], lineno: int, filename: str
) -> DecoratorInspection:
    """
    Parse the file in which the decorator is called and figure out the corresponding call AST node.

    :param lines: lines of the source file corresponding to the decorator call
    :param lineno: line index (starting with 0) of one of the lines in the decorator call
    :param filename: name of the file where decorator is called
    :return: inspected decorator call
    """
    if lineno < 0 or lineno >= len(lines):
        raise ValueError(
            (
                "Given line number {} of one of the decorator lines "
                "is not within the range [{}, {}) of lines in {}.\n\n"
                "The decorator lines were:\n{}"
            ).format(lineno, 0, len(lines), filename, "\n".join(lines))
        )

    # Go up till a line starts with a decorator
    decorator_lineno = None  # type: Optional[int]
    for i in range(lineno, -1, -1):
        if _DECORATOR_RE.match(lines[i]):
            decorator_lineno = i
            break

    if decorator_lineno is None:
        raise SyntaxError(
            "Decorator corresponding to the line {} could not be found in file {}: {!r}".format(
                lineno + 1, filename, lines[lineno]
            )
        )

    # Find the decorator end -- it's either a function definition, a class definition or another decorator
    decorator_end_lineno = None  # type: Optional[int]
    for i in range(lineno + 1, len(lines)):
        line = lines[i]

        if _DECORATOR_RE.match(line) or _DEF_CLASS_RE.match(line):
            decorator_end_lineno = i
            break

    if decorator_end_lineno is None:
        raise SyntaxError(
            (
                "The next statement following the decorator corresponding to the line {} "
                "could not be found in file {}: {!r}"
            ).format(lineno + 1, filename, lines[lineno])
        )

    decorator_lines = lines[decorator_lineno:decorator_end_lineno]

    # We need to dedent the decorator and add a dummy decorate so that we can parse its text as valid source code.
    decorator_text = textwrap.dedent(
        "".join(decorator_lines)
    ) + "def dummy_{}(): pass".format(uuid.uuid4().hex)

    atok = asttokens.asttokens.ASTTokens(decorator_text, parse=True)

    if not isinstance(atok.tree, ast.Module):
        raise ValueError(
            (
                "Expected the parsed decorator text to live in an AST module. "
                "Are you trying to inspect a condition lambda which was not stated in a decorator? "
                "(This feature is currently unsupported in icontract.) "
                "The decorator was expected at line {} in {}. "
                "The decorator lines under inspection were {}-{}."
            ).format(lineno + 1, filename, decorator_lineno + 1, decorator_end_lineno)
        )

    module_node = atok.tree

    if len(module_node.body) != 1:
        raise ValueError(
            (
                "Expected the module AST of the decorator text to have a single statement. "
                "Are you trying to inspect a condition lambda which was not stated in a decorator? "
                "(This feature is currently unsupported in icontract.) "
                "The decorator was expected at line {} in {}. "
                "The decorator lines under inspection were {}-{}."
            ).format(lineno + 1, filename, decorator_lineno + 1, decorator_end_lineno)
        )

    if not isinstance(module_node.body[0], ast.FunctionDef):
        raise ValueError(
            (
                "Expected the only statement in the AST module corresponding to the decorator text "
                "to be a function definition. "
                "Are you trying to inspect a condition lambda which was not stated in a decorator? "
                "(This feature is currently unsupported in icontract.) "
                "The decorator was expected at line {} in {}. "
                "The decorator lines under inspection were {}-{}."
            ).format(lineno + 1, filename, decorator_lineno + 1, decorator_end_lineno)
        )

    func_def_node = module_node.body[0]

    if len(func_def_node.decorator_list) != 1:
        raise ValueError(
            (
                "Expected the function AST node corresponding to the decorator text to have a single decorator. "
                "Are you trying to inspect a condition lambda which was not stated in a decorator? "
                "(This feature is currently unsupported in icontract.) "
                "The decorator was expected at line {} in {}. "
                "The decorator lines under inspection were {}-{}."
            ).format(lineno + 1, filename, decorator_lineno + 1, decorator_end_lineno)
        )

    if not isinstance(func_def_node.decorator_list[0], ast.Call):
        raise ValueError(
            (
                "Expected the only decorator in the function definition AST node corresponding "
                "to the decorator text to be a call node. "
                "Are you trying to inspect a condition lambda which was not stated in a decorator? "
                "(This feature is currently unsupported in icontract.) "
                "The decorator was expected at line {} in {}. "
                "The decorator lines under inspection were {}-{}."
            ).format(lineno + 1, filename, decorator_lineno + 1, decorator_end_lineno)
        )

    call_node = func_def_node.decorator_list[0]

    return DecoratorInspection(atok=atok, node=call_node)


def find_lambda_condition(
    decorator_inspection: DecoratorInspection,
) -> Optional[ConditionLambdaInspection]:
    """
    Inspect the decorator and extract the condition as lambda.

    If the condition is not given as a lambda function, return None.
    """
    call_node = decorator_inspection.node

    lambda_node = None  # type: Optional[ast.Lambda]

    if len(call_node.args) > 0:
        assert isinstance(call_node.args[0], ast.Lambda), (
            "Expected the first argument to the decorator to be a condition as lambda AST node, "
            "but got: {}"
        ).format(type(call_node.args[0]))

        lambda_node = call_node.args[0]

    elif len(call_node.keywords) > 0:
        for keyword in call_node.keywords:
            if keyword.arg == "condition":
                assert isinstance(
                    keyword.value, ast.Lambda
                ), "Expected lambda node as value of the 'condition' argument to the decorator."

                lambda_node = keyword.value
                break

        assert (
            lambda_node is not None
        ), "Expected to find a keyword AST node with 'condition' arg, but found none"
    else:
        raise AssertionError(
            "Expected a call AST node of a decorator to have either args or keywords, but got: {}".format(
                ast.dump(call_node)
            )
        )

    return ConditionLambdaInspection(atok=decorator_inspection.atok, node=lambda_node)


def inspect_lambda_condition(
    condition: Callable[..., Any]
) -> Optional[ConditionLambdaInspection]:
    """
    Try to extract the source code of the condition as lambda.

    If the condition is not a lambda, returns None.
    """
    if not is_lambda(condition):
        return None

    lines, condition_lineno = inspect.findsource(condition)
    filename = inspect.getsourcefile(condition)
    assert filename is not None

    decorator_inspection = inspect_decorator(
        lines=lines, lineno=condition_lineno, filename=filename
    )

    lambda_inspection = find_lambda_condition(decorator_inspection=decorator_inspection)

    return lambda_inspection


# fmt: off
def collect_variable_lookup(
        condition: Callable[..., Any],
        resolved_kwargs: Optional[Mapping[str, Any]] = None
) -> List[Mapping[str, Any]]:
    """
    Collect the variable lookups in order of precedence.

    :param condition: contract condition for which we are constructing a variable look-up tables
    :param resolved_kwargs:
        keyword arguments of the original function to be passed over to the condition (where applicable).

        The keyword arguments are added to the variable look-up tables accordingly.
        If ``resolved_kwargs`` is None, no keyword arguments will be added to the variable look-up table.
    """
    # fmt: on
    variable_lookup = []  # type: List[Mapping[str, Any]]

    ##
    # Condition-specific kwargs
    ##

    if resolved_kwargs is not None:
        variable_lookup.append(resolved_kwargs)

    ##
    # Add closure to the lookup
    ##

    closure_dict = dict()  # type: Dict[str, Any]

    if condition.__closure__ is not None:
        closure_cells = condition.__closure__
        freevars = condition.__code__.co_freevars

        assert len(closure_cells) == len(freevars), \
            "Number of closure cells of a condition function ({}) == number of free vars ({})".format(
                len(closure_cells), len(freevars))

        for cell, freevar in zip(closure_cells, freevars):
            closure_dict[freevar] = cell.cell_contents

    variable_lookup.append(closure_dict)

    ##
    # Add globals to the lookup
    ##

    if condition.__globals__ is not None:
        variable_lookup.append(condition.__globals__)

    return variable_lookup


def repr_values(condition: Callable[..., bool], lambda_inspection: Optional[ConditionLambdaInspection],
                resolved_kwargs: Mapping[str, Any], a_repr: reprlib.Repr) -> List[str]:
    """
    Represent function arguments and frame values in the error message on contract breach.

    :param condition: condition function of the contract
    :param lambda_inspection:
        inspected lambda AST node corresponding to the condition function (None if the condition was not given as a
        lambda function)
    :param resolved_kwargs: arguments put in the function call
    :param a_repr: representation instance that defines how the values are represented.
    :return: list of value representations
    """
    # Hide _ARGS and _KWARGS if they are not part of the condition for better readability
    if '_ARGS' in resolved_kwargs or '_KWARGS' in resolved_kwargs:
        parameters = inspect.signature(condition).parameters
        malleable_kwargs = cast(
            MutableMapping[str, Any],
            resolved_kwargs.copy()  # type: ignore
        )

        if '_ARGS' not in parameters:
            malleable_kwargs.pop('_ARGS', None)

        if '_KWARGS' not in parameters:
            malleable_kwargs.pop('_KWARGS', None)

        selected_kwargs = cast(Mapping[str, Any], malleable_kwargs)
    else:
        selected_kwargs = resolved_kwargs

    # Don't use ``resolved_kwargs`` from this point on.
    # ``selected_kwargs`` is meant to be used instead for better readability of error messages.

    if is_lambda(a_function=condition):
        assert lambda_inspection is not None, "Expected a lambda inspection when given a condition as a lambda function"
    else:
        assert lambda_inspection is None, "Expected no lambda inspection in a condition given as a non-lambda function"

    reprs = None  # type: Optional[MutableMapping[str, Any]]

    if lambda_inspection is not None:
        variable_lookup = collect_variable_lookup(condition=condition, resolved_kwargs=selected_kwargs)

        recompute_visitor = icontract._recompute.Visitor(variable_lookup=variable_lookup)

        recompute_visitor.visit(node=lambda_inspection.node.body)
        recomputed_values = recompute_visitor.recomputed_values

        repr_visitor = Visitor(
            recomputed_values=recomputed_values, variable_lookup=variable_lookup, atok=lambda_inspection.atok)
        repr_visitor.visit(node=lambda_inspection.node.body)

        reprs = repr_visitor.reprs

    # Add original arguments from the call unless they shadow a variable in the re-computation.
    #
    # The condition arguments are often not sufficient to figure out the error. The user usually needs
    # more context which is captured in the remainder of the call arguments.

    if reprs is None:
        reprs = dict()

    for key in sorted(selected_kwargs.keys()):
        val = selected_kwargs[key]
        if key not in reprs and _representable(value=val):
            reprs[key] = val

    parts = []  # type: List[str]

    # We need to sort in order to present the same violation error on repeated violations.
    # Otherwise, the order of the reported arguments may be arbitrary.
    for key in sorted(reprs.keys()):
        value = reprs[key]
        if isinstance(value, icontract._recompute.FirstExceptionInAll):
            writing = ['{} was False, e.g., with'.format(key)]
            for input_name, input_value in value.inputs:
                writing.append('\n')
                writing.append('  {} = {}'.format(input_name, a_repr.repr(input_value)))

            parts.append(''.join(writing))
        else:
            parts.append('{} was {}'.format(key, a_repr.repr(value)))

    return parts


def represent_condition(condition: CallableT) -> str:
    """Represent the condition as a string."""
    lambda_inspection = None  # type: Optional[ConditionLambdaInspection]
    if not is_lambda(a_function=condition):
        condition_repr = condition.__name__
    else:
        # We need to extract the source code corresponding to the decorator since inspect.getsource() is broken with
        # lambdas.
        lambda_inspection = inspect_lambda_condition(condition=condition)
        assert lambda_inspection is not None, "Unexpected no lambda inspection for condition: {}".format(condition)
        condition_repr = lambda_inspection.atok.get_text(lambda_inspection.node)

    return condition_repr


def generate_message(contract: Contract, resolved_kwargs: Mapping[str, Any]) -> str:
    """Generate the message upon contract violation."""
    parts = []  # type: List[str]

    if contract.location is not None:
        parts.append("{}:\n".format(contract.location))

    if contract.description is not None:
        parts.append("{}: ".format(contract.description))

    lambda_inspection = None  # type: Optional[ConditionLambdaInspection]
    if not is_lambda(a_function=contract.condition):
        condition_text = contract.condition.__name__
    else:
        # We need to extract the source code corresponding to the decorator since inspect.getsource() is broken with
        # lambdas.
        lambda_inspection = inspect_lambda_condition(condition=contract.condition)
        assert lambda_inspection is not None, \
            "Unexpected no lambda inspection for condition: {}".format(contract.condition)
        condition_text = lambda_inspection.text

    parts.append(condition_text)

    repr_vals = repr_values(
        condition=contract.condition,
        lambda_inspection=lambda_inspection,
        resolved_kwargs=resolved_kwargs,
        a_repr=contract._a_repr)

    if len(repr_vals) == 0:
        # Do not append anything since no value could be represented as a string.
        # This could appear in case we have, for example, a generator expression as the return value of a lambda.
        pass

    elif len(repr_vals) == 1:
        parts.append(': ')
        parts.append(repr_vals[0])
    else:
        parts.append(':\n')
        parts.append('\n'.join(repr_vals))

    msg = "".join(parts)

    return msg
