#!/usr/bin/env python3
"""Runs precommit checks on the repository."""
import argparse
import os
import pathlib
import subprocess
import sys


def main() -> int:
    """ "Execute main routine."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        help="Overwrites the unformatted source files with the well-formatted code in place. "
        "If not set, an exception is raised if any of the files do not conform to the style guide.",
        action="store_true",
    )

    args = parser.parse_args()

    overwrite = bool(args.overwrite)

    repo_root = pathlib.Path(__file__).parent

    if sys.version_info < (3, 8):
        print(
            "Our formatter, black, supports only Python versions from 3.8 on. "
            "However, you are running Python {}. Hence, the reformatting step "
            "will be skipped.".format(sys.version_info)
        )
    else:
        print("Reformatting...")

        reformat_targets = [
            "tests",
            "icontract",
            "setup.py",
            "precommit.py",
            "benchmark.py",
            "benchmarks",
            "tests_with_others",
        ]

        if sys.version_info >= (3, 6):
            reformat_targets.append("tests_3_6")

        if sys.version_info >= (3, 7):
            reformat_targets.append("tests_3_7")

        if sys.version_info >= (3, 8, 5):
            reformat_targets.append("tests_3_8")

        if overwrite:
            subprocess.check_call(
                [sys.executable, "-m", "black"] + reformat_targets, cwd=str(repo_root)
            )
        else:
            subprocess.check_call(
                [sys.executable, "-m", "black"] + reformat_targets, cwd=str(repo_root)
            )

    if sys.version_info < (3, 8):
        print(
            "Mypy since 1.5 dropped support for Python 3.7 and "
            "you are running Python {}, so skipping.".format(sys.version_info)
        )
    else:
        print("Mypy'ing...")
        mypy_targets = ["icontract", "tests"]
        if sys.version_info >= (3, 6):
            mypy_targets.append("tests_3_6")

        if sys.version_info >= (3, 7):
            mypy_targets.append("tests_3_7")

        if sys.version_info >= (3, 8):
            mypy_targets.append("tests_3_8")
            mypy_targets.append("tests_with_others")

        subprocess.check_call(["mypy", "--strict"] + mypy_targets, cwd=str(repo_root))

    if sys.version_info < (3, 7):
        print(
            "Pylint dropped support for Python 3.6 and "
            "you are running Python {}, so skipping.".format(sys.version_info)
        )
    else:
        print("Pylint'ing...")
        pylint_targets = ["icontract", "tests"]

        if sys.version_info >= (3, 6):
            pylint_targets.append("tests_3_6")

        if sys.version_info >= (3, 7):
            pylint_targets.append("tests_3_7")

        if sys.version_info >= (3, 8):
            pylint_targets.append("tests_3_8")
            pylint_targets.append("tests_with_others")

        subprocess.check_call(
            ["pylint", "--rcfile=pylint.rc"] + pylint_targets, cwd=str(repo_root)
        )

    print("Pydocstyle'ing...")
    subprocess.check_call(["pydocstyle", "icontract"], cwd=str(repo_root))

    print("Testing...")
    env = os.environ.copy()
    env["ICONTRACT_SLOW"] = "true"

    # fmt: off
    subprocess.check_call(
        ["coverage", "run",
         "--source", "icontract",
         "-m", "unittest", "discover"],
        cwd=str(repo_root),
        env=env)
    # fmt: on

    if sys.version_info >= (3, 8):
        # fmt: off
        subprocess.check_call(
            ["coverage", "run",
             "--source", "icontract",
             "-a", "-m", "tests_3_8.async.separately_test_concurrent"],
            cwd=str(repo_root),
            env=env)
        # fmt: on

    subprocess.check_call(["coverage", "report"])

    if (3, 8) <= sys.version_info < (3, 9):
        print("Doctesting...")
        doc_files = ["README.rst"]
        for pth in (repo_root / "docs" / "source").glob("**/*.rst"):
            doc_files.append(str(pth.relative_to(repo_root)))
        subprocess.check_call([sys.executable, "-m", "doctest"] + doc_files)

        for pth in (repo_root / "icontract").glob("**/*.py"):
            subprocess.check_call([sys.executable, "-m", "doctest", str(pth)])
    else:
        print(
            "We pin the doctests at Python 3.8 as the output of the exception "
            "traceback changes between the Python versions. You are running Python "
            "{}, so we will not run the doctests.".format(sys.version_info)
        )

    print("Checking the restructured text of the readme...")
    subprocess.check_call(
        [sys.executable, "setup.py", "check", "--restructuredtext", "--strict"]
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
