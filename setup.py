"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os

from setuptools import setup, find_packages

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()  # pylint: disable=invalid-name

setup(
    name='icontract',
    version='1.0.1',
    description='Provide design-by-contract with informative violation messages',
    long_description=long_description,
    url='https://github.com/Parquery/icontract',
    author='Marko Ristin',
    author_email='marko@parquery.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='design-by-contract precondition postcondition validation',
    packages=find_packages(exclude=['tests']),
    install_requires=['meta'],
    extras_require={
        'dev': ['mypy==0.570', 'pylint==1.8.2', 'yapf==0.20.2', 'tox>=3.0.0'],
        'test': ['tox>=3.0.0']
    },
    py_modules=['icontract'])
