#!/usr/bin/env python3
"""Generate a module source code containing functions to benchmark the start-up time of the library with contracts."""

import argparse
import io
import os
import pathlib
import sys
import textwrap


def generate_functions(functions: int, contracts: int, disabled: bool) -> str:
    out = io.StringIO()
    out.write("#!/usr/bin/env python3\n")
    out.write("import icontract\n\n")

    for i in range(0, functions):
        if i > 0:
            out.write("\n")

        for j in range(0, contracts):
            if not disabled:
                out.write("@icontract.require(lambda x: x > {})\n".format(j))
            else:
                out.write(
                    "@icontract.require(lambda x: x > {}, enabled=False)\n".format(j)
                )

        out.write("def some_func{}(x: int) -> None:\n    pass\n".format(i))

    return out.getvalue()


def generate_classes(classes: int, invariants: int, disabled: bool) -> str:
    out = io.StringIO()
    out.write("#!/usr/bin/env python3\n")
    out.write("import icontract\n\n")

    for i in range(0, classes):
        if i > 0:
            out.write("\n")

        for j in range(0, invariants):
            if not disabled:
                out.write("@icontract.invariant(lambda self: self.x > {})\n".format(j))
            else:
                out.write(
                    "@icontract.invariant(lambda self: self.x > {}, enabled=False)\n".format(
                        j
                    )
                )

        out.write(
            textwrap.dedent(
                """\
            class SomeClass{}:
                def __init__(self) -> None:
                    self.x = 100
                    
                def some_func(self) -> None:
                    pass
            """.format(
                    i
                )
            )
        )

    return out.getvalue()


def main() -> None:
    """ "Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir", help="output directory", default=os.path.dirname(__file__)
    )
    args = parser.parse_args()

    outdir = pathlib.Path(args.outdir)
    if not outdir.exists():
        raise FileNotFoundError("Output directory is missing: {}".format(outdir))

    for contracts in [0, 1, 5, 10]:
        if contracts == 0:
            pth = outdir / "functions_100_with_no_contract.py"
        elif contracts == 1:
            pth = outdir / "functions_100_with_1_contract.py"
        else:
            pth = outdir / "functions_100_with_{}_contracts.py".format(contracts)

        text = generate_functions(functions=100, contracts=contracts, disabled=False)
        pth.write_text(text)

    for contracts in [1, 5, 10]:
        if contracts == 1:
            pth = outdir / "functions_100_with_1_disabled_contract.py"
        else:
            pth = outdir / "functions_100_with_{}_disabled_contracts.py".format(
                contracts
            )

        text = generate_functions(functions=100, contracts=contracts, disabled=True)
        pth.write_text(text)

    for invariants in [0, 1, 5, 10]:
        if invariants == 0:
            pth = outdir / "classes_100_with_no_invariant.py"
        elif invariants == 1:
            pth = outdir / "classes_100_with_1_invariant.py"
        else:
            pth = outdir / "classes_100_with_{}_invariants.py".format(invariants)

        text = generate_classes(classes=100, invariants=invariants, disabled=False)
        pth.write_text(text)

    for invariants in [1, 5, 10]:
        if invariants == 1:
            pth = outdir / "classes_100_with_1_disabled_invariant.py"
        else:
            pth = outdir / "classes_100_with_{}_disabled_invariants.py".format(
                invariants
            )

        text = generate_classes(classes=100, invariants=invariants, disabled=True)
        pth.write_text(text)


if __name__ == "__main__":
    main()
