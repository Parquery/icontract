"""Define public decorators."""
import reprlib
from typing import Callable, Optional, Union, Any, List  # pylint: disable=unused-import

from icontract._types import Contract, Snapshot

import icontract._checkers

# pylint: disable=protected-access


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
        self._contract = None  # type: Optional[Contract]

        if not enabled:
            return

        self._contract = Contract(
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
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is not None:
            # Do not add an additional wrapper since the function has been already wrapped with a contract checker
            result = func
        else:
            # Wrap the function with a contract checker
            contract_checker = icontract._checkers.decorate_with_checker(func=func)
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
        self._snapshot = None  # type: Optional[Snapshot]
        self.enabled = enabled

        # Resolve the snapshot only if enabled so that no overhead is incurred
        if enabled:
            self._snapshot = Snapshot(capture=capture, name=name)

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
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is None:
            raise ValueError("You are decorating a function with a snapshot, but no postcondition was defined "
                             "on the function before.")

        assert self._snapshot is not None, "Expected the enabled snapshot to have the property ``snapshot`` set."

        # Add the snapshot to the list of snapshots stored at the checker
        assert hasattr(contract_checker, "__postcondition_snapshots__")

        snapshots = getattr(contract_checker, "__postcondition_snapshots__")
        assert isinstance(snapshots, list)

        for snap in snapshots:
            assert isinstance(snap, Snapshot)
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
        self._contract = None  # type: Optional[Contract]

        if not enabled:
            return

        self._contract = Contract(
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
        contract_checker = icontract._checkers.find_checker(func=func)

        if contract_checker is not None:
            # Do not add an additional wrapper since the function has been already wrapped with a contract checker
            result = func
        else:
            # Wrap the function with a contract checker
            contract_checker = icontract._checkers.decorate_with_checker(func=func)
            result = contract_checker

        # Add the postcondition to the list of postconditions stored at the checker
        assert hasattr(contract_checker, "__postconditions__")
        assert isinstance(getattr(contract_checker, "__postconditions__"), list)
        getattr(contract_checker, "__postconditions__").append(self._contract)

        return result


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
        self._contract = None  # type: Optional[Contract]

        if not enabled:
            return

        self._contract = Contract(
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
            invariants = []  # type: List[Contract]
            setattr(cls, "__invariants__", invariants)
        else:
            invariants = getattr(cls, "__invariants__")
            assert isinstance(invariants, list), \
                "Expected invariants of class {} to be a list, but got: {}".format(cls, type(invariants))

        invariants.append(self._contract)

        icontract._checkers.add_invariant_checks(cls=cls)

        return cls
