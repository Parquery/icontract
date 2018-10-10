#!/usr/bin/env python3
"""Runs precommit checks on the repository."""
import argparse
import os
import pathlib
import subprocess
import sys


def main() -> int:
    """"
    Main routine
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        help="Overwrites the unformatted source files with the well-formatted code in place. "
        "If not set, an exception is raised if any of the files do not conform to the style guide.",
        action='store_true')

    args = parser.parse_args()

    overwrite = bool(args.overwrite)

    repo_root = pathlib.Path(__file__).parent

    print("YAPF'ing...")
    if overwrite:
        subprocess.check_call(
            [
                "yapf", "--in-place", "--style=style.yapf", "--recursive", "tests", "icontract", "setup.py",
                "precommit.py"
            ],
            cwd=repo_root.as_posix())
    else:
        subprocess.check_call(
            ["yapf", "--diff", "--style=style.yapf", "--recursive", "tests", "icontract", "setup.py", "precommit.py"],
            cwd=repo_root.as_posix())

    print("Mypy'ing...")
    subprocess.check_call(["mypy", "icontract", "tests"], cwd=repo_root.as_posix())

    print("Pylint'ing...")
    subprocess.check_call(["pylint", "--rcfile=pylint.rc", "tests", "icontract"], cwd=repo_root.as_posix())

    print("Pydocstyle'ing...")
    subprocess.check_call(["pydocstyle", "icontract"], cwd=repo_root.as_posix())

    print("Testing...")
    env = os.environ.copy()
    env['ICONTRACT_SLOW'] = 'true'

    # yapf: disable
    subprocess.check_call(
        ["coverage", "run",
         "--source", "icontract",
         "-m", "unittest", "discover", "tests"],
        cwd=repo_root.as_posix(),
        env=env)
    # yapf: enable

    subprocess.check_call(["coverage", "report"])

    print("Doctesting...")
    subprocess.check_call(["python3", "-m", "doctest", "README.rst"])
    for pth in (repo_root / "icontract").glob("**/*.py"):
        subprocess.check_call(["python3", "-m", "doctest", pth.as_posix()])

    return 0


if __name__ == "__main__":
    sys.exit(main())
