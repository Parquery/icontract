#!/usr/bin/env python3

"""
Benchmark icontract against dpcontracts and no contracts.

The benchmark was supplied by: https://github.com/Parquery/icontract/issues/142
"""

import math
import timeit
from typing import List

import tabulate

import icontract
import dpcontracts


@icontract.require(lambda someArg: someArg > 0)
def function_with_icontract(someArg: int) -> float:
    return math.sqrt(someArg)


@dpcontracts.require("some dummy contract", lambda args: args.someArg > 0)
def function_with_dpcontracts(someArg: int) -> float:
    return math.sqrt(someArg)


def function_with_inline_contract(someArg: int) -> float:
    assert (someArg > 0)
    return math.sqrt(someArg)


def function_without_contracts(someArg: int) -> float:
    return math.sqrt(someArg)


def measure_functions() -> None:
    funcs = [
        'function_with_icontract',
        'function_with_dpcontracts',
        'function_with_inline_contract'
    ]

    durations = [0.0] * len(funcs)

    number = 10 * 1000

    for i, func in enumerate(funcs):
        duration = timeit.timeit(
            "{}(198.4)".format(func),
            setup="from __main__ import {}".format(func),
            number=number)
        durations[i] = duration

    table = []  # type: List[List[str]]

    for func, duration in zip(funcs, durations):
        # yapf: disable
        table.append([
            '`{}`'.format(func),
            '{:.2f} s'.format(duration),
            '{:.2f} μs'.format(duration * 1000 * 1000 / number),
            '{:.0f}%'.format(duration * 100 / durations[1])
        ])
        # yapf: enable

    # yapf: disable
    table_str = tabulate.tabulate(
        table,
        headers=['Case', 'Total time', 'Time per run', 'Relative time per run'],
        colalign=('left', 'right', 'right', 'right'),
        tablefmt='rst')
    # yapf: enable

    print(table_str)


if __name__ == "__main__":
    print("Benchmarking precondition:")
    print()
    measure_functions()
