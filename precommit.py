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
    yapf_targets = ["tests", "icontract", "setup.py", "precommit.py", "benchmark.py", "benchmarks", "tests_with_others"]

    if sys.version_info >= (3, 6):
        yapf_targets.append('tests_3_6')

    if sys.version_info >= (3, 7):
        yapf_targets.append('tests_3_7')

    if sys.version_info >= (3, 8, 5):
        yapf_targets.append('tests_3_8')

    if overwrite:
        subprocess.check_call(
            ["yapf", "--in-place", "--style=style.yapf", "--recursive"] + yapf_targets, cwd=str(repo_root))
    else:
        subprocess.check_call(
            ["yapf", "--diff", "--style=style.yapf", "--recursive"] + yapf_targets, cwd=str(repo_root))

    if sys.version_info < (3, 8):
        print("Mypy since 1.5 dropped support for Python 3.7 and "
              "you are running Python {}, so skipping.".format(sys.version_info))
    else:
        print("Mypy'ing...")
        mypy_targets = ["icontract", "tests"]
        if sys.version_info >= (3, 6):
            mypy_targets.append('tests_3_6')

        if sys.version_info >= (3, 7):
            mypy_targets.append('tests_3_7')

        if sys.version_info >= (3, 8):
            mypy_targets.append('tests_3_8')
            mypy_targets.append('tests_with_others')

        subprocess.check_call(["mypy", "--strict"] + mypy_targets, cwd=str(repo_root))

    print("Pylint'ing...")
    pylint_targets = ['icontract', 'tests']

    if sys.version_info >= (3, 6):
        pylint_targets.append('tests_3_6')

    if sys.version_info >= (3, 7):
        pylint_targets.append('tests_3_7')

    if sys.version_info >= (3, 8):
        pylint_targets.append('tests_3_8')
        pylint_targets.append('tests_with_others')

    subprocess.check_call(["pylint", "--rcfile=pylint.rc"] + pylint_targets, cwd=str(repo_root))

    print("Pydocstyle'ing...")
    subprocess.check_call(["pydocstyle", "icontract"], cwd=str(repo_root))

    print("Testing...")
    env = os.environ.copy()
    env['ICONTRACT_SLOW'] = 'true'

    # yapf: disable
    subprocess.check_call(
        ["coverage", "run",
         "--source", "icontract",
         "-m", "unittest", "discover"],
        cwd=str(repo_root),
        env=env)
    # yapf: enable

    # yapf: disable
    subprocess.check_call(
        ["coverage", "run",
         "--source", "icontract",
         "-a", "-m", "tests_3_8.async.separately_test_concurrent"],
        cwd=str(repo_root),
        env=env)
    # yapf: enable

    subprocess.check_call(["coverage", "report"])

    print("Doctesting...")
    doc_files = ["README.rst"]
    for pth in (repo_root / "docs" / "source").glob("**/*.rst"):
        doc_files.append(str(pth.relative_to(repo_root)))
    subprocess.check_call([sys.executable, "-m", "doctest"] + doc_files)

    for pth in (repo_root / "icontract").glob("**/*.py"):
        subprocess.check_call([sys.executable, "-m", "doctest", str(pth)])

    print("Checking the restructured text of the readme...")
    subprocess.check_call([sys.executable, 'setup.py', 'check', '--restructuredtext', '--strict'])

    return 0


if __name__ == "__main__":
    sys.exit(main())
