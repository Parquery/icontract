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
