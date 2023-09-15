#!/usr/bin/env python3
# pylint: disable=missing-docstring,invalid-name
# pylint: disable=unused-argument
import ast
import re
import textwrap
import unittest

import astor

# noinspection PyProtectedMember
import icontract._recompute


class TestTranslationForTracingAll(unittest.TestCase):
    @staticmethod
    def translate_all_expression(input_source_code: str) -> str:
        """
        Parse the input source code and translate it to a module with a tracing function.

        :param input_source_code: source code containing a single ``all`` expression
        :return:
            source code of the module with a tracing function.
            All non-deterministic bits are erased from it.
        """
        node = ast.parse(input_source_code)
        assert isinstance(node, ast.Module)
        expr_node = node.body[0]
        assert isinstance(expr_node, ast.Expr)
        call_node = expr_node.value
        assert isinstance(call_node, ast.Call)
        generator_exp = call_node.args[0]
        assert isinstance(generator_exp, ast.GeneratorExp)

        # We set only SOME_GLOBAL_CONSTANT in ``name_to_value``. In ``_recompute`` module
        # all the contract arguments will be set including also all the built-ins and other
        # global variables.

        module_node = icontract._recompute._translate_all_expression_to_a_module(
            generator_exp=generator_exp,
            generated_function_name="some_func",
            name_to_value={"SOME_GLOBAL_CONSTANT": 10},
        )

        got = astor.to_source(module_node)

        # We need to replace the UUID of the result variable for reproducibility.
        got = re.sub(
            r"icontract_tracing_all_result_[a-zA-Z0-9]+",
            "icontract_tracing_all_result",
            got,
        )

        assert isinstance(got, str)
        return got

    def test_global_variable(self) -> None:
        input_source_code = textwrap.dedent(
            """\
            all(
                x > SOME_GLOBAL_CONSTANT
                for x in lst
            )
            """
        )

        got_source_code = TestTranslationForTracingAll.translate_all_expression(
            input_source_code=input_source_code
        )

        # Please see ``TestTranslationForTracingAll.translate_all_expression`` and the note about ``name_to_value``
        # if you wonder why ``lst`` is not in the arguments.
        self.assertEqual(
            textwrap.dedent(
                """\
                def some_func(SOME_GLOBAL_CONSTANT):
                    for x in lst:
                        icontract_tracing_all_result = (x >
                            SOME_GLOBAL_CONSTANT)
                        if icontract_tracing_all_result:
                            pass
                        else:
                            return (
                                icontract_tracing_all_result,
                                (('x', x),))
                    return icontract_tracing_all_result, None
                """
            ),
            got_source_code,
        )

    def test_translation_two_fors_and_two_ifs(self) -> None:
        input_source_code = textwrap.dedent(
            """\
            all(
                cell > SOME_GLOBAL_CONSTANT
                for i, row in enumerate(matrix)
                if i > 0
                for j, cell in enumerate(row)
                if i == j
            )
            """
        )

        got_source_code = TestTranslationForTracingAll.translate_all_expression(
            input_source_code=input_source_code
        )

        # Please see ``TestTranslationForTracingAll.translate_all_expression`` and the note about ``name_to_value``
        # if you wonder why ``matrix`` is not in the arguments.
        self.assertEqual(
            textwrap.dedent(
                """\
                def some_func(SOME_GLOBAL_CONSTANT):
                    for i, row in enumerate(matrix):
                        if i > 0:
                            for j, cell in enumerate(row):
                                if i == j:
                                    (icontract_tracing_all_result
                                        ) = cell > SOME_GLOBAL_CONSTANT
                                    if (icontract_tracing_all_result
                                        ):
                                        pass
                                    else:
                                        return (
                                            icontract_tracing_all_result
                                            , (('i', i), ('row', row), ('j', j), ('cell',
                                            cell)))
                    return icontract_tracing_all_result, None
                """
            ),
            got_source_code,
        )

    def test_nested_all(self) -> None:
        # Nesting is not recursively followed by design. Only the outer-most all expression should be traced.

        input_source_code = textwrap.dedent(
            """\
            all(
                all(cell > SOME_GLOBAL_CONSTANT for cell in row)
                for row in matrix
            )
            """
        )

        got_source_code = TestTranslationForTracingAll.translate_all_expression(
            input_source_code=input_source_code
        )

        # Please see ``TestTranslationForTracingAll.translate_all_expression`` and the note about ``name_to_value``
        # if you wonder why ``matrix`` is not in the arguments.
        self.assertEqual(
            textwrap.dedent(
                """\
                def some_func(SOME_GLOBAL_CONSTANT):
                    for row in matrix:
                        icontract_tracing_all_result = all(
                            cell > SOME_GLOBAL_CONSTANT for cell in row)
                        if icontract_tracing_all_result:
                            pass
                        else:
                            return (
                                icontract_tracing_all_result,
                                (('row', row),))
                    return icontract_tracing_all_result, None
                """
            ),
            got_source_code,
        )


if __name__ == "__main__":
    unittest.main()
