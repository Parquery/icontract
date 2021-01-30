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

.. image:: https://readthedocs.org/projects/icontract/badge/?version=latest
    :target: https://icontract.readthedocs.io/en/latest/
    :alt: Documentation

.. image:: https://badges.gitter.im/gitterHQ/gitter.svg
    :target: https://gitter.im/Parquery-icontract/community
    :alt: Gitter chat

icontract provides `design-by-contract <https://en.wikipedia.org/wiki/Design_by_contract>`_ to Python3 with informative
violation messages and inheritance.

It also gives a base for a flourishing of a wider ecosystem:

* A linter `pyicontract-lint <https://pypi.org/project/pyicontract-lint>`__,
* A sphinx plug-in `sphinx-icontract <https://pypi.org/project/sphinx-icontract>`_,
* A tool `icontract-hypothesis <https://github.com/mristin/icontract-hypothesis>`_
  for automated testing and ghostwriting test files which infers
  `Hypothesis <https://hypothesis.readthedocs.io/en/latest/>`_ strategies based on the contracts,

  * together with IDE integrations such as
    `icontract-hypothesis-vim <https://github.com/mristin/icontract-hypothesis-vim>`_,
    `icontract-hypothesis-pycharm <https://github.com/mristin/icontract-hypothesis-pycharm>`_, and
    `icontract-hypothesis-vscode <https://github.com/mristin/icontract-hypothesis-vscode>`_,
* An ongoing integration with `CrossHair <https://github.com/pschanely/CrossHair>`_, and
* An ongoing integration with `FastAPI <https://github.com/tiangolo/fastapi/issues/1996>`_.

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
is a feature indispensable for modeling many non-trivial class hierarchies. Please see Section
`Inheritance <https://icontract.readthedocs.io/en/latest/usage.html#inheritance>`_.
To the best of our knowledge, there is currently no other Python library that supports inheritance of the contracts in a
correct way.

In the long run, we hope that design-by-contract will be adopted and integrated in the language. Consider this library
a work-around till that happens. You might be also interested in the archived discussion on how to bring
design-by-contract into Python language on
`python-ideas mailing list <https://groups.google.com/forum/#!topic/python-ideas/JtMgpSyODTU>`_.

Usage
=====
We give a couple of teasers here to motivate the library.
Please see the documentation available on `icontract.readthedocs.io
<https://icontract.readthedocs.io/en/latest/>`_ for a full scope of its
capabilities.

.. code-block:: python

    import icontract
    
    def runner(func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            breakpoint()
        except icontract.errors.ViolationError as exc:
            breakpoint()
            print(exc)
    
    @icontract.require(lambda x: x > 3)
    def some_func(x: int, y: int = 5) -> None:
        pass
    
    runner(some_func, x=5)
    runner(some_func, x=1)
    
    @icontract.require(lambda x: x > 3, "x must not be small")
    def some_func(x: int, y: int = 5) -> None:
        pass
    
    runner(some_func, x=1)
    
    class B:
        def __init__(self) -> None:
            self.x = 7
    
        def y(self) -> int:
            return 2
    
        def __repr__(self) -> str:
            return "instance of B"
    
    class A:
        def __init__(self) -> None:
            self.b = B()
    
        def __repr__(self) -> str:
            return "instance of A"
    
    SOME_GLOBAL_VAR = 13
    @icontract.require(lambda a: a.b.x + a.b.y() > SOME_GLOBAL_VAR)
    def some_func(a: A) -> None:
        pass
    
    an_a = A()
    runner(some_func, an_a)
    
    # Post-condition
    @icontract.ensure(lambda result, x: result > x)
    def some_func(x: int, y: int = 5) -> int:
        return x - y
    
    runner(some_func, x=10)
    
    # Pre-conditions fail before Post-conditions
    @icontract.ensure(lambda result, x: result > x)
    @icontract.require(lambda x: x > 3, "x must not be small")
    def some_func(x: int, y: int = 5) -> int:
        return x - y
    
    runner(some_func, x=3)
    
    # Invariant
    @icontract.invariant(lambda self: self.x > 0)
    class SomeClass:
        def __init__(self) -> None:
            self.x = -1
    
        def __repr__(self) -> str:
            return "some instance"
    
    some_instance = SomeClass()


Installation
============

* Install icontract with pip:

.. code-block:: bash

    pip3 install icontract

Versioning
==========
We follow `Semantic Versioning <http://semver.org/spec/v1.0.0.html>`_. The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).
