"""Provide external functions to sample_module to test that imports are handled correctly."""


def square_greater_than_zero(x: int) -> bool:
    """Check nothing."""
    return x**2 > 0
