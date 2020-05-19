#!/usr/bin/env python3

"""
Benchmark icontract against dpcontracts and no contracts.

The benchmark was supplied by: https://github.com/Parquery/icontract/issues/142
"""
from typing import List

import tabulate

import icontract
import dpcontracts


@icontract.invariant(lambda self: len(self.parts) > 0)
class ClassWithIcontract:
    def __init__(self, identifier: str) -> None:
        self.parts = identifier.split(".")


@dpcontracts.invariant("some dummy invariant", lambda self: len(self.parts) > 0)
class ClassWithDpcontracts:
    def __init__(self, identifier: str) -> None:
        self.parts = identifier.split(".")


class ClassWithInlineContract:
    def __init__(self, identifier: str) -> None:
        self.parts = identifier.split(".")
        assert len(self.parts) > 0


class ClassWithoutContracts:
    def __init__(self, identifier: str) -> None:
        self.parts = identifier.split(".")


if __name__ == "__main__":
    import timeit

    # dpcontracts change __name__ attribute of the class, so we can not use
    # ClassWithDpcontractsInvariant.__name__ for a more maintainable list.
    clses = [
        'ClassWithIcontract',
        'ClassWithDpcontracts',
        'ClassWithInlineContract',
        'ClassWithoutContracts'
    ]

    durations = [0.0] * len(clses)

    number = 1 * 1000 * 1000

    for i, cls in enumerate(clses):
        duration = timeit.timeit(
            "{}('X.Y')".format(cls),
            setup="from __main__ import {}".format(cls),
            number=number)
        durations[i] = duration

    print("Benchmarking invariant:\n")
    table = []  # type: List[List[str]]

    for cls, duration in zip(clses, durations):
        # yapf: disable
        table.append([
            '`{}`'.format(cls),
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
