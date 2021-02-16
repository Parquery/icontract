Async
=====

Icontract supports both adding sync contracts to *async functions* as well as enforcing *async conditions* (and
capturing *async snapshots*).

You simply define your conditions as decorators of an async function:

.. code-block:: python

    import icontract

    @icontract.require(lambda x: x > 0)
    @icontract.ensure(lambda x, result: x < result)
    async def do_something(x: int) -> int:
        ...


Limitations
-----------
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
Doing so will raise a ``ValueError`` at runtime.
The reason behind this limitation is that the wrapper around the function would need to be made async, which would
break the code calling the original function and expecting it to be synchronous.

**Invariants**.
As invariants need to wrap dunder methods, including ``__init__``, their conditions *can not* be
async, as most dunder methods need to be synchronous methods, and wrapping them with async code would
break that constraint.
You can, of course, use synchronous invariants on *async* method functions without problems.

**No async lambda**.
Another practical limitation is that Python does not support async lambda (see `this Python issue`_),
so defining async conditions (and snapshots) is indeed tedious.
Please consider asking for async lambdas on `python-ideas mailing list`_ to give the issue some visibility.

.. _this Python issue: https://bugs.python.org/issue33447
.. _python-ideas mailing list: https://mail.python.org/mailman3/lists/python-ideas.python.org/
