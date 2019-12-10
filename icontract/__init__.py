"""Decorate functions with contracts."""

# pylint: disable=invalid-name
# pylint: disable=protected-access
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
