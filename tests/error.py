#!/usr/bin/env python3
"""Manipulate the error text."""
import re

_LOCATION_RE = re.compile(
    r"\AFile [^\n]+, line [0-9]+ in [a-zA-Z_0-9]+:\n(.*)\Z",
    flags=re.MULTILINE | re.DOTALL,
)


def wo_mandatory_location(text: str) -> str:
    r"""
    Strip the location of the contract from the text of the error.

    :param text: text of the error
    :return: text without the location prefix
    :raise AssertionError: if the location is not present in the text of the error.

    >>> wo_mandatory_location(text='File /some/file.py, line 233 in some_module:\nsome\ntext')
    'some\ntext'

    >>> wo_mandatory_location(text='a text')
    Traceback (most recent call last):
    ...
    AssertionError: Expected the text to match \AFile [^\n]+, line [0-9]+ in [a-zA-Z_0-9]+:\n(.*)\Z, but got: 'a text'
    """
    mtch = _LOCATION_RE.match(text)
    if not mtch:
        raise AssertionError(
            "Expected the text to match {}, but got: {!r}".format(
                _LOCATION_RE.pattern, text
            )
        )

    return mtch.group(1)
