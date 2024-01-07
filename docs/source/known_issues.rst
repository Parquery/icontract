Known Issues
============
Integration with ``help()``
---------------------------

We wanted to include the contracts in the output of ``help()``. Unfortunately,
``help()`` renders the ``__doc__`` of the class and not of the instance. For functions, this is the class
"function" which you can not inherit from. See this
`discussion on python-ideas <https://groups.google.com/forum/#!topic/python-ideas/c9ntrVuh6WE>`_ for more details.

Defining contracts outside of decorators
----------------------------------------
We need to inspect the source code of the condition and error lambdas to
generate the violation message and infer the error type in the documentation, respectively. ``inspect.getsource(.)``
is broken on lambdas defined in decorators in Python 3.5.2+ (see
`this bug report <https://bugs.python.org/issue21217>`_). We circumvented this bug by using ``inspect.findsource(.)``,
``inspect.getsourcefile(.)`` and examining the local source code of the lambda by searching for other decorators
above and other decorators and a function or class definition below. The decorator code is parsed and then we match
the condition and error arguments in the AST of the decorator. This is brittle as it prevents us from having
partial definitions of contract functions or from sharing the contracts among functions.

Here is a short code snippet to demonstrate where the current implementation fails:

.. code-block:: python

    >>> import icontract

    >>> require_x_positive = icontract.require(lambda x: x > 0)

    >>> @require_x_positive
    ... def some_func(x: int) -> None:
    ...     pass

    >>> some_func(x=0)
    Traceback (most recent call last):
        ...
    SyntaxError: Decorator corresponding to the line 1 could not be found in file <doctest known_issues.rst[1]>: 'require_x_positive = icontract.require(lambda x: x > 0)\n'

However, we haven't faced a situation in the code base where we would do something like the above, so we are unsure
whether this is a big issue. As long as decorators are directly applied to functions and classes, everything
worked fine on our code base.

``*args`` and ``**kwargs``
--------------------------
Since handling variable number of positional and/or keyword arguments requires complex
logic and entails many edge cases (in particular in relation to how the arguments from the actual call are resolved and
passed to the contract), we did not implement it. These special cases also impose changes that need to propagate to
rendering the violation messages and related tools such as pyicontract-lint and sphinx-icontract. This is a substantial
effort and needs to be prioritized accordingly.

Before we spend a large amount of time on this feature, please give us a signal through
`the issue 147 <https://github.com/Parquery/icontract/issues/147>`_ and describe your concrete use case and its
relevance. If there is enough feedback from the users, we will of course consider implementing it.

``dataclasses``
---------------
When you define contracts for `dataclasses <https://docs.python.org/3/library/dataclasses.html>`_, make sure you define the contracts *after* decorating the class with ``@dataclass`` decorator:

.. code-block:: python

    >>> import icontract
    >>> import dataclasses

    >>> @icontract.invariant(lambda self: self.x > 0)
    ... @dataclasses.dataclass
    ... class Foo:
    ...     x: int = dataclasses.field(default=42)


This is necessary as we can not re-decorate the methods that ``dataclass`` decorator inserts.
