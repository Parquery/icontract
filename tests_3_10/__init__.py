"""
Test Python 3.10-specific features.

For example, one such feature is typing.ParamSpec.

We have to exclude these tests running on prior versions of Python since they would fail due to missing features.
"""

import sys

if sys.version_info < (3, 10):

    def load_tests(loader, suite, pattern):  # pylint: disable=unused-argument
        """Ignore all the tests for lower Python versions."""
        return suite
