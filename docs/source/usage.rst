Usage
=====
Preconditions and Postconditions
--------------------------------
.. py:currentmodule:: icontract

icontract provides two function decorators, :class:`require` and :class:`ensure` for pre-conditions
and post-conditions, respectively. Additionally, it provides a class decorator, :class:`invariant`,
to establish class invariants.

The ``condition`` argument specifies the contract and is usually written in lambda notation. In post-conditions,
condition function receives a reserved parameter ``result`` corresponding to the result of the function. The condition
can take as input a subset of arguments required by the wrapped function. This allows for very succinct conditions.

You can provide an optional description by passing in ``description`` argument.

Whenever a violation occurs, :class:`ViolationError` is raised. Its message includes:

* the human-readable representation of the condition,
* description (if supplied) and
* representation of all the values.

The representation of the values is obtained by re-executing the condition function programmatically by traversing
its abstract syntax tree and filling the tree leaves with values held in the function frame. Mind that this re-execution
will also re-execute all the functions. Therefore you need to make sure that all the function calls involved
in the condition functions do not have any side effects.

If you want to customize the error, see Section :ref:`Custom Errors`.

.. code-block:: python

    >>> import icontract

    >>> @icontract.require(lambda x: x > 3)
    ... def some_func(x: int, y: int = 5)->None:
    ...     pass
    ...

    >>> some_func(x=5)

    # Pre-condition violation
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.errors.ViolationError: File <doctest usage.rst[1]>, line 1 in <module>:
    x > 3:
    x was 1
    y was 5

    # Pre-condition violation with a description
    >>> @icontract.require(lambda x: x > 3, "x must not be small")
    ... def some_func(x: int, y: int = 5) -> None:
    ...     pass
    ...
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.errors.ViolationError: File <doctest usage.rst[4]>, line 1 in <module>:
    x must not be small: x > 3:
    x was 1
    y was 5

    # Pre-condition violation with more complex values
    >>> class B:
    ...     def __init__(self) -> None:
    ...         self.x = 7
    ...
    ...     def y(self) -> int:
    ...         return 2
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of B"
    ...
    >>> class A:
    ...     def __init__(self)->None:
    ...         self.b = B()
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of A"
    ...
    >>> SOME_GLOBAL_VAR = 13
    >>> @icontract.require(lambda a: a.b.x + a.b.y() > SOME_GLOBAL_VAR)
    ... def some_func(a: A) -> None:
    ...     pass
    ...
    >>> an_a = A()
    >>> some_func(an_a)
    Traceback (most recent call last):
      ...
    icontract.errors.ViolationError: File <doctest usage.rst[9]>, line 1 in <module>:
    a.b.x + a.b.y() > SOME_GLOBAL_VAR:
    SOME_GLOBAL_VAR was 13
    a was an instance of A
    a.b was an instance of B
    a.b.x was 7
    a.b.y() was 2

    # Post-condition
    >>> @icontract.ensure(lambda result, x: result > x)
    ... def some_func(x: int, y: int = 5) -> int:
    ...     return x - y
    ...
    >>> some_func(x=10)
    Traceback (most recent call last):
      ...
    icontract.errors.ViolationError: File <doctest usage.rst[12]>, line 1 in <module>:
    result > x:
    result was 5
    x was 10
    y was 5

Invariants
----------
Invariants are special contracts associated with an instance of a class. An invariant should hold *after* initialization
and *before* and *after* a call to any public instance method. The invariants are the pivotal element of
design-by-contract: they allow you to formally define properties of data structures that you know will be maintained
throughout the life time of *every* instance.

We consider the following methods to be "public":

* All methods not prefixed with ``_``
* All magic methods (prefix ``__`` and suffix ``__``)

Class methods (marked with ``@classmethod`` or special dunders such as ``__new__``) can not observe the invariants
since they are not associated with an instance of the class. We also exempt ``__getattribute__`` method from observing
the invariants since these functions alter the state of the instance and thus can not be considered "public".
We exempt ``__repr__`` method as well to prevent endless loops when generating error messages.
At runtime, many icontract-specific dunder attributes (such as ``__invariants__``) need to be accessed, so the method
``__getattribute__`` can not be decorated lest we end up in an endless recursion.

By default, we do not enforce the invariants on calls to ``__setattr__`` as that is usually
prohibitively expensive in terms of computation for most use cases. However, there is a parameter
``check_on`` to an :class:`invariant` which allows you to steer in a more fine-grained manner when the invariant should
be enforced.

.. note::

    Be careful with instance attributes referencing other instances or collections. For example, ``a.some_list.append(3)``
    will not trigger the check of invariants as the attribute ``a.some_list``, kept as a reference, remains unchanged.
    That is, even though the referenced object changes (the actual list), the reference does not.

The default value of ``check_on`` is set to :attr:`InvariantCheckEvent.CALL`, meaning that we check
the invariants only in the calls to the methods *excluding* ``__setattr__``. If you want to check
the invariants *only* on ``__setattr__`` and excluding *any* other method, set it to :attr:`InvariantCheckEvent.SETATTR`.
The combinations is also possible; to check invariants on method calls *including* ``__setattr__``, set ``check_on`` to
:attr:`InvariantCheckEvent.CALL` ``|`` :attr:`InvariantCheckEvent.SETATTR`.

To save you some typing, we introduced the shortcut, :attr:`InvariantCheckEvent.ALL`, which stands for the combination
:attr:`InvariantCheckEvent.CALL` ``|`` :attr:`InvariantCheckEvent.SETATTR`.

.. note::

	The property getters and setters are considered "normal" methods. If you want to check the invariants at property
	getters and/or setters, make sure to include :attr:`InvariantCheckEvent.CALL` in ``check_on``.

The following examples show various cases when an invariant is breached.

After the initialization:

.. code-block:: python

        >>> @icontract.invariant(lambda self: self.x > 0)
        ... class SomeClass:
        ...     def __init__(self) -> None:
        ...         self.x = -1
        ...
        ...     def __repr__(self) -> str:
        ...         return "an instance of SomeClass"
        ...
        >>> some_instance = SomeClass()
        Traceback (most recent call last):
         ...
        icontract.errors.ViolationError: File <doctest usage.rst[14]>, line 1 in <module>:
        self.x > 0:
        self was an instance of SomeClass
        self.x was -1


Before the invocation of a public method:

.. code-block:: python

    >>> @icontract.invariant(lambda self: self.x > 0)
    ... class SomeClass:
    ...     def __init__(self) -> None:
    ...         self.x = 100
    ...
    ...     def some_method(self) -> None:
    ...         self.x = 10
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of SomeClass"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance.x = -1
    >>> some_instance.some_method()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest usage.rst[16]>, line 1 in <module>:
    self.x > 0:
    self was an instance of SomeClass
    self.x was -1


After the invocation of a public method:

.. code-block:: python

    >>> @icontract.invariant(lambda self: self.x > 0)
    ... class SomeClass:
    ...     def __init__(self) -> None:
    ...         self.x = 100
    ...
    ...     def some_method(self) -> None:
    ...         self.x = -1
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of SomeClass"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance.some_method()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest usage.rst[20]>, line 1 in <module>:
    self.x > 0:
    self was an instance of SomeClass
    self.x was -1


After the invocation of a magic method:

.. code-block:: python

    >>> @icontract.invariant(lambda self: self.x > 0)
    ... class SomeClass:
    ...     def __init__(self) -> None:
    ...         self.x = 100
    ...
    ...     def __call__(self) -> None:
    ...         self.x = -1
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of SomeClass"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest usage.rst[23]>, line 1 in <module>:
    self.x > 0:
    self was an instance of SomeClass
    self.x was -1

Enforcing the invariants on the method calls *including* ``__setattr__``:

.. code-block:: python

    >>> @icontract.invariant(
    ...     lambda self: self.x > 0,
    ...        check_on=(
    ...            icontract.InvariantCheckEvent.CALL
    ...            | icontract.InvariantCheckEvent.SETATTR
    ...			)
    ... )
    ... class SomeClass:
    ...     def __init__(self) -> None:
    ...         self.x = 100
    ...
    ...     def do_something_bad(self) -> None:
    ...         self.x = -1
    ...
    ...     def __repr__(self) -> str:
    ...         return "an instance of SomeClass"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance.do_something_bad()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest usage.rst[26]>, line 1 in <module>:
    self.x > 0:
    self was an instance of SomeClass
    self.x was -1

    >>> another_instance = SomeClass()
    >>> another_instance.x = -1
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest usage.rst[26]>, line 1 in <module>:
    self.x > 0:
    self was an instance of SomeClass
    self.x was -1

Snapshots (a.k.a "old" argument values)
---------------------------------------
Usual postconditions can not verify the state transitions of the function's argument values. For example, it is
impossible to verify in a postcondition that the list supplied as an argument was appended an element since the
postcondition only sees the argument value as-is after the function invocation.

In order to verify the state transitions, the postcondition needs the "old" state of the argument values
(*i.e.* prior to the invocation of the function) as well as the current values (after the invocation).
:class:`snapshot` decorator instructs the checker to take snapshots of the argument values before the function call
which are then supplied as ``OLD`` argument to the postcondition function.

:class:`snapshot` takes a capture function which accepts none, one or more arguments of the function.
You set the name of the property in ``OLD`` as ``name`` argument to :class:`snapshot`. If there is a single
argument passed to the capture function, the name of the ``OLD`` property can be omitted and equals the name
of the argument.

Here is an example that uses snapshots to check that a value was appended to the list:

.. code-block:: python

    >>> import icontract
    >>> from typing import List

    >>> @icontract.snapshot(lambda lst: lst[:])
    ... @icontract.ensure(lambda OLD, lst, value: lst == OLD.lst + [value])
    ... def some_func(lst: List[int], value: int) -> None:
    ...     lst.append(value)
    ...     lst.append(1984)  # bug

    >>> some_func(lst=[1, 2], value=3)
    Traceback (most recent call last):
        ...
    icontract.errors.ViolationError: File <doctest usage.rst[33]>, line 2 in <module>:
    lst == OLD.lst + [value]:
    OLD was a bunch of OLD values
    OLD.lst was [1, 2]
    lst was [1, 2, 3, 1984]
    result was None
    value was 3

The following example shows how you can name the snapshot:

.. code-block:: python

    >>> import icontract
    >>> from typing import List

    >>> @icontract.snapshot(lambda lst: len(lst), name="len_lst")
    ... @icontract.ensure(lambda OLD, lst, value: len(lst) == OLD.len_lst + 1)
    ... def some_func(lst: List[int], value: int) -> None:
    ...     lst.append(value)
    ...     lst.append(1984)  # bug

    >>> some_func(lst=[1, 2], value=3)
    Traceback (most recent call last):
        ...
    icontract.errors.ViolationError: File <doctest usage.rst[37]>, line 2 in <module>:
    len(lst) == OLD.len_lst + 1:
    OLD was a bunch of OLD values
    OLD.len_lst was 2
    len(lst) was 4
    lst was [1, 2, 3, 1984]
    result was None
    value was 3

The next code snippet shows how you can combine multiple arguments of a function to be captured in a single snapshot:

.. code-block:: python

    >>> import icontract
    >>> from typing import List

    >>> @icontract.snapshot(
    ...     lambda lst_a, lst_b: set(lst_a).union(lst_b), name="union")
    ... @icontract.ensure(
    ...     lambda OLD, lst_a, lst_b: set(lst_a).union(lst_b) == OLD.union)
    ... def some_func(lst_a: List[int], lst_b: List[int]) -> None:
    ...     lst_a.append(1984)  # bug

    >>> some_func(lst_a=[1, 2], lst_b=[3, 4])  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    icontract.errors.ViolationError: File <doctest usage.rst[...]>, line ... in <module>:
    set(lst_a).union(lst_b) == OLD.union:
    OLD was a bunch of OLD values
    OLD.union was {1, 2, 3, 4}
    lst_a was [1, 2, 1984]
    lst_b was [3, 4]
    result was None
    set(lst_a) was {1, 2, 1984}
    set(lst_a).union(lst_b) was {1, 2, 3, 4, 1984}

Inheritance
-----------
To inherit the contracts of the parent class, the child class needs to either inherit from :class:`DBC` or have
a meta class set to :class:`icontract.DBCMeta`.

.. note::

	The inheritance from :class:`DBC` or using the meta class :class:`icontract.DBCMeta` is necessary so that
	the contracts are correctly inherited from the parent to the child class. Otherwise, it is undefined
	behavior how invariants, preconditions and postconditions will be inherited; most probably breaking
	the Liskov substitution principle.

	In particular, the contracts are collapsed into lists for efficiency. If your child class does not
	inherit from :class:`DBC` or you do not use the meta class :class:`icontract.DBCMeta`, the inherited
	contracts in the child class will leak, and thus contracts from the child will be inserted into the
	parent class.

	Hence, make sure you always use :class:`DBC` or :class:`icontract.DBCMeta` when dealing with inheritance.

When no contracts are specified in the child class, all contracts are inherited from the parent class as-are.

When the child class introduces additional preconditions or postconditions and invariants, these contracts are
*strengthened* or *weakened*, respectively. :class:`icontract.DBCMeta` allows you to specify the contracts not only on
the concrete classes, but also on abstract classes.

**Strengthening**. If you specify additional invariants in the child class then the child class will need to satisfy
all the invariants of its parent class as well as its own additional invariants. Analogously, if you specify additional
postconditions to a function of the class, that function will need to satisfy both its own postconditions and
the postconditions of the original parent function that it overrides.

**Weakining**. Adding preconditions to a function in the child class weakens the preconditions. The caller needs to
provide either arguments that satisfy the preconditions associated with the function of the parent class *or*
arguments that satisfy the preconditions of the function of the child class.

**Preconditions and Postconditions of __init__**. Mind that ``__init__`` method is a special case. Since the constructor
is exempt from polymorphism, preconditions and postconditions of base classes are *not* inherited for the
``__init__`` method. Only the preconditions and postconditions specified for the ``__init__`` method of the concrete
class apply.

**Abstract Classes**. Since Python 3 does not allow multiple meta classes, :class:`DBCMeta` inherits from
`abc.ABCMeta <https://docs.python.org/3/library/abc.html#abc.ABCMeta>`_ to allow combining contracts with abstract base
classes.

**Snapshots**. Snapshots are inherited from the base classes for computational efficiency.
You can use snapshots from the base classes as if they were defined in the concrete class.

The following example shows an abstract parent class and a child class that inherits and strengthens parent's contracts:

.. code-block:: python

        >>> import abc
        >>> import icontract

        >>> @icontract.invariant(lambda self: self.x > 0)
        ... class A(icontract.DBC):
        ...     def __init__(self) -> None:
        ...         self.x = 10
        ...
        ...     @abc.abstractmethod
        ...     @icontract.ensure(lambda y, result: result < y)
        ...     def func(self, y: int) -> int:
        ...         pass
        ...
        ...     def __repr__(self) -> str:
        ...         return "an instance of A"

        >>> @icontract.invariant(lambda self: self.x < 100)
        ... class B(A):
        ...     def func(self, y: int) -> int:
        ...         # Break intentionally the postcondition
        ...         # for an illustration
        ...         return y + 1
        ...
        ...     def break_parent_invariant(self):
        ...         self.x = -1
        ...
        ...     def break_my_invariant(self):
        ...         self.x = 101
        ...
        ...     def __repr__(self) -> str:
        ...         return "an instance of B"

        # Break the parent's postcondition
        >>> some_b = B()
        >>> some_b.func(y=0)
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest usage.rst[45]>, line 7 in A:
        result < y:
        result was 1
        self was an instance of B
        y was 0

        # Break the parent's invariant
        >>> another_b = B()
        >>> another_b.break_parent_invariant()
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest usage.rst[45]>, line 1 in <module>:
        self.x > 0:
        self was an instance of B
        self.x was -1

        # Break the child's invariant
        >>> yet_another_b = B()
        >>> yet_another_b.break_my_invariant()
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest usage.rst[46]>, line 1 in <module>:
        self.x < 100:
        self was an instance of B
        self.x was 101

The following example shows how preconditions are weakened:

.. code-block:: python

        >>> class A(icontract.DBC):
        ...     @icontract.require(lambda x: x % 2 == 0)
        ...     def func(self, x: int) -> None:
        ...         pass

        >>> class B(A):
        ...     @icontract.require(lambda x: x % 3 == 0)
        ...     def func(self, x: int) -> None:
        ...         pass
        ...
        ...     def __repr__(self) -> str:
        ...         return "an instance of B"


        >>> b = B()

        # The precondition of the parent is satisfied.
        >>> b.func(x=2)

        # The precondition of the child is satisfied,
        # while the precondition of the parent is not.
        # This is OK since the precondition has been
        # weakened.
        >>> b.func(x=3)

        # None of the preconditions have been satisfied.
        >>> b.func(x=5)
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest usage.rst[54]>, line 2 in B:
        x % 3 == 0:
        self was an instance of B
        x was 5

The example below illustrates how snapshots are inherited:

.. code-block:: python

        >>> class A(icontract.DBC):
        ...     @abc.abstractmethod
        ...     @icontract.snapshot(lambda lst: lst[:])
        ...     @icontract.ensure(lambda OLD, lst: len(lst) == len(OLD.lst) + 1)
        ...     def func(self, lst: List[int], value: int) -> None:
        ...         pass

        >>> class B(A):
        ...     # The snapshot of OLD.lst has been defined in class A.
        ...     @icontract.ensure(lambda OLD, lst: lst == OLD.lst + [value])
        ...     def func(self, lst: List[int], value: int) -> None:
        ...         lst.append(value)
        ...         lst.append(1984)  # bug
        ...
        ...     def __repr__(self) -> str:
        ...         return "an instance of B"


        >>> b = B()
        >>> b.func(lst=[1, 2], value=3)
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest usage.rst[59]>, line 4 in A:
        len(lst) == len(OLD.lst) + 1:
        OLD was a bunch of OLD values
        OLD.lst was [1, 2]
        len(OLD.lst) was 2
        len(lst) was 4
        lst was [1, 2, 3, 1984]
        result was None
        self was an instance of B
        value was 3

Toggling Contracts
------------------
By default, the contract checks (including the snapshots) are always performed at run-time. To disable them, run the
interpreter in optimized mode (``-O`` or ``-OO``, see
`Python command-line options <https://docs.python.org/3/using/cmdline.html#cmdoption-o>`_).

If you want to override this behavior, you can supply the ``enabled`` argument to the contract:

.. code-block:: python

    >>> @icontract.require(lambda x: x > 10, enabled=False)
    ... def some_func(x: int) -> int:
    ...     return 123
    ...

    # The pre-condition is breached, but the check was disabled:
    >>> some_func(x=0)
    123

Icontract provides a global variable ``icontract.SLOW`` to provide a unified way to mark a plethora of contracts
in large code bases. ``icontract.SLOW`` reflects the environment variable ``ICONTRACT_SLOW``.

While you may want to keep most contracts running both during the development and in the production, contracts
marked with ``icontract.SLOW`` should run only during the development (since they are too sluggish to execute in a real
application).

If you want to enable contracts marked with ``icontract.SLOW``, set the environment variable ``ICONTRACT_SLOW`` to a
non-empty string.

Here is some example code:

.. code-block:: python

    # some_module.py
    @icontract.require(lambda x: x > 10, enabled=icontract.SLOW)
        def some_func(x: int) -> int:
            return 123

    # in test_some_module.py
    import unittest

    class TestSomething(unittest.TestCase):
        def test_some_func(self) -> None:
            self.assertEqual(123, some_func(15))

    if __name__ == '__main__':
        unittest.main()

Run this bash command to execute the unit test with slow contracts:

.. code-block:: bash

    $ ICONTRACT_SLOW=true python test_some_module.py

.. _custom-errors:

Custom Errors
-------------

Icontract raises :class:`ViolationError` by default. However, you can also instruct icontract to raise a different error
by supplying ``error`` argument to the decorator.

The ``error`` argument can either be:

* **A callable that returns an exception.** The callable accepts the subset of arguments of the original function
  (including ``result`` and ``OLD`` for postconditions) or ``self`` in case of invariants, respectively,
  and returns an exception. The arguments to the condition function can freely differ from the arguments
  to the error function.

  The exception returned by the given callable is finally raised.

  If you specify the ``error`` argument as callable, the values will not be traced and the condition function will not
  be parsed. Hence, violation of contracts with ``error`` arguments as callables incur a much smaller computational
  overhead in case of violations compared to contracts with default violation messages for which we need to  trace
  the argument values and parse the condition function.
* **A subclass of `BaseException`_.** The exception is constructed with the violation message and finally raised.
* **An instance of `BaseException`_.** The exception is raised as-is on contract violation.

.. _BaseException: https://docs.python.org/3/library/exceptions.html#BaseException

Here is an example of the error given as a callable:

.. code-block:: python

    >>> @icontract.require(
    ...     lambda x: x > 0,
    ...     error=lambda x: ValueError('x must be positive, got: {}'.format(x)))
    ... def some_func(x: int) -> int:
    ...     return 123
    ...

    # Custom Exception class
    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    ValueError: x must be positive, got: 0


Here is an example of the error given as a subclass of `BaseException`_:

.. code-block:: python

    >>> @icontract.require(lambda x: x > 0, error=ValueError)
    ... def some_func(x: int) -> int:
    ...     return 123
    ...

    # Custom Exception class
    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    ValueError: File <doctest usage.rst[67]>, line 1 in <module>:
    x > 0: x was 0

Here is an example of the error given as an instance of a `BaseException`_:

.. code-block:: python

    >>> @icontract.require(lambda x: x > 0, error=ValueError("x non-positive"))
    ... def some_func(x: int) -> int:
    ...     return 123
    ...

    # Custom Exception class
    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    ValueError: x non-positive


.. danger::
    Be careful when you write contracts with custom errors. This might lead the caller to (ab)use the contracts as
    a control flow mechanism.

    In that case, the user will expect that the contract is *always* enabled and not only during debug or test.
    (For example, whenever you run Python interpreter with ``-O`` or ``-OO``, ``__debug__`` will be ``False``.
    If you left ``enabled`` argument to its default ``__debug__``, the contract will *not* be verified in
    ``-O`` mode.)

Variable Positional and Keyword Arguments
-----------------------------------------
Certain functions do not name their arguments explicitly, but operate on variable positional and/or
keyword arguments supplied at the function call (*e.g.*, ``def some_func(*args, **kwargs): ...``).
Contract conditions thus need a mechanism to refer to these variable arguments.
To that end, we introduced two special condition arguments, ``_ARGS`` and ``_KWARGS``, that
icontract will populate before evaluating the condition to capture the positional and keyword
arguments, respectively, of the function call.

To avoid intricacies of Python's argument resolution at runtime, icontract simply captures *all*
positional and keyword arguments in these two variables, regardless of whether the function defines
them or not. However, we would recommend you to explicitly name arguments in your conditions and
use ``_ARGS`` and ``_KWARGS`` only for the variable arguments for readability.

We present in the following a couple of valid contracts to demonstrate how to use these special
arguments:

.. code-block:: python

    # The contract refers to the positional arguments of the *call*,
    # though the decorated function does not handle
    # variable positional arguments.
    >>> @icontract.require(lambda _ARGS: _ARGS[0] > 0)
    ... def function_a(x: int) -> int:
    ...     return 123
    >>> function_a(1)
    123

    # The contract refers to the keyword arguments of the *call*,
    # though the decorated function does not handle variable keyword arguments.
    >>> @icontract.require(lambda _KWARGS: _KWARGS["x"] > 0)
    ... def function_b(x: int) -> int:
    ...     return 123
    >>> function_b(x=1)
    123

    # The contract refers both to the named argument and keyword arguments.
    # The decorated function specifies an argument and handles
    # variable keyword arguments at the same time.
    >>> @icontract.require(lambda x, _KWARGS: x < _KWARGS["y"])
    ... def function_c(x: int, **kwargs) -> int:
    ...     return 123
    >>> function_c(1, y=3)
    123

    # The decorated functions accepts only variable keyboard arguments.
    >>> @icontract.require(lambda _KWARGS: _KWARGS["x"] > 0)
    ... def function_d(**kwargs) -> int:
    ...     return 123
    >>> function_d(x=1)
    123

    # The decorated functions accepts only variable keyboard arguments.
    # The keyword arguments are given an uncommon name (``parameters`` instead
    # of ``kwargs``).
    >>> @icontract.require(lambda _KWARGS: _KWARGS["x"] > 0)
    ... def function_e(**parameters) -> int:
    ...     return 123
    >>> function_e(x=1)
    123

As a side note, we agree that the names picked for the placeholders are indeed a bit ugly.
We decided against more aesthetic or ergonomic identifiers (such as ``_`` and ``__`` or
``A`` and ``KW``) to avoid potential naming conflicts.

The underscore in front of the placeholders is meant to motivate a bit deeper understanding
of the condition.
For example, the reader needs to be aware that the logic for resolving the keyword arguments
passed to the function is *different* in condition and that ``_KWARGS`` *does not* refer to
arbitrary keyword arguments *passed to the condition*. Though this might be obvious for some
readers, we are almost certain that ``_ARGS`` and ``_KWARGS`` will cause some confusion.
We hope that a small hint like an underscore will eventually help the reading.
