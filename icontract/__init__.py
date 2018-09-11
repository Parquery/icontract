"""Decorate functions with contracts."""
import abc
import functools
import inspect
import os
import reprlib
from typing import Callable, MutableMapping, Any, Optional, Set, List, Type, Dict, \
    Tuple, Mapping, Iterable  # pylint: disable=unused-import

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


class _Contract:
    """Represent a contract to be enforced as a precondition, postcondition or as an invariant."""

    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None) -> None:
        """
        Initialize.

        :param condition: condition predicate
        :param description: textual description of the contract
        :param repr_args:
            function to represent arguments in the message on a failed condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``aRepr`` is used.

        """
        # pylint: disable=too-many-arguments
        if repr_args is not None and a_repr is not None:
            raise ValueError("Expected no repr_instance if repr_args is given.")

        self.condition = condition

        self.condition_args = list(inspect.signature(condition).parameters.keys())  # type: List[str]
        self.condition_arg_set = set(self.condition_args)  # type: Set[str]

        self.description = description

        self._repr_func = repr_args
        if repr_args is not None:
            got = list(inspect.signature(repr_args).parameters.keys())

            if got != self.condition_args:
                raise ValueError("Unexpected argument(s) of repr_args. Expected {}, got {}".format(
                    self.condition_args, got))

        self._a_repr = a_repr if a_repr is not None else aRepr


def _generate_message(contract: _Contract, condition_kwargs: Mapping[str, Any]) -> str:
    """Generate the message upon contract violation."""
    # pylint: disable=protected-access
    parts = []  # type: List[str]

    if contract.description is not None:
        parts.append("{}: ".format(contract.description))

    parts.append(icontract.represent.condition_as_text(condition=contract.condition))

    if contract._repr_func:
        parts.append(': ')
        parts.append(contract._repr_func(**condition_kwargs))
    else:
        repr_values = icontract.represent.repr_values(
            condition=contract.condition, condition_kwargs=condition_kwargs, a_repr=contract._a_repr)

        if len(repr_values) == 1:
            parts.append(': ')
            parts.append(repr_values[0])
        else:
            parts.append(':\n')
            parts.append('\n'.join(repr_values))

    msg = "".join(parts)
    return msg


def _assert_precondition(contract: _Contract, param_names: List[str], kwdefaults: Dict[str, Any], args: Tuple[Any, ...],
                         kwargs: Dict[str, Any]) -> None:
    """Assert that the contract holds as a precondition to the function ``func``."""
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    condition_kwargs = dict()  # type: MutableMapping[str, Any]

    # Set the default argument values as condition parameters.
    for param_name, param_value in kwdefaults.items():
        if param_name in contract.condition_arg_set:
            condition_kwargs[param_name] = param_value

    # Override the defaults with the values actually suplied to the function.
    for i, func_arg in enumerate(args):
        if param_names[i] in contract.condition_arg_set:
            condition_kwargs[param_names[i]] = func_arg

    for key, val in kwargs.items():
        if key in contract.condition_arg_set:
            condition_kwargs[key] = val

    # Check that all arguments to the condition function have been set.
    for arg_name in contract.condition_args:
        if arg_name not in condition_kwargs:
            raise TypeError(("The argument of the contract condition has not been set: {}. "
                             "Does the function define it?").format(arg_name))

    check = contract.condition(**condition_kwargs)

    if not check:
        msg = _generate_message(contract=contract, condition_kwargs=condition_kwargs)
        raise ViolationError(msg)


def _assert_invariant(contract: _Contract, instance: Any) -> None:
    """Assert that the contract holds as a class invariant given the instance of the class."""
    check = contract.condition(self=instance)

    if not check:
        msg = _generate_message(contract=contract, condition_kwargs={"self": instance})
        raise ViolationError(msg)


def _assert_postcondition(contract: _Contract, param_names: List[str], kwdefaults: Dict[str, Any],
                          args: Tuple[Any, ...], kwargs: Dict[str, Any], result: Any) -> None:
    """Assert that the contract holds as a postcondition given the arguments and the result of a function."""
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    condition_kwargs = dict()  # type: MutableMapping[str, Any]

    # Set the default argument values as condition parameters.
    for param_name, param_value in kwdefaults.items():
        if param_name in contract.condition_arg_set:
            condition_kwargs[param_name] = param_value

    # Override the default argument values with the values actually supplied to the function.
    for i, func_arg in enumerate(args):
        if param_names[i] in contract.condition_arg_set:
            condition_kwargs[param_names[i]] = func_arg

    # Collect the keyword arguments
    for key, val in kwargs.items():
        if key in contract.condition_arg_set:
            condition_kwargs[key] = val

    # Add the special ``result`` argument
    if "result" in contract.condition_arg_set:
        condition_kwargs["result"] = result

    # Check that all arguments to the condition function have been set.
    for arg_name in contract.condition_args:
        if arg_name not in condition_kwargs:
            raise TypeError(("The argument of the contract condition has not been set: {}. "
                             "Does the function define it?").format(arg_name))

    check = contract.condition(**condition_kwargs)

    if not check:
        msg = _generate_message(contract=contract, condition_kwargs=condition_kwargs)
        raise ViolationError(msg)


def _decorate_with_checker(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorate the function with a checker that verifies the preconditions and postconditions."""
    assert not hasattr(func, "__preconditions__"), \
        "Expected func to have no list of preconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postconditions__"), \
        "Expected func to have no list of postconditions (there should be only a single contract checker per function)."

    sign = inspect.signature(func)
    param_names = list(sign.parameters.keys())

    # Determine the default argument values.
    kwdefaults = dict()  # type: Dict[str, Any]

    # Add to the defaults all the values that are needed by the contracts.
    for param in sign.parameters.values():
        if param.default != inspect.Parameter.empty:
            kwdefaults[param.name] = param.default

    def wrapper(*args, **kwargs):
        """Wrap func by checking the preconditions and postconditions."""
        preconditions = getattr(wrapper, "__preconditions__")
        postconditions = getattr(wrapper, "__postconditions__")

        # Assert the preconditions in groups. This is necessary to implement "require else" logic when a class
        # weakens the preconditions of its base class.
        violation_err = None  # type: Optional[ViolationError]
        for group in preconditions:
            violation_err = None
            try:
                for contract in group:
                    _assert_precondition(
                        contract=contract, param_names=param_names, kwdefaults=kwdefaults, args=args, kwargs=kwargs)
                break
            except ViolationError as err:
                violation_err = err

        if violation_err is not None:
            raise violation_err  # pylint: disable=raising-bad-type

        # Execute the wrapped function
        result = func(*args, **kwargs)

        # Assert the postconditions as a conjunction
        for contract in postconditions:
            _assert_postcondition(
                contract=contract,
                param_names=param_names,
                kwdefaults=kwdefaults,
                args=args,
                kwargs=kwargs,
                result=result)

        return result

    # Copy __doc__ and other properties so that doctests can run
    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    assert not hasattr(wrapper, "__preconditions__"), "Expected no preconditions set on a pristine contract checker."
    assert not hasattr(wrapper, "__postconditions__"), "Expected no postconditions set on a pristine contract checker."

    # Precondition is a list of condition groups (i.e. disjunctive normal form):
    # each group consists of AND'ed preconditions, while the groups are OR'ed.
    #
    # This is necessary in order to implement "require else" logic when a class weakens the preconditions of
    # its base class.
    setattr(wrapper, "__preconditions__", [[]])

    setattr(wrapper, "__postconditions__", [])

    return wrapper


def _unwind_decorator_stack(func: Callable[..., Any]) -> Iterable[Callable[..., Any]]:
    """
    Iterate through the stack of decorated functions and return the original function.

    Assume that all decorators used functools.update_wrapper.
    """
    while hasattr(func, "__wrapped__"):
        yield func

        func = getattr(func, "__wrapped__")

    yield func


def _find_checker(func: Callable[..., Any]) -> Optional[Callable[..., Any]]:
    """Iterate through the decorator stack till we find the contract checker."""
    contract_checker = None  # type: Optional[Callable[..., Any]]
    for a_wrapper in _unwind_decorator_stack(func):
        if hasattr(a_wrapper, "__preconditions__") or hasattr(a_wrapper, "__postconditions__"):
            contract_checker = a_wrapper

    return contract_checker


class pre:  # pylint: disable=invalid-name
    """
    Decorate a function with a precondition.

    The arguments of the precondition are expected to be a subset of the arguments of the wrapped function.
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

        :param condition: precondition predicate
        :param description: textual description of the precondition
        :param repr_args:
            function to represent arguments in the message on a failed precondition. The repr_func needs to take the
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
        self.enabled = enabled
        self._contract = None  # type: Optional[_Contract]

        if not enabled:
            return

        self._contract = _Contract(condition=condition, description=description, repr_args=repr_args, a_repr=a_repr)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Add the precondition to the list of preconditions of the function ``func``.

        The function ``func`` is decorated with a contract checker if there is no contract checker in
        the decorator stack.

        :param func: function to be wrapped
        :return: contract checker around ``func`` if no contract checker on the decorator stack, or ``func`` otherwise
        """
        if not self.enabled:
            return func

        # Find a contract checker
        contract_checker = _find_checker(func=func)

        if contract_checker is not None:
            # Do not add an additional wrapper since the function has been already wrapped with a contract checker
            result = func
        else:
            # Wrap the function with a contract checker
            contract_checker = _decorate_with_checker(func=func)
            result = contract_checker

        # Add the precondition to the list of preconditions stored at the checker
        assert hasattr(contract_checker, "__preconditions__")
        preconditions = getattr(contract_checker, "__preconditions__")
        assert isinstance(preconditions, list)
        assert len(preconditions) == 1, \
            "A single group of preconditions expected when wrapping with a contract checker. " \
            "The preconditions are merged only in the DBC metaclass."

        assert isinstance(preconditions[0], list)
        preconditions[0].append(self._contract)

        return result


class post:  # pylint: disable=invalid-name
    """
    Decorate a function with a postcondition.

    The arguments of the postcondition are expected to be a subset of the arguments of the wrapped function.
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

        :param condition: postcondition predicate
        :param description: textual description of the postcondition
        :param repr_args:
            function to represent arguments in the message on a failed postcondition. The repr_func needs to take the
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
        self.enabled = enabled
        self._contract = None  # type: Optional[_Contract]

        if not enabled:
            return

        self._contract = _Contract(condition=condition, description=description, repr_args=repr_args, a_repr=a_repr)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Add the postcondition to the list of postconditions of the function ``func``.

        The function ``func`` is decorated with a contract checker if there is no contract checker in
        the decorator stack.

        :param func: function to be wrapped
        :return: contract checker around ``func`` if no contract checker on the decorator stack, or ``func`` otherwise
        """
        if not self.enabled:
            return func

        # Find a contract checker
        contract_checker = _find_checker(func=func)

        if contract_checker is not None:
            # Do not add an additional wrapper since the function has been already wrapped with a contract checker
            result = func
        else:
            # Wrap the function with a contract checker
            contract_checker = _decorate_with_checker(func=func)
            result = contract_checker

        # Add the precondition to the list of preconditions stored at the checker
        assert hasattr(contract_checker, "__postconditions__")
        assert isinstance(getattr(contract_checker, "__postconditions__"), list)
        getattr(contract_checker, "__postconditions__").append(self._contract)

        return result


def _find_self(param_names: List[str], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Any:
    """Find the instance of ``self`` in the arguments."""
    instance_i = param_names.index("self")
    if instance_i < len(args):
        instance = args[instance_i]
    else:
        instance = kwargs["self"]

    return instance


def _decorate_with_invariants(cls: Type, func: Callable[..., Any], is_init: bool) -> Callable[..., Any]:
    """
    Decorate the function ``func`` of the class ``cls`` with invariant checks.

    :param cls: class to be decorated
    :param func: function to be wrapped
    :param is_init: True if the ``func`` is __init__
    :return: function wrapped with invariant checks
    """
    sign = inspect.signature(func)
    param_names = list(sign.parameters.keys())

    if is_init:

        def wrapper(*args, **kwargs):
            """Wrap __init__ method of a class by checking the invariants *after* the invocation."""
            result = func(*args, **kwargs)
            instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)

            for contract in cls.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            return result
    else:

        def wrapper(*args, **kwargs):
            """Wrap a function of a class by checking the invariants *before* and *after* the invocation."""
            instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)

            for contract in cls.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            result = func(*args, **kwargs)

            for contract in cls.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            return result

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    setattr(wrapper, "__is_invariant_check__", True)

    return wrapper


def _add_invariant_checks(cls: Type) -> None:
    """Decorate each of the class functions with invariant checks if not already decorated."""
    for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
        if not inspect.ismethod(value) and not inspect.isfunction(value):
            continue

        # Ignore class methods
        if getattr(value, "__self__", None) is cls:
            continue

        # Ignore __repr__ to avoid endless loops when generating the error message on invariant breach.
        if name == "__repr__":
            continue

        func = value
        for a_decorator in _unwind_decorator_stack(func=func):
            if getattr(a_decorator, "__is_invariant_check__", False):
                continue

        if name == "__init__":
            wrapper = _decorate_with_invariants(cls=cls, func=func, is_init=True)
            setattr(cls, name, wrapper)

        elif not name.startswith("_") or (name.startswith("__") and name.endswith("__")):
            wrapper = _decorate_with_invariants(cls=cls, func=func, is_init=False)
            setattr(cls, name, wrapper)

        elif name.startswith("_"):
            # It is a private or a protected method or function, do not enforce any pre and postconditions.
            pass

        else:
            raise NotImplementedError("Unhandled method or function of class {}: {}".format(cls.__name__, name))


def _identity_decorator(cls: Type) -> Type:
    """Do not decorate the class at all."""
    return cls


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
    if not enabled:
        return _identity_decorator

    parameter_names = sorted(inspect.signature(condition).parameters.keys())
    if parameter_names != ["self"]:
        raise ValueError(
            "Expected a condition function with a single argument 'self', but got: {}".format(parameter_names))

    contract = _Contract(condition=condition, description=description, repr_args=repr_args, a_repr=a_repr)

    def decorator(cls: Type) -> Type:
        """
        Decorate each of the public methods with the invariant.

        Go through the decorator stack of each function and search for a contract checker. If there is one,
        add the invariant to the checker's invariants. If there is no checker in the stack, wrap the function with a
        contract checker.
        """
        if not hasattr(cls, "__invariants__"):
            invariants = []  # type: List[_Contract]
            setattr(cls, "__invariants__", invariants)
        else:
            invariants = getattr(cls, "__invariants__")
            assert isinstance(invariants, list), \
                "Expected invariants of class {} to be a list, but got: {}".format(cls, type(invariants))

        invariants.append(contract)

        _add_invariant_checks(cls=cls)

        return cls

    return decorator


class DBCMeta(abc.ABCMeta):
    """
    Define a meta class that allows inheritance of the contracts.

    The preconditions are weakned ("require else"), while postconditions ("ensure then") and invariants are
    strengthened according to the inheritance rules of the design-by-contract.
    """

    def __new__(mcs, name, bases, namespace):
        """Create a class with inherited preconditions, postconditions and invariants."""
        cls = super().__new__(mcs, name, bases, namespace)

        if hasattr(cls, "__invariants__"):
            _add_invariant_checks(cls=cls)

        for key, value in namespace.items():
            for base in bases:
                if hasattr(base, key):
                    # Ignore non-functions
                    if not inspect.ismethod(value) and not inspect.isfunction(value):
                        continue

                    func = value

                    # Check if there is a checker function in the base class
                    base_func = getattr(base, key)
                    base_contract_checker = _find_checker(func=base_func)

                    # Ignore functions which don't have preconditions or postconditions
                    if base_contract_checker is None:
                        continue

                    # Create a contract checker if it has not been defined already
                    contract_checker = _find_checker(func=func)

                    if contract_checker is None:
                        # Inherit the preconditions and postconditions from the base function
                        contract_checker = _decorate_with_checker(func=func)
                        contract_checker.__preconditions__ = base_contract_checker.__preconditions__[:]
                        contract_checker.__postconditions__ = base_contract_checker.__postconditions__[:]
                        setattr(cls, key, contract_checker)
                    else:
                        # Merge the contracts of the base function and this function
                        contract_checker.__preconditions__.extend(base_contract_checker.__preconditions__)
                        contract_checker.__postconditions__.extend(base_contract_checker.__postconditions__)

        return cls


class DBC(metaclass=DBCMeta):
    """Provide a standard way to create a class which can inherit the contracts."""

    pass
