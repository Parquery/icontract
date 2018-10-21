"""Define global variables used among the modules."""

import os
import reprlib

# Default representation instance.
#
# The limits are set way higher than reprlib.aRepr since the default reprlib limits are not suitable for
# the production systems.
aRepr = reprlib.Repr()  # pylint: disable=invalid-name
aRepr.maxdict = 50
aRepr.maxlist = 50
aRepr.maxtuple = 50
aRepr.maxset = 50
aRepr.maxfrozenset = 50
aRepr.maxdeque = 50
aRepr.maxarray = 50
aRepr.maxstring = 256
aRepr.maxother = 256

# SLOW provides a unified environment variable (ICONTRACT_SLOW) to enable the contracts which are slow to execute.
#
# Use SLOW to mark any contracts that are even too slow to make it to the normal (__debug__) execution of
# the interpreted program.
#
# Contracts marked with SLOW are also disabled if the interpreter is run in optimized mode (``-O`` or ``-OO``).
SLOW = __debug__ and os.environ.get("ICONTRACT_SLOW", "") != ""
