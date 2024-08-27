"""Define data structures shared among the modules."""
import enum
import inspect
import reprlib
from typing import (
    Callable,
    Optional,
    Union,
    Set,
    List,
    Any,
    Type,
    cast,
)  # pylint: disable=unused-import

import icontract._globals

from icontract._globals import ExceptionT


class Contract:
    """Represent a contract to be enforced as a precondition, postcondition or as an invariant."""

    def __init__(
        self,
        condition: Callable[..., Any],
        description: Optional[str] = None,
        a_repr: reprlib.Repr = icontract._globals.aRepr,
        error: Optional[
            Union[Callable[..., ExceptionT], Type[ExceptionT], BaseException]
        ] = None,
        location: Optional[str] = None,
    ) -> None:
        """
        Initialize.

        :param condition: condition predicate
        :param description: textual description of the contract
        :param a_repr: representation instance that defines how the values are represented
        :param error:
            if given as a callable, ``error`` is expected to accept a subset of function arguments
            (*e.g.*, also including ``result`` for preconditions, only ``self`` for invariants *etc.*) and return
            an exception. The ``error`` is called on contract violation and the resulting exception is raised.

            Otherwise, it is expected to denote an Exception class which is instantiated with the violation message
            and raised on contract violation.
        :param location: indicate where the contract was defined (*e.g.*, path and line number)
        """
        self.condition = condition

        signature = inspect.signature(condition)

        # All argument names of the condition
        self.condition_args = list(signature.parameters.keys())  # type: List[str]
        self.condition_arg_set = set(self.condition_args)  # type: Set[str]

        # Names of the mandatory arguments of the condition
        self.mandatory_args = [
            name
            for name, param in signature.parameters.items()
            if param.default == inspect.Parameter.empty
        ]

        self.description = description
        self._a_repr = a_repr

        self.error = error
        self.error_args = None  # type: Optional[List[str]]
        self.error_arg_set = None  # type: Optional[Set[str]]
        if error is not None and (inspect.isfunction(error) or inspect.ismethod(error)):
            error_as_callable = cast(Callable[..., ExceptionT], error)
            self.error_args = list(
                inspect.signature(error_as_callable).parameters.keys()
            )
            self.error_arg_set = set(self.error_args)

        self.location = location


class Snapshot:
    """Define a snapshot of an argument *prior* to the function invocation that is later supplied to a postcondition."""

    def __init__(
        self,
        capture: Callable[..., Any],
        name: Optional[str] = None,
        location: Optional[str] = None,
    ) -> None:
        """
        Initialize.

        :param capture:
            function to capture the snapshot accepting a single argument (from a set of arguments
            of the original function)

        :param name: name of the captured variable in OLD that is passed to postconditions
        :param location: indicate where the snapshot was defined (*e.g.*, path and line number)

        """
        self.capture = capture

        args = list(inspect.signature(capture).parameters.keys())  # type: List[str]

        if name is None:
            if len(args) == 0:
                raise ValueError(
                    "You must name a snapshot if no argument was given in the capture function."
                )
            elif len(args) > 1:
                raise ValueError(
                    "You must name a snapshot if multiple arguments were given in the capture function."
                )
            else:
                assert len(args) == 1
                name = args[0]

        assert (
            name is not None
        ), "Expected ``name`` to be set in the preceding execution paths."
        self.name = name

        self.args = args
        self.arg_set = set(args)

        self.location = location


class InvariantCheckEvent(enum.Flag):
    """Define when an invariant should be checked."""

    #: Evaluate the invariant before and after all calls to a method.
    CALL = enum.auto()

    #: Evaluate the invariant before and after all the calls to ``__setattr__``.
    SETATTR = enum.auto()

    #: Always evaluate the invariant, *i.e., both on calls and on attributes set.
    ALL = CALL | SETATTR


class Invariant(Contract):
    """Represent a contract which is checked on all or some of the class operations."""

    # NOTE (mristin):
    # The class ``Invariant`` inherits from ``Contract`` so that we can maintain
    # the backwards compatibility with the integrators after introducing
    # the ``check_on`` feature.

    def __init__(
        self,
        check_on: InvariantCheckEvent,
        condition: Callable[..., Any],
        description: Optional[str] = None,
        a_repr: reprlib.Repr = icontract._globals.aRepr,
        error: Optional[
            Union[Callable[..., ExceptionT], Type[ExceptionT], BaseException]
        ] = None,
        location: Optional[str] = None,
    ) -> None:
        """Initialize with the given values."""
        assert not hasattr(self, "check_on")
        self.check_on = check_on

        super().__init__(
            condition=condition,
            description=description,
            a_repr=a_repr,
            error=error,
            location=location,
        )
