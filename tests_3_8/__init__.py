"""
Test Python 3.8-specific features.

For example, one such feature is walrus operator used in named expressions.
We have to exclude these tests running on prior versions of Python since the syntax would be considered
invalid.
"""

import sys

if sys.version_info < (3, 8):

    def load_tests(loader, suite, pattern):  # pylint: disable=unused-argument
        """Ignore all the tests for lower Python versions."""
        return suite
