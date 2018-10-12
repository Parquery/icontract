"""Decorate functions with contracts."""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes

import abc
import functools
import inspect
import os
import platform
import reprlib
from typing import Callable, MutableMapping, Any, Optional, Set, List, Dict, \
    Tuple, Iterable, Mapping, cast, Union  # pylint: disable=unused-import

import icontract._represent


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
                 a_repr: Optional[reprlib.Repr] = None,
                 error: Union[Callable[..., Exception], type] = None) -> None:
        """
        Initialize.

        :param condition: condition predicate
        :param description: textual description of the contract
        :param repr_args:
            [WILL BE DEPRECATED IN ICONTRACT 2]

            function to represent arguments in the message on a failed condition. The repr_func needs to take the
            same arguments as the condition function.

            If not specified, all the involved values are represented by re-traversing the AST.
        :param a_repr:
            representation instance that defines how the values are represented.

            If ``repr_args`` is specified, ``repr_instance`` should be None.
            If no ``repr_args`` is specified, the default ``aRepr`` is used.
        :param error:
            if given as a callable, ``error`` is expected to accept a subset of function arguments
            (*e.g.*, also including ``result`` for perconditions, only ``self`` for invariants *etc.*) and return
            an exception. The ``error`` is called on contract violation and the resulting exception is raised.

            Otherwise, it is expected to denote an Exception class which is instantiated with the violation message
            and raised on contract violation.

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

        self.error = error
        self.error_args = None  # type: Optional[List[str]]
        self.error_arg_set = None  # type: Optional[Set[str]]
        if error is not None and (inspect.isfunction(error) or inspect.ismethod(error)):
            self.error_args = list(inspect.signature(error).parameters.keys())
            self.error_arg_set = set(self.error_args)


class _Snapshot:
    """Define a snapshot of an argument *prior* to the function invocation that is later supplied to a postcondition."""

    def __init__(self, capture: Callable[..., Any], name: Optional[str] = None) -> None:
        """
        Initialize.

        :param capture:
            function to capture the snapshot accepting a single argument (from a set of arguments
            of the original function)

        :param name: name of the captured variable in OLD that is passed to postconditions

        """
        self.capture = capture

        args = list(inspect.signature(capture).parameters.keys())  # type: List[str]

        if len(args) > 1:
            raise TypeError("The capture function of a snapshot expects only a single argument.")

        if len(args) == 0 and name is None:
            raise ValueError("You must name a snapshot if no argument was given in the capture function.")

        if name is None:
            name = args[0]

        assert name is not None, "Expected ``name`` to be set in the preceding execution paths."
        self.name = name

        self.arg = None  # type: Optional[str]
        if len(args) == 1:
            self.arg = args[0]
        else:
            assert len(args) == 0, "There can be at most one argument to a snapshot capture, but got: {}".format(args)


def _generate_message(contract: icontract._Contract, condition_kwargs: Mapping[str, Any]) -> str:
    """Generate the message upon contract violation."""
    # pylint: disable=protected-access
    parts = []  # type: List[str]

    if contract.description is not None:
        parts.append("{}: ".format(contract.description))

    lambda_inspection = icontract._represent.inspect_lambda_condition(condition=contract.condition)

    parts.append(
        icontract._represent.condition_as_text(condition=contract.condition, lambda_inspection=lambda_inspection))

    if contract._repr_func:
        parts.append(': ')
        parts.append(contract._repr_func(**condition_kwargs))
    else:
        repr_vals = icontract._represent.repr_values(
            condition=contract.condition,
            lambda_inspection=lambda_inspection,
            condition_kwargs=condition_kwargs,
            a_repr=contract._a_repr)

        if len(repr_vals) == 0:
            # Do not append anything since no value could be represented as a string.
            # This could appear in case we have, for example, a generator expression as the return value of a lambda.
            pass

        elif len(repr_vals) == 1:
            parts.append(': ')
            parts.append(repr_vals[0])
        else:
            parts.append(':\n')
            parts.append('\n'.join(repr_vals))

    msg = "".join(parts)
    return msg


def _kwargs_from_call(param_names: List[str], kwdefaults: Dict[str, Any], args: Tuple[Any, ...],
                      kwargs: Dict[str, Any]) -> MutableMapping[str, Any]:
    """
    Inspect the input values received at the wrapper for the actual function call.

    :param param_names: parameter (*i.e.* argument) names of the original (decorated) function
    :param kwdefaults: default argument values of the original function
    :param args: arguments supplied to the call
    :param kwargs: keyword arguments supplied to the call
    :return: resolved arguments as they would be passed to the function
    """
    # pylint: disable=too-many-arguments
    mapping = dict()  # type: MutableMapping[str, Any]

    # Set the default argument values as condition parameters.
    for param_name, param_value in kwdefaults.items():
        mapping[param_name] = param_value

    # Override the defaults with the values actually suplied to the function.
    for i, func_arg in enumerate(args):
        mapping[param_names[i]] = func_arg

    for key, val in kwargs.items():
        mapping[key] = val

    return mapping


def _assert_precondition(contract: _Contract, resolved_kwargs: Mapping[str, Any]) -> None:
    """
    Assert that the contract holds as a precondition.

    :param contract: contract to be verified
    :param resolved_kwargs: resolved keyword arguments (including the default values)
    :return:
    """
    # Check that all arguments to the condition function have been set.
    missing_args = [arg_name for arg_name in contract.condition_args if arg_name not in resolved_kwargs]
    if missing_args:
        raise TypeError(("The argument(s) of the precondition have not been set: {}. "
                         "Does the original function define them?").format(missing_args))

    condition_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items() if arg_name in contract.condition_arg_set
    }

    check = contract.condition(**condition_kwargs)

    if not check:
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            error_kwargs = {
                arg_name: value
                for arg_name, value in resolved_kwargs.items() if arg_name in contract.error_arg_set
            }

            missing_args = [arg_name for arg_name in contract.error_args if arg_name not in resolved_kwargs]
            if missing_args:
                raise TypeError(("The argument(s) of the precondition error have not been set: {}. "
                                 "Does the original function define them?").format(missing_args))

            raise contract.error(**error_kwargs)

        else:
            msg = _generate_message(contract=contract, condition_kwargs=condition_kwargs)
            if contract.error is None:
                raise ViolationError(msg)
            elif isinstance(contract.error, type):
                raise contract.error(msg)


def _assert_invariant(contract: _Contract, instance: Any) -> None:
    """Assert that the contract holds as a class invariant given the instance of the class."""
    if 'self' in contract.condition_arg_set:
        check = contract.condition(self=instance)
    else:
        check = contract.condition()

    if not check:
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            if 'self' in contract.error_arg_set:
                raise contract.error(self=instance)
            else:
                raise contract.error()
        else:
            if 'self' in contract.condition_arg_set:
                msg = _generate_message(contract=contract, condition_kwargs={"self": instance})
            else:
                msg = _generate_message(contract=contract, condition_kwargs=dict())

            if contract.error is None:
                raise ViolationError(msg)
            elif isinstance(contract.error, type):
                raise contract.error(msg)
            else:
                raise NotImplementedError("Unhandled contract.error: {}".format(contract.error))


def _capture_snapshot(a_snapshot: _Snapshot, resolved_kwargs: Mapping[str, Any]) -> Any:
    """
    Capture the snapshot from the keyword arguments resolved before the function call (including the default values).

    :param a_snapshot: snapshot to be captured
    :param resolved_kwargs: resolved keyword arguments (including the default values)
    :return: captured value
    """
    if a_snapshot.arg is not None:
        if a_snapshot.arg not in resolved_kwargs:
            raise TypeError(("The argument of the snapshot has not been set: {}. "
                             "Does the original function define it?").format(a_snapshot.arg))

        value = a_snapshot.capture(**{a_snapshot.arg: resolved_kwargs[a_snapshot.arg]})
    else:
        value = a_snapshot.capture()

    return value


def _assert_postcondition(contract: _Contract, resolved_kwargs: Mapping[str, Any]) -> None:
    """
    Assert that the contract holds as a postcondition.

    The arguments to the postcondition are given as ``resolved_kwargs`` which includes
    both argument values captured in snapshots and actual argument values and the result of a function.

    :param contract: contract to be verified
    :param resolved_kwargs: resolved keyword arguments (including the default values, ``result`` and ``OLD``)
    :return:
    """
    assert 'result' in resolved_kwargs, \
        "Expected 'result' to be set in the resolved keyword arguments of a postcondition."

    # Check that all arguments to the condition function have been set.
    missing_args = [arg_name for arg_name in contract.condition_args if arg_name not in resolved_kwargs]
    if missing_args:
        raise TypeError(("The argument(s) of the postcondition have not been set: {}. "
                         "Does the original function define them?").format(missing_args))

    condition_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items() if arg_name in contract.condition_arg_set
    }

    check = contract.condition(**condition_kwargs)

    if not check:
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            error_kwargs = {
                arg_name: value
                for arg_name, value in resolved_kwargs.items() if arg_name in contract.error_arg_set
            }

            missing_args = [arg_name for arg_name in contract.error_args if arg_name not in resolved_kwargs]
            if missing_args:
                raise TypeError(("The argument(s) of the postcondition error have not been set: {}. "
                                 "Does the original function define them?").format(missing_args))

            raise contract.error(**error_kwargs)

        else:
            msg = _generate_message(contract=contract, condition_kwargs=condition_kwargs)
            if contract.error is None:
                raise ViolationError(msg)
            elif isinstance(contract.error, type):
                raise contract.error(msg)


class _Old:
    """
    Represent argument values before the function invocation.

    Recipe taken from http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/
    """

    def __init__(self, mapping: Mapping[str, Any]) -> None:
        self.__dict__.update(mapping)

    def __getattr__(self, item):
        raise AttributeError("The snapshot with the name {!r} is not available in the OLD of a postcondition. "
                             "Have you decorated the function with an {}?".format(item, snapshot.__qualname__))

    def __repr__(self) -> str:
        return "a bunch of OLD values"


def _decorate_with_checker(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorate the function with a checker that verifies the preconditions and postconditions."""
    assert not hasattr(func, "__preconditions__"), \
        "Expected func to have no list of preconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postconditions__"), \
        "Expected func to have no list of postconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postcondition_snapshots__"), \
        "Expected func to have no list of postcondition snapshots (there should be only a single contract checker " \
        "per function)."

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
        preconditions = getattr(wrapper, "__preconditions__")  # type: List[List[_Contract]]
        snapshots = getattr(wrapper, "__postcondition_snapshots__")  # type: List[_Snapshot]
        postconditions = getattr(wrapper, "__postconditions__")  # type: List[_Contract]

        resolved_kwargs = _kwargs_from_call(param_names=param_names, kwdefaults=kwdefaults, args=args, kwargs=kwargs)

        if postconditions:
            if 'result' in resolved_kwargs:
                raise TypeError("Unexpected argument 'result' in a function decorated with postconditions.")

            if 'OLD' in resolved_kwargs:
                raise TypeError("Unexpected argument 'OLD' in a function decorated with postconditions.")

        # Assert the preconditions in groups. This is necessary to implement "require else" logic when a class
        # weakens the preconditions of its base class.
        violation_err = None  # type: Optional[ViolationError]
        for group in preconditions:
            violation_err = None
            try:
                for contract in group:
                    _assert_precondition(contract=contract, resolved_kwargs=resolved_kwargs)
                break
            except ViolationError as err:
                violation_err = err

        if violation_err is not None:
            raise violation_err  # pylint: disable=raising-bad-type

        # Capture the snapshots
        if postconditions:
            old_as_mapping = dict()  # type: MutableMapping[str, Any]
            for snap in snapshots:
                # This assert is just a last defense.
                # Conflicting snapshot names should have been caught before, either during the decoration or
                # in the meta-class.
                assert snap.name not in old_as_mapping, "Snapshots with the conflicting name: {}"
                old_as_mapping[snap.name] = _capture_snapshot(a_snapshot=snap, resolved_kwargs=resolved_kwargs)

            resolved_kwargs['OLD'] = _Old(mapping=old_as_mapping)

        # Execute the wrapped function
        result = func(*args, **kwargs)

        if postconditions:
            resolved_kwargs['result'] = result

            # Assert the postconditions as a conjunction
            for contract in postconditions:
                _assert_postcondition(contract=contract, resolved_kwargs=resolved_kwargs)

        return result

    # Copy __doc__ and other properties so that doctests can run
    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    assert not hasattr(wrapper, "__preconditions__"), "Expected no preconditions set on a pristine contract checker."
    assert not hasattr(wrapper, "__postcondition_snapshots__"), \
        "Expected no postcondition snapshots set on a pristine contract checker."
    assert not hasattr(wrapper, "__postconditions__"), "Expected no postconditions set on a pristine contract checker."

    # Precondition is a list of condition groups (i.e. disjunctive normal form):
    # each group consists of AND'ed preconditions, while the groups are OR'ed.
    #
    # This is necessary in order to implement "require else" logic when a class weakens the preconditions of
    # its base class.
    setattr(wrapper, "__preconditions__", [])
    setattr(wrapper, "__postcondition_snapshots__", [])
    setattr(wrapper, "__postconditions__", [])

    return wrapper


def _walk_decorator_stack(func: Callable[..., Any]) -> Iterable['Callable[..., Any]']:
    """
    Iterate through the stack of decorated functions until the original function.

    Assume that all decorators used functools.update_wrapper.
    """
    while hasattr(func, "__wrapped__"):
        yield func

        func = getattr(func, "__wrapped__")

    yield func


def _find_checker(func: Callable[..., Any]) -> Optional[Callable[..., Any]]:
    """Iterate through the decorator stack till we find the contract checker."""
    contract_checker = None  # type: Optional[Callable[..., Any]]
    for a_wrapper in _walk_decorator_stack(func):
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
                 enabled: bool = __debug__,
                 error: Union[Callable[..., Exception], type] = None) -> None:
        """
        Initialize.

        :param condition: precondition predicate
        :param description: textual description of the precondition
        :param repr_args:
            [WILL BE DEPRECATED IN ICONTRACT 2]

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
        :param error:
            if given as a callable, ``error`` is expected to accept a subset of function arguments
            (*e.g.*, also including ``result`` for perconditions, only ``self`` for invariants *etc.*) and return
            an exception. The ``error`` is called on contract violation and the resulting exception is raised.

            Otherwise, it is expected to denote an Exception class which is instantiated with the violation message
            and raised on contract violation.

        """
        # pylint: disable=too-many-arguments
        self.enabled = enabled
        self._contract = None  # type: Optional[_Contract]

        if not enabled:
            return

        self._contract = _Contract(
            condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, error=error)

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
        assert len(preconditions) <= 1, \
            ("At most a single group of preconditions expected when wrapping with a contract checker. "
             "The preconditions are merged only in the DBC metaclass. "
             "The current number of precondition groups: {}").format(len(preconditions))

        if len(preconditions) == 0:
            # Create the first group if there is no group so far, i.e. this is the first decorator.
            preconditions.append([])

        preconditions[0].append(self._contract)

        return result


class snapshot:  # pylint: disable=invalid-name
    """
    Decorate a function with a snapshot of an argument value captured *prior* to the function invocation.

    A snapshot is defined by a capture function (usually a lambda) that accepts a single argument of the function.
    If the name of the snapshot is not given, the name is equal to the name of the argument.

    The captured values are supplied to postconditions with the OLD argument of the condition and error function.
    Snapshots are inherited from the base classes and must not have conflicting names in the class hierarchy.
    """

    def __init__(self, capture: Callable[..., Any], name: Optional[str] = None, enabled: bool = __debug__) -> None:
        """
        Initialize.

        :param capture:
            function to capture the snapshot accepting a single argument (from a set of arguments
            of the original function)
        :param name: name of the snapshot; if omitted, the name corresponds to the name of the input argument
        :param enabled:
            The decorator is applied only if ``enabled`` is set.

            Otherwise, the snapshot is disabled and there is no run-time overhead.

            The default is to always capture the snapshot unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).

        """
        self._snapshot = None  # type: Optional[_Snapshot]
        self.enabled = enabled

        # Resolve the snapshot only if enabled so that no overhead is incurred
        if enabled:
            self._snapshot = _Snapshot(capture=capture, name=name)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Add the snapshot to the list of snapshots of the function ``func``.

        The function ``func`` is expected to be decorated with at least one postcondition before the snapshot.

        :param func: function whose arguments we need to snapshot
        :return: ``func`` as given in the input
        """
        if not self.enabled:
            return func

        # Find a contract checker
        contract_checker = _find_checker(func=func)

        if contract_checker is None:
            raise ValueError("You are decorating a function with a snapshot, but no postcondition was defined "
                             "on the function before.")

        assert self._snapshot is not None, "Expected the enabled snapshot to have the property ``snapshot`` set."

        # Add the snapshot to the list of snapshots stored at the checker
        assert hasattr(contract_checker, "__postcondition_snapshots__")

        snapshots = getattr(contract_checker, "__postcondition_snapshots__")
        assert isinstance(snapshots, list)

        for snap in snapshots:
            assert isinstance(snap, _Snapshot)
            if snap.name == self._snapshot.name:
                raise ValueError("There are conflicting snapshots with the name: {!r}".format(snap.name))

        snapshots.append(self._snapshot)

        return func


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
                 enabled: bool = __debug__,
                 error: Union[Callable[..., Exception], type] = None) -> None:
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
        :param error:
            if given as a callable, ``error`` is expected to accept a subset of function arguments
            (*e.g.*, also including ``result`` for perconditions, only ``self`` for invariants *etc.*) and return
            an exception. The ``error`` is called on contract violation and the resulting exception is raised.

            Otherwise, it is expected to denote an Exception class which is instantiated with the violation message
            and raised on contract violation.

        """
        # pylint: disable=too-many-arguments
        self.enabled = enabled
        self._contract = None  # type: Optional[_Contract]

        if not enabled:
            return

        self._contract = _Contract(
            condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, error=error)

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

        # Add the postcondition to the list of postconditions stored at the checker
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


def _decorate_with_invariants(func: Callable[..., Any], is_init: bool) -> Callable[..., Any]:
    """
    Decorate the function ``func`` of the class ``cls`` with invariant checks.

    If the function has been already decorated with invariant checks, the function returns immediately.

    :param func: function to be wrapped
    :param is_init: True if the ``func`` is __init__
    :return: function wrapped with invariant checks
    """
    if _already_decorated_with_invariants(func=func):
        return func

    sign = inspect.signature(func)
    param_names = list(sign.parameters.keys())

    if is_init:

        def wrapper(*args, **kwargs):
            """Wrap __init__ method of a class by checking the invariants *after* the invocation."""
            result = func(*args, **kwargs)
            instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)

            for contract in instance.__class__.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            return result
    else:

        def wrapper(*args, **kwargs):
            """Wrap a function of a class by checking the invariants *before* and *after* the invocation."""
            instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)

            for contract in instance.__class__.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            result = func(*args, **kwargs)

            for contract in instance.__class__.__invariants__:
                _assert_invariant(contract=contract, instance=instance)

            return result

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    setattr(wrapper, "__is_invariant_check__", True)

    return wrapper


class _DummyClass:
    """Represent a dummy class so that we can infer the type of the slot wrapper."""

    pass


_SLOT_WRAPPER_TYPE = type(_DummyClass.__init__)


def _already_decorated_with_invariants(func: Callable[..., Any]) -> bool:
    """Check if the function has been already decorated with an invariant check by going through its decorator stack."""
    already_decorated = False
    for a_decorator in _walk_decorator_stack(func=func):
        if getattr(a_decorator, "__is_invariant_check__", False):
            already_decorated = True
            break

    return already_decorated


def _add_invariant_checks(cls: type) -> None:
    """Decorate each of the class functions with invariant checks if not already decorated."""
    # Candidates for the decoration as list of (name, dir() value)
    init_name_func = None  # type: Optional[Tuple[str, Callable[..., None]]]
    names_funcs = []  # type: List[Tuple[str, Callable[..., None]]]
    names_properties = []  # type: List[Tuple[str, property]]

    # Filter out entries in the directory which are certainly not candidates for decoration.
    for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
        # We need to ignore __repr__ to prevent endless loops when generating error messages.
        # __getattribute__, __setattr__ and __delattr__ are too invasive and alter the state of the instance.
        # Hence we don't consider them "public".
        if name in ["__repr__", "__getattribute__", "__setattr__", "__delattr__"]:
            continue

        if name == "__init__":
            assert inspect.isfunction(value) or isinstance(value, _SLOT_WRAPPER_TYPE), \
                "Expected __init__ to be either a function or a slot wrapper, but got: {}".format(type(value))

            init_name_func = (name, value)
            continue

        if not inspect.isfunction(value) and not isinstance(value, _SLOT_WRAPPER_TYPE) and \
                not isinstance(value, property):
            continue

        # Ignore class methods
        if getattr(value, "__self__", None) is cls:
            continue

        # Ignore "protected"/"private" methods
        if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
            continue

        if inspect.isfunction(value) or isinstance(value, _SLOT_WRAPPER_TYPE):
            names_funcs.append((name, value))

        elif isinstance(value, property):
            names_properties.append((name, value))

        else:
            raise NotImplementedError("Unhandled directory entry of class {} for {}: {}".format(cls, name, value))

    if init_name_func:
        name, func = init_name_func
        wrapper = _decorate_with_invariants(func=func, is_init=True)
        setattr(cls, name, wrapper)

    for name, func in names_funcs:
        wrapper = _decorate_with_invariants(func=func, is_init=False)
        setattr(cls, name, wrapper)

    for name, prop in names_properties:
        fget = _decorate_with_invariants(func=prop.fget, is_init=False) if prop.fget else None
        fset = _decorate_with_invariants(func=prop.fset, is_init=False) if prop.fset else None
        fdel = _decorate_with_invariants(func=prop.fdel, is_init=False) if prop.fdel else None

        new_prop = property(fget=fget, fset=fset, fdel=fdel, doc=prop.__doc__)
        setattr(cls, name, new_prop)


class inv:  # pylint: disable=invalid-name
    """
    Represent a class decorator to establish the invariant on all the public methods.

    Class method as well as "private" (prefix ``__``) and "protected" methods (prefix ``_``) may violate the invariant.
    Note that all magic methods (prefix ``__`` and suffix ``__``) are considered public and hence also need to establish
    the invariant. To avoid endless loops when generating the error message on an invariant breach, the method
    ``__repr__`` is deliberately exempt from observing the invariant.

    The invariant is checked *before* and *after* the method invocation.

    """

    def __init__(self,
                 condition: Callable[..., bool],
                 description: Optional[str] = None,
                 repr_args: Optional[Callable[..., str]] = None,
                 a_repr: Optional[reprlib.Repr] = None,
                 enabled: bool = __debug__,
                 error: Union[Callable[..., Exception], type] = None) -> None:
        """
        Initialize a class decorator to establish the invariant on all the public methods.

        :param condition: invariant predicate
        :param description: textual description of the invariant
        :param repr_args:
                function to represent arguments in the message on a breached invariant. The repr_func takes only
                ``self`` as a single argument.

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
        :param error:
            if given as a callable, ``error`` is expected to accept a subset of function arguments
            (*e.g.*, also including ``result`` for perconditions, only ``self`` for invariants *etc.*) and return
            an exception. The ``error`` is called on contract violation and the resulting exception is raised.

            Otherwise, it is expected to denote an Exception class which is instantiated with the violation message
            and raised on contract violation.
        :return:

        """
        # pylint: disable=too-many-arguments
        self.enabled = enabled
        self._contract = None  # type: Optional[_Contract]

        if not enabled:
            return

        self._contract = _Contract(
            condition=condition, description=description, repr_args=repr_args, a_repr=a_repr, error=error)

        if self._contract.condition_args and self._contract.condition_args != ['self']:
            raise ValueError("Expected an invariant condition with at most an argument 'self', but got: {}".format(
                self._contract.condition_args))

    def __call__(self, cls: type) -> type:
        """
        Decorate each of the public methods with the invariant.

        Go through the decorator stack of each function and search for a contract checker. If there is one,
        add the invariant to the checker's invariants. If there is no checker in the stack, wrap the function with a
        contract checker.
        """
        if not self.enabled:
            return cls

        assert self._contract is not None, "self._contract must be set if the contract was enabled."

        if not hasattr(cls, "__invariants__"):
            invariants = []  # type: List[_Contract]
            setattr(cls, "__invariants__", invariants)
        else:
            invariants = getattr(cls, "__invariants__")
            assert isinstance(invariants, list), \
                "Expected invariants of class {} to be a list, but got: {}".format(cls, type(invariants))

        invariants.append(self._contract)

        _add_invariant_checks(cls=cls)

        return cls


def _collapse_invariants(bases: List[type], namespace: MutableMapping[str, Any]) -> None:
    """Collect invariants from the bases and merge them with the invariants in the namespace."""
    invariants = []  # type: List[_Contract]

    # Add invariants of the bases
    for base in bases:
        if hasattr(base, "__invariants__"):
            invariants.extend(getattr(base, "__invariants__"))

    # Add invariants in the current namespace
    if '__invariants__' in namespace:
        invariants.extend(namespace['__invariants__'])

    # Change the final invariants in the namespace
    if invariants:
        namespace["__invariants__"] = invariants


def _collapse_preconditions(base_preconditions: List[List[_Contract]], bases_have_func: bool,
                            preconditions: List[List[_Contract]], func: Callable[..., Any]) -> List[List[_Contract]]:
    """
    Collapse function preconditions with the preconditions collected from the base classes.

    :param base_preconditions: preconditions collected from the base classes (grouped by base class)
    :param bases_have_func: True if one of the base classes has the function
    :param preconditions: preconditions of the function (before the collapse)
    :param func: function whose preconditions we are collapsing
    :return: collapsed sequence of precondition groups
    """
    if not base_preconditions and bases_have_func and preconditions:
        raise TypeError(("The function {} can not weaken the preconditions because the bases specify "
                         "no preconditions at all. Hence this function must accept all possible input since "
                         "the preconditions are OR'ed and no precondition implies a dummy precondition which is always "
                         "fulfilled.").format(func.__qualname__))

    return base_preconditions + preconditions


def _collapse_snapshots(base_snapshots: List[_Snapshot], snapshots: List[_Snapshot]) -> List[_Snapshot]:
    """
    Collapse snapshots of pre-invocation values with the snapshots collected from the base classes.

    :param base_snapshots: snapshots collected from the base classes
    :param snapshots: snapshots of the function (before the collapse)
    :return: collapsed sequence of snapshots
    """
    seen_names = set()  # type: Set[str]
    collapsed = base_snapshots + snapshots

    for snap in collapsed:
        if snap.name in seen_names:
            raise ValueError("There are conflicting snapshots with the name: {!r}.\n\n"
                             "Please mind that the snapshots are inherited from the base classes. "
                             "Does one of the base classes defines a snapshot with the same name?".format(snap.name))

        seen_names.add(snap.name)

    return collapsed


def _collapse_postconditions(base_postconditions: List[_Contract], postconditions: List[_Contract]) -> List[_Contract]:
    """
    Collapse function postconditions with the postconditions collected from the base classes.

    :param base_postconditions: postconditions collected from the base classes
    :param postconditions: postconditions of the function (before the collapse)
    :return: collapsed sequence of postconditions
    """
    return base_postconditions + postconditions


def _decorate_namespace_function(bases: List[type], namespace: MutableMapping[str, Any], key: str) -> None:
    """Collect preconditions and postconditions from the bases and decorate the function at the ``key``."""
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals

    value = namespace[key]
    assert inspect.isfunction(value) or isinstance(value, (staticmethod, classmethod))

    # Determine the function to be decorated
    if inspect.isfunction(value):
        func = value
    elif isinstance(value, (staticmethod, classmethod)):
        func = value.__func__
    else:
        raise NotImplementedError("Unexpected value for a function: {}".format(value))

    # Collect preconditions and postconditions of the function
    preconditions = []  # type: List[List[_Contract]]
    snapshots = []  # type: List[_Snapshot]
    postconditions = []  # type: List[_Contract]

    contract_checker = _find_checker(func=func)
    if contract_checker is not None:
        preconditions = contract_checker.__preconditions__  # type: ignore
        snapshots = contract_checker.__postcondition_snapshots__  # type: ignore
        postconditions = contract_checker.__postconditions__  # type: ignore

    # Collect the preconditions and postconditions from bases.
    #
    # Preconditions and postconditions of __init__ of base classes are deliberately ignored (and not collapsed) since
    # initialization is an operation specific to the concrete class and does not relate to the class hierarchy.
    if key not in ['__init__']:
        base_preconditions = []  # type: List[List[_Contract]]
        base_snapshots = []  # type: List[_Snapshot]
        base_postconditions = []  # type: List[_Contract]

        bases_have_func = False
        for base in bases:
            if hasattr(base, key):
                bases_have_func = True

                # Check if there is a checker function in the base class
                base_func = getattr(base, key)
                base_contract_checker = _find_checker(func=base_func)

                # Ignore functions which don't have preconditions or postconditions
                if base_contract_checker is not None:
                    base_preconditions.extend(base_contract_checker.__preconditions__)  # type: ignore
                    base_snapshots.extend(base_contract_checker.__postcondition_snapshots__)  # type: ignore
                    base_postconditions.extend(base_contract_checker.__postconditions__)  # type: ignore

        # Collapse preconditions and postconditions from the bases with the the function's own ones
        preconditions = _collapse_preconditions(
            base_preconditions=base_preconditions,
            bases_have_func=bases_have_func,
            preconditions=preconditions,
            func=func)

        snapshots = _collapse_snapshots(base_snapshots=base_snapshots, snapshots=snapshots)

        postconditions = _collapse_postconditions(
            base_postconditions=base_postconditions, postconditions=postconditions)

    if preconditions or postconditions:
        if contract_checker is None:
            contract_checker = _decorate_with_checker(func=func)

            # Replace the function with the function decorated with contract checks
            if inspect.isfunction(value):
                namespace[key] = contract_checker
            elif isinstance(value, staticmethod):
                namespace[key] = staticmethod(contract_checker)

            elif isinstance(value, classmethod):
                namespace[key] = classmethod(contract_checker)

            else:
                raise NotImplementedError("Unexpected value for a function: {}".format(value))

        # Override the preconditions and postconditions
        contract_checker.__preconditions__ = preconditions  # type: ignore
        contract_checker.__postcondition_snapshots__ = snapshots  # type: ignore
        contract_checker.__postconditions__ = postconditions  # type: ignore


def _decorate_namespace_property(bases: List[type], namespace: MutableMapping[str, Any], key: str) -> None:
    """Collect contracts for all getters/setters/deleters corresponding to ``key`` and decorate them."""
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    value = namespace[key]
    assert isinstance(value, property)

    fget = value.fget  # type: Optional[Callable[..., Any]]
    fset = value.fset  # type: Optional[Callable[..., Any]]
    fdel = value.fdel  # type: Optional[Callable[..., Any]]

    for func in [value.fget, value.fset, value.fdel]:
        func = cast(Callable[..., Any], func)

        if func is None:
            continue

        # Collect the preconditions and postconditions from bases
        base_preconditions = []  # type: List[List[_Contract]]
        base_snapshots = []  # type: List[_Snapshot]
        base_postconditions = []  # type: List[_Contract]

        bases_have_func = False
        for base in bases:
            if hasattr(base, key):
                base_property = getattr(base, key)
                assert isinstance(base_property, property), \
                    "Expected base {} to have {} as property, but got: {}".format(base, key, base_property)

                if func == value.fget:
                    base_func = getattr(base, key).fget
                elif func == value.fset:
                    base_func = getattr(base, key).fset
                elif func == value.fdel:
                    base_func = getattr(base, key).fdel
                else:
                    raise NotImplementedError("Unhandled case: func neither value.fget, value.fset nor value.fdel")

                if base_func is None:
                    continue

                bases_have_func = True

                # Check if there is a checker function in the base class
                base_contract_checker = _find_checker(func=base_func)

                # Ignore functions which don't have preconditions or postconditions
                if base_contract_checker is not None:
                    base_preconditions.extend(base_contract_checker.__preconditions__)  # type: ignore
                    base_snapshots.extend(base_contract_checker.__postcondition_snapshots__)  # type: ignore
                    base_postconditions.extend(base_contract_checker.__postconditions__)  # type: ignore

        # Add preconditions and postconditions of the function
        preconditions = []  # type: List[List[_Contract]]
        snapshots = []  # type: List[_Snapshot]
        postconditions = []  # type: List[_Contract]

        contract_checker = _find_checker(func=func)
        if contract_checker is not None:
            preconditions = contract_checker.__preconditions__  # type: ignore
            snapshots = contract_checker.__postcondition_snapshots__
            postconditions = contract_checker.__postconditions__  # type: ignore

        preconditions = _collapse_preconditions(
            base_preconditions=base_preconditions,
            bases_have_func=bases_have_func,
            preconditions=preconditions,
            func=func)

        snapshots = _collapse_snapshots(base_snapshots=base_snapshots, snapshots=snapshots)

        postconditions = _collapse_postconditions(
            base_postconditions=base_postconditions, postconditions=postconditions)

        if preconditions or postconditions:
            if contract_checker is None:
                contract_checker = _decorate_with_checker(func=func)

                # Replace the function with the function decorated with contract checks
                if func == value.fget:
                    fget = contract_checker
                elif func == value.fset:
                    fset = contract_checker
                elif func == value.fdel:
                    fdel = contract_checker
                else:
                    raise NotImplementedError("Unhandled case: func neither fget, fset nor fdel")

            # Override the preconditions and postconditions
            contract_checker.__preconditions__ = preconditions  # type: ignore
            contract_checker.__postcondition_snapshots__ = snapshots  # type: ignore
            contract_checker.__postconditions__ = postconditions  # type: ignore

    if fget != value.fget or fset != value.fset or fdel != value.fdel:
        namespace[key] = property(fget=fget, fset=fset, fdel=fdel)


def _dbc_decorate_namespace(bases: List[type], namespace: MutableMapping[str, Any]) -> None:
    """
    Collect invariants, preconditions and postconditions from the bases and decorate all the methods.

    Instance methods are simply replaced with the decorated function/ Properties, class methods and static methods are
    overridden with new instances of ``property``, ``classmethod`` and ``staticmethod``, respectively.
    """
    _collapse_invariants(bases=bases, namespace=namespace)

    for key, value in namespace.items():
        if inspect.isfunction(value) or isinstance(value, (staticmethod, classmethod)):
            _decorate_namespace_function(bases=bases, namespace=namespace, key=key)

        elif isinstance(value, property):
            _decorate_namespace_property(bases=bases, namespace=namespace, key=key)

        else:
            # Ignore the value which is neither a function nor a property
            pass


class DBCMeta(abc.ABCMeta):
    """
    Define a meta class that allows inheritance of the contracts.

    The preconditions are weakned ("require else"), while postconditions ("ensure then") and invariants are
    strengthened according to the inheritance rules of the design-by-contract.
    """

    # We need to disable mcs check since ABCMeta doesn't follow the convention and calls the first argument ``mlcs``
    # instead of ``mcs``.
    # pylint: disable=bad-mcs-classmethod-argument

    if int(platform.python_version_tuple()[0]) < 3:
        raise NotImplementedError("Python versions below not supported, got: {}".format(platform.python_version()))

    if int(platform.python_version_tuple()[1]) <= 5:

        def __new__(mlcs, name, bases, namespace):  # pylint: disable=arguments-differ
            """Create a class with inherited preconditions, postconditions and invariants."""
            _dbc_decorate_namespace(bases, namespace)

            cls = super().__new__(mlcs, name, bases, namespace)

            if hasattr(cls, "__invariants__"):
                _add_invariant_checks(cls=cls)

            return cls
    else:

        def __new__(mlcs, name, bases, namespace, **kwargs):  # type: ignore  # pylint: disable=arguments-differ
            """Create a class with inherited preconditions, postconditions and invariants."""
            _dbc_decorate_namespace(bases, namespace)

            cls = super().__new__(mlcs, name, bases, namespace, **kwargs)

            if hasattr(cls, "__invariants__"):
                _add_invariant_checks(cls=cls)

            return cls


class DBC(metaclass=DBCMeta):
    """Provide a standard way to create a class which can inherit the contracts."""

    pass
