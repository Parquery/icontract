Introduction
============
Icontract provides `design-by-contract <https://en.wikipedia.org/wiki/Design_by_contract>`_ to Python3 with informative
violation messages and inheritance.

It also gives a base for a flourishing of a wider ecosystem:

* A linter `pyicontract-lint`_,
* A sphinx plug-in `sphinx-icontract`_,
* A tool `icontract-hypothesis`_ for automated testing and ghostwriting test files which infers
  `Hypothesis`_ strategies based on the contracts,

  * together with IDE integrations such as
    `icontract-hypothesis-vim`_,
    `icontract-hypothesis-pycharm`_, and
    `icontract-hypothesis-vscode`_,
* Directly integrated into `CrossHair`_, a tool for automatic verification of Python programs,

  * together with IDE integrations such as
    `crosshair-pycharm`_ and `crosshair-vscode`_, and
* An integration with `FastAPI`_ through `fastapi-icontract`_ to enforce contracts on your HTTP API and display them
  in OpenAPI 3 schema and Swagger UI, and
* An extensive corpus, `Python-by-contract corpus`_, of Python programs annotated with contracts for educational, testing and research purposes.

.. _pyicontract-lint: https://pypi.org/project/pyicontract-lint
.. _sphinx-icontract: https://pypi.org/project/sphinx-icontract
.. _icontract-hypothesis: https://github.com/mristin/icontract-hypothesis
.. _Hypothesis: https://hypothesis.readthedocs.io/en/latest/
.. _icontract-hypothesis-vim: https://github.com/mristin/icontract-hypothesis-vim
.. _icontract-hypothesis-pycharm: https://github.com/mristin/icontract-hypothesis-pycharm
.. _icontract-hypothesis-vscode: https://github.com/mristin/icontract-hypothesis-vscode
.. _CrossHair: https://github.com/pschanely/CrossHair
.. _crosshair-pycharm: https://github.com/mristin/crosshair-pycharm/
.. _crosshair-vscode: https://github.com/mristin/crosshair-vscode/
.. _FastAPI: https://github.com/tiangolo/fastapi/issues/1996
.. _fastapi-icontract: https://pypi.org/project/fastapi-icontract/
.. _Python-by-contract corpus: https://github.com/mristin/python-by-contract-corpus

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

Second, icontract allows inheritance of the contracts and supports weakening of the preconditions
as well as strengthening of the postconditions and invariants. Notably, weakening and strengthening of the contracts
is a feature indispensable for modeling many non-trivial class hierarchies. Please see Section :ref:`Inheritance`.
To the best of our knowledge, there is currently no other Python library that supports inheritance of the contracts in a
correct way.

In the long run, we hope that design-by-contract will be adopted and integrated in the language. Consider this library
a work-around till that happens. You might be also interested in the archived discussion on how to bring
design-by-contract into Python language on
`python-ideas mailing list <https://groups.google.com/forum/#!topic/python-ideas/JtMgpSyODTU>`_.
