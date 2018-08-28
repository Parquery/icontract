"""Decorate functions with contracts."""
import functools
import inspect
import reprlib
from typing import Callable, MutableMapping, Any, Optional, Set, List  # pylint: disable=unused-import

import icontract.represent


class ViolationError(AssertionError):
    """Indicate a violation of a contract."""

    pass


# Default representation instance.
#
# The limits are set way higher than reprlib.aRepr since the default reprlib limits are not suitable for
# the production systems.
aRepr = reprlib.Repr()  # pylint: disable=invalid-name
aRepr.maxdict = 50
aRepr.maxlist = 50
aRepr.maxtuple = 50
aRepr.maxset = 50
aRepr.maxfrozenset = 50
aRepr.maxdeque = 50
aRepr.maxarray = 50
aRepr.maxstring = 256
aRepr.maxother = 256


class pre:  # pylint: disable=invalid-name
    """
    Decorate a function with a pre-condition.

    The arguments of the pre-condition are expected to be a subset of the arguments of the wrapped function.
    """

    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None) -> None:
        """
        Initialize.

        :param condition: pre-condition function
        :param description: textual description of the pre-condition
        :param repr_args:
            function to represent arguments in the message on a failed pre-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``aRepr`` is used.
        """
        if repr_args is not None and a_repr is not None:
            raise ValueError("Expected no repr_instance if repr_args is given.")

        self.condition = condition

        self._condition_args = list(inspect.signature(condition).parameters.keys())  # type: List[str]
        self._condition_arg_set = set(self._condition_args)  # type: Set[str]
        self._condition_as_text = icontract.represent.condition_as_text(condition=condition)

        self.description = description

        self._repr_func = repr_args
        if repr_args is not None:
            got = list(inspect.signature(repr_args).parameters.keys())

            if got != self._condition_args:
                raise ValueError("Unexpected argument(s) of repr_args. Expected {}, got {}".format(
                    self._condition_args, got))

        self._a_repr = a_repr if a_repr is not None else aRepr

    def __call__(self, func: Callable[..., Any]):
        """
        Check the pre-condition before calling the function 'func'.

        :param func: function to be wrapped
        :return: return value from 'func'
        """
        sign = inspect.signature(func)
        param_names = list(sign.parameters.keys())

        for condition_arg in self._condition_args:
            if condition_arg not in sign.parameters:
                raise TypeError("Unexpected condition argument: {}".format(condition_arg))

        def wrapped(*args, **kwargs):
            """Wrap func by checking the pre-condition first which is passed only the subset of arguments it needs."""
            condition_kwargs = dict()  # type: MutableMapping[str, Any]

            if wrapped.__kwdefaults__ is not None:
                condition_kwargs.update(wrapped.__kwdefaults__)

            for i, func_arg in enumerate(args):
                if param_names[i] in self._condition_arg_set:
                    condition_kwargs[param_names[i]] = func_arg

            for key, val in kwargs.items():
                if key in self._condition_arg_set:
                    condition_kwargs[key] = val

            check = self.condition(**condition_kwargs)

            if not check:
                parts = ["Precondition violated"]

                if self.description is not None:
                    parts.append(': ' + self.description)

                parts.append(": ")
                parts.append(self._condition_as_text)

                if self._repr_func:
                    parts.append(': ')
                    parts.append(self._repr_func(**condition_kwargs))
                else:
                    repr_values = icontract.represent.repr_values(
                        condition=self.condition, condition_kwargs=condition_kwargs, a_repr=self._a_repr)

                    if len(repr_values) == 1:
                        parts.append(': ')
                        parts.append(repr_values[0])
                    else:
                        parts.append(':\n')
                        parts.append('\n'.join(repr_values))

                err = ViolationError("".join(parts))
                raise err

            return func(*args, **kwargs)

        # Copy __doc__ and other properties so that doctests can run
        functools.update_wrapper(wrapped, func)

        # We also need to propagate the defaults.
        if wrapped.__kwdefaults__ is None:  # type: ignore
            wrapped.__kwdefaults__ = dict()  # type: ignore

        for param in sign.parameters.values():
            if not isinstance(param.default, inspect.Parameter.empty) and param.name in self._condition_arg_set:
                wrapped.__kwdefaults__[param.name] = param.default

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
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None) -> None:
        """
        Initialize.

        :param condition: post-condition function
        :param description: textual description of the post-condition
        :param repr_args:
            function to represent arguments in the message on a failed post-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``reprlib.aRepr`` is used.
        """
        if repr_args is not None and a_repr is not None:
            raise ValueError("Expected no repr_instance if repr_args is given.")

        self.condition = condition

        self._condition_args = list(inspect.signature(condition).parameters.keys())  # type: List[str]
        self._condition_arg_set = set(self._condition_args)  # type: Set[str]
        self._condition_as_text = icontract.represent.condition_as_text(condition=condition)

        self.description = description

        self._repr_func = repr_args
        if repr_args is not None:
            got = list(inspect.signature(repr_args).parameters.keys())

            if got != self._condition_args:
                raise ValueError("Unexpected argument(s) of repr_func. Expected {}, got {}".format(
                    self._condition_args, got))

        self._a_repr = a_repr if a_repr is not None else aRepr

    def __call__(self, func: Callable[..., Any]):
        """
        Check the post-condition before calling the function 'func'.

        :param func: function to be wrapped
        :return: return value from 'func'
        """
        sign = inspect.signature(func)

        if "result" in sign.parameters.keys():
            raise ValueError("Unexpected argument 'result' in the wrapped function")

        param_names = list(sign.parameters.keys())

        for condition_arg in self._condition_args:
            if condition_arg != "result" and condition_arg not in sign.parameters:
                raise TypeError("Unexpected condition argument: {}".format(condition_arg))

        def wrapped(*args, **kwargs):
            """
            Wrap func by checking the post-condition on its inputs and the result.

            The post-condition is passed only the subset of arguments it needs.

            """
            condition_kwargs = dict()  # type: MutableMapping[str, Any]

            # Add first the defaults
            if wrapped.__kwdefaults__ is not None:
                condition_kwargs.update(wrapped.__kwdefaults__)

            # Collect all the positional arguments
            for i, func_arg in enumerate(args):
                if param_names[i] in self._condition_arg_set:
                    condition_kwargs[param_names[i]] = func_arg

            # Collect the keyword arguments
            for key, val in kwargs.items():
                if key in self._condition_arg_set:
                    condition_kwargs[key] = val

            result = func(*args, **kwargs)

            # Add the special ``result`` argument
            if "result" in self._condition_arg_set:
                condition_kwargs["result"] = result

            check = self.condition(**condition_kwargs)

            if not check:
                parts = ["Post-condition violated"]  # type: List[str]

                if self.description is not None:
                    parts.append(": ")
                    parts.append(self.description)

                parts.append(": ")
                parts.append(self._condition_as_text)

                if self._repr_func:
                    parts.append(': ')
                    parts.append(self._repr_func(**condition_kwargs))
                else:
                    repr_values = icontract.represent.repr_values(
                        condition=self.condition, condition_kwargs=condition_kwargs, a_repr=self._a_repr)

                    if len(repr_values) == 1:
                        parts.append(': ')
                        parts.append(repr_values[0])
                    else:
                        parts.append(':\n')
                        parts.append('\n'.join(repr_values))

                err = ViolationError("".join(parts))
                raise err

            return result

        # Copy __doc__ and other properties so that doctests can run
        functools.update_wrapper(wrapped, func)

        # Also add the default values
        if wrapped.__kwdefaults__ is None:  # type: ignore
            wrapped.__kwdefaults__ = dict()  # type: ignore

        for param in sign.parameters.values():
            if not isinstance(param.default, inspect.Parameter.empty) and param.name in self._condition_arg_set:
                wrapped.__kwdefaults__[param.name] = param.default

        return wrapped
