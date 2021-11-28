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

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as fid:
    long_description = fid.read()  # pylint: disable=invalid-name

with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as fid:
    install_requires = [line for line in fid.read().splitlines() if line.strip()]

# Please keep the meta information in sync with icontract/__init__.py.
#
# (mristin, 2020-10-09) We had to denormalize icontract_meta module (which
# used to be referenced from setup.py and this file) since readthedocs had
# problems with installing icontract through pip on their servers with
# imports in setup.py.
setup(
    name='icontract',
    # Don't forget to update the version in __init__.py and CHANGELOG.rst!
    version='2.6.0',
    description='Provide design-by-contract with informative violation messages.',
    long_description=long_description,
    url='https://github.com/Parquery/icontract',
    author='Marko Ristin',
    author_email='marko@ristin.ch',
    classifiers=[
        # yapf: disable
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
        # yapf: enable
    ],
    license='License :: OSI Approved :: MIT License',
    keywords='design-by-contract precondition postcondition validation',
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    extras_require={
        'dev': [
            'mypy==0.910', 'pylint==2.9.6', 'yapf==0.20.2', 'tox>=3.0.0', 'pydocstyle>=6.1.1,<7', 'coverage>=4.5.1,<5',
            'docutils>=0.14,<1', 'pygments>=2.2.0,<3', 'dpcontracts==0.6.0', 'tabulate>=0.8.7,<1',
            'py-cpuinfo>=5.0.0,<6', 'typeguard>=2,<3', 'astor==0.8.1', 'numpy>=1,<2'
        ] + (['deal==4.1.0'] if sys.version_info >= (3, 8) else []) + (['asyncstdlib==3.9.1']
                                                                       if sys.version_info >= (3, 8) else []),
    },
    py_modules=['icontract'],
    package_data={"icontract": ["py.typed"]},
    data_files=[(".", ["LICENSE.txt", "README.rst", "requirements.txt"])])
