"""Decorate functions with contracts."""

# pylint: disable=too-many-lines
# pylint: disable=too-many-instance-attributes

import icontract._represent
from icontract._decorators import pre, snapshot, post, inv
from icontract._globals import aRepr, SLOW
from icontract._metaclass import DBCMeta, DBC

from icontract._types import Contract as _Contract, Snapshot as _Snapshot
from icontract.errors import ViolationError
