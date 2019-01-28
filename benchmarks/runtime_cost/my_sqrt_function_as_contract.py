import math


def check_non_negative(x: float) -> None:
    assert x >= 0


def my_sqrt(x: float) -> float:
    check_non_negative(x=x)
    return math.sqrt(x)
