"""Handle representations necessary for informative error messages."""
import ast
import inspect
from typing import Any, Mapping, MutableMapping, Callable, List  # pylint: disable=unused-import

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
        inspect.ismodule(value)


class Visitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and collect the representations of the selected nodes."""

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring

    def __init__(self, recomputed_values: Mapping[ast.AST, Any], frame: Any) -> None:
        self.recomputed_values = recomputed_values
        self.reprs = dict()  # type: MutableMapping[str, str]
        self.frame = frame

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.frame.f_builtins:
            value = self.recomputed_values[node]

            if _representable(value=value):
                text = str(meta.dump_python_source(node)).strip()  # type: ignore
                self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        value = self.recomputed_values[node]

        if _representable(value=value):
            text = str(meta.dump_python_source(node)).strip()  # type: ignore
            self.reprs[text] = value

        self.generic_visit(node=node)

    def visit_Call(self, node: ast.Call) -> None:
        value = self.recomputed_values[node]

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


def repr_values(condition: Callable[..., bool], condition_kwargs: Mapping[str, Any]) -> List[str]:
    """
    Represent function arguments and frame values in the error message on contract breach.

    :param condition: contract condition function
    :param condition_kwargs: condition arguments
    :return: list of value representations
    """
    reprs = dict()  # type: MutableMapping[str, Any]

    if _is_lambda(condition=condition):
        # First f_back refers to def wrapped(), the second f_back refers to the actual condition function
        condition_frame = inspect.currentframe().f_back.f_back

        condition_node = meta.decompiler.decompile_func(condition)

        recompute_visitor = icontract.recompute.Visitor(frame=condition_frame, kwargs=condition_kwargs)
        recompute_visitor.visit(node=condition_node)
        recomputed_values = recompute_visitor.recomputed_values

        repr_visitor = Visitor(recomputed_values=recomputed_values, frame=condition_frame)
        repr_visitor.visit(node=condition_node)

        reprs = repr_visitor.reprs
    else:
        for key, val in condition_kwargs.items():
            if _representable(value=val):
                reprs[key] = val

    parts = []  # type: List[str]
    for key in sorted(reprs.keys()):
        parts.append('{} was {!r}'.format(key, reprs[key]))

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

    lambda_node = meta.decompiler.decompile_func(condition)
    assert isinstance(lambda_node, ast.Lambda)

    # pylint: disable=no-member
    body_txt = str(meta.dump_python_source(lambda_node.body)).strip()  # type: ignore

    # Strip enclosing brackets from the body
    if body_txt.startswith("(") and body_txt.endswith(")"):
        body_txt = body_txt[1:-1]

    return body_txt
