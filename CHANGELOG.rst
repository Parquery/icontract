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
