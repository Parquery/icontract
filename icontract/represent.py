"""Handle representations necessary for informative error messages."""
import ast
import inspect
import reprlib
from typing import Any, Mapping, MutableMapping, Callable, List, Dict  # pylint: disable=unused-import

import meta

import icontract.recompute


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

    def __init__(self, recomputed_values: Mapping[ast.AST, Any], variable_lookup: List[Mapping[str, Any]]) -> None:
        """
        Initialize.

        :param recomputed_values: AST node of a condition function -> value associated with the node
        :param variable_lookup:
            list of lookup tables to look-up the values of the variables, sorted by precedence.
            The visitor needs it here to check whether we overrode a built-in variable (like ``id``).

        """
        self._recomputed_values = recomputed_values
        self._variable_lookup = variable_lookup
        self.reprs = dict()  # type: MutableMapping[str, str]

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
                text = str(meta.dump_python_source(node)).strip()  # type: ignore
                self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Represent the attribute by dumping its source code."""
        value = self._recomputed_values[node]

        if _representable(value=value):
            text = str(meta.dump_python_source(node)).strip()  # type: ignore
            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Call(self, node: ast.Call) -> None:
        """Represent the call by dumping its source code."""
        value = self._recomputed_values[node]

        # pylint: disable=no-member
        text = str(meta.dump_python_source(node)).strip()  # type: ignore
        self.reprs[text] = value

        self.generic_visit(node=node)


def _is_lambda(condition: Callable[..., bool]) -> bool:
    """
    Check whether the condition is a lambda function.

    >>> def some_func()->bool: return True
    >>> _is_lambda(some_func)
    False

    >>> lmbd = lambda x: x > 0
    >>> _is_lambda(lmbd)
    True

    :param condition: condition function of a contract
    :return: True if condition is defined as lambda function
    """
    return condition.__name__ == "<lambda>"


def repr_values(condition: Callable[..., bool], condition_kwargs: Mapping[str, Any], a_repr: reprlib.Repr) -> List[str]:
    """
    Represent function arguments and frame values in the error message on contract breach.

    :param condition: contract condition function
    :param condition_kwargs: condition arguments
    :param a_repr: representation instance that defines how the values are represented.
    :return: list of value representations
    """
    # pylint: disable=too-many-locals
    reprs = dict()  # type: MutableMapping[str, Any]

    if _is_lambda(condition=condition):
        # pylint: disable=no-member

        root_node = meta.decompiler.decompile_func(condition)
        assert isinstance(root_node, ast.Lambda), \
            "Expected the node of the decompiled condition function to be a Lambda, but got: {}".format(
                ast.dump(root_node))

        assert isinstance(root_node.body, ast.Return), \
            "Expected the body of the de-compiled lambda function to be a Return, but got: {}".format(
                ast.dump(root_node))

        lambda_expression = root_node.body.value

        # pylint: enable=no-member

        # Collect the variable lookup of the condition function:
        # globals, closure, defaults, kwdefaults, arguments
        variable_lookup = []  # type: List[Dict[str, Any]]

        if condition.__globals__ is not None:
            variable_lookup.append(condition.__globals__)

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

        if condition.__kwdefaults__ is not None:
            variable_lookup.append(condition.__kwdefaults__)

        variable_lookup.append(condition_kwargs)

        recompute_visitor = icontract.recompute.Visitor(variable_lookup=variable_lookup)

        recompute_visitor.visit(node=lambda_expression)
        recomputed_values = recompute_visitor.recomputed_values

        repr_visitor = Visitor(recomputed_values=recomputed_values, variable_lookup=variable_lookup)
        repr_visitor.visit(node=lambda_expression)

        reprs = repr_visitor.reprs
    else:
        for key, val in condition_kwargs.items():
            if _representable(value=val):
                reprs[key] = val

    parts = []  # type: List[str]
    for key in sorted(reprs.keys()):
        parts.append('{} was {}'.format(key, a_repr.repr(reprs[key])))

    return parts


def condition_as_text(condition: Callable[..., bool]) -> str:
    """
    Decompile the condition function and generate the text based on its abstract syntax tree.

    The decompilation and generation is necessary since it is hard to otherwise parse the output of inspect.getsource()
    on decorator functions.

    :param condition: contract condition function
    :return: string representation of the condition function
    """
    if not _is_lambda(condition):
        return condition.__name__

    # pylint: disable=no-member

    lambda_node = meta.decompiler.decompile_func(condition)
    assert isinstance(lambda_node, ast.Lambda), \
        "Expected the root node of the de-compiled condition to be a Lambda, but got: {}".format(
            ast.dump(lambda_node))

    assert isinstance(lambda_node.body, ast.Return), \
        "Expected the body of the de-compiled condition to be a Return, but got: {}".format(
            ast.dump(lambda_node.body))

    body_txt = str(meta.dump_python_source(lambda_node.body.value)).strip()  # type: ignore

    # pylint: enable=no-member

    # Strip enclosing brackets from the body
    if body_txt.startswith("(") and body_txt.endswith(")"):
        body_txt = body_txt[1:-1]

    return body_txt
