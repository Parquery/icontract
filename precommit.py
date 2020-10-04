#!/usr/bin/env python3
"""Runs precommit checks on the repository."""
import argparse
import os
import pathlib
import subprocess
import sys


def main() -> int:
    """"Execute main routine."""
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
    yapf_targets = ["tests", "icontract", "setup.py", "precommit.py", "benchmark.py", "benchmarks"]
    if overwrite:
        subprocess.check_call(
            ["yapf", "--in-place", "--style=style.yapf", "--recursive"] + yapf_targets, cwd=str(repo_root))
    else:
        subprocess.check_call(
            ["yapf", "--diff", "--style=style.yapf", "--recursive"] + yapf_targets, cwd=str(repo_root))

    print("Mypy'ing...")
    subprocess.check_call(["mypy", "--strict", "icontract", "tests"], cwd=str(repo_root))

    print("Pylint'ing...")
    subprocess.check_call(["pylint", "--rcfile=pylint.rc", "tests", "icontract"], cwd=str(repo_root))

    print("Pydocstyle'ing...")
    subprocess.check_call(["pydocstyle", "icontract"], cwd=str(repo_root))

    print("Testing...")
    env = os.environ.copy()
    env['ICONTRACT_SLOW'] = 'true'

    # yapf: disable
    subprocess.check_call(
        ["coverage", "run",
         "--source", "icontract",
         "-m", "unittest", "discover", "tests"],
        cwd=str(repo_root),
        env=env)
    # yapf: enable

    subprocess.check_call(["coverage", "report"])

    print("Doctesting...")
    subprocess.check_call([sys.executable, "-m", "doctest", "README.rst"])
    for pth in (repo_root / "icontract").glob("**/*.py"):
        subprocess.check_call([sys.executable, "-m", "doctest", str(pth)])

    print("Checking the restructured text of the readme...")
    subprocess.check_call([sys.executable, 'setup.py', 'check', '--restructuredtext', '--strict'])

    return 0


if __name__ == "__main__":
    sys.exit(main())
