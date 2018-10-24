2.0.0
=====
* Removed ``repr_args`` argument to contracts since it is superseded by more versatile ``error`` argument
* Renamed contracts to follow naming used in other languages and libraries (``require``, ``ensure`` and ``invariant``)
* Improved error messages on missing arguments in the call

1.7.2
=====
* Demarcated decorator and lambda inspection in ``_represent`` submodule

1.7.1
=====
* Refactored implementation and tests into smaller modules

1.7.0
=====
* Added ``snapshot`` decorator to capture "old" values (prior to function invocation) for postconditions that verify
  state transitions

1.6.1
=====
* Replaced ``typing.Type`` with ``type`` so that icontract works with Python 3.5.2

1.6.0
=====
* Added ``error`` argument to the contracts

1.5.9
=====
* Removed ``ast_graph`` module which was only used for debugging
* Prefixed internal modules with an underscore (``_represent`` and ``_recompute``)

1.5.8
=====
* ``recompute`` propagates to children of generator expressions and comprehensions
* Optimized parsing of condition lambdas by considering only lines local to the decorator

1.5.7
=====
* Exempted ``__init__`` from inheritance of preconditions and postconditions if defined in the
  concrete class.

1.5.6
=====
* Contracts are observed and inherited with property getters, setters and deleters.
* Weakining of preconditions of a base function without any preconditions raises ``TypeError``.
* ``__getattribute__``, ``__setattr__` and ``__delattr__`` are exempted from invariants.
* Slot wrappers are properly handled.
* Fixed representation of conditions with attributes in generator expressions
* Added reference to sphinx-contract

1.5.5
=====
* Added reference to ``pyicontract-lint`` in the README
* Made ``inv`` a class

1.5.4
=====
* Added support for class and static methods

1.5.3
=====
* Fixed different signatures of ``DBCMeta`` depending on Python version (<=3.5 and >3.5) due to differing signatures
  of ``__new__`` in ``abc.ABCMeta``

1.5.2
=====
* Removed dependency on ``meta`` package and replaced it with re-parsing the file containing the condition
  to represent the comprehensions

1.5.1
=====
* Quoted ellipsis in ``icontract._unwind_decorator_stack`` to comply with a bug
  in Python 3.5.2 (see https://github.com/python/typing/issues/259)

1.5.0
=====
* Added inheritance of contracts

1.4.1
=====
* Contract's constructor immediately returns if the contract is disabled.

1.4.0
=====
* Added invariants as `icontract.inv`

1.3.0
=====
* Added ``icontract.SLOW`` to mark contracts which are slow and should only be
  enabled during development
* Added ``enabled`` flag to toggle contracts for development, production __etc.__

1.2.3
=====
* Removed ``version.txt`` that caused problems with ``setup.py``

1.2.2
=====
* Fixed: the ``result`` is passed to the postcondition only if necessary

1.2.1
=====
* Fixed a bug that fetched the unexpected frame when conditions were stacked
* Fixed a bug that prevented default function values propagating to the condition function

1.2.0
=====
* Added reprlib.Repr as an additional parameter to customize representation

1.1.0
=====
* Fixed unit tests to set actual and expected arguments correctly
* Made ViolationError an AssertionError
* Added representation of values by re-executing the abstract syntax tree of the function

1.0.3
=====
* ``pre`` and ``post`` decorators use ``functools.update_wrapper`` to allow for doctests

1.0.2
=====
* Moved icontract.py to a module directory
* Added py.typed to comply with mypy

1.0.1
=====
* Fixed links in the README and setup.py

1.0.0
=====
* Initial version
