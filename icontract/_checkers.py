"""Provide functions to add/find contract checkers."""
import functools
import inspect
import threading
from typing import Callable, Any, Iterable, Optional, Tuple, List, Mapping, \
    MutableMapping, Dict

import icontract._represent
from icontract._globals import CallableT
from icontract._types import Contract, Snapshot
from icontract.errors import ViolationError

# pylint: disable=protected-access

# pylint does not play with typing.Mapping.
# pylint: disable=unsubscriptable-object


def _walk_decorator_stack(func: CallableT) -> Iterable['CallableT']:
    """
    Iterate through the stack of decorated functions until the original function.

    Assume that all decorators used functools.update_wrapper.
    """
    while hasattr(func, "__wrapped__"):
        yield func

        func = getattr(func, "__wrapped__")

    yield func


def find_checker(func: CallableT) -> Optional[CallableT]:
    """Iterate through the decorator stack till we find the contract checker."""
    contract_checker = None  # type: Optional[CallableT]
    for a_wrapper in _walk_decorator_stack(func):
        if hasattr(a_wrapper, "__preconditions__") or hasattr(a_wrapper, "__postconditions__"):
            contract_checker = a_wrapper

    return contract_checker


def kwargs_from_call(param_names: List[str], kwdefaults: Dict[str, Any], args: Tuple[Any, ...],
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

    # (Marko Ristin, 2020-12-01)
    # Insert _ARGS and _KWARGS preemptively even if they are not needed by any contract.
    # This makes the code logic much simpler since we do not explicitly check if a contract would
    # need them, though it might incur a subtle computational overhead
    # (*e.g.*, when the contracts do not need them or don't use any argument at all).
    # We need to have a concrete issue where profiling helps us determine if this is a real
    # bottleneck or not and not optimize for no real benefit.
    resolved_kwargs = {'_ARGS': args, '_KWARGS': kwargs}

    # Set the default argument values as condition parameters.
    for param_name, param_value in kwdefaults.items():
        resolved_kwargs[param_name] = param_value

    # Override the defaults with the values actually supplied to the function.
    for i, func_arg in enumerate(args):
        if i < len(param_names):
            resolved_kwargs[param_names[i]] = func_arg
        else:
            # Silently ignore call arguments that were not specified in the function.
            # This way we let the underlying decorated function raise the exception
            # instead of frankensteining the exception here.
            pass

    for key, val in kwargs.items():
        resolved_kwargs[key] = val

    return resolved_kwargs


def not_check(check: Any, contract: Contract) -> bool:
    """
    Negate the check value of a condition and capture missing boolyness (*e.g.*, when check is a numpy array).

    :param check: value of the evaluated condition
    :param contract: corresponding to the check
    :return: negated check
    :raise: ValueError if the check could not be negated
    """
    try:
        return not check
    except Exception as err:  # pylint: disable=broad-except
        msg_parts = []  # type: List[str]
        if contract.location is not None:
            msg_parts.append("{}:\n".format(contract.location))

        msg_parts.append('Failed to negate the evaluation of the condition.')

        raise ValueError(''.join(msg_parts)) from err


def select_condition_kwargs(contract: Contract, resolved_kwargs: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    Select the keyword arguments that are used by the contract.

    :param contract: contract to be verified
    :param resolved_kwargs:
        resolved keyword arguments of the call (including the default argument values of the decorated function)
    :return: a subset of resolved_kwargs
    """
    # Check that all arguments to the condition function have been set.
    missing_args = [arg_name for arg_name in contract.mandatory_args if arg_name not in resolved_kwargs]
    if missing_args:
        msg_parts = []  # type: List[str]
        if contract.location is not None:
            msg_parts.append("{}:\n".format(contract.location))

        msg_parts.append(
            ("The argument(s) of the precondition have not been set: {}. "
             "Does the original function define them? Did you supply them in the call?").format(missing_args))

        raise TypeError(''.join(msg_parts))

    condition_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items() if arg_name in contract.condition_arg_set
    }

    return condition_kwargs


def _assert_precondition(contract: Contract, resolved_kwargs: Mapping[str, Any]) -> None:
    """
    Assert that the contract holds as a precondition.

    :param contract: contract to be verified
    :param resolved_kwargs:
        resolved keyword arguments of the call (including the default argument values of the decorated function)
    :return:
    """
    condition_kwargs = select_condition_kwargs(contract=contract, resolved_kwargs=resolved_kwargs)

    check = contract.condition(**condition_kwargs)

    if not_check(check=check, contract=contract):
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            error_kwargs = {
                arg_name: value
                for arg_name, value in resolved_kwargs.items() if arg_name in contract.error_arg_set
            }

            missing_args = [arg_name for arg_name in contract.error_args if arg_name not in resolved_kwargs]
            if missing_args:
                msg_parts = []
                if contract.location is not None:
                    msg_parts.append("{}:\n".format(contract.location))

                msg_parts.append(
                    ("The argument(s) of the precondition error have not been set: {}. "
                     "Does the original function define them? Did you supply them in the call?").format(missing_args))

                raise TypeError(''.join(msg_parts))

            raise contract.error(**error_kwargs)

        else:
            msg = icontract._represent.generate_message(contract=contract, condition_kwargs=condition_kwargs)
            if contract.error is None:
                raise ViolationError(msg)
            elif isinstance(contract.error, type):
                raise contract.error(msg)


def _assert_invariant(contract: Contract, instance: Any) -> None:
    """Assert that the contract holds as a class invariant given the instance of the class."""
    if 'self' in contract.condition_arg_set:
        check = contract.condition(self=instance)
    else:
        check = contract.condition()

    if not_check(check=check, contract=contract):
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            if 'self' in contract.error_arg_set:
                raise contract.error(self=instance)
            else:
                raise contract.error()
        else:
            if 'self' in contract.condition_arg_set:
                msg = icontract._represent.generate_message(contract=contract, condition_kwargs={"self": instance})
            else:
                msg = icontract._represent.generate_message(contract=contract, condition_kwargs=dict())

            if contract.error is None:
                raise ViolationError(msg)
            elif isinstance(contract.error, type):
                raise contract.error(msg)
            else:
                raise NotImplementedError("Unhandled contract.error: {}".format(contract.error))


def _capture_snapshot(a_snapshot: Snapshot, resolved_kwargs: Mapping[str, Any]) -> Any:
    """
    Capture the snapshot from the keyword arguments resolved before the function call (including the default values).

    :param a_snapshot: snapshot to be captured
    :param resolved_kwargs: resolved keyword arguments (including the default values)
    :return: captured value
    """
    missing_args = [arg_name for arg_name in a_snapshot.args if arg_name not in resolved_kwargs]
    if missing_args:
        msg_parts = []  # type: List[str]
        if a_snapshot.location is not None:
            msg_parts.append("{}:\n".format(a_snapshot.location))

        msg_parts.append(
            ("The argument(s) of the snapshot have not been set: {}. "
             "Does the original function define them? Did you supply them in the call?").format(missing_args))

        raise TypeError(''.join(msg_parts))

    capture_kwargs = {
        arg_name: arg_value
        for arg_name, arg_value in resolved_kwargs.items() if arg_name in a_snapshot.arg_set
    }

    captured_value = a_snapshot.capture(**capture_kwargs)

    return captured_value


def _assert_postcondition(contract: Contract, resolved_kwargs: Mapping[str, Any]) -> None:
    """
    Assert that the contract holds as a postcondition.

    The arguments to the postcondition are given as ``resolved_kwargs`` which includes
    both argument values captured in snapshots and actual argument values and the result of a function.

    :param contract: contract to be verified
    :param resolved_kwargs:
        resolved keyword arguments (including the default values, ``result``,``OLD``
        ``_ARGS`` and ``_KWARGS``)
    :return:
    """
    assert 'result' in resolved_kwargs, \
        "Expected 'result' to be set in the resolved keyword arguments of a postcondition."

    # Check that all arguments to the condition function have been set.
    missing_args = [arg_name for arg_name in contract.mandatory_args if arg_name not in resolved_kwargs]
    if missing_args:
        msg_parts = []  # type: List[str]
        if contract.location is not None:
            msg_parts.append("{}:\n".format(contract.location))

        msg_parts.append(
            ("The argument(s) of the postcondition have not been set: {}. "
             "Does the original function define them? Did you supply them in the call?").format(missing_args))

        if 'OLD' in missing_args:
            msg_parts.append(' Did you decorate the function with a snapshot to capture OLD values?')

        raise TypeError(''.join(msg_parts))

    condition_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items() if arg_name in contract.condition_arg_set
    }

    check = contract.condition(**condition_kwargs)

    if not_check(check=check, contract=contract):
        if contract.error is not None and (inspect.ismethod(contract.error) or inspect.isfunction(contract.error)):
            assert contract.error_arg_set is not None, "Expected error_arg_set non-None if contract.error a function."
            assert contract.error_args is not None, "Expected error_args non-None if contract.error a function."

            error_kwargs = {
                arg_name: value
                for arg_name, value in resolved_kwargs.items() if arg_name in contract.error_arg_set
            }

            missing_args = [arg_name for arg_name in contract.error_args if arg_name not in resolved_kwargs]
            if missing_args:
                msg_parts = []
                if contract.location is not None:
                    msg_parts.append("{}:\n".format(contract.location))

                msg_parts.append(
                    ("The argument(s) of the postcondition error have not been set: {}. "
                     "Does the original function define them? Did you supply them in the call?").format(missing_args))

                raise TypeError(''.join(msg_parts))

            raise contract.error(**error_kwargs)

        else:
            msg = icontract._represent.generate_message(contract=contract, condition_kwargs=condition_kwargs)
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

    def __getattr__(self, item: str) -> Any:
        raise AttributeError("The snapshot with the name {!r} is not available in the OLD of a postcondition. "
                             "Have you decorated the function with a corresponding snapshot decorator?".format(item))

    def __repr__(self) -> str:
        return "a bunch of OLD values"


def resolve_kwdefaults(sign: inspect.Signature) -> Dict[str, Any]:
    """Resolve default values for the function arguments based on its signature."""
    kwdefaults = dict()  # type: Dict[str, Any]

    # Add to the defaults all the values that are needed by the contracts.
    for param in sign.parameters.values():
        if param.default != inspect.Parameter.empty:
            kwdefaults[param.name] = param.default

    return kwdefaults


# This flag is used to avoid recursively checking contracts for the same function or instance while
# contract checking is already in progress.
#
# The key refers to the id() of the function (preconditions and postconditions) or instance (invariants).
_IN_PROGRESS = threading.local()


def decorate_with_checker(func: CallableT) -> CallableT:
    """Decorate the function with a checker that verifies the preconditions and postconditions."""
    # pylint: disable=too-many-statements
    assert not hasattr(func, "__preconditions__"), \
        "Expected func to have no list of preconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postconditions__"), \
        "Expected func to have no list of postconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postcondition_snapshots__"), \
        "Expected func to have no list of postcondition snapshots (there should be only a single contract checker " \
        "per function)."

    sign = inspect.signature(func)
    if '_ARGS' in sign.parameters:
        raise ValueError(
            'The arguments of the function to be decorated with a contract checker include "_ARGS" which is '
            'a reserved placeholder for positional arguments in the condition.')

    if '_KWARGS' in sign.parameters:
        raise ValueError(
            'The arguments of the function to be decorated with a contract checker include "_KWARGS" which is '
            'a reserved placeholder for keyword arguments in the condition.')

    param_names = list(sign.parameters.keys())

    # Determine the default argument values
    kwdefaults = resolve_kwdefaults(sign=sign)

    id_func = str(id(func))

    def wrapper(*args, **kwargs):  # type: ignore
        """Wrap func by checking the preconditions and postconditions."""
        # pylint: disable=too-many-branches

        if '_ARGS' in kwargs:
            raise TypeError('The arguments of the function call include "_ARGS" which is '
                            'a placeholder for positional arguments in a condition.')

        if '_KWARGS' in kwargs:
            raise TypeError('The arguments of the function call include "_KWARGS" which is '
                            'a placeholder for keyword arguments in a condition.')

        # Use try-finally instead of ExitStack for performance.
        try:
            # If the wrapper is already checking the contracts for the wrapped function, avoid a recursive loop
            # by skipping any subsequent contract checks for the same function.
            if hasattr(_IN_PROGRESS, id_func):
                return func(*args, **kwargs)

            setattr(_IN_PROGRESS, id_func, True)

            preconditions = getattr(wrapper, "__preconditions__")  # type: List[List[Contract]]
            snapshots = getattr(wrapper, "__postcondition_snapshots__")  # type: List[Snapshot]
            postconditions = getattr(wrapper, "__postconditions__")  # type: List[Contract]

            resolved_kwargs = kwargs_from_call(param_names=param_names, kwdefaults=kwdefaults, args=args, kwargs=kwargs)

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
            if postconditions and snapshots:
                old_as_mapping = dict()  # type: MutableMapping[str, Any]
                for snap in snapshots:
                    # This assert is just a last defense.
                    # Conflicting snapshot names should have been caught before, either during the decoration or
                    # in the meta-class.
                    assert snap.name not in old_as_mapping, "Snapshots with the conflicting name: {}"
                    old_as_mapping[snap.name] = _capture_snapshot(a_snapshot=snap, resolved_kwargs=resolved_kwargs)

                resolved_kwargs['OLD'] = _Old(mapping=old_as_mapping)

            # Ideally, we would catch any exception here and strip the checkers from the traceback.
            # Unfortunately, this can not be done in Python 3, see
            # https://stackoverflow.com/questions/44813333/how-can-i-elide-a-function-wrapper-from-the-traceback-in-python-3
            result = func(*args, **kwargs)

            if postconditions:
                resolved_kwargs['result'] = result

                # Assert the postconditions as a conjunction
                for contract in postconditions:
                    _assert_postcondition(contract=contract, resolved_kwargs=resolved_kwargs)

            return result
        finally:
            if hasattr(_IN_PROGRESS, id_func):
                delattr(_IN_PROGRESS, id_func)

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

    return wrapper  # type: ignore


def _find_self(param_names: List[str], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Any:
    """Find the instance of ``self`` in the arguments."""
    instance_i = None
    try:
        instance_i = param_names.index("self")
    except ValueError:
        pass

    if instance_i is not None:
        return args[instance_i]

    return kwargs["self"]


def _decorate_new_with_invariants(new_func: CallableT) -> CallableT:
    """
    Decorate the ``__new__`` of a class s.t. the invariants are checked on the result.

    This is necessary for optimized classes such as ``namedtuple`` which use ``object.__init__``
    as constructor and do not expect a wrapping around the constructor.
    """
    if _already_decorated_with_invariants(func=new_func):
        return new_func

    def wrapper(*args, **kwargs):  # type: ignore
        """Pass the arguments to __new__ and check invariants on the result."""
        instance = new_func(*args, **kwargs)

        for contract in instance.__class__.__invariants__:
            _assert_invariant(contract=contract, instance=instance)

        return instance

    functools.update_wrapper(wrapper=wrapper, wrapped=new_func)

    setattr(wrapper, "__is_invariant_check__", True)

    return wrapper  # type: ignore


def _decorate_with_invariants(func: CallableT, is_init: bool) -> CallableT:
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

        def wrapper(*args, **kwargs):  # type: ignore
            """Wrap __init__ method of a class by checking the invariants *after* the invocation."""
            try:
                instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)
            except KeyError as err:
                raise KeyError(("The parameter 'self' could not be found in the call to function {!r}: "
                                "the param names were {!r}, the args were {!r} and kwargs were {!r}").format(
                                    func, param_names, args, kwargs)) from err

            # We need to disable the invariants check during the constructor.
            id_instance = str(id(instance))
            setattr(_IN_PROGRESS, id_instance, True)

            # ExitStack is not used here due to performance.
            try:
                result = func(*args, **kwargs)

                for contract in instance.__class__.__invariants__:
                    _assert_invariant(contract=contract, instance=instance)

                return result
            finally:
                if hasattr(_IN_PROGRESS, id_instance):
                    delattr(_IN_PROGRESS, id_instance)

    else:

        def wrapper(*args, **kwargs):  # type: ignore
            """Wrap a function of a class by checking the invariants *before* and *after* the invocation."""
            try:
                instance = _find_self(param_names=param_names, args=args, kwargs=kwargs)
            except KeyError as err:
                raise KeyError(("The parameter 'self' could not be found in the call to function {!r}: "
                                "the param names were {!r}, the args were {!r} and kwargs were {!r}").format(
                                    func, param_names, args, kwargs)) from err

            # The following dunder indicates whether another invariant is currently being checked. If so,
            # we need to suspend any further invariant check to avoid endless recursion.
            id_instance = str(id(instance))
            if not hasattr(_IN_PROGRESS, id_instance):
                setattr(_IN_PROGRESS, id_instance, True)
            else:
                # Do not check any invariants to avoid endless recursion.
                return func(*args, **kwargs)

            # ExitStack is not used here due to performance.
            try:
                for contract in instance.__class__.__invariants__:
                    _assert_invariant(contract=contract, instance=instance)

                result = func(*args, **kwargs)

                for contract in instance.__class__.__invariants__:
                    _assert_invariant(contract=contract, instance=instance)

                return result
            finally:
                if hasattr(_IN_PROGRESS, id_instance):
                    delattr(_IN_PROGRESS, id_instance)

    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    setattr(wrapper, "__is_invariant_check__", True)

    return wrapper  # type: ignore


class _DummyClass:
    """Represent a dummy class so that we can infer the type of the slot wrapper."""


_SLOT_WRAPPER_TYPE = type(_DummyClass.__init__)  # pylint: disable=invalid-name


def _already_decorated_with_invariants(func: CallableT) -> bool:
    """Check if the function has been already decorated with an invariant check by going through its decorator stack."""
    already_decorated = False
    for a_decorator in _walk_decorator_stack(func=func):
        if getattr(a_decorator, "__is_invariant_check__", False):
            already_decorated = True
            break

    return already_decorated


def add_invariant_checks(cls: type) -> None:
    """Decorate each of the class functions with invariant checks if not already decorated."""
    # pylint: disable=too-many-branches

    # Candidates for the decoration as list of (name, dir() value)
    init_name_func = None  # type: Optional[Tuple[str, Callable[..., None]]]
    names_funcs = []  # type: List[Tuple[str, Callable[..., None]]]
    names_properties = []  # type: List[Tuple[str, property]]

    # Filter out entries in the directory which are certainly not candidates for decoration.
    for name, value in [(name, getattr(cls, name)) for name in dir(cls)]:
        # __new__ is a special class method (though not marked properly with @classmethod!).
        # We need to ignore __repr__ to prevent endless loops when generating error messages.
        # __getattribute__, __setattr__ and __delattr__ are too invasive and alter the state of the instance.
        # Hence we don't consider them "public".
        if name in ["__new__", "__repr__", "__getattribute__", "__setattr__", "__delattr__"]:
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

        # We have to distinguish this special case which is used by named
        # tuples and possibly other optimized data structures.
        # In those cases, we have to wrap __new__ instead of __init__.
        if func == object.__init__ and hasattr(cls, "__new__"):
            new_func = getattr(cls, "__new__")
            setattr(cls, "__new__", _decorate_new_with_invariants(new_func))
        else:
            wrapper = _decorate_with_invariants(func=func, is_init=True)
            setattr(cls, name, wrapper)

    for name, func in names_funcs:
        wrapper = _decorate_with_invariants(func=func, is_init=False)
        setattr(cls, name, wrapper)

    for name, prop in names_properties:
        new_prop = property(
            fget=_decorate_with_invariants(func=prop.fget, is_init=False) if prop.fget else None,  # type: ignore
            fset=_decorate_with_invariants(func=prop.fset, is_init=False) if prop.fset else None,  # type: ignore
            fdel=_decorate_with_invariants(func=prop.fdel, is_init=False) if prop.fdel else None,  # type: ignore
            doc=prop.__doc__)
        setattr(cls, name, new_prop)
