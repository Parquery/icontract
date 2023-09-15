#!/usr/bin/env python3
"""
Measure the import time of a module with contracts.

Execute this script multiple times to get a better estimate.
"""

import argparse
import time


def main() -> None:
    """ "Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module",
        help="name of the module to import",
        choices=[
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
        ],
        required=True,
    )
    args = parser.parse_args()

    a_module = str(args.module)
    if a_module == "functions_100_with_no_contract":
        start = time.time()
        import functions_100_with_no_contract

        print(time.time() - start)

    elif a_module == "functions_100_with_1_contract":
        start = time.time()
        import functions_100_with_1_contract

        print(time.time() - start)

    elif a_module == "functions_100_with_5_contracts":
        start = time.time()
        import functions_100_with_5_contracts

        print(time.time() - start)

    elif a_module == "functions_100_with_10_contracts":
        start = time.time()
        import functions_100_with_10_contracts

        print(time.time() - start)

    elif a_module == "functions_100_with_1_disabled_contract":
        start = time.time()
        import functions_100_with_1_disabled_contract

        print(time.time() - start)

    elif a_module == "functions_100_with_5_disabled_contracts":
        start = time.time()
        import functions_100_with_5_disabled_contracts

        print(time.time() - start)

    elif a_module == "functions_100_with_10_disabled_contracts":
        start = time.time()
        import functions_100_with_10_disabled_contracts

        print(time.time() - start)

    elif a_module == "classes_100_with_no_invariant":
        start = time.time()
        import classes_100_with_no_invariant

        print(time.time() - start)

    elif a_module == "classes_100_with_1_invariant":
        start = time.time()
        import classes_100_with_1_invariant

        print(time.time() - start)

    elif a_module == "classes_100_with_5_invariants":
        start = time.time()
        import classes_100_with_5_invariants

        print(time.time() - start)

    elif a_module == "classes_100_with_10_invariants":
        start = time.time()
        import classes_100_with_10_invariants

        print(time.time() - start)

    elif a_module == "classes_100_with_1_disabled_invariant":
        start = time.time()
        import classes_100_with_1_disabled_invariant

        print(time.time() - start)

    elif a_module == "classes_100_with_5_disabled_invariants":
        start = time.time()
        import classes_100_with_5_disabled_invariants

        print(time.time() - start)

    elif a_module == "classes_100_with_10_disabled_invariants":
        start = time.time()
        import classes_100_with_10_disabled_invariants

        print(time.time() - start)

    else:
        raise NotImplementedError("Unhandled module: {}".format(a_module))


if __name__ == "__main__":
    main()
