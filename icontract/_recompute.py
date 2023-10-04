"""Handle re-computation of values of a function given its abstract syntax tree and function frame."""

import ast
import builtins
import copy
import functools
import inspect
import sys
import uuid
from typing import (
    Any,
    Mapping,
    Dict,
    List,
    Optional,
    Union,
    Tuple,
    Set,
    Callable,
    cast,
    Iterable,
    TypeVar,
)  # pylint: disable=unused-import

from _ast import If


class Placeholder:
    """Represent a placeholder for variables local to the lambda such as targets in generator expressions."""

    def __repr__(self) -> str:
        """Represent the placeholder as <Placeholder>."""
        return "<Placeholder>"


PLACEHOLDER = Placeholder()


class FirstExceptionInAll:
    """Represent a first exception case for which an all quantifier does not apply."""

    def __init__(self, result: Any, inputs: Tuple[Tuple[str, Any]]) -> None:
        """
        Initialize with the given values.

        :param result: value of the evaluation which was not truthy
        :param inputs: all the target loop variables set during the iteration
        """
        self.result = result
        self.inputs = inputs

    def __bool__(self) -> Any:
        """Return the result of the ELT evaluation which invalidated the ``all`` quantifier."""
        return self.result


ContextT = TypeVar("ContextT", bound=ast.expr_context)


class _CollectStoredNamesVisitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and collect all the names which are stored."""

    def __init__(self) -> None:
        self.names = []  # type: List[str]
        self._name_set = set()  # type: Set[str]

    def visit_Name(self, node: ast.Name) -> Any:  # pylint: disable=invalid-name
        """Collect the name if it is in a store context."""
        if isinstance(node.ctx, ast.Store) and node.id not in self._name_set:
            self.names.append(node.id)
            self._name_set.add(node.id)


def _collect_stored_names(nodes: Iterable[ast.expr]) -> List[str]:
    visitor = _CollectStoredNamesVisitor()
    for node in nodes:
        visitor.visit(node)
    return visitor.names


class _CollectNameLoadsVisitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and collect all the name nodes in Load context."""

    def __init__(self) -> None:
        self.nodes = []  # type: List[ast.expr]

    def visit_Name(self, node: ast.Name) -> Any:  # pylint: disable=invalid-name
        """Collect the name if it is in a load context."""
        if isinstance(node.ctx, ast.Load):
            self.nodes.append(node)


def _collect_name_loads(nodes: Iterable[ast.expr]) -> List[ast.expr]:
    visitor = _CollectNameLoadsVisitor()
    for node in nodes:
        visitor.visit(node)
    return visitor.nodes


# noinspection PyTypeChecker
def _translate_all_expression_to_a_module(
    generator_exp: ast.GeneratorExp,
    generated_function_name: str,
    name_to_value: Mapping[str, Any],
) -> ast.Module:
    """
    Generate the AST of the module to trace an all quantifier on an generator expression.

    :param generator_exp: generator expression to be translated
    :param generated_function_name: UUID of the tracing function to be used in the code
    :param name_to_value:
        mapping of all resolved values to the variable names
        (passed as arguments to the function so that the generation can access them)
    :return: translation to a module
    """
    assert generated_function_name not in name_to_value
    assert not hasattr(builtins, generated_function_name)

    # Collect all the names involved in the generation
    relevant_names = _collect_stored_names(
        generator.target for generator in generator_exp.generators
    )

    assert generated_function_name not in relevant_names

    # Work backwards, from the most-inner block outwards

    result_id = "icontract_tracing_all_result_{}".format(uuid.uuid4().hex)
    result_assignment = ast.Assign(
        targets=[ast.Name(id=result_id, ctx=ast.Store())], value=generator_exp.elt
    )

    exceptional_return = ast.Return(
        ast.Tuple(
            elts=[
                ast.Name(id=result_id, ctx=ast.Load()),
                ast.Tuple(
                    elts=[
                        ast.Tuple(
                            elts=[
                                ast.Constant(value=relevant_name, kind=None),
                                ast.Name(id=relevant_name, ctx=ast.Load()),
                            ],
                            ctx=ast.Load(),
                        )
                        for relevant_name in relevant_names
                    ],
                    ctx=ast.Load(),
                ),
            ],
            ctx=ast.Load(),
        )
    )

    # While happy return shall not be executed, we add it here for robustness in case
    # future refactorings forget to check for that edge case.
    happy_return = ast.Return(
        ast.Tuple(
            elts=[
                ast.Name(id=result_id, ctx=ast.Load()),
                ast.Constant(value=None, kind=None),
            ],
            ctx=ast.Load(),
        )
    )

    critical_if: If = ast.If(
        test=ast.Name(id=result_id, ctx=ast.Load()),
        body=[ast.Pass()],
        orelse=[exceptional_return],
    )

    # Previous inner block to be added as body to the next outer block
    block = None  # type: Optional[List[ast.stmt]]
    for i, comprehension in enumerate(reversed(generator_exp.generators)):
        if i == 0:
            # This is the inner-most comprehension.
            block = [result_assignment, critical_if]
        assert block is not None

        for condition in reversed(comprehension.ifs):
            block = [ast.If(test=condition, body=block, orelse=[])]

        if not comprehension.is_async:
            block = [
                ast.For(
                    target=comprehension.target,
                    iter=comprehension.iter,
                    body=block,
                    orelse=[],
                )
            ]
        else:
            block = [
                ast.AsyncFor(
                    target=comprehension.target,
                    iter=comprehension.iter,
                    body=block,
                    orelse=[],
                )
            ]

    assert block is not None

    block.append(happy_return)

    # Now we are ready to generate the function.

    is_async = any(comprehension.is_async for comprehension in generator_exp.generators)

    args = [ast.arg(arg=name, annotation=None) for name in sorted(name_to_value.keys())]

    if sys.version_info < (3, 5):
        raise NotImplementedError(
            "Python versions below 3.5 not supported, got: {}".format(sys.version_info)
        )

    if not is_async:
        if sys.version_info < (3, 8):
            func_def_node = ast.FunctionDef(
                name=generated_function_name,
                args=ast.arguments(
                    args=args,
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                decorator_list=[],
                body=block,
            )  # type: Union[ast.FunctionDef, ast.AsyncFunctionDef]

            module_node = ast.Module(body=[func_def_node])
        else:
            func_def_node = ast.FunctionDef(
                name=generated_function_name,
                args=ast.arguments(
                    args=args,
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                decorator_list=[],
                body=block,
            )

            module_node = ast.Module(body=[func_def_node], type_ignores=[])
    else:
        if sys.version_info < (3, 8):
            async_func_def_node = ast.AsyncFunctionDef(
                name=generated_function_name,
                args=ast.arguments(
                    args=args,
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                decorator_list=[],
                body=block,
            )

            module_node = ast.Module(body=[async_func_def_node])
        else:
            async_func_def_node = ast.AsyncFunctionDef(
                name=generated_function_name,
                args=ast.arguments(
                    args=args,
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                decorator_list=[],
                body=block,
            )

            module_node = ast.Module(body=[async_func_def_node], type_ignores=[])

    ast.fix_missing_locations(module_node)

    return module_node


# noinspection PyTypeChecker
class Visitor(ast.NodeVisitor):
    """
    Traverse the abstract syntax tree and recompute the values of each node defined by the function frame.

    :ivar recomputed_values: mapping node -> value assigned to each visited node
    :type recomputed_values: Mapping[ast.AST, Any]
    """

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring

    def __init__(self, variable_lookup: List[Mapping[str, Any]]) -> None:
        """
        Initialize.

        :param variable_lookup: list of lookup tables to look-up the values of the variables, sorted by precedence
        """
        # _name_to_value maps the variable names to variable values.
        # This is important for Load contexts as well as Store contexts in, e.g., named expressions.
        self._name_to_value = dict()  # type: Dict[str, Any]

        # Resolve precedence of variable lookups
        for lookup in variable_lookup:
            for name, value in lookup.items():
                if name not in self._name_to_value:
                    self._name_to_value[name] = value

        # value assigned to each visited node
        self.recomputed_values = dict()  # type: Dict[ast.AST, Any]

    if sys.version_info < (3, 8):

        def visit_Num(self, node: ast.Num) -> Union[int, float]:
            """Recompute the value as the number at the node."""
            result = node.n

            self.recomputed_values[node] = result

            assert isinstance(result, (int, float))
            return result

        def visit_Str(self, node: ast.Str) -> str:
            """Recompute the value as the string at the node."""
            result = node.s

            self.recomputed_values[node] = result
            return result

        def visit_Bytes(self, node: ast.Bytes) -> bytes:
            """Recompute the value as the bytes at the node."""
            result = node.s

            self.recomputed_values[node] = result
            return node.s

        def visit_NameConstant(self, node: ast.NameConstant) -> Any:
            """Forward the node value as a result."""
            self.recomputed_values[node] = node.value
            return node.value

    else:

        def visit_Constant(self, node: ast.Constant) -> Any:
            """Forward the node value as a result."""
            self.recomputed_values[node] = node.value
            return node.value

    if sys.version_info >= (3, 6):

        def visit_FormattedValue(
            self, node: ast.FormattedValue
        ) -> Union[str, Placeholder]:
            """Format the node value."""
            recomputed_format_spec = None  # type: Optional[Union[str, Placeholder]]
            if node.format_spec is not None:
                # The following assert serves only documentation purposes so that the code is easier to follow.
                assert isinstance(node.format_spec, ast.JoinedStr)
                recomputed_format_spec = self.visit(node.format_spec)
                assert isinstance(recomputed_format_spec, (str, Placeholder))

            recomputed_value = self.visit(node.value)

            # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
            if recomputed_format_spec is PLACEHOLDER or recomputed_value is PLACEHOLDER:
                return PLACEHOLDER

            fmt = ["{"]
            # See https://docs.python.org/3/library/ast.html#ast.FormattedValue for these
            # constants
            if node.conversion == -1:
                pass
            elif node.conversion == 115:
                fmt.append("!s")
            elif node.conversion == 114:
                fmt.append("!r")
            elif node.conversion == 97:
                fmt.append("!a")
            else:
                raise NotImplementedError(
                    "Unhandled conversion of a formatted value node {!r}: {}".format(
                        node, node.conversion
                    )
                )

            if recomputed_format_spec is not None:
                fmt.append(f":{recomputed_format_spec}")

            fmt.append("}")

            return "".join(fmt).format(recomputed_value)

        def visit_JoinedStr(self, node: ast.JoinedStr) -> Union[str, Placeholder]:
            """Visit the values and concatenate them."""
            recomputed_values = [self.visit(value_node) for value_node in node.values]

            # See "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION" above.
            if PLACEHOLDER in recomputed_values:
                return PLACEHOLDER

            joined_str = "".join(recomputed_values)

            self.recomputed_values[node] = joined_str
            return joined_str

    def visit_List(self, node: ast.List) -> Union[List[Any], Placeholder]:
        """Visit the elements and assemble the results into a list."""
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a list")

        recomputed_elts = [self.visit(node=elt) for elt in node.elts]

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if any(recomputed_elt is PLACEHOLDER for recomputed_elt in recomputed_elts):
            return PLACEHOLDER

        self.recomputed_values[node] = recomputed_elts
        return recomputed_elts

    def visit_Tuple(self, node: ast.Tuple) -> Union[Tuple[Any, ...], Placeholder]:
        """Visit the elements and assemble the results into a tuple."""
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a tuple")

        recomputed_elts = tuple(self.visit(node=elt) for elt in node.elts)
        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if any(recomputed_elt is PLACEHOLDER for recomputed_elt in recomputed_elts):
            return PLACEHOLDER

        self.recomputed_values[node] = recomputed_elts
        return recomputed_elts

    def visit_Set(self, node: ast.Set) -> Union[Set[Any], Placeholder]:
        """Visit the elements and assemble the results into a set."""
        recomputed_elts = set(self.visit(node=elt) for elt in node.elts)
        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if any(recomputed_elt is PLACEHOLDER for recomputed_elt in recomputed_elts):
            return PLACEHOLDER

        self.recomputed_values[node] = recomputed_elts
        return recomputed_elts

    def visit_Dict(self, node: ast.Dict) -> Union[Dict[Any, Any], Placeholder]:
        """Visit keys and values and assemble a dictionary with the results."""
        recomputed_dict = dict()  # type: Dict[Any, Any]
        for key, val in zip(node.keys, node.values):
            assert isinstance(key, ast.AST)
            assert isinstance(val, ast.AST)

            recomputed_dict[self.visit(node=key)] = self.visit(node=val)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if any(
            key is PLACEHOLDER or value is PLACEHOLDER
            for key, value in recomputed_dict.items()
        ):
            return PLACEHOLDER

        self.recomputed_values[node] = recomputed_dict
        return recomputed_dict

    def visit_Name(self, node: ast.Name) -> Any:
        """Load the variable by looking it up in the variable look-up and in the built-ins."""
        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError(
                "Can only compute a value of Load on a name {}, but got context: {}".format(
                    node.id, node.ctx
                )
            )

        result = None  # type: Optional[Any]

        if node.id in self._name_to_value:
            result = self._name_to_value[node.id]

        if result is None and hasattr(builtins, node.id):
            result = getattr(builtins, node.id)

        if result is None and node.id != "None":
            # The variable refers to a name local of the lambda (e.g., a target in the generator expression).
            # Since we evaluate generator expressions with runtime compilation, None is returned here as a placeholder.
            return PLACEHOLDER

        self.recomputed_values[node] = result
        return result

    def visit_Expr(self, node: ast.Expr) -> Any:
        """Visit the node's ``value``."""
        recomputed_value = self.visit(node=node.value)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if recomputed_value is PLACEHOLDER:
            return PLACEHOLDER

        self.recomputed_values[node] = recomputed_value
        return recomputed_value

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        """Visit the node operand and apply the operation on the result."""
        recomputed_operand = self.visit(node=node.operand)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if recomputed_operand is PLACEHOLDER:
            return PLACEHOLDER

        if isinstance(node.op, ast.UAdd):
            result = +recomputed_operand
        elif isinstance(node.op, ast.USub):
            result = -recomputed_operand
        elif isinstance(node.op, ast.Not):
            result = not recomputed_operand
        elif isinstance(node.op, ast.Invert):
            result = ~recomputed_operand
        else:
            raise NotImplementedError("Unhandled op of {}: {}".format(node, node.op))

        self.recomputed_values[node] = result
        return result

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        """Recursively visit the left and right operand, respectively, and apply the operation on the results."""
        left = self.visit(node=node.left)
        right = self.visit(node=node.right)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if left is PLACEHOLDER or right is PLACEHOLDER:
            return PLACEHOLDER

        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            result = left // right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            result = left**right
        elif isinstance(node.op, ast.LShift):
            result = left << right
        elif isinstance(node.op, ast.RShift):
            result = left >> right
        elif isinstance(node.op, ast.BitOr):
            result = left | right
        elif isinstance(node.op, ast.BitXor):
            result = left ^ right
        elif isinstance(node.op, ast.BitAnd):
            result = left & right
        elif isinstance(node.op, ast.MatMult):
            result = left @ right
        else:
            raise NotImplementedError("Unhandled op of {}: {}".format(node, node.op))

        self.recomputed_values[node] = result
        return result

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        """Recursively visit the operands and apply the operation on them."""
        values = [self.visit(value_node) for value_node in node.values]

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if any(value is PLACEHOLDER for value in values):
            return PLACEHOLDER

        if isinstance(node.op, ast.And):
            result = functools.reduce(lambda left, right: left and right, values, True)
        elif isinstance(node.op, ast.Or):
            result = functools.reduce(lambda left, right: left or right, values, True)
        else:
            raise NotImplementedError("Unhandled op of {}: {}".format(node, node.op))

        self.recomputed_values[node] = result
        return result

    def visit_Compare(self, node: ast.Compare) -> Any:
        """Recursively visit the comparators and apply the operations on them."""
        left = self.visit(node=node.left)

        comparators = [self.visit(node=comparator) for comparator in node.comparators]

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if left is PLACEHOLDER or any(
            comparator is PLACEHOLDER for comparator in comparators
        ):
            return PLACEHOLDER

        result = None  # type: Optional[Any]
        for comparator, op in zip(comparators, node.ops):
            if isinstance(op, ast.Eq):
                comparison = left == comparator
            elif isinstance(op, ast.NotEq):
                comparison = left != comparator
            elif isinstance(op, ast.Lt):
                comparison = left < comparator
            elif isinstance(op, ast.LtE):
                comparison = left <= comparator
            elif isinstance(op, ast.Gt):
                comparison = left > comparator
            elif isinstance(op, ast.GtE):
                comparison = left >= comparator
            elif isinstance(op, ast.Is):
                comparison = left is comparator
            elif isinstance(op, ast.IsNot):
                comparison = left is not comparator
            elif isinstance(op, ast.In):
                comparison = left in comparator
            elif isinstance(op, ast.NotIn):
                comparison = left not in comparator
            else:
                raise NotImplementedError("Unhandled op of {}: {}".format(node, op))

            if result is None:
                result = comparison
            else:
                result = result and comparison

            left = comparator

        self.recomputed_values[node] = result
        return result

    def visit_Call(self, node: ast.Call) -> Any:
        """Visit the function and the arguments and finally make the function call with them."""
        func = self.visit(node=node.func)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if func is PLACEHOLDER:
            return PLACEHOLDER

        if not callable(func):
            raise ValueError(
                "Unexpected call to a non-calllable during the re-computation: {}".format(
                    func
                )
            )

        if inspect.iscoroutinefunction(func):
            raise ValueError(
                (
                    "Unexpected coroutine function {} as a condition of a contract. "
                    "You must specify your own error if the condition of your contract is a coroutine function."
                ).format(func)
            )

        # Short-circuit tracing the all quantifier over a generator expression
        # fmt: off
        if (
                func == builtins.all  # pylint: disable=comparison-with-callable
                and len(node.args) == 1
                and isinstance(node.args[0], ast.GeneratorExp)
        ):
            # fmt: on
            result = self._trace_all_with_generator(func=func, node=node)

            if result is PLACEHOLDER:
                return PLACEHOLDER
        else:
            args = []  # type: List[Any]
            for arg_node in node.args:
                if isinstance(arg_node, ast.Starred):
                    args.extend(self.visit(node=arg_node))
                else:
                    args.append(self.visit(node=arg_node))

            kwargs = dict()  # type: Dict[Union[str, Placeholder], Any]
            for keyword in node.keywords:
                if keyword.arg is None:
                    kw = self.visit(node=keyword.value)
                    for key, val in kw.items():
                        kwargs[key] = val

                else:
                    kwargs[keyword.arg] = self.visit(node=keyword.value)

            # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
            if (any(arg is PLACEHOLDER for arg in args)
                    or any(key is PLACEHOLDER or value is PLACEHOLDER for key, value in kwargs.items())):
                return PLACEHOLDER

            result = func(*args, **kwargs)

        assert result is not PLACEHOLDER

        self.recomputed_values[node] = result
        if inspect.iscoroutine(result):
            raise ValueError(
                ("Unexpected coroutine {} as a result from a call. "
                 "You must specify your own error if the condition of your contract gives a coroutine.").format(result))

        assert node in self.recomputed_values
        return result

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        """Visit the ``test``, and depending on its outcome, the ``body`` or ``orelse``."""
        test = self.visit(node=node.test)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if test is PLACEHOLDER:
            return PLACEHOLDER

        if test:
            result = self.visit(node=node.body)
        else:
            result = self.visit(node=node.orelse)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if result is PLACEHOLDER:
            return PLACEHOLDER

        self.recomputed_values[node] = result
        return result

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Visit the node's ``value`` and get the attribute from the result."""
        value = self.visit(node=node.value)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if value is PLACEHOLDER:
            return PLACEHOLDER

        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError(
                "Can only compute a value of Load on the attribute {}, but got context: {}".format(
                    node.attr, node.ctx
                )
            )

        result = getattr(value, node.attr)

        self.recomputed_values[node] = result
        return result

    if sys.version_info >= (3, 8):

        def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
            """Visit the node's ``value`` and assign it to both this node and the target."""
            value = self.visit(node=node.value)

            # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
            if value is PLACEHOLDER:
                return PLACEHOLDER

            self.recomputed_values[node] = value

            target = node.target

            if not isinstance(target.ctx, ast.Store):
                raise NotImplementedError(
                    "Expected Store context in the target of a named expression, but got: {}".format(
                        target.ctx
                    )
                )

            self._name_to_value[target.id] = value

            return value

    if sys.version_info < (3, 9):

        def visit_Index(self, node: ast.Index) -> Any:
            """Visit the node's ``value``."""
            result = self.visit(node=node.value)

            # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
            if result is PLACEHOLDER:
                return PLACEHOLDER

            self.recomputed_values[node] = result
            return result

    def visit_Slice(self, node: ast.Slice) -> Union[slice, Placeholder]:
        """Visit ``lower``, ``upper`` and ``step`` and recompute the node as a ``slice``."""
        lower = None  # type: Optional[Union[int, Placeholder]]
        if node.lower is not None:
            lower = self.visit(node=node.lower)

        upper = None  # type: Optional[Union[int, Placeholder]]
        if node.upper is not None:
            upper = self.visit(node=node.upper)

        step = None  # type: Optional[Union[int, Placeholder]]
        if node.step is not None:
            step = self.visit(node=node.step)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if lower is PLACEHOLDER or upper is PLACEHOLDER or step is PLACEHOLDER:
            return PLACEHOLDER

        result = slice(lower, upper, step)

        self.recomputed_values[node] = result
        return result

    if sys.version_info < (3, 9):

        def visit_ExtSlice(
            self, node: ast.ExtSlice
        ) -> Union[Tuple[Any, ...], Placeholder]:
            """Visit each dimension of the advanced slicing and assemble the dimensions in a tuple."""
            result = tuple(self.visit(node=dim) for dim in node.dims)

            if any(value is PLACEHOLDER for value in result):
                return PLACEHOLDER

            self.recomputed_values[node] = result
            return result

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        """Visit the ``slice`` and a ``value`` and get the element."""
        value = self.visit(node=node.value)
        a_slice = self.visit(node=node.slice)

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        if value is PLACEHOLDER or a_slice is PLACEHOLDER:
            return PLACEHOLDER

        result = value[a_slice]
        self.recomputed_values[node] = result
        return result

    def _trace_all_with_generator(
        self, func: Callable[..., Any], node: ast.Call
    ) -> Any:
        """Re-write the all call with for loops to trace the first offending item, if any."""
        assert func == builtins.all  # pylint: disable=comparison-with-callable
        assert len(node.args) == 1
        assert isinstance(node.args[0], ast.GeneratorExp)

        # Try the happy path first

        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION"
        recomputed_arg = self.visit(node=node.args[0])
        if recomputed_arg is PLACEHOLDER:
            return PLACEHOLDER

        result = func(*(self.visit(node=node.args[0]),))
        if result:
            return result

        # The all quantifier has not been satisfied. We need to re-trace it.
        # To that end, we translate the generator expression to a tracing function and
        # execute it.

        generator_exp = node.args[0]
        assert isinstance(generator_exp, ast.GeneratorExp)

        generated_function_name = "icontract_tracing_all_with_generator_expr_{}".format(
            uuid.uuid4().hex
        )

        module_node = _translate_all_expression_to_a_module(
            generator_exp=generator_exp,
            generated_function_name=generated_function_name,
            name_to_value=self._name_to_value,
        )

        # In case you want to debug the generated function at this point,
        # you probably want to use ``astor`` module to generate the source code
        # based on the ``module_node``.

        code = compile(source=module_node, filename="<ast>", mode="exec")

        module_locals = {}  # type: Dict[str, Any]
        module_globals = {}  # type: Dict[str, Any]
        exec(code, module_globals, module_locals)  # pylint: disable=exec-used

        generated_func = module_locals[generated_function_name]

        result, inputs = generated_func(**self._name_to_value)

        assert not bool(result), "Expected the unhappy path here"
        assert isinstance(inputs, tuple)
        assert all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in inputs
        )

        return FirstExceptionInAll(
            result=result, inputs=cast(Tuple[Tuple[str, Any]], inputs)
        )

    def _execute_comprehension(
        self, node: Union[ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp]
    ) -> Any:
        """Compile the generator or comprehension from the node and execute the compiled code."""
        # Please see "NOTE ABOUT NAME 🠒 VALUE STACKING".
        if any(value is PLACEHOLDER for value in self._name_to_value.values()):
            return PLACEHOLDER

        args = [
            ast.arg(arg=name, annotation=None)
            for name in sorted(self._name_to_value.keys())
        ]

        if sys.version_info < (3,):
            raise NotImplementedError(
                "Python versions below 3 not supported, got: {}".format(
                    sys.version_info
                )
            )

        if sys.version_info < (3, 8):
            func_def_node = ast.FunctionDef(
                name="generator_expr",
                args=ast.arguments(
                    args=args, kwonlyargs=[], kw_defaults=[], defaults=[]
                ),
                decorator_list=[],
                body=[ast.Return(node)],
            )

            module_node = ast.Module(body=[func_def_node])
        else:
            func_def_node = ast.FunctionDef(
                name="generator_expr",
                args=ast.arguments(
                    args=args,
                    posonlyargs=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                decorator_list=[],
                body=[ast.Return(node)],
            )

            module_node = ast.Module(body=[func_def_node], type_ignores=[])

        ast.fix_missing_locations(module_node)

        code = compile(source=module_node, filename="<ast>", mode="exec")

        module_locals = {}  # type: Dict[str, Any]
        module_globals = {}  # type: Dict[str, Any]
        exec(code, module_globals, module_locals)  # pylint: disable=exec-used

        generator_expr_func = module_locals["generator_expr"]

        return generator_expr_func(**self._name_to_value)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        """Compile the generator expression as a function and call it."""
        # NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION:
        # Re-computing the comprehensions would be too slow. Therefore we re-compile the comprehension and call
        # the compiled code directly.
        #
        # However, we still want to report the values of the variables unrelated to the comprehension back
        # to the user. Therefore we introduce PLACEHOLDER's and propagate them through re-computation in all
        # the visit methods.

        # The following visits propagate the visitation to descendant nodes.
        # However, as we re-compute the comprehension *via* re-compilation & execution,
        # the results of the visits are all PLACEHOLDER's.

        # NOTE ABOUT NAME 🠒 VALUE STACKING:
        # We need to make a copy of name 🠒 value mapping since we need to add targets as placeholders
        # while we visit the comprehension. For example, as we compute comprehensions through re-compilation
        # and not through manual re-computation, we can not re-compute nested comprehensions.
        #
        # However, when our visit of comprehension is finished, the targets are not valid any more,
        # so we need to remove them from the mapping.
        #
        # Finally, we compute the comprehension with the original name 🠒 value mapping by using
        # re-compilation. This final step is skipped if any of the names involved in the comprehension are
        # PLACEHOLDER's.

        old_name_to_value = copy.copy(self._name_to_value)
        for target_name in _collect_stored_names(
            [generator.target for generator in node.generators]
        ):
            self._name_to_value[target_name] = PLACEHOLDER

        self.visit(node.elt)

        for generator in node.generators:
            self.visit(generator.iter)

            for generator_if in generator.ifs:
                self.visit(generator_if)

        self._name_to_value = old_name_to_value

        result = self._execute_comprehension(node=node)

        # Do not set the computed value of the node since its representation would be non-informative.
        return result

    def visit_ListComp(self, node: ast.ListComp) -> Any:
        """Compile the list comprehension as a function and call it."""
        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION".
        # The note also explains why we do not use the result of the following visits.

        # Please see "NOTE ABOUT NAME 🠒 VALUE STACKING".
        old_name_to_value = copy.copy(self._name_to_value)
        for target_name in _collect_stored_names(
            [generator.target for generator in node.generators]
        ):
            self._name_to_value[target_name] = PLACEHOLDER

        self.visit(node.elt)

        for generator in node.generators:
            self.visit(generator.iter)

            for generator_if in generator.ifs:
                self.visit(generator_if)

        self._name_to_value = old_name_to_value

        result = self._execute_comprehension(node=node)

        if result is not PLACEHOLDER:
            self.recomputed_values[node] = result

        return result

    def visit_SetComp(self, node: ast.SetComp) -> Any:
        """Compile the set comprehension as a function and call it."""
        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION".
        # The note also explains why we do not use the result of the following visits.

        # Please see "NOTE ABOUT NAME 🠒 VALUE STACKING".
        old_name_to_value = copy.copy(self._name_to_value)
        for target_name in _collect_stored_names(
            [generator.target for generator in node.generators]
        ):
            self._name_to_value[target_name] = PLACEHOLDER

        self.visit(node.elt)

        for generator in node.generators:
            self.visit(generator.iter)

            for generator_if in generator.ifs:
                self.visit(generator_if)

        self._name_to_value = old_name_to_value

        result = self._execute_comprehension(node=node)

        if result is not PLACEHOLDER:
            self.recomputed_values[node] = result

        return result

    def visit_DictComp(self, node: ast.DictComp) -> Any:
        """Compile the dictionary comprehension as a function and call it."""
        # Please see "NOTE ABOUT PLACEHOLDERS AND RE-COMPUTATION".
        # The note also explains why we do not use the result of the following visits.

        # Please see "NOTE ABOUT NAME 🠒 VALUE STACKING".
        old_name_to_value = copy.copy(self._name_to_value)
        for target_name in _collect_stored_names(
            [generator.target for generator in node.generators]
        ):
            self._name_to_value[target_name] = PLACEHOLDER

        self.visit(node.key)
        self.visit(node.value)

        for generator in node.generators:
            self.visit(generator.iter)

            for generator_if in generator.ifs:
                self.visit(generator_if)

        self._name_to_value = old_name_to_value

        result = self._execute_comprehension(node=node)

        if result is not PLACEHOLDER:
            self.recomputed_values[node] = result

        return result

    def visit_Lambda(self, node: ast.Lambda) -> Callable[..., Any]:
        """Do not support inline lambda until there is a feature request since this is quite tricky to implement."""
        raise NotImplementedError(
            "Re-computation of in-line lambda functions is not supported since it is quite tricky to implement and "
            "we decided to implement it only once there is a real need for it. "
            "Please make a feature request on https://github.com/Parquery/icontract"
        )

    def visit_Return(self, node: ast.Return) -> Any:
        """Raise an exception that this node is unexpected."""
        raise AssertionError(
            "Unexpected return node during the re-computation: {}".format(
                ast.dump(node)
            )
        )

    def generic_visit(self, node: ast.AST) -> None:
        """Raise an exception that this node has not been handled."""
        raise NotImplementedError(
            "Unhandled re-computation of the node: {} {}".format(type(node), node)
        )
