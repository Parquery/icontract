"""Define public decorators."""
import inspect
import reprlib
import traceback
from typing import (
    Callable,
    Optional,
    Union,
    Any,
    List,
    Type,
)  # pylint: disable=unused-import

import icontract._checkers
from icontract._globals import CallableT, ExceptionT, ClassT
from icontract._types import Contract, Snapshot, InvariantCheckEvent, Invariant


class require:  # pylint: disable=invalid-name
    """
    Decorate a function with a precondition.

    The arguments of the precondition are expected to be a subset of the arguments of the wrapped function.
    """

    def __init__(
        self,
        condition: Callable[..., Any],
        description: Optional[str] = None,
        a_repr: reprlib.Repr = icontract._globals.aRepr,
        enabled: bool = __debug__,
        error: Optional[
            Union[Callable[..., ExceptionT], Type[ExceptionT], BaseException]
        ] = None,
    ) -> None:
        """
        Initialize.

        :param condition: precondition predicate

            If the condition returns a coroutine, you must specify the `error` as
            coroutines have side effects and can not be recomputed.
        :param description: textual description of the precondition
        :param a_repr: representation instance that defines how the values are represented
        :param enabled:
            The decorator is applied only if this argument is set.

            Otherwise, the condition check is disabled and there is no run-time overhead.

            The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).
        :param error:
            The error is expected to denote either:

            * A callable. ``error`` is expected to accept a subset of function arguments and return an exception.
              The ``error`` is called on contract violation and the resulting exception is raised.
            * A subclass of ``BaseException`` which is instantiated with the violation message and raised
              on contract violation.
            * An instance of ``BaseException`` that will be raised with the traceback on contract violation.

        """
        self.enabled = enabled
        self._contract = None  # type: Optional[Contract]

        if not enabled:
            return

        if error is None:
            pass
        elif isinstance(error, type):
            if not issubclass(error, BaseException):
                raise ValueError(
                    (
                        "The error of the contract is given as a type, "
                        "but the type does not inherit from BaseException: {}"
                    ).format(error)
                )
        else:
            if (
                not inspect.isfunction(error)
                and not inspect.ismethod(error)
                and not isinstance(error, BaseException)
            ):
                raise ValueError(
                    (
                        "The error of the contract must be either a callable (a function or a method), "
                        "a class (subclass of BaseException) or an instance of BaseException, but got: {}"
                    ).format(error)
                )

        location = None  # type: Optional[str]
        tb_stack = traceback.extract_stack(limit=2)[:1]
        if len(tb_stack) > 0:
            frame = tb_stack[0]
            location = "File {}, line {} in {}".format(
                frame.filename, frame.lineno, frame.name
            )

        self._contract = Contract(
            condition=condition,
            description=description,
            a_repr=a_repr,
            error=error,
            location=location,
        )

    def __call__(self, func: CallableT) -> CallableT:
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
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is None:
            # Wrap the function with a contract checker
            contract_checker = icontract._checkers.decorate_with_checker(func=func)

        result = contract_checker

        assert self._contract is not None
        icontract._checkers.add_precondition_to_checker(
            checker=contract_checker, contract=self._contract
        )

        return result


class snapshot:  # pylint: disable=invalid-name
    """
    Decorate a function with a snapshot of argument values captured *prior* to the function invocation.

    A snapshot is defined by a capture function (usually a lambda) that accepts one or more arguments of the function.
    If the name of the snapshot is not given, the capture function must have a single argument and the name is equal to
    the name of that single argument.

    The captured values are supplied to postconditions with the OLD argument of the condition and error function.
    Snapshots are inherited from the base classes and must not have conflicting names in the class hierarchy.
    """

    def __init__(
        self,
        capture: Callable[..., Any],
        name: Optional[str] = None,
        enabled: bool = __debug__,
    ) -> None:
        """
        Initialize.

        :param capture:
            function to capture the snapshot accepting a one or more arguments of the original function *prior*
            to the execution
        :param name: name of the snapshot; if omitted, the name corresponds to the name of the input argument
        :param enabled:
            The decorator is applied only if ``enabled`` is set.

            Otherwise, the snapshot is disabled and there is no run-time overhead.

            The default is to always capture the snapshot unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).

        """
        self._snapshot = None  # type: Optional[Snapshot]
        self.enabled = enabled

        # Resolve the snapshot only if enabled so that no overhead is incurred
        if enabled:
            location = None  # type: Optional[str]
            tb_stack = traceback.extract_stack(limit=2)[:1]
            if len(tb_stack) > 0:
                frame = tb_stack[0]
                location = "File {}, line {} in {}".format(
                    frame.filename, frame.lineno, frame.name
                )

            self._snapshot = Snapshot(capture=capture, name=name, location=location)

    def __call__(self, func: CallableT) -> CallableT:
        """
        Add the snapshot to the list of snapshots of the function ``func``.

        The function ``func`` is expected to be decorated with at least one postcondition before the snapshot.

        :param func: function whose arguments we need to snapshot
        :return: ``func`` as given in the input
        """
        if not self.enabled:
            return func

        # Find a contract checker
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is None:
            raise ValueError(
                "You are decorating a function with a snapshot, but no postcondition was defined "
                "on the function before."
            )

        assert (
            self._snapshot is not None
        ), "Expected the enabled snapshot to have the property ``snapshot`` set."

        icontract._checkers.add_snapshot_to_checker(
            checker=contract_checker, snapshot=self._snapshot
        )

        return func


class ensure:  # pylint: disable=invalid-name
    """
    Decorate a function with a postcondition.

    The arguments of the postcondition are expected to be a subset of the arguments of the wrapped function.
    Additionally, the argument "result" is reserved for the result of the wrapped function. The wrapped function must
    not have "result" among its arguments.
    """

    def __init__(
        self,
        condition: Callable[..., Any],
        description: Optional[str] = None,
        a_repr: reprlib.Repr = icontract._globals.aRepr,
        enabled: bool = __debug__,
        error: Optional[
            Union[Callable[..., ExceptionT], Type[ExceptionT], BaseException]
        ] = None,
    ) -> None:
        """
        Initialize.

        :param condition:
            postcondition predicate.

            If the condition returns a coroutine, you must specify the `error` as
            coroutines have side effects and can not be recomputed.
        :param description: textual description of the postcondition
        :param a_repr: representation instance that defines how the values are represented
        :param enabled:
            The decorator is applied only if this argument is set.

            Otherwise, the condition check is disabled and there is no run-time overhead.

            The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
            ``-OO``).
        :param error:
            The error is expected to denote either:

            * A callable. ``error`` is expected to accept a subset of function arguments and return an exception.
              The ``error`` is called on contract violation and the resulting exception is raised.
            * A subclass of ``BaseException`` which is instantiated with the violation message and raised
              on contract violation.
            * An instance of ``BaseException`` that will be raised with the traceback on contract violation.
        """
        self.enabled = enabled
        self._contract = None  # type: Optional[Contract]

        if not enabled:
            return

        if error is None:
            pass
        elif isinstance(error, type):
            if not issubclass(error, BaseException):
                raise ValueError(
                    (
                        "The error of the contract is given as a type, "
                        "but the type does not inherit from BaseException: {}"
                    ).format(error)
                )
        else:
            if (
                not inspect.isfunction(error)
                and not inspect.ismethod(error)
                and not isinstance(error, BaseException)
            ):
                raise ValueError(
                    (
                        "The error of the contract must be either a callable (a function or a method), "
                        "a class (subclass of BaseException) or an instance of BaseException, but got: {}"
                    ).format(error)
                )

        location = None  # type: Optional[str]
        tb_stack = traceback.extract_stack(limit=2)[:1]
        if len(tb_stack) > 0:
            frame = tb_stack[0]
            location = "File {}, line {} in {}".format(
                frame.filename, frame.lineno, frame.name
            )

        self._contract = Contract(
            condition=condition,
            description=description,
            a_repr=a_repr,
            error=error,
            location=location,
        )

    def __call__(self, func: CallableT) -> CallableT:
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
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is None:
            # Wrap the function with a contract checker
            contract_checker = icontract._checkers.decorate_with_checker(func=func)

        result = contract_checker

        assert self._contract is not None
        icontract._checkers.add_postcondition_to_checker(
            checker=contract_checker, contract=self._contract
        )

        return result


class invariant:  # pylint: disable=invalid-name
    """
    Represent a class decorator to establish the invariant on all the public methods.

    Class method as well as "private" (prefix ``__``) and "protected" methods (prefix ``_``) may violate the invariant.
    Note that all magic methods (prefix ``__`` and suffix ``__``) are considered public and hence also need to establish
    the invariant. To avoid endless loops when generating the error message on an invariant breach, the method
    ``__repr__`` is deliberately exempt from observing the invariant.

    The invariant is checked *before* and *after* the method invocation.

    As invariants need to wrap dunder methods, including ``__init__``, their conditions *can not* be
    async, as most dunder methods need to be synchronous methods, and wrapping them with async code would
    break that constraint.

    For efficiency reasons, we do not check the invariants at the calls to ``__setattr__`` and ``__getattr__``
    methods by default. If you indeed want to check the invariants in those calls as well, make sure to adapt
    the argument ``check_on`` accordingly.
    """

    def __init__(
        self,
        condition: Callable[..., Any],
        description: Optional[str] = None,
        a_repr: reprlib.Repr = icontract._globals.aRepr,
        enabled: bool = __debug__,
        error: Optional[
            Union[Callable[..., ExceptionT], Type[ExceptionT], BaseException]
        ] = None,
        check_on: InvariantCheckEvent = InvariantCheckEvent.CALL,
    ) -> None:
        """
        Initialize a class decorator to establish the invariant on all the public methods.

        :param condition:
            invariant predicate.

            The condition must not be a coroutine function as dunder functions (including ``__init__``)
            of a class can not be async.
        :param description: textual description of the invariant
        :param a_repr: representation instance that defines how the values are represented
        :param enabled:
                The decorator is applied only if this argument is set.

                Otherwise, the condition check is disabled and there is no run-time overhead.

                The default is to always check the condition unless the interpreter runs in optimized mode (``-O`` or
                ``-OO``).
        :param error:
            The error is expected to denote either:

            * A callable. ``error`` is expected to accept a subset of function arguments and return an exception.
              The ``error`` is called on contract violation and the resulting exception is raised.
            * A subclass of ``BaseException`` which is instantiated with the violation message and raised
              on contract violation.
            * An instance of ``BaseException`` that will be raised with the traceback on contract violation.
        :param check_on:
            Specify when to check the invariant.

            * If :py:attr:`InvariantCheckEvent.CALL` is set, the invariant will be checked on all the method calls
              except ``__setattr__``.
            * If :py:attr:`InvariantCheckEvent.SETATTR` is set, the invariant will be checked on ``__setattr__`` calls.
        :return:

        """
        self.enabled = enabled
        self._invariant = None  # type: Optional[Invariant]

        if not enabled:
            return

        if error is None:
            pass
        elif isinstance(error, type):
            if not issubclass(error, BaseException):
                raise ValueError(
                    (
                        "The error of the contract is given as a type, "
                        "but the type does not inherit from BaseException: {}"
                    ).format(error)
                )
        else:
            if (
                not inspect.isfunction(error)
                and not inspect.ismethod(error)
                and not isinstance(error, BaseException)
            ):
                raise ValueError(
                    (
                        "The error of the contract must be either a callable (a function or a method), "
                        "a class (subclass of BaseException) or an instance of BaseException, but got: {}"
                    ).format(error)
                )

        location = None  # type: Optional[str]
        tb_stack = traceback.extract_stack(limit=2)[:1]
        if len(tb_stack) > 0:
            frame = tb_stack[0]
            location = "File {}, line {} in {}".format(
                frame.filename, frame.lineno, frame.name
            )

        if inspect.iscoroutinefunction(condition):
            raise ValueError(
                "Async conditions are not possible in invariants as sync methods such as __init__ have to be wrapped."
            )

        self._invariant = Invariant(
            check_on=check_on,
            condition=condition,
            description=description,
            a_repr=a_repr,
            error=error,
            location=location,
        )

        if self._invariant.mandatory_args and self._invariant.mandatory_args != [
            "self"
        ]:
            raise ValueError(
                "Expected an invariant condition with at most an argument 'self', but got: {}".format(
                    self._invariant.condition_args
                )
            )

    def __call__(self, cls: ClassT) -> ClassT:
        """
        Decorate each of the public methods with the invariant.

        Go through the decorator stack of each function and search for a contract checker. If there is one,
        add the invariant to the checker's invariants. If there is no checker in the stack, wrap the function with a
        contract checker.
        """
        if not self.enabled:
            return cls

        assert (
            self._invariant is not None
        ), "self._contract must be set if the contract was enabled."

        if not hasattr(cls, "__invariants__"):
            invariants = []  # type: List[Invariant]
            setattr(cls, "__invariants__", invariants)

            invariants_on_call = []  # type: List[Invariant]
            setattr(cls, "__invariants_on_call__", invariants_on_call)

            invariants_on_setattr = []  # type: List[Invariant]
            setattr(cls, "__invariants_on_setattr__", invariants_on_setattr)
        else:
            invariants = getattr(cls, "__invariants__")
            assert isinstance(
                invariants, list
            ), "Expected invariants of class {} to be a list, but got: {}".format(
                cls, type(invariants)
            )

            invariants_on_call = getattr(cls, "__invariants_on_call__")
            assert isinstance(invariants_on_call, list), (
                "Expected invariants on call of class {} to be a list, "
                "but got: {}".format(cls, type(invariants_on_call))
            )

            invariants_on_setattr = getattr(cls, "__invariants_on_setattr__")
            assert isinstance(invariants_on_setattr, list), (
                "Expected invariants on call of class {} to be a list, "
                "but got: {}".format(cls, type(invariants_on_setattr))
            )

        invariants.append(self._invariant)

        if InvariantCheckEvent.CALL in self._invariant.check_on:
            invariants_on_call.append(self._invariant)

        if InvariantCheckEvent.SETATTR in self._invariant.check_on:
            invariants_on_setattr.append(self._invariant)

        icontract._checkers.add_invariant_checks(cls=cls)

        return cls
