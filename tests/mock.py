"""Provide mock structures used accross the tests."""
from typing import List, Union


class NumpyArray:
    """Represent a class that mocks a numpy.array and it's behavior on less-then operator."""

    def __init__(self, values: List[Union[int, bool]]) -> None:
        """Initialize with the given values."""
        self.values = values

    def __lt__(self, other: int) -> "NumpyArray":
        """Map the value to each comparison with ``other``."""
        return NumpyArray(values=[value < other for value in self.values])

    def __gt__(self, other: int) -> "NumpyArray":
        """Map the value to each comparison with ``other``."""
        return NumpyArray(values=[value > other for value in self.values])

    def __bool__(self) -> bool:
        """Raise a ValueError."""
        raise ValueError(
            "The truth value of an array with more than one element is ambiguous."
        )

    def all(self) -> bool:
        """Return True if all values are True."""
        return all(self.values)

    def __repr__(self) -> str:
        """Represent with the constructor."""
        return "NumpyArray({!r})".format(self.values)
