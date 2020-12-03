"""Provide an invalid module for testing pyicontract-hypothesis."""

import icontract


@icontract.require(lambda x: x > 0)
def some_func(x: int) -> None:
    # pyicontract-hypothesis: disable-once
    pass
