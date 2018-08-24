"""Handle recomputation of values of a function given its abstract syntax tree and function frame."""

import ast
import builtins
import functools
from typing import Any, Mapping, Dict, List, Optional, Union, Tuple, Set, Callable  # pylint: disable=unused-import


class Visitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and recompute the values of each node defined by the function frame."""

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring
    # pylint: disable=too-many-public-methods

    def __init__(self, variable_lookup: List[Mapping[str, Any]]) -> None:
        """
        Initialize.

        :param variable_lookup: list of lookup tables to look-up the values of the variables, sorted by precedence
        """
        self._variable_lookup = variable_lookup

        # value assigned to each visited node
        self.recomputed_values = dict()  # type: Dict[ast.AST, Any]

    def visit_Num(self, node: ast.Num) -> Union[int, float]:
        """Recompute the value as the number at the node."""
        result = node.n

        self.recomputed_values[node] = result
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

    def visit_List(self, node: ast.List) -> List[Any]:
        """Visit the elements and assemble the results into a list."""
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a list")

        result = [self.visit(node=elt) for elt in node.elts]

        self.recomputed_values[node] = result
        return result

    def visit_Tuple(self, node: ast.Tuple) -> Tuple[Any, ...]:
        """Visit the elements and assemble the results into a tuple."""
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a tuple")

        result = tuple(self.visit(node=elt) for elt in node.elts)

        self.recomputed_values[node] = result
        return result

    def visit_Set(self, node: ast.Set) -> Set[Any]:
        """Visit the elements and assemble the results into a set."""
        result = set(self.visit(node=elt) for elt in node.elts)

        self.recomputed_values[node] = result
        return result

    def visit_Dict(self, node: ast.Dict) -> Dict[Any, Any]:
        """Visit keys and values and assemble a dictionary with the results."""
        recomputed_dict = dict()  # type: Dict[Any, Any]
        for key, val in zip(node.keys, node.values):
            recomputed_dict[self.visit(node=key)] = self.visit(node=val)

        self.recomputed_values[node] = recomputed_dict
        return recomputed_dict

    def visit_NameConstant(self, node: ast.NameConstant) -> Any:
        """Forward the node value as a result."""
        self.recomputed_values[node] = node.value
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        """Load the variable by looking it up in the variable look-up and in the built-ins."""
        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError("Can only compute a value of Load on a name {}, but got context: {}".format(
                node.id, node.ctx))

        result = None  # type: Optional[Any]
        for lookup in self._variable_lookup:
            if node.id in lookup:
                result = lookup[node.id]
                break

        if result is None and hasattr(builtins, node.id):
            result = getattr(builtins, node.id)

        if result is None and node.id != "None":
            raise ValueError("Name not found in the variable lookup: {}".format(node.id))

        self.recomputed_values[node] = result
        return result

    def visit_Expr(self, node: ast.Expr) -> Any:
        """Visit the node's ``value``."""
        result = self.visit(node=node.value)

        self.recomputed_values[node] = result
        return result

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        """Visit the node operand and apply the operation on the result."""
        if isinstance(node.op, ast.UAdd):
            result = +self.visit(node=node.operand)
        elif isinstance(node.op, ast.USub):
            result = -self.visit(node=node.operand)
        elif isinstance(node.op, ast.Not):
            result = not self.visit(node=node.operand)
        elif isinstance(node.op, ast.Invert):
            result = ~self.visit(node=node.operand)
        else:
            raise NotImplementedError("Unhandled op of {}: {}".format(node, node.op))

        self.recomputed_values[node] = result
        return result

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        """Recursively visit the left and right operand, respectively, and apply the operation on the results."""
        # pylint: disable=too-many-branches
        left = self.visit(node=node.left)
        right = self.visit(node=node.right)

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
        # pylint: disable=too-many-branches
        left = self.visit(node=node.left)

        comparators = [self.visit(node=comparator) for comparator in node.comparators]

        result = True
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

            if not comparison:
                result = False
                break

            left = comparator

        self.recomputed_values[node] = result
        return result

    def visit_Call(self, node: ast.Call) -> Any:
        """Visit the function and the arguments and finally make the function call with them."""
        func = self.visit(node=node.func)

        args = []  # type: List[Any]
        for arg_node in node.args:
            if isinstance(arg_node, ast.Starred):
                args.extend(self.visit(node=arg_node))
            else:
                args.append(self.visit(node=arg_node))

        kwargs = dict()  # type: Dict[str, Any]
        for keyword in node.keywords:
            if keyword.arg is None:
                kw = self.visit(node=keyword.value)
                for key, val in kw.items():
                    kwargs[key] = val

            else:
                kwargs[keyword.arg] = self.visit(node=keyword.value)

        result = func(*args, **kwargs)

        self.recomputed_values[node] = result
        return result

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        """Visit the ``test``, and depending on its outcome, the ``body`` or ``orelse``."""
        test = self.visit(node=node.test)

        if test:
            result = self.visit(node=node.body)
        else:
            result = self.visit(node=node.orelse)

        self.recomputed_values[node] = result
        return result

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        """Visit the node's ``value`` and get the attribute from the result."""
        value = self.visit(node=node.value)
        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError(
                "Can only compute a value of Load on the attribute {}, but got context: {}".format(node.attr, node.ctx))

        result = getattr(value, node.attr)

        self.recomputed_values[node] = result
        return result

    def visit_Index(self, node: ast.Index) -> Any:
        """Visit the node's ``value``."""
        result = self.visit(node=node.value)

        self.recomputed_values[node] = result
        return result

    def visit_Slice(self, node: ast.Slice) -> slice:
        """Visit ``lower``, ``upper`` and ``step`` and recompute the node as a ``slice``."""
        lower = None  # type: Optional[int]
        if node.lower is not None:
            lower = self.visit(node=node.lower)

        upper = None  # type: Optional[int]
        if node.upper is not None:
            upper = self.visit(node=node.upper)

        step = None  # type: Optional[int]
        if node.step is not None:
            step = self.visit(node=node.step)

        result = slice(lower, upper, step)

        self.recomputed_values[node] = result
        return result

    def visit_ExtSlice(self, node: ast.ExtSlice) -> Tuple[Any, ...]:
        """Visit each dimension of the advanced slicing and assemble the dimensions in a tuple."""
        result = tuple(self.visit(node=dim) for dim in node.dims)

        self.recomputed_values[node] = result
        return result

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        """Visit the ``slice`` and a ``value`` and get the element."""
        value = self.visit(node=node.value)
        a_slice = self.visit(node=node.slice)

        result = value[a_slice]

        self.recomputed_values[node] = result
        return result

    def visit_Lambda(self, node: ast.Lambda) -> Callable:
        """Visit the lambda's body."""
        result = self.visit(node.body)

        self.recomputed_values[node] = result
        return result

    def visit_Return(self, node: ast.Return) -> Any:  # pylint: disable=no-self-use
        """Raise an exception that this node is unexpected."""
        raise AssertionError("Unexpected return node during the re-computation: {}".format(ast.dump(node)))

    def generic_visit(self, node: ast.AST) -> None:
        """Raise an exception that this node has not been handled."""
        raise NotImplementedError("Unhandled recomputation of the node: {} {}".format(type(node), node))
