import argparse
import pathlib
import platform
import subprocess
import sys
from typing import List

import cpuinfo

import icontract

"""Run benchmarks and, if specified, overwrite README."""


def benchmark_against_others(repo_root: pathlib.Path, overwrite: bool) -> None:
    """Run benchmars against other libraries and include them in the Readme."""
    script_rel_paths = [
        "benchmarks/against_others/compare_invariant.py",
        "benchmarks/against_others/compare_precondition.py",
        "benchmarks/against_others/compare_postcondition.py",
    ]

    if not overwrite:
        for i, script_rel_path in enumerate(script_rel_paths):
            if i > 0:
                print()
            subprocess.check_call([sys.executable, str(repo_root / script_rel_path)])
    else:
        out = ["The following scripts were run:\n\n"]
        for script_rel_path in script_rel_paths:
            out.append(
                "* `{0} <https://github.com/Parquery/icontract/tree/master/{0}>`_\n".format(
                    script_rel_path
                )
            )
        out.append("\n")

        out.append(
            (
                "The benchmarks were executed on {}.\nWe used Python {}, "
                "icontract {}, deal 4.23.3 and dpcontracts 0.6.0.\n\n"
            ).format(
                cpuinfo.get_cpu_info()["brand"],
                platform.python_version(),
                icontract.__version__,
            )
        )

        out.append("The following tables summarize the results.\n\n")
        stdouts = []  # type: List[str]

        for script_rel_path in script_rel_paths:
            stdout = subprocess.check_output(
                [sys.executable, str(repo_root / script_rel_path)]
            ).decode()
            stdouts.append(stdout)

            out.append(stdout)
            out.append("\n")

        readme_path = repo_root / "docs" / "source" / "benchmarks.rst"
        readme = readme_path.read_text(encoding="utf-8")
        marker_start = ".. Becnhmark report from benchmark.py starts."
        marker_end = ".. Benchmark report from benchmark.py ends."
        lines = readme.splitlines()

        try:
            index_start = lines.index(marker_start)
        except ValueError as exc:
            raise ValueError(
                "Could not find the marker for the benchmarks in the {}: {}".format(
                    readme_path, marker_start
                )
            ) from exc

        try:
            index_end = lines.index(marker_end)
        except ValueError as exc:
            raise ValueError(
                "Could not find the start marker for the benchmarks in the {}: {}".format(
                    readme_path, marker_end
                )
            ) from exc

        assert (
            index_start < index_end
        ), "Unexpected end marker before start marker for the benchmarks."

        lines = (
            lines[: index_start + 1]
            + ["\n"]
            + ("".join(out)).splitlines()
            + ["\n"]
            + lines[index_end:]
        )
        readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # This is necessary so that the benchmarks do not complain on a Windows machine if the console encoding has not
        # been properly set.
        sys.stdout.buffer.write(("\n\n".join(stdouts) + "\n").encode("utf-8"))


def main() -> int:
    """ "Execute main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        help="Overwrites the corresponding section in the docs.",
        action="store_true",
    )

    args = parser.parse_args()

    overwrite = bool(args.overwrite)

    print("Benchmarking against other libraries...")
    repo_root = pathlib.Path(__file__).parent
    benchmark_against_others(repo_root=repo_root, overwrite=overwrite)

    return 0


if __name__ == "__main__":
    sys.exit(main())
