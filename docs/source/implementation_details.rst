Implementation Details
======================

Decorator Stack
---------------
The precondition and postcondition decorators have to be stacked together to allow for inheritance.
Hence, when multiple precondition and postcondition decorators are given, the function is actually decorated only once
with a precondition/postcondition checker while the contracts are stacked to the checker's ``__preconditions__`` and
``__postconditions__`` attribute, respectively. The checker functions iterates through these two attributes to verify
the contracts at run-time.

All the decorators in the function's decorator stack are expected to call `functools.update_wrapper`_.
Notably, we use ``__wrapped__`` attribute to iterate through the decorator stack and find the checker function which is
set with `functools.update_wrapper`_.
Mind that this implies that preconditions and postconditions are verified at the inner-most decorator and *not* when
outer preconditions and postconditions are defined.

Consider the following example:

.. code-block:: python

    @some_custom_decorator
    @icontract.require(lambda x: x > 0)
    @another_custom_decorator
    @icontract.require(lambda x, y: y < x)
    def some_func(x: int, y: int) -> None:
      # ...

The checker function will verify the two preconditions after both ``some_custom_decorator`` and
``another_custom_decorator`` have been applied, whily you would expect that the outer precondition (``x > 0``)
is verified immediately after ``some_custom_decorator`` is applied.

To prevent bugs due to unexpected behavior, we recommend to always group preconditions and postconditions together.

Decoration with Invariants
--------------------------
Since invariants are handled by a class decorator (in contrast to function decorators that handle
preconditions and postconditions), they do not need to be stacked. The first invariant decorator wraps each public
method of a class with a checker function. The invariants are added to the class attribute ``__invariants__``.
At run-time, the checker function iterates through the ``__invariants__`` attribute when it needs to actually verify the
invariants.

Mind that we still expect each class decorator that decorates the class functions to use `functools.update_wrapper`_
in order to be able to iterate through decorator stacks of the individual functions.

Recursion in Contracts
----------------------
In certain cases functions depend on each other through contracts. Consider the following snippet:

.. code-block:: python

    @icontract.require(lambda: another_func())
    def some_func() -> bool:
        ...

    @icontract.require(lambda: some_func())
    def another_func() -> bool:
        ...

    some_func()

Naively evaluating such preconditions and postconditions would result in endless recursions. Therefore, icontract
suspends any further contract checking for a function when re-entering it for the second time while checking its
contracts.

Invariants depending on the instance methods would analogously result in endless recursions. The following snippet
gives an example of such an invariant:

.. code-block:: python

    @icontract.invariant(lambda self: self.some_func())
    class SomeClass(icontract.DBC):
        def __init__(self) -> None:
            ...

        def some_func(self) -> bool:
            ...

To avoid endless recursion icontract suspends further invariant checks while checking an invariant. The dunder
``__dbc_invariant_check_is_in_progress__`` is set on the instance for a diode effect as soon as invariant check is
in progress and removed once the invariants checking finished. As long as the dunder
``__dbc_invariant_check_is_in_progress__`` is present, the wrappers that check invariants simply return the result of
the function.

Invariant checks also need to be disabled during the construction since calling member functions would trigger invariant
checks which, on their hand, might check on yet-to-be-defined instance attributes. See the following snippet:

.. code-block:: python

        @icontract.invariant(lambda self: self.some_attribute > 0)
        class SomeClass(icontract.DBC):
            def __init__(self) -> None:
                self.some_attribute = self.some_func()

            def some_func(self) -> int:
                return 1984

.. _functools.update_wrapper: https://docs.python.org/3/library/functools.html#functools.update_wrapper