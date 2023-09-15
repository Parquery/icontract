#!/usr/bin/env python3
"""Measure the start-up time of the modules with differing number of contracts."""
import os
import statistics
import subprocess
from typing import List


def main() -> None:
    """ "Execute the main routine."""
    modules = [
        "functions_100_with_no_contract",
        "functions_100_with_1_contract",
        "functions_100_with_5_contracts",
        "functions_100_with_10_contracts",
        "functions_100_with_1_disabled_contract",
        "functions_100_with_5_disabled_contracts",
        "functions_100_with_10_disabled_contracts",
        "classes_100_with_no_invariant",
        "classes_100_with_1_invariant",
        "classes_100_with_5_invariants",
        "classes_100_with_10_invariants",
        "classes_100_with_1_disabled_invariant",
        "classes_100_with_5_disabled_invariants",
        "classes_100_with_10_disabled_invariants",
    ]

    for a_module in modules:
        durations = []  # type: List[float]
        for i in range(0, 10):
            duration = float(
                subprocess.check_output(
                    ["./measure.py", "--module", a_module],
                    cwd=os.path.dirname(__file__),
                ).strip()
            )
            durations.append(duration)

        print(
            "Duration to import the module {} (in milliseconds): {:.2f} ± {:.2f}".format(
                a_module,
                statistics.mean(durations) * 10e3,
                statistics.stdev(durations) * 10e3,
            )
        )


if __name__ == "__main__":
    main()
