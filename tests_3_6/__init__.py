"""
Test Python 3.6-specific features.

For example, one such feature is literal string interpolation.
"""

import sys

if sys.version_info < (3, 6):

    def load_tests(loader, suite, pattern):  # pylint: disable=unused-argument
        """Ignore all the tests for lower Python versions."""
        return suite
