icontract
=========
.. image:: https://travis-ci.com/Parquery/icontract.svg?branch=master
    :target: https://travis-ci.com/Parquery/icontract

.. image:: https://coveralls.io/repos/github/Parquery/icontract/badge.svg?branch=master
    :target: https://coveralls.io/github/Parquery/icontract

icontract provides `design-by-contract <https://en.wikipedia.org/wiki/Design_by_contract>`_ to Python3 with informative
violation messages.

There exist a couple of contract libraries. However, at the time of this writing (July 2018), they all required the
programmer either to learn a new syntax (`PyContracts <https://pypi.org/project/PyContracts/>`_) or to write
redundant condition descriptions (
*e.g.*,
`contracts <https://pypi.org/project/contracts/>`_,
`covenant <https://github.com/kisielk/covenant>`_,
`dpcontracts <https://pypi.org/project/dpcontracts/>`_,
`pyadbc <https://pypi.org/project/pyadbc/>`_ and
`pcd <https://pypi.org/project/pcd>`_).

This library was strongly inspired by them, but we go a step further and use the
`meta <https://github.com/srossross/Meta>`_ programming library to infer violation messages from the code in order to
promote dont-repeat-yourself principle (`DRY <https://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`_) and spare the
programmer the tedious task of repeating the message that was already written in code.

We want this library to be used mainly in production code and let us spot both development and production bugs with
enough information. Therefore, we decided to implement only the pre-conditions and post-conditions which require
little overhead, and intentionally left out the class invariants.  Class invariants seem to us tricky to grasp (
for example, depending on the design class invariants may hold only at the first call of the public function, but
not in the private functions; or they may hold only at the first call to a method of a class, but not in the sequent
calls to other class methods *etc.*). The invariants hence need to come with an overhead which is generally impractical
for production systems.

Usage
=====
icontract provides two decorators, ``pre`` and ``post`` for pre-conditions and post-conditions, respectively.

The ``condition`` argument specifies the contract and is usually written in lambda notation. In post-conditions,
condition function receives a reserved parameter ``result`` corresponding to the result of the function. The condition
can take as input a subset of arguments required by the wrapped function. This allows for very succinct conditions.

You can provide an optional description by passing in ``description`` argument.

Whenever a violation occurs, ``ViolationError`` is raised. Its message includes:

* the human-readable representation of the condition,
* description (if supplied) and
* representation of all the values.

You can provide a custom representation function with the argument ``repr_args`` that needs to cover all the input
arguments (including ``result`` in post-conditions) of the condition function and return a string. If no representation
function was specified, the input arguments are represented by concatenation of ``__repr__`` on each one of them.

If no custom representation function has been supplied, the representation of the values is obtained by re-executing
the condition function programmatically by traversing its abstract syntax tree and filling the tree leaves with
values held in the function frame. Mind that this re-execution will also re-execute all the functions.
Therefore you need to make sure that all the function calls involved in the condition functions do not have any side
effects.

.. code-block:: python

    >>> import icontract

    >>> @icontract.pre(lambda x: x > 3)
    ... def some_func(x: int, y: int = 5)->None:
    ...     pass
    ...

    >>> some_func(x=5)

    # Pre-condition violation
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.ViolationError: Precondition violated: x > 3: x was 1

    # Pre-condition violation with a description
    >>> @icontract.pre(lambda x: x > 3, "x must not be small")
    ... def some_func(x: int, y: int = 5) -> None:
    ...     pass
    ...
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.ViolationError: Precondition violated: x must not be small: x > 3: x was 1

    # Pre-condition violation with a custom representation function
    >>> @icontract.pre(lambda x: x > 3, repr_args=lambda x: "x was 0x{:x}".format(x))
    ... def some_func(x: int, y: int = 5) -> None:
    ...     pass
    ...
    >>> some_func(x=1)
    Traceback (most recent call last):
      ...
    icontract.ViolationError: Precondition violated: x > 3: x was 0x1


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
    >>> @icontract.pre(lambda a: a.b.x + a.b.y() > SOME_GLOBAL_VAR)
    ... def some_func(a: A) -> None:
    ...     pass
    ...
    >>> an_a = A()
    >>> some_func(an_a)
    Traceback (most recent call last):
      ...
    icontract.ViolationError: Precondition violated: (a.b.x + a.b.y()) > SOME_GLOBAL_VAR:
    SOME_GLOBAL_VAR was 13
    a was instance of A
    a.b was instance of B
    a.b.x was 7
    a.b.y() was 2

    # Post-condition
    >>> @icontract.post(lambda result, x: result > x)
    ... def some_func(x: int, y: int = 5) -> int:
    ...     return x - y
    ...
    >>> some_func(x=10)
    Traceback (most recent call last):
      ...
    icontract.ViolationError: Post-condition violated: result > x:
    result was 5
    x was 10

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
