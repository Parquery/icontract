#!/usr/bin/env python3
"""Manipulate the text of the violation error."""
import re


def lstrip_location(text: str) -> str:
    r"""
    Strip the location of the contract from the text of the violation error.

    :param text: text of the violation error
    :return: text without the location prefix

    >>> lstrip_location(text='File /some/file.py, line 233 in some_module:\\nsome text')
    'some text'
    """
    return re.sub(r'^File .+, line [0-9]+ in [a-zA-Z_0-9]+:\n', '', text, flags=re.MULTILINE)
