"""Handle representations necessary for informative error messages."""
import ast
import inspect
import re
import reprlib
import textwrap
import uuid
from typing import Any, Mapping, MutableMapping, Callable, List, Dict, Iterable  # pylint: disable=unused-import
from typing import Optional, Tuple  # pylint: disable=unused-import

import asttokens

import icontract._recompute

from icontract._types import Contract


def _representable(value: Any) -> bool:
    """
    Check whether we want to represent the value in the error message on contract breach.

    We do not want to represent classes, methods, modules and functions.

    :param value: value related to an AST node
    :return: True if we want to represent it in the violation error
    """
    return not inspect.isclass(value) and not inspect.isfunction(value) and not inspect.ismethod(value) and not \
        inspect.ismodule(value) and not inspect.isbuiltin(value)


class Visitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and collect the representations of the selected nodes."""

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring

    def __init__(self, recomputed_values: Mapping[ast.AST, Any], variable_lookup: List[Mapping[str, Any]],
                 atok: asttokens.ASTTokens) -> None:
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

    def visit_SetComp(self, node: ast.ListComp) -> None:
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


def _is_lambda(a_function: Callable[..., Any]) -> bool:
    """
    Check whether the function is a lambda function.

    >>> def some_func()->bool: return True
    >>> _is_lambda(some_func)
    False

    >>> lmbd = lambda x: x > 0
    >>> _is_lambda(lmbd)
    True

    :param condition: condition function of a contract
    :return: True if condition is defined as lambda function
    """
    return a_function.__name__ == "<lambda>"


class ConditionLambdaInspection:
    """Represent the inspection of the condition function given as a lambda."""

    def __init__(self, atok: asttokens.ASTTokens, node: ast.Lambda) -> None:
        """
        Initialize.

        :param atok: parsed AST tree and tokens with added positional properties
        :param node: lambda AST node corresponding to the condition
        """
        self.atok = atok
        self.node = node
        self.text = atok.get_text(node.body)


_DECORATOR_RE = re.compile(r'^\s*@[a-zA-Z_]')
_DEF_CLASS_RE = re.compile(r'^\s*(def |class )')


class DecoratorInspection:
    """Represent the inspection of a decorator extracted from a source file and embedded in a dummy dynamic module."""

    def __init__(self, atok: asttokens.ASTTokens, node: ast.Call) -> None:
        """
        Initialize.

        :param atok: parsed AST tree and tokens with added positional properties
        :param node: lambda AST node corresponding to the condition
        """
        self.atok = atok
        self.node = node


def inspect_decorator(lines: List[str], lineno: int, filename: str) -> DecoratorInspection:
    """
    Parse the file in which the decorator is called and figure out the corresponding call AST node.

    :param lines: lines of the source file corresponding to the decorator call
    :param lineno: line index (starting with 0) of one of the lines in the decorator call
    :param filename: name of the file where decorator is called
    :return: inspected decorator call
    """
    if lineno < 0 or lineno >= len(lines):
        raise ValueError(("Given line number {} of one of the decorator lines "
                          "is not within the range [{}, {}) of lines in {}").format(lineno, 0, len(lines), filename))

    # Go up till a line starts with a decorator
    decorator_lineno = None  # type: Optional[int]
    for i in range(lineno, -1, -1):
        if _DECORATOR_RE.match(lines[i]):
            decorator_lineno = i
            break

    if decorator_lineno is None:
        raise SyntaxError("Decorator corresponding to the line {} could not be found in file {}: {!r}".format(
            lineno + 1, filename, lines[lineno]))

    # Find the decorator end -- it's either a function definition, a class definition or another decorator
    decorator_end_lineno = None  # type: Optional[int]
    for i in range(lineno + 1, len(lines)):
        line = lines[i]

        if _DECORATOR_RE.match(line) or _DEF_CLASS_RE.match(line):
            decorator_end_lineno = i
            break

    if decorator_end_lineno is None:
        raise SyntaxError(("The next statement following the decorator corresponding to the line {} "
                           "could not be found in file {}: {!r}").format(lineno + 1, filename, lines[lineno]))

    decorator_lines = lines[decorator_lineno:decorator_end_lineno]

    # We need to dedent the decorator and add a dummy decoratee so that we can parse its text as valid source code.
    decorator_text = textwrap.dedent("".join(decorator_lines)) + "def dummy_{}(): pass".format(uuid.uuid4().hex)

    atok = asttokens.ASTTokens(decorator_text, parse=True)

    assert isinstance(atok.tree, ast.Module), "Expected the parsed decorator text to live in an AST module."

    module_node = atok.tree
    assert len(module_node.body) == 1, "Expected the module AST of the decorator text to have a single statement."
    assert isinstance(module_node.body[0], ast.FunctionDef), \
        "Expected the only statement in the AST module corresponding to the decorator text to be a function definition."

    func_def_node = module_node.body[0]

    assert len(func_def_node.decorator_list) == 1, \
        "Expected the function AST node corresponding to the decorator text to have a single decorator."

    assert isinstance(func_def_node.decorator_list[0], ast.Call), \
        "Expected the only decorator in the function definition AST node corresponding to the decorator text " \
        "to be a call node."

    call_node = func_def_node.decorator_list[0]

    return DecoratorInspection(atok=atok, node=call_node)


def inspect_lambda_condition(condition: Callable[..., bool]) -> Optional[ConditionLambdaInspection]:
    """
    Parse the file in which condition resides and figure out the corresponding lambda AST node.

    :param condition: condition lambda function
    :return: inspected lambda function, or None if the condition is not a lambda function
    """
    if not _is_lambda(a_function=condition):
        return None

    # We need to extract the source code corresponding to the decorator since inspect.getsource() is broken with
    # lambdas.

    # Find the line corresponding to the condition lambda
    lines, condition_lineno = inspect.findsource(condition)
    filename = inspect.getsourcefile(condition)

    decorator_inspection = inspect_decorator(lines=lines, lineno=condition_lineno, filename=filename)

    call_node = decorator_inspection.node

    lambda_node = None  # type: Optional[ast.Lambda]

    if len(call_node.args) > 0:
        assert isinstance(call_node.args[0], ast.Lambda), \
            ("Expected the first argument to the decorator to be a condition as lambda AST node, "
             "but got: {}").format(type(call_node.args[0]))

        lambda_node = call_node.args[0]

    elif len(call_node.keywords) > 0:
        for keyword in call_node.keywords:
            if keyword.arg == "condition":
                assert isinstance(keyword.value, ast.Lambda), \
                    "Expected lambda node as value of the 'condition' argument to the decorator."

                lambda_node = keyword.value
                break

        assert lambda_node is not None, "Expected to find a keyword AST node with 'condition' arg, but found none"
    else:
        raise AssertionError(
            "Expected a call AST node of a decorator to have either args or keywords, but got: {}".format(
                ast.dump(call_node)))

    return ConditionLambdaInspection(atok=decorator_inspection.atok, node=lambda_node)


def repr_values(condition: Callable[..., bool], lambda_inspection: Optional[ConditionLambdaInspection],
                condition_kwargs: Mapping[str, Any], a_repr: reprlib.Repr) -> List[str]:
    # pylint: disable=too-many-locals
    """
    Represent function arguments and frame values in the error message on contract breach.

    :param condition: condition function of the contract
    :param lambda_inspection:
        inspected lambda AST node corresponding to the condition function (None if the condition was not given as a
        lambda function)
    :param condition_kwargs: condition arguments
    :param a_repr: representation instance that defines how the values are represented.
    :return: list of value representations
    """
    if _is_lambda(a_function=condition):
        assert lambda_inspection is not None, "Expected a lambda inspection when given a condition as a lambda function"
    else:
        assert lambda_inspection is None, "Expected no lambda inspection in a condition given as a non-lambda function"

    reprs = dict()  # type: MutableMapping[str, Any]

    if lambda_inspection is not None:
        # Collect the variable lookup of the condition function:
        variable_lookup = []  # type: List[Mapping[str, Any]]

        # Add condition arguments to the lookup
        variable_lookup.append(condition_kwargs)

        # Add closure to the lookup
        closure_dict = dict()  # type: Dict[str, Any]

        if condition.__closure__ is not None:  # type: ignore
            closure_cells = condition.__closure__  # type: ignore
            freevars = condition.__code__.co_freevars

            assert len(closure_cells) == len(freevars), \
                "Number of closure cells of a condition function ({}) == number of free vars ({})".format(
                    len(closure_cells), len(freevars))

            for cell, freevar in zip(closure_cells, freevars):
                closure_dict[freevar] = cell.cell_contents

        variable_lookup.append(closure_dict)

        # Add globals to the lookup
        if condition.__globals__ is not None:  # type: ignore
            variable_lookup.append(condition.__globals__)  # type: ignore

        # pylint: disable=protected-access
        recompute_visitor = icontract._recompute.Visitor(variable_lookup=variable_lookup)

        recompute_visitor.visit(node=lambda_inspection.node.body)
        recomputed_values = recompute_visitor.recomputed_values

        repr_visitor = Visitor(
            recomputed_values=recomputed_values, variable_lookup=variable_lookup, atok=lambda_inspection.atok)
        repr_visitor.visit(node=lambda_inspection.node.body)

        reprs = repr_visitor.reprs
    else:
        for key, val in condition_kwargs.items():
            if _representable(value=val):
                reprs[key] = val

    parts = []  # type: List[str]
    for key in sorted(reprs.keys()):
        parts.append('{} was {}'.format(key, a_repr.repr(reprs[key])))

    return parts


def _walk_with_parent(node: ast.AST) -> Iterable[Tuple[ast.AST, Optional[ast.AST]]]:
    """Walk the abstract syntax tree by (node, parent)."""
    stack = [(node, None)]  # type: List[Tuple[ast.AST, Optional[ast.AST]]]
    while stack:
        node, parent = stack.pop()

        for child in ast.iter_child_nodes(node):
            stack.append((child, node))

        yield node, parent


def condition_as_text(condition: Callable[..., bool], lambda_inspection: Optional[ConditionLambdaInspection]) -> str:
    """
    Convert the condition into text.

    :param condition: condition function
    :param lambda_inspection: lambda inspection if the condition is a lambda function, or None otherwise
    :return: string representation of the condition
    """
    if _is_lambda(a_function=condition):
        assert lambda_inspection is not None, "Expected a lambda inspection when given a condition as a lambda function"
    else:
        assert lambda_inspection is None, "Expected no lambda inspection in a condition given as a non-lambda function"

    if lambda_inspection is None:
        condition_text = condition.__name__
    else:
        condition_text = lambda_inspection.text

    return condition_text


def generate_message(contract: Contract, condition_kwargs: Mapping[str, Any]) -> str:
    """Generate the message upon contract violation."""
    # pylint: disable=protected-access
    parts = []  # type: List[str]

    if contract.description is not None:
        parts.append("{}: ".format(contract.description))

    lambda_inspection = inspect_lambda_condition(condition=contract.condition)

    parts.append(condition_as_text(condition=contract.condition, lambda_inspection=lambda_inspection))

    if contract._repr_func:
        parts.append(': ')
        parts.append(contract._repr_func(**condition_kwargs))
    else:
        repr_vals = repr_values(
            condition=contract.condition,
            lambda_inspection=lambda_inspection,
            condition_kwargs=condition_kwargs,
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
