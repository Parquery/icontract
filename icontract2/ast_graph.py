"""Generate and visualie the AST as a graph."""
import ast
import pathlib
import subprocess
import tempfile
from typing import List, BinaryIO, cast  # pylint: disable=unused-import

# We do not want to compute the coverage since visualizing AST graphs is used only for debugging.
# pragma: no cover


class Graph:
    """
    Generate DOT graph of an abstract syntax tree (AST).

    We use ``Graph`` to visualize ASTs during debugging.

    """

    def __init__(self) -> None:
        """Initialize."""
        self._nodes = []  # type: List[str]
        self._edges = []  # type: List[str]
        self._init = False

    def visit(self, root: ast.AST) -> None:
        """
        Walk recursively starting from the node and generate the tree.

        :param root: root of the AST
        :return:
        """
        # pylint: disable=too-many-nested-blocks
        self._init = True
        self._edges = []  # type: List[str]
        self._nodes = []  # type: List[str]

        stack = [root]
        while stack:
            node = stack.pop()

            label = ["<b>{}<br/>{:x}</b>".format(type(node).__name__, id(node))]

            for name, field in ast.iter_fields(node):
                if isinstance(field, ast.AST):
                    self._edges.append("node_{} -> node_{} [label={}];".format(id(node), id(field), name))
                    stack.append(field)
                elif isinstance(field, list):
                    if len(field) == 0:
                        label.append("{}: []".format(name))
                    else:
                        if isinstance(field[0], ast.AST):
                            for i, item in enumerate(field):
                                self._edges.append("node_{} -> node_{} [label=<{}[{}]>];".format(
                                    id(node), id(item), name, i))
                            stack.extend(field)

                        else:
                            label.append('{}: {}'.format(name, field))
                else:
                    label.append('{}: {}'.format(name, field))

            self._nodes.append("node_{} [label=<{}>];".format(id(node), "<br/>".join(label)))

    def dot(self) -> str:
        """
        Generate the dot file.

        :return: dot file as a string
        """
        return '\n'.join(['digraph G {'] + self._nodes + self._edges + ['}', ''])

    def show(self) -> None:
        """Call ``graphviz`` and ``display`` to visualize the graph."""
        with tempfile.NamedTemporaryFile() as tmp_in, tempfile.NamedTemporaryFile() as tmp_out:
            tmp_in.file.write(self.dot().encode())  # type: ignore
            tmp_in.file.flush()  # type: ignore
            subprocess.check_call(['dot', tmp_in.name, '-Tsvg', '-o', tmp_out.name])
            subprocess.check_call(['display', tmp_out.name])

    def save_as_svg(self, path: pathlib.Path) -> None:
        """
        Convert the graph from DOT to SVG with ``graphviz``.

        :param path: where the SVG should be stored
        :return:
        """
        with tempfile.NamedTemporaryFile() as tmp_in:
            tmp_in.file.write(self.dot().encode())  # type: ignore
            tmp_in.file.flush()  # type: ignore
            subprocess.check_call(['dot', tmp_in.name, '-Tsvg', '-o', path.as_posix()])
