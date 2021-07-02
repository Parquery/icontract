Async
=====

Icontract supports both adding sync contracts to `coroutine functions <coroutine function_>`_ as well as enforcing
*async conditions* (and capturing *async snapshots*).

.. _coroutine function: https://docs.python.org/3/glossary.html#term-coroutine-function

You simply define your conditions as decorators of a `coroutine function`_:

.. code-block:: python

    import icontract

    @icontract.require(lambda x: x > 0)
    @icontract.ensure(lambda x, result: x < result)
    async def do_something(x: int) -> int:
        ...


Special Considerations
----------------------
**Async conditions**.
If you want to enforce async conditions, the function also needs to be defined as async:

.. code-block:: python

    import icontract

    async def has_author(author_id: str) -> bool:
        ...

    @icontract.ensure(has_author)
    async def upsert_author(name: str) -> str:
        ...

It is not possible to add an async condition to a sync function.
Doing so will raise a `ValueError`_ at runtime.
The reason behind this limitation is that the wrapper around the function would need to be made async, which would
break the code calling the original function and expecting it to be synchronous.

**Invariants**.
As invariants need to wrap dunder methods, including ``__init__``, their conditions *can not* be
async, as most dunder methods need to be synchronous methods, and wrapping them with async code would
break that constraint.
You can, of course, use synchronous invariants on *async* method functions without problems.

.. _no_async_lambda_limitation:

**No async lambda**.
Another practical limitation is that Python does not support async lambda (see `this Python issue`_),
so defining async conditions (and snapshots) is indeed tedious (see the
:ref:`next section <coroutine as condition result>`).
Please consider asking for async lambdas on `python-ideas mailing list`_ to give the issue some visibility.

.. _this Python issue: https://bugs.python.org/issue33447
.. _python-ideas mailing list: https://mail.python.org/mailman3/lists/python-ideas.python.org/

.. _coroutine as condition result:

**Coroutine as condition result**.
If the condition returns a `coroutine`_, the `coroutine`_ will be awaited before it is evaluated for truthiness.

This means in practice that you can work around :ref:`no-async lambda limitation <no_async_lambda_limitation>` applying coroutine functions
on your condition arguments (which in turn makes the condition result in a `coroutine`_).

.. _coroutine: https://docs.python.org/3/glossary.html#term-coroutine

For example:

.. code-block:: python

        async def some_condition(a: float, b: float) -> bool:
            ...

        @icontract.require(lambda x: some_condition(a=x, b=x**2))
        async def some_func(x: float) -> None:
            ...

A big fraction of contracts on sequences require an `all`_ operation to check that all the item of a sequence are
``True``.
Unfortunately, `all`_ does not automatically operate on a sequence of `Awaitables <awaitable_>`_,
but the library `asyncstdlib`_ comes in very handy:

.. _all: https://docs.python.org/3/library/functions.html#all
.. _awaitable: https://docs.python.org/3/library/asyncio-task.html#awaitables
.. _asyncstdlib: https://pypi.org/project/asyncstdlib/

.. code-block:: python

    import asyncstdlib as a

Here is a practical example that uses `asyncstdlib.map`_, `asyncstdlib.all`_ and `asyncstdlib.await_each`_:

.. _asyncstdlib.map: https://asyncstdlib.readthedocs.io/en/latest/source/api/builtins.html#asyncstdlib.builtins.map
.. _asyncstdlib.all: https://asyncstdlib.readthedocs.io/en/latest/source/api/builtins.html#asyncstdlib.builtins.all
.. _asyncstdlib.await_each: https://asyncstdlib.readthedocs.io/en/latest/source/api/asynctools.html#asyncstdlib.asynctools.await_each

.. code-block:: python

    import asyncstdlib as a

    async def has_author(identifier: str) -> bool:
        ...

    async def has_category(category: str) -> bool:
        ...

    @dataclasses.dataclass
    class Book:
        identifier: str
        author: str

    @icontract.require(lambda categories: a.map(has_category, categories))
    @icontract.ensure(
        lambda result: a.all(a.await_each(has_author(book.author) for book in result)))
    async def list_books(categories: List[str]) -> List[Book]:
        ...

**Coroutines have side effects.**
If the condition of a contract returns a `coroutine`_, the condition can not be
re-computed upon the violation to produce an informative violation message.
This means that you need to :ref:`specify an explicit error <custom-errors>` which should be raised
on contract violation.

For example:

.. code-block:: python

    async def some_condition() -> bool:
        ...

    @icontract.require(
        lambda: some_condition(),
        error=lambda: icontract.ViolationError("Something went wrong."))

If you do not specify the error, and the condition returns a `coroutine`_, the decorator will raise a
`ValueError`_ at re-computation time.

.. _ValueError: https://docs.python.org/3/library/exceptions.html#ValueError
