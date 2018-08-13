"""Handle recomputation of values of a function given its abstract syntax tree and function frame."""

import ast
import functools
from typing import Any, Mapping, Dict, List, Optional  # pylint: disable=unused-import


class Visitor(ast.NodeVisitor):
    """Traverse the abstract syntax tree and recompute the values of each node defined by the function frame."""

    # pylint: disable=invalid-name
    # pylint: disable=missing-docstring
    # pylint: disable=too-many-public-methods

    def __init__(self, frame: Any, kwargs: Mapping[str, Any]) -> None:
        self.frame = frame
        self.kwargs = kwargs

        # value assigned to each visited node
        self.recomputed_values = dict()  # type: Dict[ast.AST, Any]

    def visit_Num(self, node: ast.Num) -> Any:
        result = node.n

        self.recomputed_values[node] = result
        return result

    def visit_Str(self, node: ast.Str) -> Any:
        result = node.s

        self.recomputed_values[node] = result
        return result

    def visit_Bytes(self, node: ast.Bytes) -> Any:
        result = node.s

        self.recomputed_values[node] = result
        return node.s

    def visit_List(self, node: ast.List) -> Any:
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a list")

        result = [self.visit(node=elt) for elt in node.elts]

        self.recomputed_values[node] = result
        return result

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        if isinstance(node.ctx, ast.Store):
            raise NotImplementedError("Can not compute the value of a Store on a tuple")

        result = tuple(self.visit(node=elt) for elt in node.elts)

        self.recomputed_values[node] = result
        return result

    def visit_Set(self, node: ast.Set) -> Any:
        result = set(self.visit(node=elt) for elt in node.elts)

        self.recomputed_values[node] = result
        return result

    def visit_Dict(self, node: ast.Dict) -> Any:
        recomputed_dict = dict()  # type: Dict[Any, Any]
        for key, val in zip(node.keys, node.values):
            recomputed_dict[self.visit(node=key)] = self.visit(node=val)

        self.recomputed_values[node] = recomputed_dict
        return recomputed_dict

    def visit_NameConstant(self, node: ast.NameConstant) -> Any:
        self.recomputed_values[node] = node.value
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError("Can only compute a value of Load on a name {}, but got context: {}".format(
                node.id, node.ctx))

        if node.id in self.kwargs:
            result = self.kwargs[node.id]
        elif node.id in self.frame.f_locals:
            result = self.frame.f_locals[node.id]
        elif node.id in self.frame.f_globals:
            result = self.frame.f_globals[node.id]
        elif node.id in self.frame.f_builtins:
            result = self.frame.f_builtins[node.id]
        else:
            raise ValueError("Name is neither in locals, globals or built-ins of the frame: {}".format(node.id))

        self.recomputed_values[node] = result
        return result

    def visit_Expr(self, node: ast.Expr) -> Any:
        result = self.visit(node=node.value)

        self.recomputed_values[node] = result
        return result

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
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

            kwargs[keyword.arg] = self.visit(node=keyword.value)

        result = func(*args, **kwargs)

        self.recomputed_values[node] = result
        return result

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        test = self.visit(node=node.test)
        if test:
            result = self.visit(node=node.body)
        else:
            result = self.visit(node=node.orelse)

        self.recomputed_values[node] = result
        return result

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        value = self.visit(node=node.value)
        if not isinstance(node.ctx, ast.Load):
            raise NotImplementedError(
                "Can only compute a value of Load on the attribute {}, but got context: {}".format(node.attr, node.ctx))

        result = getattr(value, node.attr)

        self.recomputed_values[node] = result
        return result

    def visit_Index(self, node: ast.Index) -> Any:
        result = self.visit(node=node.value)

        self.recomputed_values[node] = result
        return result

    def visit_Slice(self, node: ast.Slice) -> Any:
        lower = None  # type: Optional[int]
        if node.lower is not None:
            lower = self.visit(node=node.lower)

        upper = None  # type: Optional[int]
        if node.upper is not None:
            upper = self.visit(node=node.upper)

        step = None  # type: Optional[int]
        if node.step is not None:
            step = self.visit(node=node.step)

        result = slice(start=lower, stop=upper, step=step)

        self.recomputed_values[node] = result
        return result

    def visit_ExtSlice(self, node: ast.ExtSlice) -> Any:
        result = tuple(self.visit(node=dim) for dim in node.dims)

        self.recomputed_values[node] = result
        return result

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        value = self.visit(node=node.value)
        a_slice = self.visit(node=node.slice)

        result = value[a_slice]

        self.recomputed_values[node] = result
        return result

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        result = self.visit(node.body)

        self.recomputed_values[node] = result
        return result

    def generic_visit(self, node: ast.AST) -> None:
        raise NotImplementedError("Unhandled recomputation of the node: {} {}".format(type(node), node))
