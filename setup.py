"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os

from setuptools import setup, find_packages

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as fid:
    long_description = fid.read()  # pylint: disable=invalid-name

setup(
    name='icontract',
    version='2.3.1',
    description='Provide design-by-contract with informative violation messages',
    long_description=long_description,
    url='https://github.com/Parquery/icontract',
    author='Marko Ristin',
    author_email='marko@parquery.com',
    classifiers=[
        # yapf: disable
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
        # yapf: enable
    ],
    license='License :: OSI Approved :: MIT License',
    keywords='design-by-contract precondition postcondition validation',
    packages=find_packages(exclude=['tests']),
    install_requires=['asttokens>=2,<3'],
    extras_require={
        'dev': [
            # yapf: disable
            'mypy==0.750',
            'pylint==2.3.1',
            'yapf==0.20.2',
            'tox>=3.0.0',
            'pydocstyle>=2.1.1,<3',
            'coverage>=4.5.1,<5',
            'docutils>=0.14,<1',
            'pygments>=2.2.0,<3'
            # yapf: enable
        ],
    },
    py_modules=['icontract'],
    package_data={"icontract": ["py.typed"]})
