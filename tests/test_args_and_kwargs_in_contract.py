# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda
# pylint: disable=unused-variable

import copy
import textwrap
import unittest
from typing import Optional, Any, Tuple, Dict

import icontract
import tests.error


class TestArgs(unittest.TestCase):
    def test_args_without_variable_positional_arguments(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]

        def set_args(args: Tuple[Any, ...]) -> bool:
            nonlocal recorded_args
            recorded_args = copy.copy(args)
            return True

        @icontract.require(lambda _ARGS: set_args(_ARGS))
        def some_func(x: int) -> None:
            pass

        some_func(3)

        assert recorded_args is not None
        self.assertTupleEqual((3,), recorded_args)

    def test_args_with_named_and_variable_positional_arguments(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]

        def set_args(args: Tuple[Any, ...]) -> bool:
            nonlocal recorded_args
            recorded_args = copy.copy(args)
            return True

        @icontract.require(lambda _ARGS: set_args(_ARGS))
        def some_func(x: int, *args: Any) -> None:
            pass

        some_func(3, 2)

        assert recorded_args is not None
        self.assertTupleEqual((3, 2), recorded_args)

    def test_args_with_only_variable_positional_arguments(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]

        def set_args(args: Tuple[Any, ...]) -> bool:
            nonlocal recorded_args
            recorded_args = copy.copy(args)
            return True

        @icontract.require(lambda _ARGS: set_args(_ARGS))
        def some_func(*args: Any) -> None:
            pass

        some_func(3, 2, 1)

        assert recorded_args is not None
        self.assertTupleEqual((3, 2, 1), recorded_args)

    def test_args_with_uncommon_variable_positional_arguments(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]

        def set_args(args: Tuple[Any, ...]) -> bool:
            nonlocal recorded_args
            recorded_args = copy.copy(args)
            return True

        @icontract.require(lambda _ARGS: set_args(_ARGS))
        def some_func(*arguments: Any) -> None:
            pass

        some_func(3, 2, 1, 0)

        assert recorded_args is not None
        self.assertTupleEqual((3, 2, 1, 0), recorded_args)

    def test_fail(self) -> None:
        @icontract.require(lambda _ARGS: len(_ARGS) > 2)
        def some_func(*args: Any) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(3)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None
        self.assertEqual(
            textwrap.dedent(
                """\
                len(_ARGS) > 2:
                _ARGS was (3,)
                args was 3
                len(_ARGS) was 1"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestKwargs(unittest.TestCase):
    def test_kwargs_without_variable_keyword_arguments(self) -> None:
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_kwargs(kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_kwargs
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _KWARGS: set_kwargs(_KWARGS))
        def some_func(x: int) -> None:
            pass

        some_func(x=3)

        assert recorded_kwargs is not None
        self.assertDictEqual({"x": 3}, recorded_kwargs)

    def test_kwargs_with_named_and_variable_keyword_arguments(self) -> None:
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_kwargs(kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_kwargs
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _KWARGS: set_kwargs(_KWARGS))
        def some_func(x: int, **kwargs: Any) -> None:
            pass

        some_func(x=3, y=2)

        assert recorded_kwargs is not None
        self.assertDictEqual({"x": 3, "y": 2}, recorded_kwargs)

    def test_kwargs_with_only_variable_keyword_arguments(self) -> None:
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_kwargs(kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_kwargs
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _KWARGS: set_kwargs(_KWARGS))
        def some_func(**kwargs: Any) -> None:
            pass

        some_func(x=3, y=2, z=1)

        assert recorded_kwargs is not None
        self.assertDictEqual({"x": 3, "y": 2, "z": 1}, recorded_kwargs)

    def test_kwargs_with_uncommon_argument_name_for_variable_keyword_arguments(
        self,
    ) -> None:
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_kwargs(kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_kwargs
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _KWARGS: set_kwargs(_KWARGS))
        def some_func(**parameters: Any) -> None:
            pass

        some_func(x=3, y=2, z=1, a=0)

        assert recorded_kwargs is not None
        self.assertDictEqual({"x": 3, "y": 2, "z": 1, "a": 0}, recorded_kwargs)

    def test_fail(self) -> None:
        @icontract.require(lambda _KWARGS: "x" in _KWARGS)
        def some_func(**kwargs: Any) -> None:
            pass

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            some_func(y=3)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None
        self.assertEqual(
            textwrap.dedent(
                """\
                "x" in _KWARGS:
                _KWARGS was {'y': 3}
                y was 3"""
            ),
            tests.error.wo_mandatory_location(str(violation_error)),
        )


class TestArgsAndKwargs(unittest.TestCase):
    def test_that_args_and_kwargs_are_both_passed_as_placeholders(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_args_and_kwargs(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_args
            nonlocal recorded_kwargs
            recorded_args = copy.copy(args)
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _ARGS, _KWARGS: set_args_and_kwargs(_ARGS, _KWARGS))
        def some_func(*args: Any, **kwargs: Any) -> None:
            pass

        some_func(5, x=10, y=20, z=30)

        assert recorded_args is not None
        self.assertTupleEqual((5,), recorded_args)

        assert recorded_kwargs is not None
        self.assertDictEqual({"x": 10, "y": 20, "z": 30}, recorded_kwargs)

    def test_a_very_mixed_case(self) -> None:
        recorded_args = None  # type: Optional[Tuple[Any, ...]]
        recorded_kwargs = None  # type: Optional[Dict[str, Any]]

        def set_args_and_kwargs(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> bool:
            nonlocal recorded_args
            nonlocal recorded_kwargs
            recorded_args = copy.copy(args)
            recorded_kwargs = copy.copy(kwargs)
            return True

        @icontract.require(lambda _ARGS, _KWARGS: set_args_and_kwargs(_ARGS, _KWARGS))
        def some_func(x: int, y: int, *args: Any, **kwargs: Any) -> None:
            pass

        some_func(5, 10, 20, z=30)

        assert recorded_args is not None
        self.assertTupleEqual((5, 10, 20), recorded_args)

        assert recorded_kwargs is not None
        self.assertDictEqual({"z": 30}, recorded_kwargs)


class TestConflictOnARGSReported(unittest.TestCase):
    def test_in_function_definition(self) -> None:
        type_error = None  # type: Optional[TypeError]
        try:

            @icontract.require(lambda _ARGS: True)
            def some_func(_ARGS: Any) -> None:
                pass

        except TypeError as error:
            type_error = error

        assert type_error is not None
        self.assertEqual(
            'The arguments of the function to be decorated with a contract checker include "_ARGS" '
            "which is a reserved placeholder for positional arguments in the condition.",
            str(type_error),
        )

    def test_in_kwargs_in_call(self) -> None:
        @icontract.require(lambda _ARGS: True)
        def some_func(*args, **kwargs) -> None:  # type: ignore
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(_ARGS="something")
        except TypeError as error:
            type_error = error

        assert type_error is not None
        self.assertEqual(
            'The arguments of the function call include "_ARGS" '
            "which is a placeholder for positional arguments in a condition.",
            str(type_error),
        )


class TestConflictOnKWARGSReported(unittest.TestCase):
    def test_in_function_definition(self) -> None:
        type_error = None  # type: Optional[TypeError]
        try:

            @icontract.require(lambda _ARGS: True)
            def some_func(_KWARGS: Any) -> None:
                pass

        except TypeError as error:
            type_error = error

        assert type_error is not None
        self.assertEqual(
            'The arguments of the function to be decorated with a contract checker include "_KWARGS" '
            "which is a reserved placeholder for keyword arguments in the condition.",
            str(type_error),
        )

    def test_in_kwargs_in_call(self) -> None:
        @icontract.require(lambda _ARGS: True)
        def some_func(*args, **kwargs) -> None:  # type: ignore
            pass

        type_error = None  # type: Optional[TypeError]
        try:
            some_func(_KWARGS="something")
        except TypeError as error:
            type_error = error

        assert type_error is not None
        self.assertEqual(
            'The arguments of the function call include "_KWARGS" '
            "which is a placeholder for keyword arguments in a condition.",
            str(type_error),
        )


if __name__ == "__main__":
    unittest.main()
