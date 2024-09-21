2.7.1
=====
* Fixed invariants leak between related classes (#297)

This is a critical bugfix patch version. We introduced a bug in
2.7.0 (#292) where invariants defined on derived classes leaked up
to parent classes. This bug is fixed in this version.

2.7.0
=====
* Allowed to enforce invariants on attribute setting (#292)

  Originally, we had enforced invariants only at calls to "normal"
  methods, and excluded ``__setattr__`` since it is usually too expensive
  to verify invariants whenever setting an attribute.

  However, there are use cases where the users prefer to incur to
  computational overhead for correctness. To that end, we introduced the
  feature to steer when the invariants are enforced (at method calls,
  on setting attributes, or in both situations).

2.6.6
=====
* Updated typeguard and deal to latest versions (#284)

  This change is needed so that distributions can successfully run
  the necessary tests with the development dependencies. Previously,
  the dependencies were outdated, and the old versions were already
  deprecated in distributions (notably, typegard and deal).

2.6.5
=====
* Added Python 3.11 to the list of supported Pythons (#280)
* Fixed deal dependency marker (#279)

  This patch is important as we silently broke ``setup.py``, which was
  tolerated by older versions of setuptools, but not any more by
  the newer ones. With this patch, icontract's ``setup.py`` is made
  valid again.

2.6.4
=====
* Restored Python 3.6 support (#274)

  The support for Python 3.6 has been dropped in #257 as GitHub removed
  its support in the CI pipeline. With this patch, we restored
  the support of Python 3.6. Notably, we had to add
  the package ``contextvars`` conditioned on Python 3.6.

2.6.3
=====
* Removed meta data files from setup.py (#262)
* Added support for python 3.11 (#260)
* Fixed in-progress set for async (#256)

2.6.2
=====
* Added wheels to releases (#251)
* Fixed mypy error on missing ``asttokens.ASTTokens`` (#252)

2.6.1
=====
*  Excluded all tests from package (#240)

2.6.0
=====
* Added support for Python 3.9 and 3.10 (#236)
* Added representation of subscripts (#237)

2.5.5
=====
* Fixed representation of numpy arrays (#232)
* Removed tag for Python 3.5 (#231)

2.5.4
=====
* Made type annotation for ``invariant`` decorator more specific (#227)

2.5.3
=====
* Fixed reporting all arguments on violation (#219)
* Propagated placeholders in re-computation (#218)
* Fixed docstring for ``collect_variable_lookup`` (#217)

2.5.2
=====
* Fixed handling of ``self`` when passed as kwarg (#213)
* Added reporting of all arguments on violation (#214)
* Added tracing of ``all`` on generator expressions (#215)

2.5.1
=====
* Allowed ``__new__`` to tighten pre-conditions (#211)
* Fixed recomputation of calls in generator expr (#210)
* Added better reporting on recompute failure (#207)

2.5.0
=====
* Encapsulated adding contracts for integrators (#202)
* Added support for error-as-instance (#201)
* Added support for coroutine (#197)
* Added support for async (#196)


2.4.1
=====
*  Removed automatic registration with Hypothesis and replaced it with a hook that
   downstream libraries such as icontract-hypothesis can use (#181)
* Refactored and added tests for integrators (#182)

2.4.0
=====
* Integrated with icontract-hypothesis (#179)
* Refactored for icontract-hypothesis (#178)
* Added special arguments `_ARGS` and `_KWARGS` (#176)
* Tested with typeguard (#175)
* Tested with `dataclasses.dataclass` (#173)
* Added invariants to namedtuple (#172)
* Added support for recomputation of f-strings (#170)
* Exempted `__new__` from invariant checks (#168)
* Added support for named expressions in contracts (#166)

2.3.7
=====
* Acted upon deprecation warning ins ``ast`` module when generating the
  violation error message.

2.3.6
=====
* Denormalized icontract_meta so that icontract can be installed on
  readthedocs.

2.3.5
=====
* Disabled invariant checks during the construction to avoid attribute errors
  on uninitialized attributes

2.3.4
=====
* Added ``icontract_meta`` to ``setup.py``
* Noted that contracts on ``*args`` and ``**kwargs`` are known issues

2.3.3
=====
* Fixed performance regression due to state

2.3.2
=====
* Fixed bug related to threading.local and mutables

2.3.1
=====
* Fixed race conditions in endless recursion blockers

2.3.0
=====
* Disabled recursion in the contracts
* Upgraded min version of asttokens to 2

2.2.0
=====
* Made compatible with Python 3.8

2.1.0
=====
* Made snapshot accept multiple arguments

2.0.7
=====
* Fixed mypy complaints in clients due to import aliases
* Made compliant to mypy 0.750 --strict

2.0.6
=====
* Added location to errors on calls with missing arguments

2.0.5
=====
* Improved error message on unexpected arguments in a call
* Distinguished between optional and mandatory arguments in conditions.
  Default argument values in conditions are accepted instead of raising a misleading "missing argument" exception.
* Added a boolyness check to detect if the condition evaluation can be negated.
  If the condition evaluation lacks boolyness, a more informative exception is now raised.
  For example, this is important for all the code operating with numpy arrays where boolyness is not given.
* Added contract location to ``require``, ``ensure`` and ``snapshot``.
  This feature had been erroneously omitted in 2.0.4.

2.0.4
=====
* Added contract location to the message of the violation error

2.0.3
=====
* Fixed representation of numpy conditions
* Updated pylint to 2.3.1

2.0.2
=====
* Specified ``require`` and ``ensure`` to use generics in order to fix typing erasure of the decorated functions

2.0.1
=====
* Fixed forgotten renamings in the Readme left from icontract 1.x

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
