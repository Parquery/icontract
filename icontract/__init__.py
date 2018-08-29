"""Decorate functions with contracts."""

import functools
import inspect
import os
import reprlib
from typing import Callable, MutableMapping, Any, Optional, Set, List, Type  # pylint: disable=unused-import

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

# SLOW provides a unified environment variable (ICONTRACT_SLOW) to enable the contracts which are slow to execute.
#
# Use SLOW to mark any contracts that are even too slow to make it to the normal (__debug__) execution of
# the interpreted program.
#
# Contracts marked with SLOW are also disabled if the interpreter is run in optimized mode (``-O`` or ``-OO``).
SLOW = __debug__ and os.environ.get("ICONTRACT_SLOW", "") != ""


class pre:  # pylint: disable=invalid-name
    """
    Decorate a function with a pre-condition.

    The arguments of the pre-condition are expected to be a subset of the arguments of the wrapped function.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None,
                 enabled: bool = __debug__) -> None:
        """
        Initialize.

        :param condition: pre-condition predicate
        :param description: textual description of the pre-condition
        :param repr_args:
            function to represent arguments in the message on a failed pre-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``aRepr`` is used.
        :param enabled:
            The decorator is applied only if this argument is set.

            Otherwise, the condition check is disabled and there is no run-time overhead.

            The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).

        """
        # pylint: disable=too-many-arguments
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

        self.enabled = enabled

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Check the pre-condition before calling the function ``func``.

        :param func: function to be wrapped
        :return: wrapped ``func``
        """
        if not self.enabled:
            return func

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
                parts = []  # type: List[str]

                if self.description is not None:
                    parts.append("{}: ".format(self.description))

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

    # pylint: disable=too-many-instance-attributes
    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None,
                 enabled: bool = __debug__) -> None:
        """
        Initialize.

        :param condition: post-condition predicate
        :param description: textual description of the post-condition
        :param repr_args:
            function to represent arguments in the message on a failed post-condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``reprlib.aRepr`` is used.
        :param enabled:
            The decorator is applied only if this argument is set.

            Otherwise, the condition check is disabled and there is no run-time overhead.

            The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).

        """
        # pylint: disable=too-many-arguments
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

        self.enabled = enabled

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Check the post-condition before calling the function ``func``.

        :param func: function to be wrapped
        :return: wrapped ``func``
        """
        if not self.enabled:
            return func

        sign = inspect.signature(func)

        if "result" in sign.parameters.keys():
            raise ValueError("Unexpected argument 'result' in the wrapped function")

        param_names = list(sign.parameters.keys())

        for condition_arg in self._condition_args:
            if condition_arg != "result" and condition_arg not in sign.parameters:
                raise TypeError("Unexpected condition argument: {}".format(condition_arg))

        def wrapped(*args, **kwargs):
            """
            Wrap ``func`` by checking the post-condition on its inputs and the result.

            The post-condition is passed only the subset of arguments it needs (including a special ``result``
            argument representing the result of the wrapped function).

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
                parts = []  # type: List[str]

                if self.description is not None:
                    parts.append("{}: ".format(self.description))

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


def inv(condition: Callable[..., bool],
        description: Optional[str] = None,
        repr_args: Optional[Callable[..., str]] = None,
        a_repr: Optional[reprlib.Repr] = None,
        enabled: bool = __debug__) -> Callable[[Type], Type]:
    """
    Create a class decorator to establish the invariant on all the public methods.

    Class method as well as "private" (prefix ``__``) and "protected" methods (prefix ``_``) may violate the invariant.
    Note that all magic methods (prefix ``__`` and suffix ``__``) are considered public and hence also need to establish
    the invariant. To avoid endless loops when generating the error message on an invariant breach, the method
    ``__repr__`` is deliberately exempt from observing the invariant.

    The invariant is checked *before* and *after* the method invocation.

    :param condition: invariant predicate
    :param description: textual description of the invariant
    :param repr_args:
            function to represent arguments in the message on a breached invariant. The repr_func takes only ``self``
            as a single argument.

            If not specified, all the involved values are represented by re-traversing the AST.

    :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``icontract.aRepr`` is used.
    :param enabled:
            The decorator is applied only if this argument is set.

            Otherwise, the condition check is disabled and there is no run-time overhead.

            The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).

    :return: class decorator

    """
    parameter_names = sorted(inspect.signature(condition).parameters.keys())
    if parameter_names != ["self"]:
        raise ValueError(
            "Expected a condition function with a single argument 'self', but got: {}".format(parameter_names))

    def decorator(cls: Type) -> Type:
        """Decorate each of the public methods with the invariant as a pre and a postcondition, respectively."""
        if not enabled:
            return cls

        for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
            if not inspect.ismethod(value) and not inspect.isfunction(value):
                continue

            # Ignore class methods
            if getattr(value, "__self__", None) is cls:
                continue

            # Ignore __repre__ to avoid endless loops when generating the error message on invariant breach.
            if name == "__repr__":
                continue

            if name == "__init__":
                post_decorator = post(
                    condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, enabled=enabled)

                wrapped = post_decorator(func=value)
                setattr(cls, name, wrapped)

            elif not name.startswith("_") or (name.startswith("__") and name.endswith("__")):
                pre_decorator = pre(
                    condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, enabled=enabled)

                post_decorator = post(
                    condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, enabled=enabled)

                wrapped = pre_decorator(post_decorator(func=value))
                setattr(cls, name, wrapped)

            elif name.startswith("_"):
                # It is a private or a protected method or function, do not enforce any pre and postconditions.
                pass

            else:
                raise NotImplementedError("Unhandled method or function of class {}: {}".format(cls.__name__, name))

        return cls

    return decorator
