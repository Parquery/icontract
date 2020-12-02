icontract
=========
.. image:: https://travis-ci.com/Parquery/icontract.svg?branch=master
    :target: https://travis-ci.com/Parquery/icontract

.. image:: https://coveralls.io/repos/github/Parquery/icontract/badge.svg?branch=master
    :target: https://coveralls.io/github/Parquery/icontract

.. image:: https://badge.fury.io/py/icontract.svg
    :target: https://badge.fury.io/py/icontract
    :alt: PyPI - version

.. image:: https://img.shields.io/pypi/pyversions/icontract.svg
    :alt: PyPI - Python Version

.. image:: https://badges.gitter.im/gitterHQ/gitter.png
    :target: https://gitter.im/Parquery-icontract/community
    :alt: Gitter chat

icontract provides `design-by-contract <https://en.wikipedia.org/wiki/Design_by_contract>`_ to Python3 with informative
violation messages and inheritance.

Related Projects
----------------
There exist a couple of contract libraries. However, at the time of this writing (September 2018), they all required the
programmer either to learn a new syntax (`PyContracts <https://pypi.org/project/PyContracts/>`_) or to write
redundant condition descriptions (
*e.g.*,
`contracts <https://pypi.org/project/contracts/>`_,
`covenant <https://github.com/kisielk/covenant>`_,
`deal <https://github.com/life4/deal>`_,
`dpcontracts <https://pypi.org/project/dpcontracts/>`_,
`pyadbc <https://pypi.org/project/pyadbc/>`_ and
`pcd <https://pypi.org/project/pcd>`_).

This library was strongly inspired by them, but we go two steps further.

First, our violation message on contract breach are much more informative. The message includes the source code of the
contract condition as well as variable values at the time of the breach. This promotes don't-repeat-yourself principle
(`DRY <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_) and spare the programmer the tedious task of repeating
the message that was already written in code.

Second, icontract allows inheritance of the contracts and supports weakining of the preconditions
as well as strengthening of the postconditions and invariants. Notably, weakining and strengthening of the contracts
is a feature indispensable for modeling many non-trivial class hierarchies. Please see Section `Inheritance`_.
To the best of our knowledge, there is currently no other Python library that supports inheritance of the contracts in a
correct way.

In the long run, we hope that design-by-contract will be adopted and integrated in the language. Consider this library
a work-around till that happens. You might be also interested in the archived discussion on how to bring
design-by-contract into Python language on
`python-ideas mailing list <https://groups.google.com/forum/#!topic/python-ideas/JtMgpSyODTU>`_.

Usage
=====
icontract provides two function decorators, ``require`` and ``ensure`` for pre-conditions and post-conditions,
respectively. Additionally, it provides a class decorator, ``invariant``, to establish class invariants.

The ``condition`` argument specifies the contract and is usually written in lambda notation. In post-conditions,
condition function receives a reserved parameter ``result`` corresponding to the result of the function. The condition
can take as input a subset of arguments required by the wrapped function. This allows for very succinct conditions.

You can provide an optional description by passing in ``description`` argument.

Whenever a violation occurs, ``ViolationError`` is raised. Its message includes:

* the human-readable representation of the condition,
* description (if supplied) and
* representation of all the values.

The representation of the values is obtained by re-executing the condition function programmatically by traversing
its abstract syntax tree and filling the tree leaves with values held in the function frame. Mind that this re-execution
will also re-execute all the functions. Therefore you need to make sure that all the function calls involved
in the condition functions do not have any side effects.

If you want to customize the error, see Section "Custom Errors".

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
    icontract.errors.ViolationError: File <doctest README.rst[1]>, line 1 in <module>:
    x > 3: x was 1

    # Pre-condition violation with a description
    >>> @icontract.require(lambda x: x > 3, "x must not be small")
    ... def some_func(x: int, y: int = 5) -> None:
    ...     pass
    ...
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.errors.ViolationError: File <doctest README.rst[4]>, line 1 in <module>:
    x must not be small: x > 3: x was 1

    # Pre-condition violation with more complex values
    >>> class B:
    ...     def __init__(self) -> None:
    ...         self.x = 7
    ...
    ...     def y(self) -> int:
    ...         return 2
    ...
    ...     def __repr__(self) -> str:
    ...         return "instance of B"
    ...
    >>> class A:
    ...     def __init__(self)->None:
    ...         self.b = B()
    ...
    ...     def __repr__(self) -> str:
    ...         return "instance of A"
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
    icontract.errors.ViolationError: File <doctest README.rst[9]>, line 1 in <module>:
    a.b.x + a.b.y() > SOME_GLOBAL_VAR:
    SOME_GLOBAL_VAR was 13
    a was instance of A
    a.b was instance of B
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
    icontract.errors.ViolationError: File <doctest README.rst[12]>, line 1 in <module>:
    result > x:
    result was 5
    x was 10

Invariants
----------
Invariants are special contracts associated with an instance of a class. An invariant should hold *after* initialization
and *before* and *after* a call to any public instance method. The invariants are the pivotal element of
design-by-contract: they allow you to formally define properties of a data structures that you know will be maintained
throughout the life time of *every* instance.

We consider the following methods to be "public":

* All methods not prefixed with ``_``
* All magic methods (prefix ``__`` and suffix ``__``)

Class methods (marked with ``@classmethod`` or special dunders such as ``__new__``) can not observe the invariant
since they are not associated with an instance of the class.

We exempt ``__getattribute__``, ``__setattr__`` and ``__delattr__`` methods from observing the invariant since
these functions alter the state of the instance and thus can not be considered "public".

We also excempt ``__repr__`` method to prevent endless loops when generating error messages.

The icontract invariants are implemented as class decorators.

The following examples show various cases when an invariant is breached.

After the initialization:

.. code-block:: python

        >>> @icontract.invariant(lambda self: self.x > 0)
        ... class SomeClass:
        ...     def __init__(self) -> None:
        ...         self.x = -1
        ...
        ...     def __repr__(self) -> str:
        ...         return "some instance"
        ...
        >>> some_instance = SomeClass()
        Traceback (most recent call last):
         ...
        icontract.errors.ViolationError: File <doctest README.rst[14]>, line 1 in <module>:
        self.x > 0:
        self was some instance
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
    ...         return "some instance"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance.x = -1
    >>> some_instance.some_method()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest README.rst[16]>, line 1 in <module>:
    self.x > 0:
    self was some instance
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
    ...         return "some instance"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance.some_method()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest README.rst[20]>, line 1 in <module>:
    self.x > 0:
    self was some instance
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
    ...         return "some instance"
    ...
    >>> some_instance = SomeClass()
    >>> some_instance()
    Traceback (most recent call last):
     ...
    icontract.errors.ViolationError: File <doctest README.rst[23]>, line 1 in <module>:
    self.x > 0:
    self was some instance
    self.x was -1

Snapshots (a.k.a "old" argument values)
---------------------------------------
Usual postconditions can not verify the state transitions of the function's argument values. For example, it is
impossible to verify in a postcondition that the list supplied as an argument was appended an element since the
postcondition only sees the argument value as-is after the function invocation.

In order to verify the state transitions, the postcondition needs the "old" state of the argument values
(*i.e.* prior to the invocation of the function) as well as the current values (after the invocation).
``icontract.snapshot`` decorator instructs the checker to take snapshots of the argument values before the function call
which are then supplied as ``OLD`` argument to the postcondition function.

``icontract.snapshot`` takes a capture function which accepts none, one or more arguments of the function.
You set the name of the property in ``OLD`` as ``name`` argument to ``icontract.snapshot``. If there is a single
argument passed to the the capture function, the name of the ``OLD`` property can be omitted and equals the name
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
    icontract.errors.ViolationError: File <doctest README.rst[28]>, line 2 in <module>:
    lst == OLD.lst + [value]:
    OLD was a bunch of OLD values
    OLD.lst was [1, 2]
    lst was [1, 2, 3, 1984]
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
    icontract.errors.ViolationError: File <doctest README.rst[32]>, line 2 in <module>:
    len(lst) == OLD.len_lst + 1:
    OLD was a bunch of OLD values
    OLD.len_lst was 2
    len(lst) was 4
    lst was [1, 2, 3, 1984]

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
    icontract.errors.ViolationError: File <doctest README.rst[36]>, line ... in <module>:
    set(lst_a).union(lst_b) == OLD.union:
    OLD was a bunch of OLD values
    OLD.union was {1, 2, 3, 4}
    lst_a was [1, 2, 1984]
    lst_b was [3, 4]
    set(lst_a) was {1, 2, 1984}
    set(lst_a).union(lst_b) was {1, 2, 3, 4, 1984}

Inheritance
-----------
To inherit the contracts of the parent class, the child class needs to either inherit from ``icontract.DBC`` or have
a meta class set to ``icontract.DBCMeta``.

When no contracts are specified in the child class, all contracts are inherited from the parent class as-are.

When the child class introduces additional preconditions or postconditions and invariants, these contracts are
*strengthened* or *weakened*, respectively. ``icontract.DBCMeta`` allows you to specify the contracts not only on the
concrete classes, but also on abstract classes.

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

**Abstract Classes**. Since Python 3 does not allow multiple meta classes, ``icontract.DBCMeta`` inherits from
``abc.ABCMeta`` to allow combining contracts with abstract base classes.

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
        ...         return "instance of A"

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
        ...         return "instance of B"

        # Break the parent's postcondition
        >>> some_b = B()
        >>> some_b.func(y=0)
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest README.rst[40]>, line 7 in A:
        result < y:
        result was 1
        y was 0

        # Break the parent's invariant
        >>> another_b = B()
        >>> another_b.break_parent_invariant()
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest README.rst[40]>, line 1 in <module>:
        self.x > 0:
        self was instance of B
        self.x was -1

        # Break the child's invariant
        >>> yet_another_b = B()
        >>> yet_another_b.break_my_invariant()
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest README.rst[41]>, line 1 in <module>:
        self.x < 100:
        self was instance of B
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
        icontract.errors.ViolationError: File <doctest README.rst[49]>, line 2 in B:
        x % 3 == 0: x was 5

The example below illustrates how snaphots are inherited:

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

        >>> b = B()
        >>> b.func(lst=[1, 2], value=3)
        Traceback (most recent call last):
            ...
        icontract.errors.ViolationError: File <doctest README.rst[54]>, line 4 in A:
        len(lst) == len(OLD.lst) + 1:
        OLD was a bunch of OLD values
        OLD.lst was [1, 2]
        len(OLD.lst) was 2
        len(lst) was 4
        lst was [1, 2, 3, 1984]


Toggling Contracts
------------------
By default, the contract checks (including the snapshots) are always perfromed at run-time. To disable them, run the
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

Icontract raises ``ViolationError`` by default. However, you can also instruct icontract to raise a different error
by supplying ``error`` argument to the decorator.

The ``error`` argument can either be:

* **An exception class.** The exception is constructed with the violation message and finally raised.
* **A callable that returns an exception.** The callable accepts the subset of arguments of the original function
  (including ``result`` and ``OLD`` for postconditions) or ``self`` in case of invariants, respectively,
  and returns an exception. The arguments to the condition function can freely differ from the arguments
  to the error function.

  The exception returned by the given callable is finally raised.

  If you specify the ``error`` argument as callable, the values will not be traced and the condition function will not
  be parsed. Hence, violation of contracts with ``error`` arguments as callables incur a much smaller computational
  overhead in case of violations compared to contracts with default violation messages for which we need to  trace
  the argument values and parse the condition function.

Here is an example of the error given as an exception class:

.. code-block:: python

    >>> @icontract.require(lambda x: x > 0, error=ValueError)
    ... def some_func(x: int) -> int:
    ...     return 123
    ...

    # Custom Exception class
    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    ValueError: File <doctest README.rst[60]>, line 1 in <module>:
    x > 0: x was 0

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

Implementation Details
----------------------

**Decorator stack**. The precondition and postcondition decorators have to be stacked together to allow for inheritance.
Hence, when multiple precondition and postcondition decorators are given, the function is actually decorated only once
with a precondition/postcondition checker while the contracts are stacked to the checker's ``__preconditions__`` and
``__postconditions__`` attribute, respectively. The checker functions iterates through these two attributes to verify
the contracts at run-time.

All the decorators in the function's decorator stack are expected to call ``functools.update_wrapper()``.
Notably, we use ``__wrapped__`` attribute to iterate through the decorator stack and find the checker function which is
set with ``functools.update_wrapper()``. Mind that this implies that preconditions and postconditions are verified at
the inner-most decorator and *not* when outer preconditios and postconditions are defined.

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

**Invariants**. Since invariants are handled by a class decorator (in contrast to function decorators that handle
preconditions and postconditions), they do not need to be stacked. The first invariant decorator wraps each public
method of a class with a checker function. The invariants are added to the class' ``__invariants__`` attribute.
At run-time, the checker function iterates through the ``__invariants__`` attribute when it needs to actually verify the
invariants.

Mind that we still expect each class decorator that decorates the class functions to use ``functools.update_wrapper()``
in order to be able to iterate through decorator stacks of the individual functions.

**Recursion in contracts**. In certain cases functions depend on each other through contracts. Consider the following
snippet:

.. code-block:: python

    @icontract.require(lambda: another_func())
    def some_func() -> bool:
        ...

    @icontract.require(lambda: some_func())
    def another_func() -> bool:
        ...

    some_func()

Naïvely evaluating such preconditions and postconditions would result in endless recursions. Therefore, icontract
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

Linter
------
We provide a linter that statically verifies the arguments of the contracts (*i.e.* that they are
well-defined with respect to the function). The tool is available as a separate package,
`pyicontract-lint <https://pypi.org/project/pyicontract-lint>`_.

Sphinx
------
We implemented a Sphinx extension to include contracts in the documentation. The extension is available as a package
`sphinx-icontract <https://pypi.org/project/sphinx-icontract>`_.

Checking Types at Runtime
-------------------------
Icontract focuses on logical contracts in the code. Theoretically, you could use icontract to check the types
at runtime and condition the contracts using
`material implication <https://en.wikipedia.org/wiki/Material_implication_(rule_of_inference)>`_:

.. code-block:: python

        @icontract.require(lambda x: not isinstance(x, int) or x > 0)
        @icontract.require(lambda x: not isinstance(x, str) or x.startswith('x-'))
        def some_func(x: Any) -> None
            ...

This is a good solution if your code lacks type annotations or if you do not know the type in advance.

However, if you already annotated the code with the type annotations, re-stating the types in the contracts
breaks the `DRY principle <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_ and makes the code
unnecessarily hard to maintain and read:

.. code-block:: python

        @icontract.require(lambda x: isinstance(x, int))
        def some_func(x: int) -> None
            ...

Elegant runtime type checks are out of icontract's scope. We would recommend you to use one of the available
libraries specialized only on such checks such as `typeguard <https://pypi.org/project/typeguard/>`_.

The icontract's test suite explicitly includes tests to make sure that icontract and typeguard work well together and
to enforce their interplay in the future.

Known Issues
============
**Integration with ``help()``**. We wanted to include the contracts in the output of ``help()``. Unfortunately,
``help()`` renders the ``__doc__`` of the class and not of the instance. For functions, this is the class
"function" which you can not inherit from. See this
`discussion on python-ideas <https://groups.google.com/forum/#!topic/python-ideas/c9ntrVuh6WE>`_ for more details.

**Defining contracts outside of decorators**. We need to inspect the source code of the condition and error lambdas to
generate the violation message and infer the error type in the documentation, respectively. ``inspect.getsource(.)``
is broken on lambdas defined in decorators in Python 3.5.2+ (see
`this bug report <https://bugs.python.org/issue21217>`_). We circumvented this bug by using ``inspect.findsource(.)``,
``inspect.getsourcefile(.)`` and examining the local source code of the lambda by searching for other decorators
above and other decorators and a function or class definition below. The decorator code is parsed and then we match
the condition and error arguments in the AST of the decorator. This is brittle as it prevents us from having
partial definitions of contract functions or from sharing the contracts among functions.

Here is a short code snippet to demonstrate where the current implementation fails:

.. code-block:: python

    >>> require_x_positive = icontract.require(lambda x: x > 0)

    >>> @require_x_positive
    ... def some_func(x: int) -> None:
    ...     pass

    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    SyntaxError: Decorator corresponding to the line 1 could not be found in file <doctest README.rst[74]>: 'require_x_positive = icontract.require(lambda x: x > 0)\n'

However, we haven't faced a situation in the code base where we would do something like the above, so we are unsure
whether this is a big issue. As long as decorators are directly applied to functions and classes, everything
worked fine on our code base.

**`*args` and `**kwargs`**. Since handling variable number of positional and/or keyword arguments requires complex
logic and entails many edge cases (in particular in relation to how the arguments from the actual call are resolved and
passed to the contract), we did not implement it. These special cases also impose changes that need to propagate to
rendering the violation messages and related tools such as pyicontract-lint and sphinx-icontract. This is a substantial
effort and needs to be prioritized accordingly.

Before we spend a large amount of time on this feature, please give us a signal through
`the issue 147 <https://github.com/Parquery/icontract/issues/147>`_ and describe your concrete use case and its
relevance. If there is enough feedback from the users, we will of course consider implementing it.

Benchmarks
==========
We run benchmarks against `deal` and `dpcontracts` libraries as part of our continuous integration.

The bodies of the constructors and functions were intentionally left simple so that you can
better estimate **overhead** of the contracts in absolute terms rather than relative.
This means that the code without contracts will run extremely fast (nanoseconds) in the benchmarks
which might make the contracts seem sluggish. However, the methods in the real world usually run
in the order of microseconds and milliseconds, not nanoseconds. As long as the overhead
of the contract is in the order of microseconds, it is often practically acceptable.

.. Becnhmark report from precommit.py starts.


The following scripts were run:

* `benchmarks/against_others/compare_invariant.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_invariant.py>`_
* `benchmarks/against_others/compare_precondition.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_precondition.py>`_
* `benchmarks/against_others/compare_postcondition.py <https://github.com/Parquery/icontract/tree/master/benchmarks/against_others/compare_postcondition.py>`_

The benchmarks were executed on Intel(R) Xeon(R) E-2276M  CPU @ 2.80GHz.
We used Python 3.8.5, icontract 2.3.5, deal 4.2.0 and dpcontracts 0.6.0.

The following tables summarize the results.

Benchmarking invariant at __init__:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             1.74 s         1.74 μs                     100%
`ClassWithDpcontracts`           0.55 s         0.55 μs                      32%
`ClassWithDeal`                  3.26 s         3.26 μs                     187%
`ClassWithInlineContract`        0.33 s         0.33 μs                      19%
=========================  ============  ==============  =======================

Benchmarking invariant at a function:

=========================  ============  ==============  =======================
Case                         Total time    Time per run    Relative time per run
=========================  ============  ==============  =======================
`ClassWithIcontract`             2.48 s         2.48 μs                     100%
`ClassWithDpcontracts`           0.56 s         0.56 μs                      22%
`ClassWithDeal`                  9.76 s         9.76 μs                     393%
`ClassWithInlineContract`        0.28 s         0.28 μs                      11%
=========================  ============  ==============  =======================

Benchmarking precondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.03 s         3.17 μs                     100%
`function_with_dpcontracts`            0.65 s        64.62 μs                    2037%
`function_with_deal`                   0.16 s        16.04 μs                     506%
`function_with_inline_contract`        0.00 s         0.17 μs                       6%
===============================  ============  ==============  =======================

Benchmarking postcondition:

===============================  ============  ==============  =======================
Case                               Total time    Time per run    Relative time per run
===============================  ============  ==============  =======================
`function_with_icontract`              0.03 s         3.01 μs                     100%
`function_with_dpcontracts`            0.66 s        65.78 μs                    2187%
`function_with_deal_post`              0.01 s         1.12 μs                      37%
`function_with_deal_ensure`            0.02 s         1.62 μs                      54%
`function_with_inline_contract`        0.00 s         0.18 μs                       6%
===============================  ============  ==============  =======================



.. Benchmark report from precommit.py ends.

Note that neither the `dpcontracts` nor the `deal` library support recursion and inheritance of the contracts.
This allows them to use faster enforcement mechanisms and thus gain a speed-up.

We also ran a much more extensive battery of benchmarks on icontract 2.0.7. Unfortunately,
it would cost us too much effort to integrate the results in the continous integration.
The report is available at:
`benchmarks/benchmark_2.0.7.rst <https://github.com/Parquery/icontract/tree/master/benchmarks/benchmark_2.0.7.rst>`_.

The scripts are available at:
`benchmarks/import_cost/ <https://github.com/Parquery/icontract/tree/master/benchmarks/import_cost>`_
and
`benchmarks/runtime_cost/ <https://github.com/Parquery/icontract/tree/master/benchmarks/runtime_cost>`_.
Please re-run the scripts manually to obtain the results with the latest icontract version.

Installation
============

* Install icontract with pip:

.. code-block:: bash

    pip3 install icontract

Development
===========

* Check out the repository.

* In the repository root, create the virtual environment:

.. code-block:: bash

    python3 -m venv venv3

* Activate the virtual environment:

.. code-block:: bash

    source venv3/bin/activate

* Install the development dependencies:

.. code-block:: bash

    pip3 install -e .[dev]

* We use tox for testing and packaging the distribution. Run:

.. code-block:: bash

    tox

* We also provide a set of pre-commit checks that lint and check code for formatting. Run them locally from an activated
  virtual environment with development dependencies:

.. code-block:: bash

    ./precommit.py

* The pre-commit script can also automatically format the code:

.. code-block:: bash

    ./precommit.py  --overwrite

Versioning
==========
We follow `Semantic Versioning <http://semver.org/spec/v1.0.0.html>`_. The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).
