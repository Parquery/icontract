"""
Test Python 3.-specific features.

For example, one such feature is decorator ``dataclasses.dataclass``.
"""

import sys

if sys.version_info < (3, 7):

    def load_tests(loader, suite, pattern):  # pylint: disable=unused-argument
        """Ignore all the tests for lower Python versions."""
        return suite
