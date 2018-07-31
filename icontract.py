"""Decorate functions with contracts."""
import ast
import inspect
from typing import Callable, MutableMapping, Any, Optional, Set, List  # pylint: disable=unused-import

import meta.decompiler


class ViolationError(Exception):
    """Indicate a violation of a contract."""

    pass


def _condition_as_text(condition: Callable) -> str:
    if condition.__name__ != "<lambda>":
        return condition.__name__

    lambda_node = meta.decompiler.decompile_func(condition)
    assert isinstance(lambda_node, ast.Lambda)

    body_txt = str(meta.dump_python_source(lambda_node.body)).strip()

    # Strip enclosing brackets from the body
    if body_txt.startswith("(") and body_txt.endswith(")"):
        body_txt = body_txt[1:-1]

    return body_txt


class pre:  # pylint: disable=invalid-name
    """
    Decorate a function with a pre-condition.

    The arguments of the pre-condition are expected to be a subset of the arguments of the wrapped function.
    """

    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None) -> None:
        """
        Initialize.

        :param condition: pre-condition function
        :param description: textual description of the pre-condition
        :param repr_args:
            function to represent arguments in the message on a failed pre-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, a concatenation of __repr__'s called on each argument respectively is used.
        """
        self.condition = condition

        self._condition_args = list(inspect.signature(condition).parameters.keys())  # type: List[str]
        self._condition_arg_set = set(self._condition_args)  # type: Set[str]
        self._condition_as_text = _condition_as_text(condition=condition)

        self.description = description

        self._repr_func = repr_args
        if repr_args is not None:
            got = list(inspect.signature(repr_args).parameters.keys())

            if got != self._condition_args:
                raise ValueError("Unexpected argument(s) of repr_args. Expected {}, got {}".format(
                    self._condition_args, got))

    def __call__(self, func: Callable[..., Any]):
        """
        Check the pre-condition before calling the function 'func'.

        :param func: function to be wrapped
        :return: return value from 'func'
        """
        sign = inspect.signature(func)
        params = list(sign.parameters.keys())

        for condition_arg in self._condition_args:
            if condition_arg not in sign.parameters:
                raise TypeError("Unexpected condition argument: {}".format(condition_arg))

        def wrapped(*args, **kwargs):
            """Wrap func by checking the pre-condition first which is passed only the subset of arguments it needs."""
            condition_kwargs = dict()  # type: MutableMapping[str, Any]

            for i, func_arg in enumerate(args):
                if params[i] in self._condition_arg_set:
                    condition_kwargs[params[i]] = func_arg

            for key, val in kwargs.items():
                if key in self._condition_arg_set:
                    condition_kwargs[key] = val

            check = self.condition(**condition_kwargs)

            if not check:
                parts = ["Precondition violated"]

                if self.description is not None:
                    parts.append(self.description)

                parts.append(self._condition_as_text)

                if self._repr_func:
                    parts.append(self._repr_func(**condition_kwargs))
                else:
                    for key in self._condition_args:
                        parts.append("{} was {!r}".format(key, condition_kwargs[key]))

                raise ViolationError(": ".join(parts))

            return func(*args, **kwargs)

        return wrapped


class post:  # pylint: disable=invalid-name
    """
    Decorate a function with a post-condition.

    The arguments of the post-condition are expected to be a subset of the arguments of the wrapped function.
    Additionally, the argument "result" is reserved for the result of the wrapped function. The wrapped function must
    not have "result" among its arguments.
    """

    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None) -> None:
        """
        Initialize.

        :param condition: post-condition function
        :param description: textual description of the post-condition
        :param repr_args:
            function to represent arguments in the message on a failed post-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, a concatenation of __repr__'s called on each argument respectively is used.
        """
        self.condition = condition

        self._condition_args = list(inspect.signature(condition).parameters.keys())  # type: List[str]
        self._condition_arg_set = set(self._condition_args)  # type: Set[str]
        self._condition_as_text = _condition_as_text(condition=condition)

        self.description = description

        self._repr_args = repr_args
        if repr_args is not None:
            got = list(inspect.signature(repr_args).parameters.keys())

            if got != self._condition_args:
                raise ValueError("Unexpected argument(s) of repr_func. Expected {}, got {}".format(
                    self._condition_args, got))

    def __call__(self, func: Callable[..., Any]):
        """
        Check the post-condition before calling the function 'func'.

        :param func: function to be wrapped
        :return: return value from 'func'
        """
        sign = inspect.signature(func)

        if "result" in sign.parameters.keys():
            raise ValueError("Unexpected argument 'result' in the wrapped function")

        params = list(sign.parameters.keys())

        for condition_arg in self._condition_args:
            if condition_arg != "result" and condition_arg not in sign.parameters:
                raise TypeError("Unexpected condition argument: {}".format(condition_arg))

        def wrapped(*args, **kwargs):
            """
            Wrap func by checking the post-condition on its inputs and the result.

            The post-condition is passed only the subset of arguments it needs.

            """
            condition_kwargs = dict()  # type: MutableMapping[str, Any]

            for i, func_arg in enumerate(args):
                if params[i] in self._condition_arg_set:
                    condition_kwargs[params[i]] = func_arg

            for key, val in kwargs.items():
                if key in self._condition_arg_set:
                    condition_kwargs[key] = val

            result = func(*args, **kwargs)

            condition_kwargs["result"] = result

            check = self.condition(**condition_kwargs)

            if not check:
                parts = ["Post-condition violated"]  # type: List[str]

                if self.description is not None:
                    parts.append(self.description)

                parts.append(self._condition_as_text)

                if self._repr_args:
                    parts.append(self._repr_args(**condition_kwargs))
                else:
                    for key in self._condition_args:
                        parts.append("{} was {!r}".format(key, condition_kwargs[key]))

                raise ViolationError(": ".join(parts))

            return result

        return wrapped
