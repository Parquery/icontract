import math

import icontract


@icontract.require(lambda x: x >= 0, enabled=False)
def my_sqrt(x: float) -> float:
    return math.sqrt(x)
