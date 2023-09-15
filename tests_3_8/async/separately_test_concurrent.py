# pylint: disable=missing-docstring
# pylint: disable=unnecessary-lambda
# pylint: disable=disallowed-name
import asyncio
import random

import icontract


async def main() -> None:
    # NOTE (mristin, 2023-01-26):
    # This is a regression test for #255.
    #
    # We have to run it as a separate script since unittest.IsolatedAsyncioTestCase
    # messes up the contextvars in such a way that they are shared among the coroutines.

    async def is_between_0_and_100(value: int) -> bool:
        sleep_time = random.randint(1, 3)
        await asyncio.sleep(sleep_time)
        return 0 <= value < 100

    @icontract.require(
        lambda bar: is_between_0_and_100(bar),
        error=lambda bar: icontract.ViolationError(
            f"bar between 0 and 100, but got {bar}"
        ),
    )
    async def is_less_than_42(bar: int) -> bool:
        sleep_time = random.randint(1, 5)
        await asyncio.sleep(sleep_time)
        return bar < 42

    results_or_errors = await asyncio.gather(
        is_less_than_42(0),  # Should return True
        is_less_than_42(101),  # Should violate the pre-condition
        is_less_than_42(-1),  # Should violate the pre-condition
        return_exceptions=True,
    )

    assert len(results_or_errors) == 3
    assert results_or_errors[0]

    assert isinstance(results_or_errors[1], icontract.ViolationError)
    assert "bar between 0 and 100, but got 101" == str(results_or_errors[1])

    assert isinstance(results_or_errors[2], icontract.ViolationError)
    assert "bar between 0 and 100, but got -1" == str(results_or_errors[2])


if __name__ == "__main__":
    asyncio.run(main())
