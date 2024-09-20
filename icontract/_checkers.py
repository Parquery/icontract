"""Provide functions to add/find contract checkers."""
import contextvars
import functools
import inspect
from typing import (
    Callable,
    Any,
    Iterable,
    Optional,
    Tuple,
    List,
    Mapping,
    MutableMapping,
    Dict,
    cast,
    Set,
)

import icontract._represent
from icontract._globals import CallableT, ClassT
from icontract._types import Contract, Snapshot, InvariantCheckEvent
from icontract.errors import ViolationError


# pylint does not play with typing.Mapping.
# pylint: disable=unsubscriptable-object
# pylint: disable=raising-bad-type


def _walk_decorator_stack(func: CallableT) -> Iterable["CallableT"]:
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
        if hasattr(a_wrapper, "__preconditions__") or hasattr(
            a_wrapper, "__postconditions__"
        ):
            contract_checker = a_wrapper

    return contract_checker


def kwargs_from_call(
    param_names: List[str],
    kwdefaults: Dict[str, Any],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> MutableMapping[str, Any]:
    """
    Inspect the input values received at the wrapper for the actual function call.

    :param param_names: parameter (*i.e.* argument) names of the original (decorated) function
    :param kwdefaults: default argument values of the original function
    :param args: arguments supplied to the call
    :param kwargs: keyword arguments supplied to the call
    :return: resolved arguments as they would be passed to the function
    """
    # (Marko Ristin, 2020-12-01)
    # Insert _ARGS and _KWARGS preemptively even if they are not needed by any contract.
    # This makes the code logic much simpler since we do not explicitly check if a contract would
    # need them, though it might incur a subtle computational overhead
    # (*e.g.*, when the contracts do not need them or don't use any argument at all).
    # We need to have a concrete issue where profiling helps us determine if this is a real
    # bottleneck or not and not optimize for no real benefit.
    resolved_kwargs = {"_ARGS": args, "_KWARGS": kwargs}

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

            # It seems that this line can not be covered,
            # see https://github.com/nedbat/coveragepy/issues/1041.
            # The branch was covered manually in ``tests.test_checkers``.
            pass  # pragma: no cover

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

        msg_parts.append("Failed to negate the evaluation of the condition.")

        raise ValueError("".join(msg_parts)) from err


def select_condition_kwargs(
    contract: Contract, resolved_kwargs: Mapping[str, Any]
) -> Mapping[str, Any]:
    """
    Select the keyword arguments that are used by the contract.

    :param contract: contract to be verified
    :param resolved_kwargs:
        resolved keyword arguments of the call (including the default argument values of the decorated function)
    :return: a subset of resolved_kwargs
    """
    # Check that all arguments to the condition function have been set.
    missing_args = [
        arg_name
        for arg_name in contract.mandatory_args
        if arg_name not in resolved_kwargs
    ]
    if missing_args:
        msg_parts = []  # type: List[str]
        if contract.location is not None:
            msg_parts.append("{}:\n".format(contract.location))

        msg_parts.append(
            (
                "The argument(s) of the contract condition have not been set: {}. "
                "Does the original function define them? Did you supply them in the call?"
            ).format(missing_args)
        )

        if "OLD" in missing_args:
            msg_parts.append(
                " Did you decorate the function with a snapshot to capture OLD values?"
            )

        raise TypeError("".join(msg_parts))

    condition_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items()
        if arg_name in contract.condition_arg_set
    }

    return condition_kwargs


def _assert_no_invalid_kwargs(kwargs: Any) -> Optional[TypeError]:
    """Check that kwargs of a function contain no unexpected arguments."""
    if "_ARGS" in kwargs:
        return TypeError(
            'The arguments of the function call include "_ARGS" which is '
            "a placeholder for positional arguments in a condition."
        )

    if "_KWARGS" in kwargs:
        return TypeError(
            'The arguments of the function call include "_KWARGS" which is '
            "a placeholder for keyword arguments in a condition."
        )

    return None


def _unpack_pre_snap_posts(
    wrapper: CallableT,
) -> Tuple[List[List[Contract]], List[Snapshot], List[Contract]]:
    """Retrieve the preconditions, snapshots and postconditions defined for the given wrapper checker."""
    preconditions = getattr(wrapper, "__preconditions__")  # type: List[List[Contract]]
    snapshots = getattr(wrapper, "__postcondition_snapshots__")  # type: List[Snapshot]
    postconditions = getattr(wrapper, "__postconditions__")  # type: List[Contract]

    return preconditions, snapshots, postconditions


def _assert_resolved_kwargs_valid(
    postconditions: List[Contract], resolved_kwargs: Mapping[str, Any]
) -> Optional[TypeError]:
    """Check that the resolved kwargs of a decorated function are valid."""
    if postconditions:
        if "result" in resolved_kwargs:
            return TypeError(
                "Unexpected argument 'result' in a function decorated with postconditions."
            )

        if "OLD" in resolved_kwargs:
            return TypeError(
                "Unexpected argument 'OLD' in a function decorated with postconditions."
            )

    return None


def _create_violation_error(
    contract: Contract, resolved_kwargs: Mapping[str, Any]
) -> BaseException:
    """Create the violation error based on the violated contract."""
    exception = None  # type: Optional[BaseException]

    if contract.error is None:
        try:
            msg = icontract._represent.generate_message(
                contract=contract, resolved_kwargs=resolved_kwargs
            )
        except Exception as err:
            parts = ["Failed to recompute the values of the contract condition:\n"]
            if contract.location is not None:
                parts.append("{}:\n".format(contract.location))

            if contract.description is not None:
                parts.append("{}: ".format(contract.description))

            parts.append(
                icontract._represent.represent_condition(condition=contract.condition)
            )

            raise RuntimeError("".join(parts)) from err

        exception = ViolationError(msg)
    elif inspect.ismethod(contract.error) or inspect.isfunction(contract.error):
        assert (
            contract.error_arg_set is not None
        ), "Expected error_arg_set non-None if contract.error a function."
        assert (
            contract.error_args is not None
        ), "Expected error_args non-None if contract.error a function."

        error_kwargs = select_error_kwargs(
            contract=contract, resolved_kwargs=resolved_kwargs
        )

        exception = cast(BaseException, contract.error(**error_kwargs))

        if not isinstance(exception, BaseException):
            raise TypeError(
                "The exception returned by the contract's error {} does not inherit from BaseException.".format(
                    contract.error
                )
            )
    elif isinstance(contract.error, type):
        if not issubclass(contract.error, BaseException):
            raise TypeError(
                "The exception class supplied in the contract's error {} is not a subclass of BaseException.".format(
                    contract.error
                )
            )

        msg = icontract._represent.generate_message(
            contract=contract, resolved_kwargs=resolved_kwargs
        )
        exception = contract.error(msg)
    elif isinstance(contract.error, BaseException):
        exception = contract.error
    else:
        raise NotImplementedError(
            (
                "icontract does not know how to handle the error of type {} "
                "(expected a function, a subclass of BaseException or an instance of BaseException)"
            ).format(type(contract.error))
        )

    assert exception is not None
    return exception


async def _assert_preconditions_async(
    preconditions: List[List[Contract]], resolved_kwargs: Mapping[str, Any]
) -> Optional[BaseException]:
    """Assert that the preconditions of an async function hold."""
    exception = None  # type: Optional[BaseException]

    # Assert the preconditions in groups. This is necessary to implement "require else" logic when a class
    # weakens the preconditions of its base class.

    for group in preconditions:
        exception = None

        for contract in group:
            assert (
                exception is None
            ), "No exception as long as pre-condition group is satisfiable."

            condition_kwargs = select_condition_kwargs(
                contract=contract, resolved_kwargs=resolved_kwargs
            )

            if inspect.iscoroutinefunction(contract.condition):
                check = await contract.condition(**condition_kwargs)
            else:
                check_or_coroutine = contract.condition(**condition_kwargs)
                if inspect.iscoroutine(check_or_coroutine):
                    check = await check_or_coroutine
                else:
                    check = check_or_coroutine

            if not_check(check=check, contract=contract):
                exception = _create_violation_error(
                    contract=contract, resolved_kwargs=resolved_kwargs
                )
                break

        # The group of preconditions was satisfied, no need to check the other groups.
        if exception is None:
            break

    return exception


def _assert_preconditions(
    preconditions: List[List[Contract]],
    resolved_kwargs: Mapping[str, Any],
    func: CallableT,
) -> Optional[BaseException]:
    """Assert that the preconditions of a sync function hold."""
    exception = None  # type: Optional[BaseException]

    # Assert the preconditions in groups. This is necessary to implement "require else" logic when a class
    # weakens the preconditions of its base class.

    for group in preconditions:
        exception = None

        for contract in group:
            assert (
                exception is None
            ), "No exception as long as pre-condition group is satisfiable."

            condition_kwargs = select_condition_kwargs(
                contract=contract, resolved_kwargs=resolved_kwargs
            )

            if inspect.iscoroutinefunction(contract.condition):
                raise ValueError(
                    "Unexpected coroutine (async) condition {} for a sync function {}.".format(
                        contract.condition, func
                    )
                )

            check = contract.condition(**condition_kwargs)

            if inspect.iscoroutine(check):
                raise ValueError(
                    "Unexpected coroutine resulting from the condition {} for a sync function {}.".format(
                        contract.condition, func
                    )
                )

            if not_check(check=check, contract=contract):
                exception = _create_violation_error(
                    contract=contract, resolved_kwargs=resolved_kwargs
                )
                break

        # The group of preconditions was satisfied, no need to check the other groups.
        if exception is None:
            break

    return exception


async def _capture_old_async(
    snapshots: List[Snapshot], resolved_kwargs: Mapping[str, Any]
) -> "Old":
    """Capture all snapshots of an async function and return the captured values bundled in an ``Old``."""
    old_as_mapping = dict()  # type: MutableMapping[str, Any]
    for snap in snapshots:
        # This assert is just a last defense.
        # Conflicting snapshot names should have been caught before, either during the decoration or
        # in the meta-class.
        assert (
            snap.name not in old_as_mapping
        ), "Snapshots with the conflicting name: {}"

        capture_kwargs = select_capture_kwargs(
            a_snapshot=snap, resolved_kwargs=resolved_kwargs
        )

        if inspect.iscoroutinefunction(snap.capture):
            old_as_mapping[snap.name] = await snap.capture(**capture_kwargs)
        else:
            captured_or_coroutine = snap.capture(**capture_kwargs)
            if inspect.iscoroutine(captured_or_coroutine):
                captured = await captured_or_coroutine
            else:
                captured = captured_or_coroutine

            old_as_mapping[snap.name] = captured

    return Old(mapping=old_as_mapping)


def _capture_old(
    snapshots: List[Snapshot], resolved_kwargs: Mapping[str, Any], func: CallableT
) -> "Old":
    """Capture all snapshots of a sync function and return the captured values bundled in an ``Old``."""
    old_as_mapping = dict()  # type: MutableMapping[str, Any]
    for snap in snapshots:
        # This assert is just a last defense.
        # Conflicting snapshot names should have been caught before, either during the decoration or
        # in the meta-class.
        assert (
            snap.name not in old_as_mapping
        ), "Snapshots with the conflicting name: {}"

        if inspect.iscoroutinefunction(snap.capture):
            raise ValueError(
                "Unexpected coroutine (async) snapshot capture {} for a sync function {}.".format(
                    snap.capture, func
                )
            )

        capture_kwargs = select_capture_kwargs(
            a_snapshot=snap, resolved_kwargs=resolved_kwargs
        )

        captured = snap.capture(**capture_kwargs)
        if inspect.iscoroutine(captured):
            raise ValueError(
                (
                    "Unexpected coroutine resulting from the snapshot capture {} "
                    "of a sync function {}."
                ).format(snap.capture, func)
            )

        old_as_mapping[snap.name] = captured

    return Old(mapping=old_as_mapping)


async def _assert_postconditions_async(
    postconditions: List[Contract], resolved_kwargs: Mapping[str, Any]
) -> Optional[BaseException]:
    """Assert that the postconditions of an async function hold."""
    assert (
        "result" in resolved_kwargs
    ), "Expected 'result' to be already set in resolved kwargs before calling this function."

    for contract in postconditions:
        condition_kwargs = select_condition_kwargs(
            contract=contract, resolved_kwargs=resolved_kwargs
        )

        if inspect.iscoroutinefunction(contract.condition):
            check = await contract.condition(**condition_kwargs)
        else:
            check_or_coroutine = contract.condition(**condition_kwargs)
            if inspect.iscoroutine(check_or_coroutine):
                check = await check_or_coroutine
            else:
                check = check_or_coroutine

        if not_check(check=check, contract=contract):
            exception = _create_violation_error(
                contract=contract, resolved_kwargs=resolved_kwargs
            )

            return exception

    return None


def _assert_postconditions(
    postconditions: List[Contract], resolved_kwargs: Mapping[str, Any], func: CallableT
) -> Optional[BaseException]:
    """Assert that the postconditions of a sync function hold."""
    assert (
        "result" in resolved_kwargs
    ), "Expected 'result' to be already set in resolved kwargs before calling this function."

    for contract in postconditions:
        if inspect.iscoroutinefunction(contract.condition):
            raise ValueError(
                "Unexpected coroutine (async) condition {} for a sync function {}.".format(
                    contract.condition, func
                )
            )

        condition_kwargs = select_condition_kwargs(
            contract=contract, resolved_kwargs=resolved_kwargs
        )

        check = contract.condition(**condition_kwargs)

        if inspect.iscoroutine(check):
            raise ValueError(
                "Unexpected coroutine resulting from the condition {} for a sync function {}.".format(
                    contract.condition, func
                )
            )

        if not_check(check=check, contract=contract):
            exception = _create_violation_error(
                contract=contract, resolved_kwargs=resolved_kwargs
            )

            return exception

    return None


def _assert_invariant(contract: Contract, instance: Any) -> None:
    """Assert that the contract holds as a class invariant given the instance of the class."""
    if "self" in contract.condition_arg_set:
        check = contract.condition(self=instance)
    else:
        check = contract.condition()

    if not_check(check=check, contract=contract):
        raise _create_violation_error(
            contract=contract, resolved_kwargs={"self": instance}
        )


def select_capture_kwargs(
    a_snapshot: Snapshot, resolved_kwargs: Mapping[str, Any]
) -> Mapping[str, Any]:
    """
    Select the keyword arguments that are used by the snapshot capture.

    :param a_snapshot: snapshot to be captured
    :param resolved_kwargs: resolved keyword arguments (including the default values)
    :return: a subset of resolved_kwargs
    """
    missing_args = [
        arg_name for arg_name in a_snapshot.args if arg_name not in resolved_kwargs
    ]
    if missing_args:
        msg_parts = []
        if a_snapshot.location is not None:
            msg_parts.append("{}:\n".format(a_snapshot.location))

        msg_parts.append(
            (
                "The argument(s) of the snapshot have not been set: {}. "
                "Does the original function define them? Did you supply them in the call?"
            ).format(missing_args)
        )

        raise TypeError("".join(msg_parts))

    return {
        arg_name: arg_value
        for arg_name, arg_value in resolved_kwargs.items()
        if arg_name in a_snapshot.arg_set
    }


def select_error_kwargs(
    contract: Contract, resolved_kwargs: Mapping[str, Any]
) -> Mapping[str, Any]:
    """
    Select the keyword arguments that are used by the error creator of the contract.

    :param contract: contract that was violated and for which we want to generate an error
    :param resolved_kwargs: resolved keyword arguments (including the default values)
    :return: a subset of resolved_kwargs
    """
    assert contract.error_arg_set is not None
    assert contract.error_args is not None

    error_kwargs = {
        arg_name: value
        for arg_name, value in resolved_kwargs.items()
        if arg_name in contract.error_arg_set
    }

    missing_args = [
        arg_name for arg_name in contract.error_args if arg_name not in resolved_kwargs
    ]
    if missing_args:
        msg_parts = []  # type: List[str]
        if contract.location is not None:
            msg_parts.append("{}:\n".format(contract.location))

        msg_parts.append(
            (
                "The argument(s) of the contract error have not been set: {}. "
                "Does the original function define them? Did you supply them in the call?"
            ).format(missing_args)
        )

        raise TypeError("".join(msg_parts))

    return error_kwargs


class Old:
    """
    Represent argument values before the function invocation.

    Recipe taken from http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/
    """

    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """Update the ``__dict__`` with the given mapping."""
        self.__dict__.update(mapping)

    def __getattr__(self, item: str) -> Any:
        """Raise an error as this ``item`` should not be in the ``__dict__``."""
        raise AttributeError(
            "The snapshot with the name {!r} is not available in the OLD of a postcondition. "
            "Have you decorated the function with a corresponding snapshot decorator?".format(
                item
            )
        )

    def __repr__(self) -> str:
        """Represent the old values with a string literal as user is unaware of the class."""
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
_IN_PROGRESS = contextvars.ContextVar(
    "_IN_PROGRESS", default=None
)  # type: contextvars.ContextVar[Optional[Set[int]]]


def decorate_with_checker(func: CallableT) -> CallableT:
    """Decorate the function with a checker that verifies the preconditions and postconditions."""
    assert not hasattr(
        func, "__preconditions__"
    ), "Expected func to have no list of preconditions (there should be only a single contract checker per function)."

    assert not hasattr(
        func, "__postconditions__"
    ), "Expected func to have no list of postconditions (there should be only a single contract checker per function)."

    assert not hasattr(func, "__postcondition_snapshots__"), (
        "Expected func to have no list of postcondition snapshots (there should be only a single contract checker "
        "per function)."
    )

    sign = inspect.signature(func)
    if "_ARGS" in sign.parameters:
        raise TypeError(
            'The arguments of the function to be decorated with a contract checker include "_ARGS" which is '
            "a reserved placeholder for positional arguments in the condition."
        )

    if "_KWARGS" in sign.parameters:
        raise TypeError(
            'The arguments of the function to be decorated with a contract checker include "_KWARGS" which is '
            "a reserved placeholder for keyword arguments in the condition."
        )

    param_names = list(sign.parameters.keys())

    # Determine the default argument values
    kwdefaults = resolve_kwdefaults(sign=sign)

    id_func = id(func)

    # (mristin, 2021-02-16)
    # Admittedly, this branching on sync/async is absolutely monstrous.
    # However, I couldn't find out an easier way to refactor the code so that it supports async.
    # Python expects us to explicitly colour functions as sync/async so we can not just put in an if-statement and
    # introduce an "await".
    #
    # The two wrappers need to be manually maintained in parallel.
    # Whenever you make a change, please inspect manually that both sync and async code exercises equivalent behavior.
    # For example, copy/paste the two blocks of code in separate files and perform a diff.

    if inspect.iscoroutinefunction(func):

        async def wrapper(*args, **kwargs):  # type: ignore
            """Wrap func by checking the preconditions and postconditions."""
            kwargs_error = _assert_no_invalid_kwargs(kwargs)
            if kwargs_error:
                raise kwargs_error

            # We need to create a new in-progress set if it is None as the ``ContextVar`` does not accept
            # a factory function for the default argument. If we didn't do this, and simply set an empty
            # set as the default, ``ContextVar`` would always point to the same set by copying the default
            # by reference.
            in_progress = _IN_PROGRESS.get()
            if in_progress is None:
                in_progress = set()
                _IN_PROGRESS.set(in_progress)

            # Use try-finally instead of ExitStack for performance.
            try:
                # If the wrapper is already checking the contracts for the wrapped function, avoid a recursive loop
                # by skipping any subsequent contract checks for the same function.
                if id_func in in_progress:
                    return await func(*args, **kwargs)

                in_progress.add(id_func)

                (preconditions, snapshots, postconditions) = _unpack_pre_snap_posts(
                    wrapper
                )

                resolved_kwargs = kwargs_from_call(
                    param_names=param_names,
                    kwdefaults=kwdefaults,
                    args=args,
                    kwargs=kwargs,
                )

                type_error = _assert_resolved_kwargs_valid(
                    postconditions, resolved_kwargs
                )
                if type_error:
                    raise type_error

                violation_error = await _assert_preconditions_async(
                    preconditions=preconditions, resolved_kwargs=resolved_kwargs
                )
                if violation_error:
                    raise violation_error

                # Capture the snapshots
                if postconditions and snapshots:
                    resolved_kwargs["OLD"] = await _capture_old_async(
                        snapshots=snapshots, resolved_kwargs=resolved_kwargs
                    )

                # Ideally, we would catch any exception here and strip the checkers from the traceback.
                # Unfortunately, this can not be done in Python 3, see
                # https://stackoverflow.com/questions/44813333/how-can-i-elide-a-function-wrapper-from-the-traceback-in-python-3
                result = await func(*args, **kwargs)

                if postconditions:
                    resolved_kwargs["result"] = result

                    violation_error = await _assert_postconditions_async(
                        postconditions=postconditions, resolved_kwargs=resolved_kwargs
                    )
                    if violation_error:
                        raise violation_error

                return result
            finally:
                in_progress.discard(id_func)

    else:

        def wrapper(*args, **kwargs):  # type: ignore
            """Wrap func by checking the preconditions and postconditions."""
            kwargs_error = _assert_no_invalid_kwargs(kwargs)
            if kwargs_error:
                raise kwargs_error

            # We need to create a new in-progress set if it is None as the ``ContextVar`` does not accept
            # a factory function for the default argument. If we didn't do this, and simply set an empty
            # set as the default, ``ContextVar`` would always point to the same set by copying the default
            # by reference.
            in_progress = _IN_PROGRESS.get()
            if in_progress is None:
                in_progress = set()
                _IN_PROGRESS.set(in_progress)

            # Use try-finally instead of ExitStack for performance.
            try:
                # If the wrapper is already checking the contracts for the wrapped function, avoid a recursive loop
                # by skipping any subsequent contract checks for the same function.
                if id_func in in_progress:
                    return func(*args, **kwargs)

                in_progress.add(id_func)

                (preconditions, snapshots, postconditions) = _unpack_pre_snap_posts(
                    wrapper
                )

                resolved_kwargs = kwargs_from_call(
                    param_names=param_names,
                    kwdefaults=kwdefaults,
                    args=args,
                    kwargs=kwargs,
                )

                type_error = _assert_resolved_kwargs_valid(
                    postconditions=postconditions, resolved_kwargs=resolved_kwargs
                )
                if type_error:
                    raise type_error

                violation_error = _assert_preconditions(
                    preconditions=preconditions,
                    resolved_kwargs=resolved_kwargs,
                    func=func,
                )
                if violation_error:
                    raise violation_error

                # Capture the snapshots
                if postconditions and snapshots:
                    resolved_kwargs["OLD"] = _capture_old(
                        snapshots=snapshots, resolved_kwargs=resolved_kwargs, func=func
                    )

                # Ideally, we would catch any exception here and strip the checkers from the traceback.
                # Unfortunately, this can not be done in Python 3, see
                # https://stackoverflow.com/questions/44813333/how-can-i-elide-a-function-wrapper-from-the-traceback-in-python-3
                result = func(*args, **kwargs)

                if postconditions:
                    resolved_kwargs["result"] = result

                    violation_error = _assert_postconditions(
                        postconditions=postconditions,
                        resolved_kwargs=resolved_kwargs,
                        func=func,
                    )
                    if violation_error:
                        raise violation_error

                return result
            finally:
                in_progress.discard(id_func)

    # Copy __doc__ and other properties so that doctests can run
    functools.update_wrapper(wrapper=wrapper, wrapped=func)

    assert not hasattr(
        wrapper, "__preconditions__"
    ), "Expected no preconditions set on a pristine contract checker."
    assert not hasattr(
        wrapper, "__postcondition_snapshots__"
    ), "Expected no postcondition snapshots set on a pristine contract checker."
    assert not hasattr(
        wrapper, "__postconditions__"
    ), "Expected no postconditions set on a pristine contract checker."

    # Precondition is a list of condition groups (i.e. disjunctive normal form):
    # each group consists of AND'ed preconditions, while the groups are OR'ed.
    #
    # This is necessary in order to implement "require else" logic when a class weakens the preconditions of
    # its base class.
    setattr(wrapper, "__preconditions__", [])
    setattr(wrapper, "__postcondition_snapshots__", [])
    setattr(wrapper, "__postconditions__", [])

    return wrapper  # type: ignore


def add_precondition_to_checker(checker: CallableT, contract: Contract) -> None:
    """
    Add the precondition to the function's checker.

    Use :func:`find_checker` to find the checker.
    If it returns ``None``, decorate it with the checker first using :func:`decorate_with_checker`.
    """
    # Add the precondition to the list of preconditions stored at the checker
    assert hasattr(checker, "__preconditions__")
    preconditions = getattr(checker, "__preconditions__")
    assert isinstance(preconditions, list)
    assert len(preconditions) <= 1, (
        "At most a single group of preconditions expected when wrapping with a contract checker. "
        "The preconditions are merged only in the DBC metaclass. "
        "The current number of precondition groups: {}"
    ).format(len(preconditions))

    if len(preconditions) == 0:
        # Create the first group if there is no group so far, i.e. this is the first decorator.
        preconditions.append([])

    preconditions[0].append(contract)


def add_snapshot_to_checker(checker: CallableT, snapshot: Snapshot) -> None:
    """
    Add the snapshot to the function's checker.

    Use :func:`find_checker` to find the checker.
    If it returns ``None``, decorate it with the checker first using :func:`decorate_with_checker`.
    """
    # Add the snapshot to the list of snapshots stored at the checker
    assert hasattr(checker, "__postcondition_snapshots__")

    snapshots = getattr(checker, "__postcondition_snapshots__")
    assert isinstance(snapshots, list)

    for snap in snapshots:
        assert isinstance(snap, Snapshot)
        if snap.name == snapshot.name:
            raise ValueError(
                "There are conflicting snapshots with the name: {!r}".format(snap.name)
            )

    snapshots.append(snapshot)


def add_postcondition_to_checker(checker: CallableT, contract: Contract) -> None:
    """
    Add the postcondition to the function's checker.

    Use :func:`find_checker` to find the checker.
    If it returns ``None``, decorate it with the checker first using :func:`decorate_with_checker`.
    """
    # Add the postcondition to the list of postconditions stored at the checker
    assert hasattr(checker, "__postconditions__")
    assert isinstance(getattr(checker, "__postconditions__"), list)
    getattr(checker, "__postconditions__").append(contract)


def _find_self(
    param_names: List[str], args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> Any:
    """Find the instance of ``self`` in the arguments."""
    instance_i = None
    try:
        instance_i = param_names.index("self")
    except ValueError:
        pass

    if instance_i is not None and instance_i < len(args):
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

    # __new__ can not be async in Python, so we don't need to check whether it is sync or async here
    # (as opposed to the function `_decorate_with_invariants`).
    # See this StackOverflow answer: https://stackoverflow.com/a/33134213/1600678.

    def wrapper(*args, **kwargs):  # type: ignore
        """Pass the arguments to __new__ and check invariants on the result."""
        instance = new_func(*args, **kwargs)

        for invariant in instance.__class__.__invariants__:
            _assert_invariant(contract=invariant, instance=instance)

        return instance

    functools.update_wrapper(wrapper=wrapper, wrapped=new_func)

    setattr(wrapper, "__is_invariant_check__", True)

    return wrapper  # type: ignore


def _decorate_with_invariants(func: CallableT, is_init: bool) -> CallableT:
    """
    Decorate the method ``func`` with invariant checks.

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
                raise KeyError(
                    (
                        "The parameter 'self' could not be found in the call to function {!r}: "
                        "the param names were {!r}, the args were {!r} and kwargs were {!r}"
                    ).format(func, param_names, args, kwargs)
                ) from err

            # We need to disable the invariants check during the constructor.

            # We need to create a new in-progress set if it is None as the ``ContextVar`` does not accept
            # a factory function for the default argument. If we didn't do this, and simply set an empty
            # set as the default, ``ContextVar`` would always point to the same set by copying the default
            # by reference.
            in_progress = _IN_PROGRESS.get()
            if in_progress is None:
                in_progress = set()
                _IN_PROGRESS.set(in_progress)

            id_instance = id(instance)
            in_progress.add(id_instance)

            # ExitStack is not used here due to performance.
            try:
                result = func(*args, **kwargs)

                for invariant in instance.__class__.__invariants__:
                    _assert_invariant(contract=invariant, instance=instance)

                return result
            finally:
                in_progress.discard(id_instance)

    else:
        # (mristin, 2021-02-16)
        # Admittedly, this branching on sync/async is absolutely monstrous.
        # However, I couldn't find out an easier way to refactor the code so that it supports async.
        # Python expects us to explicitly colour functions as sync/async so we can not just put in an if-statement and
        # introduce an "await".
        #
        # The two wrappers need to be manually maintained in parallel.
        # Whenever you make a change, please inspect manually that both sync and async code exercises equivalent
        # behavior.
        # For example, copy/paste the two blocks of code in separate files and perform a diff.

        if inspect.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):  # type: ignore
                """Wrap a function of a class by checking the invariants *before* and *after* the invocation."""
                try:
                    instance = _find_self(
                        param_names=param_names, args=args, kwargs=kwargs
                    )
                except KeyError as err:
                    raise KeyError(
                        (
                            "The parameter 'self' could not be found in the call to function {!r}: "
                            "the param names were {!r}, the args were {!r} and kwargs were {!r}"
                        ).format(func, param_names, args, kwargs)
                    ) from err

                invariants = (
                    instance.__class__.__invariants_on_setattr__
                    if func.__name__ == "__setattr__"
                    else instance.__class__.__invariants_on_call__
                )

                # We need to create a new in-progress set if it is None as the ``ContextVar`` does not accept
                # a factory function for the default argument. If we didn't do this, and simply set an empty
                # set as the default, ``ContextVar`` would always point to the same set by copying the default
                # by reference.
                in_progress = _IN_PROGRESS.get()
                if in_progress is None:
                    in_progress = set()
                    _IN_PROGRESS.set(in_progress)

                # The following dunder indicates whether another invariant is currently being checked. If so,
                # we need to suspend any further invariant check to avoid endless recursion.
                id_instance = id(instance)
                if id_instance not in in_progress:
                    in_progress.add(id_instance)
                else:
                    # Do not check any invariants to avoid endless recursion.
                    return await func(*args, **kwargs)

                # ExitStack is not used here due to performance.
                try:
                    for invariant in invariants:
                        _assert_invariant(contract=invariant, instance=instance)

                    result = await func(*args, **kwargs)

                    for invariant in invariants:
                        _assert_invariant(contract=invariant, instance=instance)

                    return result
                finally:
                    in_progress.discard(id_instance)

        else:

            def wrapper(*args, **kwargs):  # type: ignore
                """Wrap a function of a class by checking the invariants *before* and *after* the invocation."""
                try:
                    instance = _find_self(
                        param_names=param_names, args=args, kwargs=kwargs
                    )
                except KeyError as err:
                    raise KeyError(
                        (
                            "The parameter 'self' could not be found in the call to function {!r}: "
                            "the param names were {!r}, the args were {!r} and kwargs were {!r}"
                        ).format(func, param_names, args, kwargs)
                    ) from err

                invariants = (
                    instance.__class__.__invariants_on_setattr__
                    if func.__name__ == "__setattr__"
                    else instance.__class__.__invariants_on_call__
                )

                # The following dunder indicates whether another invariant is currently being checked. If so,
                # we need to suspend any further invariant check to avoid endless recursion.

                # We need to create a new in-progress set if it is None as the ``ContextVar`` does not accept
                # a factory function for the default argument. If we didn't do this, and simply set an empty
                # set as the default, ``ContextVar`` would always point to the same set by copying the default
                # by reference.
                in_progress = _IN_PROGRESS.get()
                if in_progress is None:
                    in_progress = set()
                    _IN_PROGRESS.set(in_progress)

                id_instance = id(instance)
                if id_instance not in in_progress:
                    in_progress.add(id_instance)
                else:
                    # Do not check any invariants to avoid endless recursion.
                    return func(*args, **kwargs)

                # ExitStack is not used here due to performance.
                try:
                    for invariant in invariants:
                        _assert_invariant(contract=invariant, instance=instance)

                    result = func(*args, **kwargs)

                    for invariant in invariants:
                        _assert_invariant(contract=invariant, instance=instance)

                    return result
                finally:
                    in_progress.discard(id_instance)

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


def add_invariant_checks(cls: ClassT) -> None:
    """Decorate each of the class functions with invariant checks if not already decorated."""
    # Candidates for the decoration as list of (name, dir() value)
    init_func = None  # type: Optional[Callable[..., None]]
    names_funcs = []  # type: List[Tuple[str, Callable[..., None]]]
    names_properties = []  # type: List[Tuple[str, property]]

    # As we continuously decorate the class with invariants, we never definitely know
    # whether this decoration is the last one. Hence, we can only retrieve the list
    # of invariants decorated *thus far*. As we only add one invariant at the time,
    # we only need to check for the last invariant.
    assert cls.__invariants__ is not None, (  # type: ignore
        "Expected to set ``__invariants__`` in the invariant decorator before "
        "the call to {}".format(add_invariant_checks.__name__)
    )
    assert len(cls.__invariants__) > 0, (  # type: ignore
        "Expected at least one invariant in the ``__invariants__`` since we expect "
        "to push the latest invariant in the invariant decorator before the call to "
        "{}".format(add_invariant_checks.__name__)
    )
    last_invariant = cls.__invariants__[-1]  # type: ignore
    assert isinstance(last_invariant, icontract._types.Invariant)

    # Filter out entries in the directory which are certainly not candidates for decoration
    # regarding the ``last_invariant``. Note that the functions which are already decorated
    # will not be re-decorated, so that this loop runs in O( dir(cls) * len(invariants) ),
    # but with a negligible constant.
    for name in dir(cls):
        value = getattr(cls, name)

        # __new__ is a special class method (though not marked properly with @classmethod!).
        # We need to ignore __repr__ to prevent endless loops when generating error messages.
        # We also need to ignore __getattribute__ since pretty much any operation on the instance
        # will result in an endless loop.
        if name in ("__new__", "__repr__", "__getattribute__"):
            continue

        if name == "__init__":
            assert inspect.isfunction(value) or isinstance(
                value, _SLOT_WRAPPER_TYPE
            ), "Expected __init__ to be either a function or a slot wrapper, but got: {}".format(
                type(value)
            )

            init_func = value
            continue

        if (
            name != "__setattr__"
            and InvariantCheckEvent.CALL not in last_invariant.check_on
        ):
            continue

        if (
            name == "__setattr__"
            and InvariantCheckEvent.SETATTR not in last_invariant.check_on
        ):
            continue

        if (
            not inspect.isfunction(value)
            and not isinstance(value, _SLOT_WRAPPER_TYPE)
            and not isinstance(value, property)
        ):
            continue

        # Ignore "protected"/"private" methods
        if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
            continue

        if inspect.isfunction(value) or isinstance(value, _SLOT_WRAPPER_TYPE):
            # Ignore class methods
            if getattr(value, "__self__", None) is cls:
                continue

            # Ignore static methods
            # See https://stackoverflow.com/questions/14187973/python3-check-if-method-is-static
            bound_value = inspect.getattr_static(cls, name, None)
            if isinstance(bound_value, staticmethod):
                continue

            names_funcs.append((name, value))

        elif isinstance(value, property):
            names_properties.append((name, value))

        else:
            raise NotImplementedError(
                "Unhandled directory entry of class {} for {}: {}".format(
                    cls, name, value
                )
            )

    if init_func:
        # We have to distinguish this special case which is used by named
        # tuples and possibly other optimized data structures.
        # In those cases, we have to wrap __new__ instead of __init__.
        if init_func == object.__init__ and hasattr(cls, "__new__"):
            new_func = getattr(cls, "__new__")
            setattr(cls, "__new__", _decorate_new_with_invariants(new_func))
        else:
            wrapper = _decorate_with_invariants(func=init_func, is_init=True)
            setattr(cls, init_func.__name__, wrapper)

    for name, func in names_funcs:
        wrapper = _decorate_with_invariants(func=func, is_init=False)
        setattr(cls, name, wrapper)

    for name, prop in names_properties:
        new_prop = property(
            fget=_decorate_with_invariants(func=prop.fget, is_init=False)
            if prop.fget
            else None,
            fset=_decorate_with_invariants(func=prop.fset, is_init=False)
            if prop.fset
            else None,
            fdel=_decorate_with_invariants(func=prop.fdel, is_init=False)
            if prop.fdel
            else None,
            doc=prop.__doc__,
        )
        setattr(cls, name, new_prop)
