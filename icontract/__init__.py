"""Decorate functions with contracts."""

# Please keep the meta information in sync with setup.py.
#
# (mristin, 2020-10-09) We had to denormalize icontract_meta module (which
# used to be referenced from setup.py and this file) since readthedocs had
# problems with installing icontract through pip on their servers with
# imports in setup.py.

# Don't forget to update the version in __init__.py and CHANGELOG.rst!
__version__ = "2.7.1"
__author__ = "Marko Ristin"
__copyright__ = "Copyright 2019 Parquery AG"
__license__ = "MIT"
__status__ = "Production"

# pylint: disable=invalid-name
# pylint: disable=wrong-import-position

# We need to explicitly assign the aliases instead of using
# ``from ... import ... as ...`` statements since mypy complains
# that the module icontract lacks these imports.
# See also:
# https://stackoverflow.com/questions/44344327/cant-make-mypy-work-with-init-py-aliases

import icontract._decorators

require = icontract._decorators.require
snapshot = icontract._decorators.snapshot
ensure = icontract._decorators.ensure
invariant = icontract._decorators.invariant

import icontract._globals

aRepr = icontract._globals.aRepr
SLOW = icontract._globals.SLOW

import icontract._metaclass

DBCMeta = icontract._metaclass.DBCMeta
DBC = icontract._metaclass.DBC

import icontract._types

_Contract = icontract._types.Contract
_Snapshot = icontract._types.Snapshot

import icontract.errors

ViolationError = icontract.errors.ViolationError

InvariantCheckEvent = icontract._types.InvariantCheckEvent
