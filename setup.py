"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os
import sys

from setuptools import setup, find_packages

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, "README.rst"), encoding="utf-8") as fid:
    long_description = fid.read()  # pylint: disable=invalid-name

# Please keep the meta information in sync with icontract/__init__.py.
#
# (mristin, 2020-10-09) We had to denormalize icontract_meta module (which
# used to be referenced from setup.py and this file) since readthedocs had
# problems with installing icontract through pip on their servers with
# imports in setup.py.
setup(
    name="icontract",
    # Don't forget to update the version in __init__.py and CHANGELOG.rst!
    version="2.7.1",
    description="Provide design-by-contract with informative violation messages.",
    long_description=long_description,
    url="https://github.com/Parquery/icontract",
    author="Marko Ristin",
    author_email="marko@ristin.ch",
    classifiers=[
        # fmt: off
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        # fmt: on
    ],
    license="License :: OSI Approved :: MIT License",
    keywords="design-by-contract precondition postcondition validation",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "asttokens>=2,<3",
        'contextvars;python_version=="3.6"',
        "typing_extensions",
    ],
    extras_require={
        "dev": [
            'pylint==2.17.5;python_version>="3.7"',
            "tox>=3.0.0",
            "pydocstyle>=6.3.0,<7",
            "coverage>=6.5.0,<7",
            "docutils>=0.14,<1",
            "pygments>=2.2.0,<3",
            "dpcontracts==0.6.0",
            "tabulate>=0.8.7,<1",
            "py-cpuinfo>=5.0.0,<6",
            "typeguard>=2,<5",
            "astor==0.8.1",
            "numpy>=1,<2",
            'mypy==1.5.1;python_version>="3.8"',
            'black==23.9.1;python_version>="3.8"',
            'deal>=4,<5;python_version>="3.8"',
            'asyncstdlib==3.9.1;python_version>="3.8"',
        ]
    },
    py_modules=["icontract"],
    package_data={"icontract": ["py.typed"]},
)
