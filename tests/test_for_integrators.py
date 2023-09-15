"""Test logic that can be potentially used by the integrators such as third-party libraries."""

# pylint: disable=missing-docstring
# pylint: disable=invalid-name,unnecessary-lambda

import ast
import unittest
from typing import List, MutableMapping, Any, Optional

import icontract._checkers
import icontract._represent


@icontract.require(lambda x: x > 0)
@icontract.snapshot(
    lambda cumulative: None if len(cumulative) == 0 else cumulative[-1], "last"
)
@icontract.snapshot(lambda cumulative: len(cumulative), "len_cumulative")
@icontract.ensure(lambda cumulative, OLD: len(cumulative) == OLD.len_cumulative + 1)
@icontract.ensure(
    lambda x, cumulative, OLD: OLD.last is None or OLD.last + x == cumulative[-1]
)
@icontract.ensure(
    lambda x, cumulative, OLD: OLD.last is not None or x == cumulative[-1]
)
def func_with_contracts(x: int, cumulative: List[int]) -> None:
    if len(cumulative) == 0:
        cumulative.append(x)
    else:
        cumulative.append(x + cumulative[-1])


def func_without_contracts() -> None:
    pass


@icontract.invariant(lambda self: self.x > 0)
class ClassWithInvariants(icontract.DBC):
    def __init__(self) -> None:
        self.x = 1


class TestInitial(unittest.TestCase):
    def test_that_there_is_no_checker_if_no_contracts(self) -> None:
        checker = icontract._checkers.find_checker(func=func_without_contracts)
        self.assertIsNone(checker)


class TestPreconditions(unittest.TestCase):
    def test_evaluating(self) -> None:
        checker = icontract._checkers.find_checker(func=func_with_contracts)
        assert checker is not None

        preconditions = checker.__preconditions__  # type: ignore
        assert isinstance(preconditions, list)
        assert all(isinstance(group, list) for group in preconditions)
        assert all(
            isinstance(contract, icontract._types.Contract)
            for group in preconditions
            for contract in group
        )

        ##
        # Evaluate manually preconditions
        ##

        kwargs = {"x": 4, "cumulative": [2]}

        success = True
        # We have to check preconditions in groups in case they are weakened
        for group in preconditions:
            success = True
            for contract in group:
                condition_kwargs = icontract._checkers.select_condition_kwargs(
                    contract=contract, resolved_kwargs=kwargs
                )

                success = contract.condition(**condition_kwargs)
                if not success:
                    break

            if success:
                break

        assert success

    def test_adding(self) -> None:
        def some_func(x: int) -> None:  # pylint: disable=unused-argument
            return

        checker = icontract._checkers.find_checker(func=some_func)
        assert checker is None

        wrapped = checker = icontract._checkers.decorate_with_checker(func=some_func)

        # The contract needs to have its own error specified since it is not added as a decorator,
        # so the module ``icontract._represent`` will be confused.
        icontract._checkers.add_precondition_to_checker(
            checker=checker,
            contract=icontract._types.Contract(
                condition=lambda x: x > 0,
                error=lambda x: icontract.ViolationError(
                    "x must be positive, but got: {}".format(x)
                ),
            ),
        )

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            wrapped(x=-1)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None

        self.assertEqual("x must be positive, but got: -1", str(violation_error))


class TestPostconditions(unittest.TestCase):
    def test_evaluating(self) -> None:
        checker = icontract._checkers.find_checker(func=func_with_contracts)
        assert checker is not None

        # Retrieve postconditions
        postconditions = checker.__postconditions__  # type: ignore
        assert isinstance(postconditions, list)
        assert all(
            isinstance(contract, icontract._types.Contract)
            for contract in postconditions
        )

        # Retrieve snapshots
        snapshots = checker.__postcondition_snapshots__  # type: ignore
        assert isinstance(snapshots, list)
        assert all(
            isinstance(snapshot, icontract._types.Snapshot) for snapshot in snapshots
        )

        ##
        # Evaluate manually postconditions
        ##

        cumulative = [2]
        kwargs = {"x": 4, "cumulative": cumulative}  # kwargs **before** the call

        # Capture OLD
        old_as_mapping = dict()  # type: MutableMapping[str, Any]
        for snap in snapshots:
            snap_kwargs = icontract._checkers.select_capture_kwargs(
                a_snapshot=snap, resolved_kwargs=kwargs
            )

            old_as_mapping[snap.name] = snap.capture(**snap_kwargs)

        old = icontract._checkers.Old(mapping=old_as_mapping)

        # Simulate the call
        cumulative.append(6)

        # Evaluate the postconditions
        kwargs["OLD"] = old

        success = True
        for contract in postconditions:
            condition_kwargs = icontract._checkers.select_condition_kwargs(
                contract=contract, resolved_kwargs=kwargs
            )

            success = contract.condition(**condition_kwargs)

            if not success:
                break

        assert success

    def test_adding(self) -> None:
        def some_func(lst: List[int]) -> None:
            # This will break the post-condition, see below.
            lst.append(1984)

        checker = icontract._checkers.find_checker(func=some_func)
        assert checker is None

        wrapped = checker = icontract._checkers.decorate_with_checker(func=some_func)

        # The contract needs to have its own error specified since it is not added as a decorator,
        # so the module ``icontract._represent`` will be confused.
        icontract._checkers.add_postcondition_to_checker(
            checker=checker,
            contract=icontract._types.Contract(
                condition=lambda OLD, lst: OLD.len_lst == len(lst),
                error=icontract.ViolationError("The size of lst must not change."),
            ),
        )

        icontract._checkers.add_snapshot_to_checker(
            checker=checker,
            snapshot=icontract._types.Snapshot(
                capture=lambda lst: len(lst), name="len_lst"
            ),
        )

        violation_error = None  # type: Optional[icontract.ViolationError]
        try:
            lst = [1, 2, 3]
            wrapped(lst=lst)
        except icontract.ViolationError as err:
            violation_error = err

        assert violation_error is not None

        self.assertEqual("The size of lst must not change.", str(violation_error))


class TestInvariants(unittest.TestCase):
    def test_reading(self) -> None:
        instance = ClassWithInvariants()
        assert instance.x == 1  # Test assumption

        invariants = ClassWithInvariants.__invariants__  # type: ignore
        assert isinstance(invariants, list)
        assert all(
            isinstance(invariant, icontract._types.Contract) for invariant in invariants
        )

        invariants = instance.__invariants__  # type: ignore
        assert isinstance(invariants, list)
        assert all(
            isinstance(invariant, icontract._types.Contract) for invariant in invariants
        )

        success = True
        for contract in invariants:
            success = contract.condition(self=instance)

            if not success:
                break

        assert success


class TestRepresentation(unittest.TestCase):
    def test_condition_text(self) -> None:
        checker = icontract._checkers.find_checker(func=func_with_contracts)
        assert checker is not None

        # Retrieve postconditions
        contract = checker.__postconditions__[0]  # type: ignore
        assert isinstance(contract, icontract._types.Contract)

        assert icontract._represent.is_lambda(a_function=contract.condition)

        lambda_inspection = icontract._represent.inspect_lambda_condition(
            condition=contract.condition
        )

        assert lambda_inspection is not None

        self.assertEqual(
            "OLD.last is not None or x == cumulative[-1]", lambda_inspection.text
        )

        assert isinstance(lambda_inspection.node, ast.Lambda)

    def test_condition_representation(self) -> None:
        checker = icontract._checkers.find_checker(func=func_with_contracts)
        assert checker is not None

        # Retrieve postconditions
        contract = checker.__postconditions__[0]  # type: ignore
        assert isinstance(contract, icontract._types.Contract)

        text = icontract._represent.represent_condition(contract.condition)
        self.assertEqual(
            "lambda x, cumulative, OLD: OLD.last is not None or x == cumulative[-1]",
            text,
        )


if __name__ == "__main__":
    unittest.main()
