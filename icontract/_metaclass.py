"""Define the metaclass necessary to inherit the contracts from the base classes."""
import abc
import inspect
import platform
from typing import List, MutableMapping, Any, Callable, Optional, cast, Set  # pylint: disable=unused-import

from icontract._types import Contract, Snapshot
import icontract._checkers

# pylint: disable=protected-access


def _collapse_invariants(bases: List[type], namespace: MutableMapping[str, Any]) -> None:
    """Collect invariants from the bases and merge them with the invariants in the namespace."""
    invariants = []  # type: List[Contract]

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


def _collapse_preconditions(base_preconditions: List[List[Contract]], bases_have_func: bool,
                            preconditions: List[List[Contract]], func: Callable[..., Any]) -> List[List[Contract]]:
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


def _collapse_snapshots(base_snapshots: List[Snapshot], snapshots: List[Snapshot]) -> List[Snapshot]:
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


def _collapse_postconditions(base_postconditions: List[Contract], postconditions: List[Contract]) -> List[Contract]:
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
    preconditions = []  # type: List[List[Contract]]
    snapshots = []  # type: List[Snapshot]
    postconditions = []  # type: List[Contract]

    contract_checker = icontract._checkers.find_checker(func=func)
    if contract_checker is not None:
        preconditions = contract_checker.__preconditions__  # type: ignore
        snapshots = contract_checker.__postcondition_snapshots__  # type: ignore
        postconditions = contract_checker.__postconditions__  # type: ignore

    # Collect the preconditions and postconditions from bases.
    #
    # Preconditions and postconditions of __init__ of base classes are deliberately ignored (and not collapsed) since
    # initialization is an operation specific to the concrete class and does not relate to the class hierarchy.
    if key not in ['__init__']:
        base_preconditions = []  # type: List[List[Contract]]
        base_snapshots = []  # type: List[Snapshot]
        base_postconditions = []  # type: List[Contract]

        bases_have_func = False
        for base in bases:
            if hasattr(base, key):
                bases_have_func = True

                # Check if there is a checker function in the base class
                base_func = getattr(base, key)
                base_contract_checker = icontract._checkers.find_checker(func=base_func)

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
            contract_checker = icontract._checkers.decorate_with_checker(func=func)

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
        base_preconditions = []  # type: List[List[Contract]]
        base_snapshots = []  # type: List[Snapshot]
        base_postconditions = []  # type: List[Contract]

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
                base_contract_checker = icontract._checkers.find_checker(func=base_func)

                # Ignore functions which don't have preconditions or postconditions
                if base_contract_checker is not None:
                    base_preconditions.extend(base_contract_checker.__preconditions__)  # type: ignore
                    base_snapshots.extend(base_contract_checker.__postcondition_snapshots__)  # type: ignore
                    base_postconditions.extend(base_contract_checker.__postconditions__)  # type: ignore

        # Add preconditions and postconditions of the function
        preconditions = []  # type: List[List[Contract]]
        snapshots = []  # type: List[Snapshot]
        postconditions = []  # type: List[Contract]

        contract_checker = icontract._checkers.find_checker(func=func)
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
                contract_checker = icontract._checkers.decorate_with_checker(func=func)

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
                icontract._checkers.add_invariant_checks(cls=cls)

            return cls
    else:

        def __new__(mlcs, name, bases, namespace, **kwargs):  # type: ignore  # pylint: disable=arguments-differ
            """Create a class with inherited preconditions, postconditions and invariants."""
            _dbc_decorate_namespace(bases, namespace)

            cls = super().__new__(mlcs, name, bases, namespace, **kwargs)

            if hasattr(cls, "__invariants__"):
                icontract._checkers.add_invariant_checks(cls=cls)

            return cls


class DBC(metaclass=DBCMeta):
    """Provide a standard way to create a class which can inherit the contracts."""

    pass
